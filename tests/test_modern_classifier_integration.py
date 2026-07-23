"""P6-02 integration tests for read-only Modern classification diagnostics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


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
    modern_events, excluded = load_mtgo_events_for_format(
        sorted((ROOT / "data" / "modern").glob("*.json")),
        ROOT,
        "modern",
    )
    expected_decks = sum(len(event.get("players", [])) for _, event in modern_events)

    audit = audit_mtgo_classification(ROOT, "modern")
    reports = audit.reports
    summary = reports["index"]["summary"]

    assert audit.format_id == "modern"
    assert audit.expected_event_format == "CMODERN"
    assert audit.event_directory == ROOT / "data" / "modern"
    assert audit.rule_path == MODERN_RULES
    assert audit.included_event_count == reports["index"]["event_count"] == len(modern_events)
    assert audit.excluded_events == excluded == ()
    assert summary["total_decks"] == expected_decks
    assert (
        summary["classified"] + summary["unknown"] + summary["conflicts"]
        + summary["invalid_decks"]
        == expected_decks
    )
    assert summary["conflicts"] == 0
    assert summary["invalid_decks"] == 0
    assert summary["multiple_matches"] == summary["overridden_matches"]
    assert summary["strict_validation"] == "pass"
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


def test_production_cli_generates_strict_deidentified_modern_reports(tmp_path):
    standard_before = {
        path.name: path.read_bytes()
        for path in sorted(STANDARD_REPORTS.glob("*.json"))
    }
    modern_before = report_bytes()
    output_dir = tmp_path / "reports"
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
            "--output-dir",
            str(output_dir),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    audit = audit_mtgo_classification(ROOT, "modern")
    summary = audit.reports["index"]["summary"]
    assert f"decks={summary['total_decks']}" in result.stdout
    assert f"unknown={summary['unknown']}" in result.stdout
    assert "validation PASS" in result.stdout
    assert sorted(path.name for path in output_dir.glob("*.json")) == [
        "classification_conflicts.json",
        "index.json",
        "multiple_matches.json",
        "overridden_matches.json",
        "subtype_diagnostics.json",
        "unknown_decks.json",
    ]
    generated = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(output_dir.glob("*.json"))
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
    assert report_bytes() == modern_before


def test_p6_07_does_not_make_modern_public_or_change_existing_statistics():
    statistics = ROOT / "stats" / "modern" / "mtgo"
    statistics_before = {
        path.name: path.read_bytes()
        for path in sorted(statistics.glob("*.json"))
        if path.name not in {"meta.json", "archetype_hierarchy.json"}
    }
    assert len(statistics_before) >= 9
    registry = yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    assert modern["public"] is False
    assert set(modern["mtgo"]["capabilities"]) >= {
        "weekly_pickup",
        "metadata_generation",
        "catalog_generation",
    }
    assert {
        path.name: path.read_bytes()
        for path in sorted(statistics.glob("*.json"))
        if path.name not in {"meta.json", "archetype_hierarchy.json"}
    } == statistics_before
