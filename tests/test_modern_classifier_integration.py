"""P6-02 integration tests for read-only Modern classification diagnostics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import RuleConfigError
from mtgmeta.mtgo.classification import (
    MTGOClassificationAuditError,
    audit_mtgo_classification,
    load_mtgo_events_for_format,
    mtgo_event_format,
)
from mtgmeta.reports import find_identity_fields, has_blocking_diagnostics


MODERN_RULES = ROOT / "my_archetypes" / "modern.yaml"
MODERN_REPORTS = ROOT / "reports" / "modern" / "mtgo"
STANDARD_REPORTS = ROOT / "reports" / "standard" / "mtgo"


def report_bytes():
    return {
        path.name: path.read_bytes()
        for path in sorted(MODERN_REPORTS.glob("*.json"))
    }


def test_complete_modern_audit_uses_shared_paths_without_mutating_product_output():
    before = report_bytes()

    audit = audit_mtgo_classification(ROOT, "modern")
    reports = audit.reports
    summary = reports["index"]["summary"]

    assert audit.format_id == "modern"
    assert audit.expected_event_format == "CMODERN"
    assert audit.event_directory == ROOT / "data" / "modern"
    assert audit.rule_path == MODERN_RULES
    assert audit.included_event_count == reports["index"]["event_count"] == 181
    assert audit.excluded_events == ()
    assert summary == {
        "total_decks": 5792,
        "classified": 5664,
        "unknown": 128,
        "conflicts": 0,
        "invalid_decks": 0,
        "multiple_matches": 1519,
        "overridden_matches": 1519,
        "selected_subtypes": 2329,
        "same_parent_multiple_subtype_matches": 132,
        "strict_validation": "pass",
    }
    assert {report["format"] for report in reports.values()} == {"modern"}
    assert {report["source"] for report in reports.values()} == {"mtgo"}
    assert find_identity_fields(reports) == []
    assert not has_blocking_diagnostics(reports)
    assert report_bytes() == before


def test_audit_preserves_the_active_rule_artifact_exactly():
    digest = hashlib.sha256(MODERN_RULES.read_text(encoding="utf-8").encode()).hexdigest()

    audit_mtgo_classification(ROOT, "modern")

    assert hashlib.sha256(MODERN_RULES.read_text(encoding="utf-8").encode()).hexdigest() == digest


def test_event_loader_excludes_cross_format_records_and_rejects_missing_format(tmp_path):
    modern = tmp_path / "modern.json"
    premodern = tmp_path / "premodern.json"
    malformed = tmp_path / "missing-format.json"
    modern.write_text(json.dumps({"format": "CMODERN", "players": []}), encoding="utf-8")
    premodern.write_text(json.dumps({"format": "CPREMODERN", "players": []}), encoding="utf-8")

    events, excluded = load_mtgo_events_for_format(
        [premodern, modern],
        tmp_path,
        "modern",
    )
    assert [name for name, _ in events] == ["modern.json"]
    assert [(item.source_file, item.actual_format) for item in excluded] == [
        ("premodern.json", "CPREMODERN")
    ]
    assert mtgo_event_format("modern") == "CMODERN"

    malformed.write_text(json.dumps({"players": []}), encoding="utf-8")
    with pytest.raises(MTGOClassificationAuditError, match="embedded event format"):
        load_mtgo_events_for_format([malformed], tmp_path, "modern")


def test_planned_format_audit_never_falls_back_to_standard_rules():
    with pytest.raises(RuleConfigError, match="pauper.yaml"):
        audit_mtgo_classification(ROOT, "pauper")


def test_production_cli_generates_strict_deidentified_modern_reports():
    standard_before = {
        path.name: path.read_bytes()
        for path in sorted(STANDARD_REPORTS.glob("*.json"))
    }
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "mtgmeta.mtgo",
            "--root",
            str(ROOT),
            "--format",
            "modern",
            "classification-reports",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "decks=5792" in result.stdout
    assert "unknown=128" in result.stdout
    assert "validation PASS" in result.stdout
    assert sorted(path.name for path in MODERN_REPORTS.glob("*.json")) == [
        "classification_conflicts.json",
        "index.json",
        "multiple_matches.json",
        "overridden_matches.json",
        "subtype_diagnostics.json",
        "unknown_decks.json",
    ]
    generated = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(MODERN_REPORTS.glob("*.json"))
    }
    assert find_identity_fields(generated) == []
    assert all(report["format"] == "modern" for report in generated.values())
    for report in generated.values():
        for record in report.get("records", []):
            assert record["source_file"].startswith("data/modern/")
    assert {
        path.name: path.read_bytes()
        for path in sorted(STANDARD_REPORTS.glob("*.json"))
    } == standard_before


@pytest.mark.parametrize(
    "command",
    [
        ["fetch-matches"],
        ["build-matchups"],
        ["pickup", "candidates"],
        ["generate-metadata"],
    ],
)
def test_every_post_p6_05_modern_product_command_remains_disabled(command):
    statistics = ROOT / "stats" / "modern" / "mtgo"
    matches = ROOT / "data" / "modern" / "mtgo" / "matches"
    statistics_before = {
        path.name: path.read_bytes() for path in sorted(statistics.glob("*.json"))
    }
    assert len(statistics_before) == 9
    assert not matches.exists()
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "mtgmeta.mtgo",
            "--root",
            str(ROOT),
            "--format",
            "modern",
            *command,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 2
    assert "does not support" in result.stderr
    assert {
        path.name: path.read_bytes() for path in sorted(statistics.glob("*.json"))
    } == statistics_before
    assert not matches.exists()
