"""Validate an MTGO production candidate without relying on frozen data counts."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
BASELINE_SCHEMA_VERSION = "2.0.0"
PRODUCTION_CAPABILITIES = frozenset(
    {
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
        "weekly_pickup",
        "metadata_generation",
        "catalog_generation",
    }
)


class CandidateValidationError(RuntimeError):
    """Raised when candidate-validation infrastructure cannot be trusted."""


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    previous_path: str | None = None


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CandidateValidationError(f"git {' '.join(args)} failed: {exc}") from exc
    return result.stdout


def collect_changes(root: Path) -> list[Change]:
    """Return tracked and untracked candidate changes relative to HEAD."""

    raw = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    records = raw.split("\0")
    changes: list[Change] = []
    index = 0
    while index < len(records) and records[index]:
        record = records[index]
        if len(record) < 4 or record[2] != " ":
            raise CandidateValidationError(f"unrecognized git status record: {record!r}")
        status = record[:2]
        path = record[3:].replace("\\", "/")
        previous = None
        index += 1
        if "R" in status or "C" in status:
            if index >= len(records) or not records[index]:
                raise CandidateValidationError("rename/copy status omitted its original path")
            previous = records[index].replace("\\", "/")
            index += 1
        changes.append(Change(status=status, path=path, previous_path=previous))
    return changes


def _configured_formats(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    registry_path = root / "configs" / "formats.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    formats = registry.get("formats") if isinstance(registry, dict) else None
    if not isinstance(formats, list):
        raise CandidateValidationError(f"{registry_path}: formats must be a list")
    collection_formats = []
    product_formats = []
    for item in formats:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise CandidateValidationError(f"{registry_path}: invalid format entry")
        mtgo = item.get("mtgo")
        if not isinstance(mtgo, dict):
            raise CandidateValidationError(f"{registry_path}: invalid MTGO format entry")
        if mtgo.get("event_collection_enabled") is True:
            collection_formats.append(item["id"])
        capabilities = mtgo.get("capabilities")
        if not isinstance(capabilities, list) or any(
            not isinstance(capability, str) for capability in capabilities
        ):
            raise CandidateValidationError(
                f"{registry_path}: invalid MTGO capabilities for {item['id']}"
            )
        if mtgo.get("enabled") is True and PRODUCTION_CAPABILITIES <= set(capabilities):
            product_formats.append(item["id"])
    if not collection_formats:
        raise CandidateValidationError(f"{registry_path}: no MTGO collection formats enabled")
    if not product_formats:
        raise CandidateValidationError(f"{registry_path}: no complete MTGO products enabled")
    return tuple(collection_formats), tuple(product_formats)


def _ledger_entries(root: Path) -> list[str]:
    path = root / "fetched.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def snapshot_state(root: Path) -> dict[str, Any]:
    collection_formats, product_formats = _configured_formats(root)
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "event_files": {
            format_id: len(list((root / "data" / format_id).glob("*.json")))
            for format_id in collection_formats
        },
        "match_files": {
            format_id: len(
                list((root / "data" / format_id / "mtgo" / "matches").glob("*.json"))
            )
            for format_id in product_formats
        },
        "fetched_entries": len(_ledger_entries(root)),
    }


def _allowed_path(
    path: str,
    collection_formats: tuple[str, ...],
    product_formats: tuple[str, ...],
) -> bool:
    parts = PurePosixPath(path).parts
    if path == "fetched.txt":
        return True
    if len(parts) == 3 and parts[0] == "data" and parts[1] in collection_formats:
        return parts[2].endswith(".json")
    if (
        len(parts) == 5
        and parts[0] == "data"
        and parts[1] in product_formats
        and parts[2:4] == ("mtgo", "matches")
    ):
        return parts[4].endswith(".json")
    return (
        len(parts) >= 3
        and parts[0] in {"stats", "reports"}
        and parts[1] in product_formats
        and parts[2] == "mtgo"
    )


def _area(path: str) -> str:
    if path == "fetched.txt":
        return "ledger"
    parts = PurePosixPath(path).parts
    if (
        len(parts) >= 4
        and parts[0] == "data"
        and parts[2:4] == ("mtgo", "matches")
    ):
        return f"matches_{parts[1]}"
    if parts and parts[0] == "data" and len(parts) > 1:
        return f"events_{parts[1]}"
    if len(parts) > 1 and parts[0] == "stats":
        return f"statistics_{parts[1]}"
    if len(parts) > 1 and parts[0] == "reports":
        return f"reports_{parts[1]}"
    return "outside_candidate_scope"


def _allowed_new_path(
    path: str,
    collection_formats: tuple[str, ...],
    product_formats: tuple[str, ...],
) -> bool:
    parts = PurePosixPath(path).parts
    if len(parts) == 3 and parts[0] == "data" and parts[1] in collection_formats:
        return parts[2].endswith(".json")
    if (
        len(parts) == 5
        and parts[0] == "data"
        and parts[1] in product_formats
        and parts[2:4] == ("mtgo", "matches")
    ):
        return parts[4].endswith(".json")
    if (
        len(parts) == 5
        and parts[0] == "stats"
        and parts[1] in product_formats
        and parts[2:4] == ("mtgo", "pickup")
    ):
        return bool(
            re.fullmatch(r"(?:candidates|base_reference)_\d{4}-W\d{2}\.yaml", parts[4])
        )
    return False


def _validate_event_document(path: str, value: Any) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path}: event JSON must be an object"]
    required = {"event_id", "description", "format", "starttime", "player_count", "inplayoffs", "players"}
    missing = sorted(required - set(value))
    failures = [f"{path}: missing event fields: {', '.join(missing)}"] if missing else []
    if "players" in value and (not isinstance(value["players"], list) or not value["players"]):
        failures.append(f"{path}: players must be a non-empty list")
    parts = PurePosixPath(path).parts
    expected_format = parts[1].upper() if len(parts) >= 2 else ""
    actual_format = str(value.get("format", "")).strip().upper()
    if actual_format.startswith("C"):
        actual_format = actual_format[1:]
    if actual_format and actual_format != expected_format:
        failures.append(
            f"{path}: embedded format {actual_format!r} does not match {expected_format!r}"
        )
    return failures


def _validate_match_document(path: str, value: Any) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path}: match JSON must be an object"]
    failures = []
    if "event_id" not in value:
        failures.append(f"{path}: match JSON is missing event_id")
    if not isinstance(value.get("matches"), list):
        failures.append(f"{path}: matches must be a list")
    return failures


def _validate_changed_document(root: Path, change: Change) -> list[str]:
    path = root / PurePosixPath(change.path)
    if path.is_symlink():
        return [f"{change.path}: symbolic links are not allowed in production output"]
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return [f"{change.path}: candidate path escapes the repository root"]
    if not path.is_file():
        return [f"{change.path}: changed candidate path is not a regular file"]
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() in {".yaml", ".yml"}:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            return []
        else:
            return []
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"{change.path}: cannot parse candidate file: {exc}"]
    parts = PurePosixPath(change.path).parts
    if len(parts) == 3 and parts[0] == "data":
        return _validate_event_document(change.path, value)
    if (
        len(parts) == 5
        and parts[0] == "data"
        and parts[2:4] == ("mtgo", "matches")
    ):
        return _validate_match_document(change.path, value)
    return []


def validate_candidate(
    root: Path,
    baseline: dict[str, Any],
    changes: list[Change],
) -> tuple[dict[str, Any], list[str]]:
    collection_formats, product_formats = _configured_formats(root)
    current = snapshot_state(root)
    failures: list[str] = []
    if baseline.get("schema_version") != BASELINE_SCHEMA_VERSION:
        failures.append("baseline snapshot has an unsupported schema_version")
    baseline_events = baseline.get("event_files")
    if (
        not isinstance(baseline_events, dict)
        or set(baseline_events) != set(collection_formats)
    ):
        failures.append("baseline snapshot does not match the configured collection formats")
        baseline_events = {}
    for format_id in collection_formats:
        before = baseline_events.get(format_id)
        after = current["event_files"][format_id]
        if not isinstance(before, int):
            failures.append(f"baseline event count for {format_id} is invalid")
        elif after < before:
            failures.append(f"event file count decreased for {format_id}: {before} -> {after}")
    baseline_matches = baseline.get("match_files")
    if (
        not isinstance(baseline_matches, dict)
        or set(baseline_matches) != set(product_formats)
    ):
        failures.append("baseline snapshot does not match the configured product formats")
        baseline_matches = {}
    for format_id in product_formats:
        before = baseline_matches.get(format_id)
        after = current["match_files"][format_id]
        if not isinstance(before, int):
            failures.append(f"baseline match count for {format_id} is invalid")
        elif after < before:
            failures.append(
                f"match file count decreased for {format_id}: {before} -> {after}"
            )
    before_fetched = baseline.get("fetched_entries")
    if not isinstance(before_fetched, int):
        failures.append("baseline fetched_entries is invalid")
    elif current["fetched_entries"] < before_fetched:
        failures.append(
            f"fetched_entries decreased: {before_fetched} -> {current['fetched_entries']}"
        )

    for change in changes:
        if "U" in change.status:
            failures.append(f"{change.path}: unmerged candidate change")
            continue
        if change.previous_path is not None or "R" in change.status or "C" in change.status:
            failures.append(f"{change.path}: rename/copy is not allowed in production output")
            continue
        if "D" in change.status:
            failures.append(f"{change.path}: deletion is not allowed in production output")
            continue
        if not _allowed_path(change.path, collection_formats, product_formats):
            failures.append(f"{change.path}: change is outside the production publication scope")
            continue
        if (change.status == "??" or "A" in change.status) and not _allowed_new_path(
            change.path,
            collection_formats,
            product_formats,
        ):
            failures.append(
                f"{change.path}: new generated path is not in the approved creation scope"
            )
            continue
        failures.extend(_validate_changed_document(root, change))

    ledger = _ledger_entries(root)
    if len(ledger) != len(set(ledger)):
        failures.append("fetched.txt contains duplicate entries")
    invalid_ledger = [entry for entry in ledger if not entry.startswith("/decklist/")]
    if invalid_ledger:
        failures.append("fetched.txt contains entries outside /decklist/")

    area_counts = Counter(_area(change.path) for change in changes)
    report = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "change_count": len(changes),
        "changes_by_area": dict(sorted(area_counts.items())),
        "baseline": baseline,
        "candidate": current,
        "event_file_deltas": {
            format_id: current["event_files"][format_id] - baseline_events.get(format_id, current["event_files"][format_id])
            for format_id in collection_formats
        },
        "match_file_deltas": {
            format_id: current["match_files"][format_id]
            - baseline_matches.get(format_id, current["match_files"][format_id])
            for format_id in product_formats
        },
        "fetched_entry_delta": current["fetched_entries"] - baseline.get("fetched_entries", current["fetched_entries"]),
    }
    return report, sorted(set(failures))


def _append_actions_summary(report: dict[str, Any], failures: list[str]) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    with Path(target).open("a", encoding="utf-8") as handle:
        handle.write("## Production candidate validation\n\n")
        handle.write(f"- Result: {'FAIL' if failures else 'PASS'}\n")
        handle.write(f"- Candidate changes: {report['change_count']}\n")
        handle.write(f"- Event deltas: `{json.dumps(report['event_file_deltas'], sort_keys=True)}`\n")
        handle.write(
            f"- Match-file deltas: `{json.dumps(report['match_file_deltas'], sort_keys=True)}`\n"
        )
        handle.write(f"- Fetched-ledger delta: {report['fetched_entry_delta']}\n")
        if failures:
            handle.write(f"- Blocking failures: {len(failures)}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="record the clean production baseline")
    snapshot.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate", help="validate generated candidate changes")
    validate.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "snapshot":
            existing_changes = collect_changes(root)
            if existing_changes:
                paths = ", ".join(change.path for change in existing_changes[:5])
                suffix = " ..." if len(existing_changes) > 5 else ""
                raise CandidateValidationError(
                    f"baseline snapshot requires a clean checkout; found: {paths}{suffix}"
                )
            state = snapshot_state(root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            print(f"Production baseline snapshot PASS: {args.output}")
            return 0
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        report, failures = validate_candidate(root, baseline, collect_changes(root))
        _append_actions_summary(report, failures)
        print(json.dumps(report, indent=2, sort_keys=True))
        for failure in failures:
            print(f"FAIL: {failure}")
        print("Production candidate validation PASS" if not failures else "Production candidate validation FAIL")
        return 0 if not failures else 1
    except (CandidateValidationError, OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
        print(f"Production candidate validation ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
