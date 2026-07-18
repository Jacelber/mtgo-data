import subprocess
import sys
from pathlib import Path

import validate_rules as rules


VALID = "format: Standard\ndate: '2026-03-08'\narchetypes:\n  - name: A\n    signatureCards:\n      - name: Card\n"


def test_minimal_and_legacy_default_pass():
    assert rules.validate_text(VALID) == []


def test_zones_and_copy_conditions_pass():
    for key in ("minCopies", "maxCopies", "exactCopies"):
        text = VALID.replace("name: Card", f"name: Card\n        zone: main\n        {key}: 0")
        assert rules.validate_text(text) == []


def test_same_names_are_allowed():
    text = VALID + "  - name: A\n    signatureCards:\n      - name: Other\n"
    assert rules.validate_text(text) == []


def test_duplicate_keys_fail_at_all_requested_depths():
    for text in (VALID.replace("format: Standard", "format: Standard\nformat: Modern"), VALID.replace("name: A", "name: A\n    name: B"), VALID.replace("name: Card", "name: Card\n        name: Other")):
        assert rules.validate_text(text)


def test_structure_and_card_failures():
    cases = ["", "[]", "format: ''\narchetypes: []", "format: S\narchetypes:\n - name: A\n   signatureCards: []", "format: S\narchetypes:\n - name: A\n   signatureCards:\n    - {}", "format: S\narchetypes:\n - name: A\n   signatureCards:\n    - name: C\n      zone: bad"]
    assert all(rules.validate_text(case) for case in cases)


def test_copy_count_rejections():
    for value in ("-1", "1.5", "'1'", "true", "null"):
        text = VALID.replace("name: Card", f"name: Card\n        minCopies: {value}")
        assert rules.validate_text(text)
    text = VALID.replace("name: Card", "name: Card\n        minCopies: 1\n        maxCopies: 2")
    assert rules.validate_text(text)


def test_real_production_file_passes_unchanged():
    assert rules.validate_path(Path("my_archetypes/standard.yaml")) == []


def test_cli_explicit_invalid_and_default(tmp_path):
    bad = tmp_path / "bad.yaml"; bad.write_text("format: S\narchetypes: []", encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "validate_rules.py", str(bad)], text=True, capture_output=True)
    assert result.returncode == 1 and "FAIL" in result.stdout
    result = subprocess.run([sys.executable, "-B", "validate_rules.py"], text=True, capture_output=True)
    assert result.returncode == 0 and "PASS" in result.stdout
