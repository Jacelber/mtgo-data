"""Run deterministic, read-only validation of repository content."""

from __future__ import annotations

import argparse
import ast
import io
import json
import ntpath
import subprocess
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class InfrastructureError(Exception):
    """Indicate that validation could not be performed reliably."""


@dataclass(frozen=True)
class Failure:
    category: str
    path: str
    message: str
    line: int | None = None
    column: int | None = None


CATEGORY_ORDER = {"Python": 0, "JSON": 1, "YAML": 2, "References": 3}


def repository_root() -> Path:
    try:
        return Path(__file__).resolve().parent
    except OSError as exc:
        raise InfrastructureError(f"cannot determine repository root: {exc}") from exc


def tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InfrastructureError(f"cannot obtain tracked-file inventory: {exc}") from exc
    try:
        return sorted(name for name in result.stdout.decode("utf-8").split("\0") if name)
    except UnicodeDecodeError as exc:
        raise InfrastructureError(f"tracked-file inventory is not UTF-8: {exc}") from exc


def safe_path(root: Path, name: str) -> Path:
    if "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise InfrastructureError(f"unsafe repository path: {name}")
    path = (root / Path(name)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise InfrastructureError(f"path escapes repository: {name}") from exc
    return path


def read_bytes(root: Path, name: str) -> bytes:
    path = safe_path(root, name)
    try:
        if not path.is_file():
            raise InfrastructureError(f"listed file is not a regular file: {name}")
        return path.read_bytes()
    except OSError as exc:
        raise InfrastructureError(f"cannot safely read {name}: {exc}") from exc


def content_failure(category: str, path: str, exc: Exception) -> Failure:
    line = column = None
    if isinstance(exc, SyntaxError):
        line, column = exc.lineno, exc.offset
    elif isinstance(exc, json.JSONDecodeError):
        line, column = exc.lineno, exc.colno
    elif isinstance(exc, yaml.MarkedYAMLError) and exc.problem_mark is not None:
        line, column = exc.problem_mark.line + 1, exc.problem_mark.column + 1
    return Failure(category, path, f"{type(exc).__name__}: {exc}", line, column)


def decode_python(data: bytes) -> str:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data.decode(encoding)


def validate_files(root: Path, names: list[str]) -> tuple[dict[str, int], list[Failure], dict[str, Any]]:
    failures: list[Failure] = []
    parsed_status: dict[str, Any] = {}
    groups = {
        "Python": [n for n in names if n.lower().endswith(".py")],
        "JSON": [n for n in names if n.lower().endswith(".json")],
        "YAML": [n for n in names if n.lower().endswith((".yaml", ".yml"))],
    }
    for name in groups["Python"]:
        try:
            ast.parse(decode_python(read_bytes(root, name)), filename=name)
        except SyntaxError as exc:
            failures.append(content_failure("Python", name, exc))
        except (tokenize.TokenError, LookupError, UnicodeError) as exc:
            failures.append(content_failure("Python", name, exc))
    for name in groups["JSON"]:
        try:
            json.loads(read_bytes(root, name).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(content_failure("JSON", name, exc))
    for name in groups["YAML"]:
        try:
            value = yaml.safe_load(read_bytes(root, name).decode("utf-8"))
            if name == "docs/STATUS.yaml":
                parsed_status[name] = value
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            failures.append(content_failure("YAML", name, exc))
    counts = {label: len(files) for label, files in groups.items()}
    return counts, failures, parsed_status


def tracked_regular(root: Path, names: set[str], name: str, suffix: str | None = None) -> bool:
    if name not in names or (suffix and not name.lower().endswith(suffix)):
        return False
    return safe_path(root, name).is_file()


def safe_declared_reference(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if Path(value).is_absolute() or ntpath.splitdrive(value)[0] or value.startswith("//"):
        return False
    return ".." not in Path(value).parts


def reference_check(failures: list[Failure], path: str, message: str | None) -> None:
    if message:
        failures.append(Failure("References", path, message))


def validate_references(root: Path, names: list[str], status: dict[str, Any]) -> tuple[int, list[Failure], dict[str, int]]:
    failures: list[Failure] = []
    tracked = set(names)
    breakdown = {"authoritative-document paths": 0, "requirement includes": 0, "front-end templates": 0, "required Standard files": 0, "pickup week entries": 0}
    authoritative = status.get("authoritative_documents") if isinstance(status, dict) else None
    sections = ("reading_order", "agent_adapter_documents", "historical_documents")
    for section in sections:
        items = authoritative.get(section) if isinstance(authoritative, dict) else None
        if not isinstance(items, list):
            reference_check(failures, f"docs/STATUS.yaml:{section}", "required section is not a list")
            continue
        for index, item in enumerate(items):
            breakdown["authoritative-document paths"] += 1
            path = f"docs/STATUS.yaml:{section}[{index}]"
            value = item.get("path") if isinstance(item, dict) else None
            if not isinstance(value, str) or not value:
                reference_check(failures, path, f"path must be a non-empty string, got {value!r}")
            elif not safe_declared_reference(value):
                reference_check(failures, path, f"unsafe declared path {value!r}")
            else:
                if not tracked_regular(root, tracked, value):
                    reference_check(failures, path, f"missing tracked path {value}")
    for manifest in ("requirements.txt", "requirements-dev.txt"):
        if manifest not in tracked:
            continue
        for line_number, raw in enumerate(read_bytes(root, manifest).decode("utf-8").splitlines(), 1):
            text = raw.strip()
            target = None
            if text.startswith("-r="):
                target = text[3:]
            elif text.startswith("-r") and len(text) > 2 and not text[2].isspace():
                target = text[2:]
            elif text.startswith("-r "):
                target = text.split(None, 1)[1].strip()
            elif text.startswith("--requirement="):
                target = text.split("=", 1)[1].strip()
            elif text.startswith("--requirement "):
                target = text.split(None, 1)[1].strip()
            if target is None:
                continue
            breakdown["requirement includes"] += 1
            message = None
            if not target or "\\" in target or Path(target).is_absolute() or ".." in Path(target).parts:
                message = f"invalid requirement include {target!r}"
            else:
                resolved = (Path(manifest).parent / target).as_posix()
                if not tracked_regular(root, tracked, resolved):
                    message = f"missing tracked requirement include {target}"
            reference_check(failures, f"{manifest}:{line_number}", message)
    templates = [
        "stats/${currentFormat}/mtgo/meta.json",
        "stats/${currentFormat}/mtgo/range_${currentRange}w.json",
        "stats/${currentFormat}/mtgo/decks_${currentRange}w.json",
        "stats/${currentFormat}/mtgo/pickup/index.json",
        "stats/${currentFormat}/mtgo/pickup/${week}.json",
        "stats/${currentFormat}/mtgo/matchup_${mxRange}w.json",
    ]
    if "index.html" not in tracked:
        reference_check(failures, "index.html", "missing tracked index.html")
    else:
        html = read_bytes(root, "index.html").decode("utf-8")
        for template in templates:
            breakdown["front-end templates"] += 1
            reference_check(failures, "index.html", f"missing template {template}" if template not in html else None)
    required = [
        "stats/standard/mtgo/meta.json", "stats/standard/mtgo/range_1w.json",
        "stats/standard/mtgo/range_4w.json", "stats/standard/mtgo/range_12w.json",
        "stats/standard/mtgo/decks_1w.json", "stats/standard/mtgo/decks_4w.json",
        "stats/standard/mtgo/decks_12w.json", "stats/standard/mtgo/matchup_1w.json",
        "stats/standard/mtgo/matchup_4w.json", "stats/standard/mtgo/matchup_12w.json",
        "stats/standard/mtgo/pickup/index.json",
    ]
    for path in required:
        breakdown["required Standard files"] += 1
        reference_check(failures, path, None if tracked_regular(root, tracked, path, ".json") else "missing tracked regular JSON file")
    pickup = "stats/standard/mtgo/pickup/index.json"
    if tracked_regular(root, tracked, pickup, ".json"):
        try:
            data = json.loads(read_bytes(root, pickup).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            reference_check(failures, pickup, f"invalid pickup index: {type(exc).__name__}: {exc}")
        else:
            weeks = data.get("weeks") if isinstance(data, dict) else None
            if not isinstance(weeks, list):
                reference_check(failures, pickup, "weeks must be a list")
            else:
                for index, entry in enumerate(weeks):
                    breakdown["pickup week entries"] += 1
                    value = entry.get("file") if isinstance(entry, dict) else None
                    valid = isinstance(value, str) and bool(value) and value.endswith(".json") and Path(value).name == value and value not in (".", "..") and not Path(value).is_absolute() and "/" not in value and "\\" not in value and tracked_regular(root, tracked, f"stats/standard/mtgo/pickup/{value}", ".json")
                    reference_check(failures, f"{pickup}:weeks[{index}]", None if valid else f"invalid pickup week file {value!r}")
    checked = sum(breakdown.values())
    return checked, failures, breakdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tracked repository content read-only.")
    parser.parse_args()
    try:
        root = repository_root()
        tracked = tracked_files(root)
        candidates = sorted(set(tracked) | {"validate_repository.py"})
        counts, failures, parsed = validate_files(root, candidates)
        reference_count, reference_failures, breakdown = validate_references(root, tracked, parsed.get("docs/STATUS.yaml"))
        failures.extend(reference_failures)
        failures.sort(key=lambda f: (CATEGORY_ORDER[f.category], f.path, f.line or 0, f.column or 0, f.message))
        failed_paths = {category: {f.path for f in failures if f.category == category} for category in CATEGORY_ORDER}
        print("Repository validation")
        print(f"Repository root: {root}")
        for category in ("Python", "JSON", "YAML"):
            checked = counts[category]
            failed = len(failed_paths[category])
            print(f"{category}: checked={checked} passed={checked - failed} failed={failed}")
        print(f"References: checked={reference_count} passed={reference_count - len({f.path for f in reference_failures})} failed={len({f.path for f in reference_failures})}")
        for item in failures:
            location = f" line {item.line}, column {item.column}" if item.line is not None else ""
            print(f"{item.category}: {item.path}{location}: {item.message}")
        print("RESULT: PASS" if not failures else "RESULT: FAIL")
        return 0 if not failures else 1
    except InfrastructureError as exc:
        print(f"Repository validation infrastructure error: {exc}")
        print("RESULT: ERROR")
        return 2
    except Exception as exc:
        print(f"Repository validation infrastructure error: {type(exc).__name__}: {exc}")
        print("RESULT: ERROR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
