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
P6_01_CONTRACT = ROOT / "tests" / "fixtures" / "modern" / "rule_migration_contract.json"


def test_complete_modern_audit_uses_shared_paths_without_product_output():
    output = ROOT / "reports" / "modern" / "mtgo"
    assert not output.exists()

    audit = audit_mtgo_classification(ROOT, "modern")
    reports = audit.reports
    summary = reports["index"]["summary"]

    assert audit.format_id == "modern"
    assert audit.expected_event_format == "CMODERN"
    assert audit.event_directory == ROOT / "data" / "modern"
    assert audit.rule_path == MODERN_RULES
    assert audit.included_event_count == reports["index"]["event_count"] == 181
    assert len(audit.excluded_events) == 2
    assert {item.actual_format for item in audit.excluded_events} == {"CPREMODERN"}
    assert all(item.expected_format == "CMODERN" for item in audit.excluded_events)
    assert summary == {
        "total_decks": 5792,
        "classified": 5157,
        "unknown": 635,
        "conflicts": 0,
        "invalid_decks": 0,
        "multiple_matches": 324,
        "overridden_matches": 324,
        "selected_subtypes": 0,
        "same_parent_multiple_subtype_matches": 0,
        "strict_validation": "pass",
    }
    assert {report["format"] for report in reports.values()} == {"modern"}
    assert {report["source"] for report in reports.values()} == {"mtgo"}
    assert find_identity_fields(reports) == []
    assert not has_blocking_diagnostics(reports)
    assert not output.exists()


def test_audit_preserves_the_p6_01_rule_artifact_exactly():
    contract = json.loads(P6_01_CONTRACT.read_text(encoding="utf-8"))
    digest = hashlib.sha256(MODERN_RULES.read_text(encoding="utf-8").encode()).hexdigest()

    audit_mtgo_classification(ROOT, "modern")

    assert digest == contract["production_rule_content_sha256"]
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


def test_production_cli_still_rejects_modern_before_writing_reports(tmp_path):
    output = ROOT / "reports" / "modern" / "mtgo"
    assert not output.exists()
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
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 2
    assert "not enabled" in result.stderr
    assert not output.exists()
