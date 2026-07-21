"""P2-07 machine-readable classification report regression tests."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import load_rule_set
from mtgmeta.reports import (
    REPORT_FILENAMES,
    build_classification_reports,
    find_identity_fields,
    has_blocking_diagnostics,
    load_events,
)


STANDARD_RULES = ROOT / "my_archetypes" / "standard.yaml"
RULE_FIXTURE = ROOT / "tests" / "fixtures" / "rules" / "valid_shared_rules.yaml"
REPORT_DIR = ROOT / "reports" / "standard" / "mtgo"


def production_reports():
    events = load_events((ROOT / "data" / "standard").glob("*.json"), ROOT)
    return build_classification_reports(events, load_rule_set(STANDARD_RULES))


@pytest.mark.committed_baseline
def test_production_report_baseline_and_subtype_contract():
    reports = production_reports()
    assert reports["index"]["summary"] == {
        "total_decks": 3936,
        "classified": 3865,
        "unknown": 71,
        "conflicts": 0,
        "invalid_decks": 0,
        "multiple_matches": 947,
        "overridden_matches": 947,
        "selected_subtypes": 45,
        "same_parent_multiple_subtype_matches": 21,
        "strict_validation": "pass",
    }
    subtype = reports["subtype_diagnostics"]["summary"]
    assert subtype["selected_by_subtype"] == {
        "4-color-control/inevitable-defeat": 1,
        "4-color-control/rakshasas-bargain": 4,
        "izzet-aggro/hired-claw": 32,
        "izzet-aggro/razorkin-needlehead": 8,
    }
    assert reports["classification_conflicts"]["records"] == []
    assert not has_blocking_diagnostics(reports)


def test_report_metadata_accepts_an_explicit_format_without_changing_classification():
    reports = build_classification_reports(
        load_events((ROOT / "data" / "standard").glob("*.json"), ROOT),
        load_rule_set(STANDARD_RULES),
        format_id="format-fixture",
        source="mtgo",
    )
    assert {report["format"] for report in reports.values()} == {"format-fixture"}
    assert {report["source"] for report in reports.values()} == {"mtgo"}
    assert reports["index"]["summary"] == production_reports()["index"]["summary"]


def test_reports_are_deidentified_and_unknowns_retain_deck_evidence():
    reports = production_reports()
    assert find_identity_fields(reports) == []
    unknown = reports["unknown_decks"]["records"][0]
    assert set(unknown) == {
        "deck_id", "event_id", "event_name", "event_start", "source_file",
        "main_deck", "sideboard",
    }
    assert len(unknown["deck_id"]) == 20
    assert unknown["main_deck"]
    serialized = json.dumps(reports, ensure_ascii=False)
    sample_event = json.loads(next((ROOT / "data" / "standard").glob("*.json")).read_text(encoding="utf-8"))
    sample_player = sample_event["players"][0]
    assert sample_player["player"] not in serialized
    assert sample_player["loginid"] not in serialized


def test_committed_reports_are_deterministic_generator_output():
    reports = production_reports()
    filenames = {**REPORT_FILENAMES, "index": "index.json"}
    for name, filename in filenames.items():
        expected = json.dumps(reports[name], ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        assert (REPORT_DIR / filename).read_text(encoding="utf-8") == expected


def test_equal_priority_conflict_is_reported_and_blocks_strict_validation():
    rules = load_rule_set(RULE_FIXTURE)
    aggro = rules.archetypes[1]
    tied = replace(aggro, rules=(replace(aggro.rules[0], priority=100),))
    rules = replace(rules, archetypes=(rules.archetypes[0], tied))
    event = {
        "event_id": "fixture-event",
        "description": "Fixture Event",
        "starttime": "2026-01-01 00:00:00.0",
        "players": [{
            "player": "must-not-leak",
            "loginid": "123456",
            "main_deck": [
                {"name": "Example Engine", "qty": 3},
                {"name": "Example Threat", "qty": 1},
            ],
            "sideboard": [],
        }],
    }
    reports = build_classification_reports([("data/standard/fixture.json", event)], rules)
    assert reports["index"]["summary"]["conflicts"] == 1
    assert reports["classification_conflicts"]["summary"] == {"record_count": 1, "blocking": True}
    record = reports["classification_conflicts"]["records"][0]
    assert record["selected"] is None
    assert record["conflict_kind"] == "parent_archetype"
    assert {item["rule_id"] for item in record["matches"]} == {
        "example-control-artifacts", "example-aggro-core",
    }
    assert "must-not-leak" not in json.dumps(reports)
    assert has_blocking_diagnostics(reports)


def test_cli_regenerates_and_strictly_validates_in_any_working_directory(tmp_path):
    script = ROOT / "generate_classification_reports.py"
    output = tmp_path / "reports"
    result = subprocess.run(
        [sys.executable, "-B", str(script), "--output-dir", str(output), "--strict"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "conflicts=0" in result.stdout
    assert sorted(path.name for path in output.glob("*.json")) == sorted([
        "index.json", *REPORT_FILENAMES.values(),
    ])


def test_cli_writes_conflict_report_before_strict_failure(tmp_path):
    data_dir = tmp_path / "data" / "standard"
    data_dir.mkdir(parents=True)
    event = {
        "event_id": "strict-fixture",
        "description": "Strict Fixture",
        "starttime": "2026-01-01 00:00:00.0",
        "players": [{
            "player": "must-not-leak",
            "loginid": "654321",
            "main_deck": [
                {"name": "Example Engine", "qty": 3},
                {"name": "Example Threat", "qty": 1},
            ],
            "sideboard": [],
        }],
    }
    (data_dir / "fixture.json").write_text(json.dumps(event), encoding="utf-8")
    rule_text = RULE_FIXTURE.read_text(encoding="utf-8").replace("priority: 50", "priority: 100")
    rules = tmp_path / "rules.yaml"
    rules.write_text(rule_text, encoding="utf-8")
    script = ROOT / "generate_classification_reports.py"
    result = subprocess.run(
        [
            sys.executable, "-B", str(script), "--root", str(tmp_path),
            "--registry", str(ROOT / "configs" / "formats.yaml"),
            "--rules", str(rules), "--strict",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "strict validation FAIL" in result.stdout
    report = json.loads((tmp_path / "reports/standard/mtgo/classification_conflicts.json").read_text(encoding="utf-8"))
    assert report["summary"] == {"record_count": 1, "blocking": True}
    assert "must-not-leak" not in json.dumps(report)


def test_cli_rejects_a_disabled_format_before_creating_report_output(tmp_path):
    script = ROOT / "generate_classification_reports.py"
    output = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(script),
            "--format",
            "pauper",
            "--output-dir",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "not enabled" in result.stdout
    assert not output.exists()
