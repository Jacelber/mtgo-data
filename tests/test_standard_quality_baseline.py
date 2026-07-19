import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_text = str(ROOT)
if root_text not in sys.path:
    sys.path.insert(0, root_text)

import validate_standard_quality as quality


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
    records = [
        {"id": ["fixture", 0], "main": [["A", 4]], "side": []},
        {"id": ["fixture", 1], "main": [["Missing", 4]], "side": []},
    ]
    rules = [
        {"name": "First", "signatureCards": [{"name": "A", "minCopies": 1}]},
        {"name": "Second", "signatureCards": [{"name": "A", "minCopies": 2}]},
    ]
    result = quality.analyze(records, rules)
    assert result["unknown"] == 1
    assert result["multiple_matches"] == 1
    assert result["maximum_matches_per_deck"] == 2


def test_cli_reports_a_deterministic_summary(capsys):
    assert quality.main([]) == 0
    assert capsys.readouterr().out == (
        "Standard quality baseline PASS: records=3936 unknown=71 multiple_matches=947\n"
    )
