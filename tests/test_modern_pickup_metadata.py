"""P6-07 Modern Pickup, metadata, and hierarchy catalog contracts."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from mtgmeta.mtgo import pickup
import validate_schemas


REFERENCE_TODAY = date(2026, 7, 23)
MODERN_STATS = ROOT / "stats" / "modern" / "mtgo"


def test_modern_hierarchy_catalog_is_complete_stable_and_matchup_aligned(tmp_path):
    destination = pickup.generate_hierarchy_catalog(
        ROOT,
        "modern",
        rules_updated="2026-07-23T00:00:00+09:00",
        output_directory=tmp_path,
    )
    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["format"] == "modern"
    assert document["summary"] == {
        "parents": 55,
        "leaves": 92,
        "expandable_parents": 17,
    }
    assert all(
        parent["expandable"] == (len(parent["subtype_ids"]) >= 2)
        for parent in document["parents"]
    )
    matchup = json.loads((MODERN_STATS / "matchup_36w.json").read_text(encoding="utf-8"))
    assert document["parents"] == matchup["hierarchy"]["parents"]
    assert document["leaves"] == matchup["hierarchy"]["leaves"]


def test_modern_metadata_reports_partial_videre_coverage_without_public_pickup(tmp_path):
    destination = pickup.generate_metadata(
        ROOT,
        "modern",
        rules_updated="2026-07-23T00:00:00+09:00",
        data_updated="2026-07-23T00:00:00+09:00",
        output_directory=tmp_path,
    )
    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["statistics_catalog"] == "index.json"
    assert document["matchup_catalog"] == "matchup_index.json"
    assert document["hierarchy_catalog"] == "archetype_hierarchy.json"
    assert document["pickup_catalog"] is None
    assert document["matchup_source"] == "Videre"
    assert document["matchup_coverage"] == {
        "official_events": 183,
        "events_with_archives": 161,
        "events_without_archives": 22,
        "stored_archives": 165,
        "archives_outside_official_events": 4,
    }


def test_modern_pickup_uses_stable_parent_ids_and_preserves_manual_boundary(tmp_path):
    state = tmp_path / "state"
    known_path = pickup.initialize_known_state(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        output_directory=state,
    )
    assert known_path is not None
    known_document = json.loads(known_path.read_text(encoding="utf-8"))
    assert "known" not in known_document
    assert known_document["known_ids"] == sorted(set(known_document["known_ids"]))
    assert known_path.read_bytes() == (
        MODERN_STATS / "pickup" / "known_archetypes.json"
    ).read_bytes()

    candidates = tmp_path / "candidates"
    generated = pickup.generate_candidates(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        known_file=known_path,
        output_directory=candidates,
    )
    assert generated is not None
    assert generated["week"] == "2026-W29"
    assert generated["first_run"] is False
    assert generated["candidate_path"].read_bytes() == (
        MODERN_STATS / "pickup" / "candidates_2026-W29.yaml"
    ).read_bytes()
    assert generated["base_reference_path"].read_bytes() == (
        MODERN_STATS / "pickup" / "base_reference_2026-W29.yaml"
    ).read_bytes()
    document = yaml.safe_load(generated["candidate_path"].read_text(encoding="utf-8"))
    entries = document["existing_changes"] + document["new_archetypes"]
    assert entries
    assert all(entry["archetype_id"] for entry in entries)
    assert all("subtype_id" in entry and "subtype" in entry for entry in entries)
    assert all(
        entry["source"]
        == (
            "existing"
            if entry["archetype_id"] in known_document["known_ids"]
            else "new"
        )
        for entry in entries
    )

    before = known_path.read_bytes()
    assert pickup.publish(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        candidate_directory=candidates,
        state_directory=state,
        output_directory=tmp_path / "published",
    ) is None
    assert known_path.read_bytes() == before
    assert not (tmp_path / "published").exists()

    selected = document["existing_changes"][0]
    selected["approved"] = True
    selected["comment_zh"] = "人工审核"
    generated["candidate_path"].write_text(
        yaml.dump(
            document,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    published_result = pickup.publish(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        candidate_directory=candidates,
        state_directory=state,
        output_directory=tmp_path / "published",
    )
    assert published_result is not None
    published = json.loads(
        published_result["published_path"].read_text(encoding="utf-8")
    )
    published_entry = published["existing_changes"][0]
    assert published_entry["archetype_id"] == selected["archetype_id"]
    assert published_entry["subtype_id"] == selected["subtype_id"]
    assert published_entry["subtype"] == selected["subtype"]
    loaded, registry = validate_schemas.load_schemas(ROOT / "schemas")
    assert validate_schemas.validate_instance(
        published,
        loaded["mtgo-pickup-week.schema.json"],
        registry,
    ) == []


def test_modern_known_state_initialization_refuses_implicit_overwrite(tmp_path):
    assert pickup.initialize_known_state(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        output_directory=tmp_path,
    )
    try:
        pickup.initialize_known_state(
            ROOT,
            "modern",
            today=REFERENCE_TODAY,
            output_directory=tmp_path,
        )
    except pickup.MTGOPickupError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("known state initialization must not overwrite existing state")
