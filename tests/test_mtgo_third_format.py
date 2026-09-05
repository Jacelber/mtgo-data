"""Third-format admission oracles use only fixed synthetic sources and states."""

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from build_pages_artifact import PublicationError as PagesError, publication_paths
from mtgmeta.catalog import build_catalog, write_catalog
from mtgmeta.classification_reports_cli import generate_reports
from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo import completeness, matchup, metadata, stats, top8
from mtgmeta.mtgo.publication import (
    PublicationError, _digest, require_private_output, resolve_scope,
)
from validate_production_candidate import (
    CandidateValidationError, _configured_formats,
)
from validate_schemas import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
THIRD = "synthetic-third"
NOW = "2025-01-27T00:00:00+00:00"
TODAY = date(2025, 1, 27)
CAPABILITIES = ["classification", "event_statistics", "range_statistics",
                "matchup_statistics", "weekly_top8", "completeness_reporting",
                "landing_generation", "metadata_generation", "catalog_generation"]
POLICY = {
    "site_files": ["index.html", "stats/catalog.json"],
    "site_directories": ["stats", "reports", "data"],
    "excluded_patterns": ["stats/*/mtgo/landing/review/*"],
}


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def definition(fmt, *, public=True, enabled=True):
    return {"id": fmt, "display_name": fmt.title(),
            "state": "executable" if enabled else "planned", "public": public,
            "mtgo": {"enabled": enabled, "event_collection_enabled": True,
                     "capabilities": CAPABILITIES.copy() if enabled else [],
                     "paths": {"events": f"data/{fmt}",
                               "matches": f"data/{fmt}/mtgo/matches",
                               "rules": f"my_archetypes/{fmt}.yaml",
                               "statistics": f"stats/{fmt}/mtgo",
                               "reports": f"reports/{fmt}/mtgo"}}}


def repository(root, state):
    entries = [definition("standard"), definition("modern"),
               definition(THIRD, public=state.endswith("public"), enabled=state != "planned")]
    write(root, "configs/formats.yaml", {"schema_version": "1.3.0", "formats": entries})
    write(root, "configs/pages_publication.json", POLICY)
    write(root, "index.html", "synthetic entry")
    # These are catalog-boundary fixtures, not claims of Landing content acceptance.
    for entry in entries:
        fmt = entry["id"]
        for suffix in ("meta.json", "matchup_index.json", "top8/index.json", "landing/current.json"):
            if state == "incomplete_public" and fmt == THIRD and suffix == "landing/current.json":
                continue
            write(root, f"stats/{fmt}/mtgo/{suffix}", {})
        write(root, f"reports/{fmt}/mtgo/index.json", {})
    for event_id, day in (("100", "2025-01-06"), ("200", "2025-01-13")):
        write(root, f"data/{THIRD}/{event_id}.json", {
            "event_id": event_id, "format": "CSYNTHETIC-THIRD", "description": "Synthetic Challenge",
            "starttime": day + "T12:00:00Z", "player_count": 8,
            "players": [{"player": f"Player {rank}", "loginid": str(rank), "final_rank": rank,
                         "swiss_score": 9, "main_deck": [{"name": "Signal Card", "qty": 60}],
                         "sideboard": [{"name": "Side Card", "qty": 15}]} for rank in range(1, 9)]})
    write(root, f"my_archetypes/{THIRD}.yaml", {
        "schema_version": "1.0.0", "format": THIRD,
        "archetypes": [{"id": "alpha", "name": "Alpha", "priority": 100,
                        "rules": [{"id": "alpha-rule", "priority": 100,
                                   "conditions": {"all": [{"card": "Signal Card", "zone": "main"}]}}]}]})
    if state.endswith("public"):
        source = f"data/{THIRD}/100.json"
        write(root, "configs/mtgo_weekly_review_completions.yaml", {
            "schema_version": "1.2.0", "records": [],
            "data_admissions": {"schema_version": "1.0.0", "formats": {THIRD: {
                "initial": {"kind": "grandfathered_existing_public_scope", "week": "2025-W02",
                            "event_ids": ["100"], "evidence": "Synthetic pre-existing public scope only",
                            "source_manifest_digest": _digest([{"event_id": "100", "source_file": source,
                                "sha256": sha256((root / source).read_bytes()).hexdigest()}])},
                "weekly_acceptances": []}}}})
    return entries


@pytest.mark.parametrize("state", ["planned", "private_executable", "incomplete_public", "complete_public"])
def test_four_states_share_execution_catalog_and_direct_path_boundary(tmp_path, state):
    repository(tmp_path, state)
    if state == "incomplete_public":
        with pytest.raises(CandidateValidationError, match="missing required MTGO products"):
            _configured_formats(tmp_path)
        with pytest.raises(ValueError, match="missing required MTGO products"):
            build_catalog(tmp_path)
        write(tmp_path, "stats/catalog.json", {"formats": []})
        with pytest.raises(PagesError, match="missing required MTGO products"):
            publication_paths(tmp_path, POLICY)
        return
    collection, products = _configured_formats(tmp_path)
    assert THIRD in collection
    assert (THIRD in products) == state.endswith("public")
    if state == "planned":
        with pytest.raises(DisabledFormatError):
            load_mtgo_context(tmp_path, THIRD, "event_statistics")
    else:
        assert load_mtgo_context(tmp_path, THIRD, "event_statistics").definition.id == THIRD
    write_catalog(tmp_path, generated_at=NOW)
    paths = publication_paths(tmp_path, POLICY)
    third = build_catalog(tmp_path)["formats"][2]
    available = state == "complete_public"
    assert bool(third["default_product_id"]) == available
    assert all(item["available"] == available for item in third["products"] if item["id"].startswith("mtgo-"))
    assert (f"stats/{THIRD}/mtgo/meta.json" in paths) == available
    assert (f"reports/{THIRD}/mtgo/index.json" in paths) == available
    assert f"data/{THIRD}/100.json" in paths  # Existing public archive policy is unchanged.
    if not available:
        assert not any(path.startswith((f"stats/{THIRD}/", f"reports/{THIRD}/")) for path in paths)
        require_private_output(tmp_path, tmp_path / f"reports/{THIRD}/mtgo/private.json")
        with pytest.raises(PublicationError, match="Pages"):
            require_private_output(tmp_path, tmp_path / "reports/standard/mtgo/private.json")


@pytest.mark.parametrize("state,expected_events,expected_week", [
    ("private_executable", 2, "2025-01-13"), ("complete_public", 1, "2025-01-06"),
])
def test_shared_producers_and_dynamic_manifest_use_the_correct_population(tmp_path, state, expected_events, expected_week):
    repository(tmp_path, state)
    (tmp_path / f"stats/{THIRD}/mtgo/top8/index.json").unlink()
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    outputs = stats.build_all_stats(tmp_path, THIRD, today=TODAY, generated_at=NOW)
    matchup_outputs, _ = matchup.build_all_matchups(tmp_path, THIRD, today=TODAY, generated_at=NOW)
    outputs.update(matchup_outputs)
    outputs.update(completeness.build_all_completeness(tmp_path, THIRD, today=TODAY, generated_at=NOW))
    outputs.update(top8.build_all_top8(tmp_path, THIRD, today=TODAY, generated_at=NOW))
    reports = generate_reports(tmp_path, THIRD)
    metadata.generate_hierarchy_catalog(tmp_path, THIRD, rules_updated=NOW)
    metadata.generate_metadata(tmp_path, THIRD, rules_updated=NOW, data_updated=NOW)
    stats_root = tmp_path / f"stats/{THIRD}/mtgo"
    index = json.loads((stats_root / "index.json").read_text())
    assert index["latest_complete_week"] == expected_week
    meta = json.loads((stats_root / "meta.json").read_text())
    assert meta["matchup_coverage"]["official_events"] == expected_events
    assert all(doc["event_count"] == expected_events for doc in reports.values())
    if state == "private_executable":
        assert "publication" not in meta
        assert all(doc["scope"] == "all_available_events" for doc in reports.values())
        with pytest.raises(PublicationError, match="non-public"):
            resolve_scope(tmp_path, THIRD)
    else:
        assert meta["publication"]["week"] == "2025-W02"
        assert all(doc["scope"] == "all_admitted_events" for doc in reports.values())
        assert resolve_scope(tmp_path, THIRD).pending_event_ids == frozenset({"200"})
    selected = {path.relative_to(tmp_path).as_posix()
                for prefix in (f"stats/{THIRD}/mtgo", f"reports/{THIRD}/mtgo")
                for path in (tmp_path / prefix).rglob("*.json") if "/landing/" not in path.as_posix()}
    checked, failures = validate_manifest(tmp_path, tmp_path / "schemas/manifest.json", selected)
    assert checked == len(selected)
    assert failures == []


def test_stale_catalog_and_incomplete_public_capabilities_fail_closed(tmp_path):
    entries = repository(tmp_path, "private_executable")
    write_catalog(tmp_path, generated_at=NOW)
    catalog = json.loads((tmp_path / "stats/catalog.json").read_text())
    catalog["formats"][2]["products"][0].update(available=True, path=f"stats/{THIRD}/mtgo/meta.json")
    write(tmp_path, "stats/catalog.json", catalog)
    with pytest.raises(PagesError, match="current format admission"):
        publication_paths(tmp_path, POLICY)
    entries[2]["public"] = True
    entries[2]["mtgo"]["capabilities"].remove("landing_generation")
    write(tmp_path, "configs/formats.yaml", {"schema_version": "1.3.0", "formats": entries})
    with pytest.raises(CandidateValidationError, match="incomplete public"):
        _configured_formats(tmp_path)


def test_dynamic_manifest_rejects_unregistered_or_mismatched_output(tmp_path):
    entries = repository(tmp_path, "private_executable")
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    path = f"stats/{THIRD}/mtgo/meta.json"
    value = {"schema_version": "1.0.0", "format": THIRD, "source": "mtgo",
             "rules_updated": NOW, "data_updated": NOW}
    write(tmp_path, path, value)
    value["format"] = "standard"
    write(tmp_path, path, value)
    _, failures = validate_manifest(tmp_path, tmp_path / "schemas/manifest.json", {path})
    assert any("registered output path" in failure.message for failure in failures)
    entries.pop()
    write(tmp_path, "configs/formats.yaml", {"schema_version": "1.3.0", "formats": entries})
    _, failures = validate_manifest(tmp_path, tmp_path / "schemas/manifest.json", {path})
    assert any("unknown format" in failure.message for failure in failures)


@pytest.mark.parametrize("producer", [stats.build_all_stats, matchup.build_all_matchups,
    completeness.build_all_completeness, top8.build_all_top8, metadata.generate_metadata,
    metadata.generate_hierarchy_catalog, generate_reports])
def test_private_generation_cannot_target_a_public_tree(tmp_path, producer):
    repository(tmp_path, "private_executable")
    destination = tmp_path / "stats/standard/mtgo/private-output"
    with pytest.raises(PublicationError, match="Pages"):
        producer(tmp_path, THIRD, output_directory=destination)
    assert not destination.exists()
