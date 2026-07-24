"""Behavioral tests for the read-only repository validator."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_repository", ROOT / "validate_repository.py")
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["validate_repository"] = validator
SPEC.loader.exec_module(validator)


def test_decode_utf8_source():
    assert "value" in validator.decode_python(b"value = 1\n")


def test_decode_cookie_source():
    assert validator.decode_python(b"# coding: latin-1\nvalue = '\xe9'\n").endswith("'é'\n")


def test_decode_bom_source():
    assert validator.decode_python(b"\xef\xbb\xbfx = 1\n").startswith("x = 1")


def test_conflicting_bom_cookie_fails():
    with pytest.raises(SyntaxError):
        validator.decode_python(b"\xef\xbb\xbf# coding: latin-1\nx = 1\n")


def test_validate_python_syntax_failure(tmp_path):
    path = tmp_path / "bad.py"
    path.write_text("if True print('x')\n", encoding="utf-8")
    counts, failures, _ = validator.validate_files(tmp_path, ["bad.py"])
    assert counts["Python"] == 1 and failures[0].line == 1 and failures[0].column


def test_unknown_python_encoding_is_failure(tmp_path):
    (tmp_path / "bad.py").write_bytes(b"# coding: unknown_codec\nx=1\n")
    _, failures, _ = validator.validate_files(tmp_path, ["bad.py"])
    assert failures[0].category == "Python"


def test_valid_json(tmp_path):
    (tmp_path / "a.json").write_text('{"a": 1}', encoding="utf-8")
    _, failures, _ = validator.validate_files(tmp_path, ["a.json"])
    assert not failures


def test_invalid_json_location(tmp_path):
    (tmp_path / "a.json").write_text('{"a": }', encoding="utf-8")
    _, failures, _ = validator.validate_files(tmp_path, ["a.json"])
    assert failures[0].category == "JSON" and failures[0].line == 1 and failures[0].column


def test_invalid_json_utf8(tmp_path):
    (tmp_path / "a.json").write_bytes(b"\xff")
    _, failures, _ = validator.validate_files(tmp_path, ["a.json"])
    assert failures[0].category == "JSON"


def test_valid_yaml(tmp_path):
    (tmp_path / "a.yaml").write_text("a: 1\n", encoding="utf-8")
    _, failures, _ = validator.validate_files(tmp_path, ["a.yaml"])
    assert not failures


def test_invalid_yaml_location(tmp_path):
    (tmp_path / "a.yaml").write_text("a: [\n", encoding="utf-8")
    _, failures, _ = validator.validate_files(tmp_path, ["a.yaml"])
    assert failures[0].category == "YAML" and failures[0].line


def test_invalid_yaml_utf8(tmp_path):
    (tmp_path / "a.yaml").write_bytes(b"\xff")
    _, failures, _ = validator.validate_files(tmp_path, ["a.yaml"])
    assert failures[0].category == "YAML"


def test_tracked_files_invocation(monkeypatch, tmp_path):
    calls = []
    class Result:
        def __init__(self, stdout):
            self.stdout = stdout
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return Result(
            b"b.py\0a.py\0removed.py\0\0"
            if "--deleted" not in args
            else b"removed.py\0"
        )
    monkeypatch.setattr(validator.subprocess, "run", run)
    assert validator.tracked_files(tmp_path) == ["a.py", "b.py"]
    assert calls[0][0] == [
        "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    ]
    assert calls[1][0] == ["git", "ls-files", "-z", "--deleted"]
    assert all("shell" not in kwargs for _, kwargs in calls)


def test_tracked_files_failure(monkeypatch, tmp_path):
    def run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(validator.subprocess, "run", run)
    with pytest.raises(validator.InfrastructureError):
        validator.tracked_files(tmp_path)


def test_tracked_files_bad_utf8(monkeypatch, tmp_path):
    class Result:
        stdout = b"\xff"
    monkeypatch.setattr(validator.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(validator.InfrastructureError):
        validator.tracked_files(tmp_path)


def test_repository_hygiene_accepts_source_and_generated_reports():
    checked, failures = validator.validate_hygiene([
        "src/module.py", "unknown_highperf.txt", "stats/standard/mtgo/meta.json"
    ])
    assert checked == 3
    assert failures == []


def test_repository_hygiene_rejects_tracked_runtime_artifacts():
    names = [
        "src/__pycache__/module.pyc", ".pytest_cache/state", ".venv/pyvenv.cfg",
        "debug.log", "scratch.tmp", "backup.bak", ".DS_Store", "assets/THUMBS.DB",
    ]
    checked, failures = validator.validate_hygiene(names)
    assert checked == len(names)
    assert [failure.path for failure in failures] == names
    assert all(failure.category == "Hygiene" for failure in failures)


@pytest.mark.parametrize("value,expected", [("a/b.txt", True), ("../a", False), ("a\\b", False), ("C:\\a", False), ("//server/a", False)])
def test_safe_declared_reference(value, expected):
    assert validator.safe_declared_reference(value) is expected


def test_read_missing_is_infrastructure(tmp_path):
    with pytest.raises(validator.InfrastructureError):
        validator.read_bytes(tmp_path, "missing.txt")


def test_read_non_regular_tracked_path_is_infrastructure(tmp_path):
    (tmp_path / "directory.json").mkdir()
    with pytest.raises(validator.InfrastructureError, match="not a regular file"):
        validator.read_bytes(tmp_path, "directory.json")


def test_reference_invalid_values(tmp_path):
    status = {"authoritative_documents": {s: [{"path": "ok.txt"}] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    for value in ("", None, 1, "../outside.md", "C:\\outside.md", "a\\b", "//server/share"):
        status["authoritative_documents"]["reading_order"][0]["path"] = value
        checked, failures, _ = validator.validate_references(tmp_path, ["ok.txt"], status)
        matching = [f for f in failures if repr(value) in f.message]
        assert checked == 14 and len(matching) == 1 and matching[0].category == "References"


def test_status_structure_failure(tmp_path):
    checked, failures, _ = validator.validate_references(tmp_path, [], {"authoritative_documents": {}})
    assert checked == 11 and len(failures) == 15 and all(f.category == "References" for f in failures)


def test_requirement_include_forms(tmp_path):
    (tmp_path / "requirements.txt").write_text("x\n", encoding="utf-8")
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    (tmp_path / "requirements-dev.txt").write_text("-r requirements.txt\n-rrequirements.txt\n-r=requirements.txt\n--requirement requirements.txt\n--requirement=requirements.txt\n", encoding="utf-8")
    checked, failures, _ = validator.validate_references(tmp_path, ["requirements.txt", "requirements-dev.txt"], status)
    assert checked == 16 and not [f for f in failures if f.path.startswith("requirements-dev.txt")]


def test_frontend_and_standard_missing_references(tmp_path):
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    (tmp_path / "index.html").write_text("", encoding="utf-8")
    checked, failures, _ = validator.validate_references(tmp_path, ["index.html"], status)
    assert checked == 17 and len(failures) == 20
    assert {failure.path for failure in failures if failure.message == "missing front-end asset"} == {
        "assets/js/common.js",
        "assets/js/matchup.js",
        "assets/js/mtgo.js",
    }


def test_all_frontend_templates_are_recognized(tmp_path):
    templates = [
        "stats/${currentFormat}/mtgo/meta.json",
        "stats/${currentFormat}/mtgo/range_${currentRange}w.json",
        "stats/${currentFormat}/mtgo/decks_${currentRange}w.json",
        "stats/${currentFormat}/mtgo/pickup/index.json",
        "stats/${currentFormat}/mtgo/pickup/${week}.json",
        "stats/${currentFormat}/mtgo/matchup_${mxRange}w.json",
    ]
    (tmp_path / "index.html").write_text("", encoding="utf-8")
    (tmp_path / "assets" / "js").mkdir(parents=True)
    (tmp_path / "assets" / "js" / "common.js").write_text("", encoding="utf-8")
    (tmp_path / "assets" / "js" / "mtgo.js").write_text("\n".join(templates), encoding="utf-8")
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    _, failures, breakdown = validator.validate_references(tmp_path, ["index.html"], status)
    assert breakdown["front-end templates"] == 6
    assert not [f for f in failures if "template" in f.message]


def test_all_standard_reference_paths_are_regular_json(tmp_path):
    paths = [
        "stats/standard/mtgo/meta.json", "stats/standard/mtgo/range_1w.json",
        "stats/standard/mtgo/range_4w.json", "stats/standard/mtgo/range_12w.json",
        "stats/standard/mtgo/decks_1w.json", "stats/standard/mtgo/decks_4w.json",
        "stats/standard/mtgo/decks_12w.json", "stats/standard/mtgo/matchup_1w.json",
        "stats/standard/mtgo/matchup_4w.json", "stats/standard/mtgo/matchup_12w.json",
        "stats/standard/mtgo/pickup/index.json",
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"weeks": []}' if name.endswith("pickup/index.json") else "{}", encoding="utf-8")
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    _, failures, breakdown = validator.validate_references(tmp_path, paths, status)
    assert breakdown["required Standard files"] == 11
    assert not [f for f in failures if f.path in paths]
    assert len(set(paths)) == 11 and all((tmp_path / p).is_file() for p in paths)


def test_posix_absolute_authoritative_path_is_structured_failure(tmp_path):
    status = {"authoritative_documents": {s: [{"path": "ok.txt"}] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    status["authoritative_documents"]["reading_order"][0]["path"] = "/absolute/path.md"
    checked, failures, _ = validator.validate_references(tmp_path, ["ok.txt"], status)
    matching = [f for f in failures if repr("/absolute/path.md") in f.message]
    assert checked == 14 and len(matching) == 1 and matching[0].category == "References"


def test_pickup_valid_entry(tmp_path):
    pickup = tmp_path / "stats/standard/mtgo/pickup"
    pickup.mkdir(parents=True)
    (pickup / "index.json").write_text('{"weeks": [{"file": "w.json"}]}', encoding="utf-8")
    (pickup / "w.json").write_text("{}", encoding="utf-8")
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    checked, failures, _ = validator.validate_references(tmp_path, ["stats/standard/mtgo/pickup/index.json", "stats/standard/mtgo/pickup/w.json"], status)
    assert checked == 12 and not [f for f in failures if "pickup" in f.path]


def test_pickup_malformed_structure(tmp_path):
    pickup = tmp_path / "stats/standard/mtgo/pickup"
    pickup.mkdir(parents=True)
    (pickup / "index.json").write_text('{"weeks": {}}', encoding="utf-8")
    status = {"authoritative_documents": {s: [] for s in ("reading_order", "agent_adapter_documents", "historical_documents")}}
    _, failures, _ = validator.validate_references(tmp_path, ["stats/standard/mtgo/pickup/index.json"], status)
    assert failures and failures[0].category == "References"


def test_content_failure_exit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_repository.py"])
    monkeypatch.setattr(validator, "tracked_files", lambda root: [])
    monkeypatch.setattr(validator, "validate_files", lambda root, names: ({"Python": 0, "JSON": 0, "YAML": 0}, [validator.Failure("JSON", "a.json", "bad")], {}))
    assert validator.main() == 1 and "RESULT: FAIL" in capsys.readouterr().out


def test_infrastructure_failure_exit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_repository.py"])
    monkeypatch.setattr(validator, "repository_root", lambda: (_ for _ in ()).throw(validator.InfrastructureError("bad")))
    assert validator.main() == 2 and "RESULT: ERROR" in capsys.readouterr().out


def test_help_exit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_repository.py", "--help"])
    with pytest.raises(SystemExit) as exc:
        validator.main()
    assert exc.value.code == 0


def test_deterministic_failure_sorting():
    failures = [validator.Failure("YAML", "z", "b"), validator.Failure("Python", "a", "a"), validator.Failure("JSON", "b", "a")]
    ordered = sorted(failures, key=lambda f: (validator.CATEGORY_ORDER[f.category], f.path, f.line or 0, f.column or 0, f.message))
    assert [f.category for f in ordered] == ["Python", "JSON", "YAML"]


def test_source_safety_invariants():
    source = (ROOT / "validate_repository.py").read_text(encoding="utf-8")
    assert "shell=True" not in source and "write_text" not in source and "requests" not in source


def test_real_cli_smoke():
    result = subprocess.run([sys.executable, "-B", str(ROOT / "validate_repository.py")], cwd=ROOT, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
    assert result.returncode == 0 and "RESULT: PASS" in result.stdout


def test_unsupported_cli_argument():
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "validate_repository.py"), "--unsupported-p1-04-option"],
        cwd=ROOT,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
    assert "RESULT: PASS" not in result.stdout
    assert "Traceback" not in result.stderr
