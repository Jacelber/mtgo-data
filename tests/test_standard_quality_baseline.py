import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "validate_standard_quality.py"
SPEC = importlib.util.spec_from_file_location("validate_standard_quality", TOOL)
assert SPEC is not None and SPEC.loader is not None
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


def test_frozen_quality_baseline_matches_legacy_classifier():
    assert quality.validate() == []


def test_quality_baseline_is_aggregate_only_and_anonymized():
    baseline = json.loads(quality.BASELINE.read_text(encoding="utf-8"))
    assert baseline["legacy_resolution"] == "first_match"
    assert baseline["rule_ids_present"] is False
    assert baseline["priorities_present"] is False
    serialized = json.dumps(baseline).lower()
    assert all(field not in serialized for field in ("player_name", "loginid"))


def test_analysis_detects_unknown_and_multiple_matches_without_resolving_them():
    records = quality.load_json(quality.CORPUS)["records"]
    selected = [
        next(
            record
            for record in records
            if record["source"] == "Standard_Challenge_32_12838092.json"
            and record["index"] == 23
        ),
        next(
            record
            for record in records
            if record["source"] == "Standard_Challenge_32_12839956.json"
            and record["index"] == 8
        ),
    ]
    result = quality.analyze(selected, quality.load_rule_set(quality.RULES))
    assert result["unknown"] == 1
    assert result["multiple_matches"] == 1
    assert result["maximum_matches_per_deck"] == 2


def test_cli_reports_a_deterministic_summary(capsys):
    assert quality.main([]) == 0
    assert capsys.readouterr().out == (
        "Standard quality baseline PASS: records=3936 unknown=71 multiple_matches=947\n"
    )
