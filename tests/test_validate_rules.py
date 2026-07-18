import subprocess
import sys
from pathlib import Path

import pytest

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


def test_malformed_missing_and_unreadable_inputs(monkeypatch, tmp_path):
    assert rules.validate_text("format: [")
    assert rules.validate_path(tmp_path / "missing.yaml")
    monkeypatch.setattr(Path, "read_text", lambda self, **_: (_ for _ in ()).throw(PermissionError("denied")))
    assert rules.validate_path("denied.yaml")


def test_cli_help_usage_and_deterministic_failure(tmp_path):
    command = [sys.executable, "-B", "validate_rules.py", "--bad"]
    first = subprocess.run(command, text=True, capture_output=True)
    second = subprocess.run(command, text=True, capture_output=True)
    assert first.returncode == second.returncode == 2 and first.stderr == second.stderr
    help_result = subprocess.run([sys.executable, "-B", "validate_rules.py", "--help"], text=True, capture_output=True)
    assert help_result.returncode == 0 and "usage:" in help_result.stdout
    bad = tmp_path / "bad.yaml"; bad.write_text("format: S\narchetypes: []", encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "validate_rules.py", str(bad)], text=True, capture_output=True)
    assert result.returncode == 1 and "Traceback" not in result.stderr


@pytest.mark.parametrize("replacement", ["name: 1", "name: ''", "name: '   '", "zone: 1", "name: C\n        minCopies: []", "name: C\n        minCopies: {}"])
def test_invalid_scalar_and_collection_fields(replacement):
    assert rules.validate_text(VALID.replace("name: Card", replacement))


@pytest.mark.parametrize("key", ["minCopies", "maxCopies", "exactCopies"])
def test_each_copy_count_accepts_positive_integer(key):
    assert rules.validate_text(VALID.replace("name: Card", f"name: Card\n        {key}: 2")) == []


def test_non_mapping_and_missing_required_entries_fail():
    assert rules.validate_text("format: S\narchetypes:\n - nope")
    assert rules.validate_text("format: S\narchetypes:\n - signatureCards: []")
    assert rules.validate_text("format: S\narchetypes:\n - name: A\n   signatureCards:\n    - nope")


def test_three_copy_count_conditions_fail():
    text = VALID.replace("name: Card", "name: Card\n        minCopies: 1\n        maxCopies: 2\n        exactCopies: 1")
    assert rules.validate_text(text)


def test_production_bytes_and_repository_status_are_unchanged():
    production = Path("my_archetypes/standard.yaml")
    before = production.read_bytes()
    assert rules.main([]) == 0
    assert production.read_bytes() == before
    status = subprocess.run(["git", "status", "--porcelain"], text=True, capture_output=True).stdout.splitlines()
    assert all(line.endswith("tests/test_validate_rules.py") for line in status)


def test_explicit_valid_path_and_legacy_order_are_preserved(tmp_path):
    path = tmp_path / "valid.yaml"
    ordered = VALID + "  - name: Second\n    signatureCards:\n      - name: Other\n"
    path.write_text(ordered, encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "validate_rules.py", str(path)], text=True, capture_output=True)
    assert result.returncode == 0 and "PASS" in result.stdout
    data = __import__("yaml").safe_load(ordered)
    assert [entry["name"] for entry in data["archetypes"]] == ["A", "Second"]
