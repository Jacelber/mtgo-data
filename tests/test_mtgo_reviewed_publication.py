"""Synthetic publication membership; no current event or week is an oracle."""
from datetime import date
from hashlib import sha256
import json

import pytest

from mtgmeta.mtgo.publication import PublicationError, resolve_timeline


def _baseline():
    return {"week": "2025-W02", "event_ids": ["100"]}


def test_unreviewed_week_blocks_a_later_accepted_week():
    events = {"100": date(2025, 1, 6), "200": date(2025, 1, 13),
              "300": date(2025, 1, 20)}
    end, ids = resolve_timeline(_baseline(), [{"week": "2025-W04", "event_ids": ["300"]}], events)
    assert end == date(2025, 1, 6)
    assert ids == frozenset({"100"})


def test_empty_week_can_be_crossed_but_never_admits_late_event():
    events = {"100": date(2025, 1, 6), "300": date(2025, 1, 20)}
    reviews = [{"week": "2025-W04", "event_ids": ["300"],
                "observed_empty_weeks": ["2025-W03"]}]
    end, ids = resolve_timeline(_baseline(), reviews, events)
    assert end == date(2025, 1, 20)
    assert ids == frozenset({"100", "300"})
    events["200"] = date(2025, 1, 13)
    end, ids = resolve_timeline(_baseline(), reviews, events)
    assert "200" not in ids
    assert end == date(2025, 1, 20)


def test_completed_never_grants_data_admission():
    baseline = {**_baseline(), "completed": True}
    end, ids = resolve_timeline(baseline, [], {"100": date(2025, 1, 6), "200": date(2025, 1, 13)})
    assert end == date(2025, 1, 6)
    assert ids == frozenset({"100"})


def test_formats_advance_independently_without_landing_acceptance():
    events = {"100": date(2025, 1, 6), "200": date(2025, 1, 13)}
    accepted = [{"week": "2025-W03", "event_ids": ["200"]}]
    assert resolve_timeline(_baseline(), accepted, events) == (
        date(2025, 1, 13), frozenset({"100", "200"}))
    assert resolve_timeline(_baseline(), [], events) == (
        date(2025, 1, 6), frozenset({"100"}))


def test_late_event_in_accepted_week_is_not_implicitly_admitted():
    events = {"100": date(2025, 1, 6), "101": date(2025, 1, 7),
              "200": date(2025, 1, 13), "201": date(2025, 1, 14)}
    end, ids = resolve_timeline(_baseline(), [{"week": "2025-W03", "event_ids": ["200"]}], events)
    assert end == date(2025, 1, 13)
    assert ids == frozenset({"100", "200"})


@pytest.mark.parametrize("reviews", [
    [{"week": "2025-W03", "event_ids": ["999"]}],
    [{"week": "2025-W04", "event_ids": ["200"]}],
    [{"week": "2025-W03", "event_ids": ["200", "200"]}],
])
def test_invalid_admission_fails_closed(reviews):
    with pytest.raises(PublicationError):
        resolve_timeline(_baseline(), reviews, {"100": date(2025, 1, 6), "200": date(2025, 1, 13)})


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _repository(root):
    from mtgmeta.mtgo.publication import _digest
    formats, admissions, names = [], {}, []
    for fmt in ("standard", "modern"):
        formats.append({"id": fmt, "display_name": fmt.title(), "state": "executable", "public": True,
            "mtgo": {"enabled": True, "event_collection_enabled": True,
                "capabilities": ["classification", "event_statistics", "range_statistics", "matchup_statistics",
                                 "weekly_top8", "completeness_reporting", "metadata_generation", "catalog_generation"],
                "paths": {"events": f"data/{fmt}", "matches": f"data/{fmt}/mtgo/matches",
                          "rules": f"my_archetypes/{fmt}.yaml", "statistics": f"stats/{fmt}/mtgo",
                          "reports": f"reports/{fmt}/mtgo"}}})
        for event_id, day in (("100", "2025-01-06"), ("200", "2025-01-13"), ("300", "2025-01-20")):
            _write(root / f"data/{fmt}/{event_id}.json", {
                "event_id": event_id, "format": f"C{fmt.upper()}", "description": "Synthetic Challenge",
                "starttime": day + "T12:00:00Z", "player_count": 8,
                "players": [{"player": f"Player {rank}", "loginid": str(rank), "final_rank": rank,
                             "swiss_score": 9, "main_deck": [{"name": "Signal Card", "qty": 60}],
                             "sideboard": [{"name": "Side Card", "qty": 15}]} for rank in range(1, 9)]})
        _write(root / f"my_archetypes/{fmt}.yaml", {"schema_version": "1.0.0", "format": fmt,
            "archetypes": [{"id": "alpha", "name": "Alpha", "priority": 100,
                "rules": [{"id": "alpha-rule", "priority": 100,
                           "conditions": {"all": [{"card": "Signal Card", "zone": "main"}]}}]}]})
        source = f"data/{fmt}/100.json"
        admissions[fmt] = {"initial": {"kind": "grandfathered_existing_public_scope", **_baseline(),
            "source_manifest_digest": _digest([{"event_id": "100", "source_file": source,
                                                "sha256": sha256((root / source).read_bytes()).hexdigest()}]),
            "evidence": "synthetic grandfathered scope, not full human review"}, "weekly_acceptances": []}
        names.append({"format": fmt, "parent_id": "alpha", "subtype_id": None, "english": "Alpha",
                      "chinese": "甲类", "review_status": "approved"})
        _write(root / f"stats/{fmt}/mtgo/landing/current.json", {"week": {"id": "2025-W02"}, "source_event_ids": ["100"]})
        _write(root / f"stats/{fmt}/archetype_names.json", {})
    _write(root / "configs/formats.yaml", {"schema_version": "1.3.0", "formats": formats})
    _write(root / "configs/mtgo_archetype_names.yaml", {"schema_version": "1.0.0", "names": names})
    _write(root / "configs/mtgo_intentional_unknowns.yaml", {"schema_version": "1.0.0", "records": []})
    _write(root / "stats/catalog.json", {})
    registry = {"schema_version": "1.2.0", "records": [],
                "data_admissions": {"schema_version": "1.0.0", "formats": admissions}}
    _write(root / "configs/mtgo_weekly_review_completions.yaml", registry)
    return registry


def _generate(root, fmt):
    from mtgmeta.mtgo import stats, matchup, top8, completeness, metadata
    from mtgmeta.classification_reports_cli import generate_reports
    fixed = {"today": date(2025, 2, 3), "generated_at": "2025-02-03T00:00:00Z"}
    stats.build_all_stats(root, fmt, **fixed)
    matchup.build_all_matchups(root, fmt, **fixed)
    top8.build_all_top8(root, fmt, **fixed)
    completeness.build_all_completeness(root, fmt, **fixed)
    metadata.generate_hierarchy_catalog(root, fmt, rules_updated=fixed["generated_at"])
    generate_reports(root, fmt)
    metadata.generate_metadata(root, fmt, data_updated=fixed["generated_at"], rules_updated=fixed["generated_at"])


def test_all_public_producers_share_membership_and_standard_can_publish_before_landing(tmp_path):
    from mtgmeta.mtgo.publication import acceptance_record, inspect_publication, resolve_scope
    from mtgmeta.weekly_review import build_mtgo_weekly_review
    registry = _repository(tmp_path)
    for fmt in ("standard", "modern"):
        _generate(tmp_path, fmt)
        assert inspect_publication(tmp_path, fmt) == []
        index = json.loads((tmp_path / f"reports/{fmt}/mtgo/index.json").read_text())
        assert index["event_count"] == 1
        assert index["summary"]["total_decks"] == 8
    modern_before = {path.relative_to(tmp_path): path.read_bytes()
                     for directory in ("stats/modern", "reports/modern")
                     for path in (tmp_path / directory).rglob("*.json")}
    landing = tmp_path / "stats/standard/mtgo/landing/current.json"
    old_landing = landing.read_bytes()
    review = build_mtgo_weekly_review(tmp_path, "standard", "2025-W03")
    assert review["event_ids"] == ["200"]  # private review is not the public Top 8 window
    row = acceptance_record(tmp_path, "standard", "2025-W03",
        expected_review_digest=review["classification_review_digest"], accepted_on="2025-02-03", evidence="synthetic Owner acceptance")
    registry["data_admissions"]["formats"]["standard"]["weekly_acceptances"].append(row)
    _write(tmp_path / "configs/mtgo_weekly_review_completions.yaml", registry)
    _generate(tmp_path, "standard")
    assert inspect_publication(tmp_path, "standard") == []
    assert resolve_scope(tmp_path, "standard").event_ids == {"100", "200"}
    assert resolve_scope(tmp_path, "modern").event_ids == {"100"}
    assert all((tmp_path / path).read_bytes() == content for path, content in modern_before.items())
    assert landing.read_bytes() == old_landing
    assert registry["records"] == []
    assert "300" in resolve_scope(tmp_path, "standard").pending_event_ids


def test_current_binding_rejects_unadmitted_references_even_if_rehashed(tmp_path):
    from mtgmeta.mtgo.publication import inspect_publication, publication_binding
    _repository(tmp_path)
    _generate(tmp_path, "standard")
    _write(tmp_path / "reports/standard/mtgo/leak.json", {"records": [{"event_id": "200"}]})
    path = tmp_path / "stats/standard/mtgo/meta.json"
    meta = json.loads(path.read_text())
    meta["publication"] = publication_binding(tmp_path, "standard")
    _write(path, meta)
    assert any("unadmitted public event" in issue for issue in inspect_publication(tmp_path, "standard"))
    assert any("public report population" in issue for issue in inspect_publication(tmp_path, "standard"))


def test_changed_accepted_source_and_public_review_destination_fail_closed(tmp_path):
    from mtgmeta.mtgo.publication import require_private_output, resolve_scope
    _repository(tmp_path)
    _write(tmp_path / "configs/pages_publication.json", {
        "site_files": [], "site_directories": ["stats", "reports"],
        "excluded_patterns": ["stats/*/mtgo/landing/review/*"]})
    with pytest.raises(PublicationError, match="Pages"):
        require_private_output(tmp_path, tmp_path / "reports/pending.json")
    require_private_output(tmp_path, tmp_path / "stats/standard/mtgo/landing/review/private.json")
    require_private_output(tmp_path, tmp_path / "task-local/review.json")
    source = tmp_path / "data/standard/100.json"
    source.write_text(source.read_text() + "\n")
    with pytest.raises(PublicationError, match="source binding"):
        resolve_scope(tmp_path, "standard")


def test_staging_failure_never_materializes_partial_format(tmp_path, monkeypatch):
    from mtgmeta.mtgo import publication, stats
    from mtgmeta import classifier_closure
    import subprocess
    _repository(tmp_path)
    _generate(tmp_path, "standard")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    monkeypatch.setattr(classifier_closure, "_protected_input_fingerprints", lambda *args: {})
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    def fail(stage, fmt):
        assert stage != tmp_path
        _write(stage / f"stats/{fmt}/mtgo/partial.json", {"partial": True})
        raise OSError("synthetic generator failure")
    monkeypatch.setattr(stats, "build_all_stats", fail)
    with pytest.raises(OSError, match="generator failure"):
        publication.stage_publication(tmp_path, "standard", execute=True)
    assert {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_unknown_policy_is_not_expanded_by_data_acceptance(tmp_path):
    from mtgmeta.mtgo.publication import acceptance_record
    from mtgmeta.weekly_review import build_mtgo_weekly_review
    _repository(tmp_path)
    path = tmp_path / "data/standard/200.json"
    event = json.loads(path.read_text())
    event["players"][0]["main_deck"] = [{"name": "Unresolved Card", "qty": 60}]
    _write(path, event)
    review = build_mtgo_weekly_review(tmp_path, "standard", "2025-W03")
    with pytest.raises(PublicationError, match="Unknown policy"):
        acceptance_record(tmp_path, "standard", "2025-W03",
            expected_review_digest=review["classification_review_digest"],
            accepted_on="2025-02-03", evidence="synthetic acceptance cannot override Unknown policy")


def test_execute_materializes_only_after_existing_validation_and_browser_gate(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import subprocess
    from mtgmeta import classifier_closure, catalog
    from mtgmeta.mtgo import publication, metadata, landing_editorial
    _repository(tmp_path)
    _generate(tmp_path, "standard")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    calls = []
    def run(command, **kwargs):
        calls.append([str(part) for part in command])
        return SimpleNamespace(stdout="", returncode=0)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(metadata, "rules_last_commit_iso", lambda *args: "2025-02-03T00:00:00Z")
    monkeypatch.setattr(catalog, "write_catalog", lambda *args: None)
    monkeypatch.setattr(landing_editorial, "generate_public_name_contract", lambda *args: None)
    monkeypatch.setattr(classifier_closure, "inspect_format", lambda *args: {"state": "CURRENT"})
    materialize = classifier_closure._materialize_with_rollback
    def replace(root, stage, paths, **kwargs):
        assert {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()} == before
        executed = "\n".join(" ".join(command) for command in calls)
        for name in ("validate_repository.py", "validate_rules.py", "validate_schemas.py",
                     "validate_output_invariants.py", "test_generated_consumer_contracts.py",
                     "production-pages.spec.js", "diff --exit-code"):
            assert name in executed
        assert executed.index("validate_schemas.py") < executed.index("production-pages.spec.js") < executed.index("diff --exit-code")
        assert all(path.startswith(("stats/standard/", "reports/standard/")) or path == "stats/catalog.json" for path in paths)
        materialize(root, stage, paths, **kwargs)
    monkeypatch.setattr(classifier_closure, "_materialize_with_rollback", replace)
    result = publication.stage_publication(tmp_path, "standard", execute=True)
    assert result["executed"] is True
    assert result["publication_node"] == "reviewed_data"
    assert publication.inspect_publication(tmp_path, "standard") == []
    for path, content in before.items():
        if str(path).replace("\\", "/").startswith(("data/", "configs/", "stats/modern/")):
            assert (tmp_path / path).read_bytes() == content
