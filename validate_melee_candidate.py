"""Validate one Melee production candidate before review-branch publication."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "1.1.0"


class MeleeCandidateError(RuntimeError):
    """Raised when candidate inspection cannot be completed."""


@dataclass(frozen=True)
class Change:
    status: str
    path: str


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise MeleeCandidateError(result.stderr.strip() or "git command failed")
    return result.stdout


def collect_changes(root: Path) -> list[Change]:
    output = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    changes: list[Change] = []
    for line in output.splitlines():
        if len(line) < 4:
            raise MeleeCandidateError(f"cannot parse git status line: {line!r}")
        changes.append(Change(line[:2], line[3:].replace("\\", "/")))
    return changes


def _catalog_snapshot(root: Path, format_id: str) -> dict[str, Any]:
    path = root / "stats" / format_id / "melee" / "index.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MeleeCandidateError(f"{path}: cannot read event catalog") from exc
    if not isinstance(catalog, dict):
        raise MeleeCandidateError(f"{path}: must contain a JSON object")
    expected_identity = {
        "document_type": "event_catalog",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": format_id,
    }
    for field, expected in expected_identity.items():
        if catalog.get(field) != expected:
            raise MeleeCandidateError(f"{path}: invalid catalog {field}")
    events = catalog.get("events")
    if not isinstance(events, list) or not events:
        raise MeleeCandidateError(f"{path}: catalog has no events")
    event_ids: list[str] = []
    for event in events:
        candidate_id = event.get("event_id") if isinstance(event, dict) else None
        if not isinstance(candidate_id, str) or not candidate_id.isdecimal():
            raise MeleeCandidateError(f"{path}: catalog has an invalid event")
        if candidate_id in event_ids:
            raise MeleeCandidateError(
                f"{path}: catalog has duplicate event {candidate_id}"
            )
        event_ids.append(candidate_id)
    default_event_id = catalog.get("default_event_id")
    if default_event_id not in event_ids:
        raise MeleeCandidateError(f"{path}: catalog has an invalid default event")
    return {
        "schema_version": catalog.get("schema_version"),
        "active_taxonomy": catalog.get("active_taxonomy"),
        "default_event_id": default_event_id,
        "events": events,
    }


def snapshot_state(root: Path, event_id: str, format_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "format": format_id,
        "head": _git(root, "rev-parse", "HEAD").strip(),
        "catalog": _catalog_snapshot(root, format_id),
    }


def _allowed_path(path: str, event_id: str, format_id: str) -> bool:
    if path == "stats/catalog.json":
        return True
    event_file = f"{event_id}.json"
    if path.startswith(f"data_raw/melee/{event_id}/"):
        return True
    if path in {
        f"data/{format_id}/melee/events/{event_file}",
        f"data/{format_id}/melee/classifications/{event_file}",
        f"data/{format_id}/melee/opportunities/{event_file}",
        f"stats/{format_id}/melee/index.json",
    }:
        return True
    return path in {
        f"stats/{format_id}/melee/events/{event_id}/{name}.json"
        for name in ("overview", "decks", "matchup", "quality", "meta")
    }


def _validate_json_identity(
    root: Path, change: Change, event_id: str, format_id: str
) -> list[str]:
    if not change.path.endswith(".json") or change.path.startswith("data_raw/"):
        return []
    try:
        value = json.loads((root / change.path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{change.path}: cannot read JSON: {exc}"]
    if not isinstance(value, dict):
        return [f"{change.path}: must contain a JSON object"]
    failures: list[str] = []
    if change.path == "stats/catalog.json":
        return []
    if change.path != f"stats/{format_id}/melee/index.json":
        if value.get("event_id") != event_id:
            failures.append(f"{change.path}: event_id does not match {event_id}")
    if value.get("format") != format_id:
        failures.append(f"{change.path}: format does not match {format_id}")
    if value.get("source") != "melee":
        failures.append(f"{change.path}: source must equal melee")
    return failures


def _event_map(catalog: dict[str, Any], *, label: str) -> dict[str, dict[str, Any]]:
    events = catalog.get("events")
    if not isinstance(events, list) or not events:
        raise MeleeCandidateError(f"{label} catalog has no events")
    result: dict[str, dict[str, Any]] = {}
    for event in events:
        event_id = event.get("event_id") if isinstance(event, dict) else None
        if not isinstance(event_id, str) or not event_id.isdecimal():
            raise MeleeCandidateError(f"{label} catalog has an invalid event")
        if event_id in result:
            raise MeleeCandidateError(
                f"{label} catalog has duplicate event {event_id}"
            )
        result[event_id] = event
    return result


def _validate_catalog_cohort(
    root: Path,
    baseline: dict[str, Any],
    event_id: str,
    format_id: str,
) -> list[str]:
    baseline_catalog = baseline.get("catalog")
    if not isinstance(baseline_catalog, dict):
        return ["baseline has no catalog snapshot"]
    try:
        current_catalog = _catalog_snapshot(root, format_id)
        before = _event_map(baseline_catalog, label="baseline")
        after = _event_map(current_catalog, label="candidate")
    except MeleeCandidateError as exc:
        return [str(exc)]

    failures: list[str] = []
    missing = sorted(set(before) - set(after))
    if missing:
        failures.append(f"event catalog removed existing events: {', '.join(missing)}")
    unexpected = sorted(set(after) - set(before) - {event_id})
    if unexpected:
        failures.append(
            f"event catalog added events outside the candidate: {', '.join(unexpected)}"
        )
    if event_id not in after:
        failures.append(f"event catalog does not contain candidate event {event_id}")
    if current_catalog.get("default_event_id") != baseline_catalog.get(
        "default_event_id"
    ):
        failures.append("event catalog changed the existing default event")
    for protected_id in sorted(set(before) - {event_id}):
        if protected_id in after and after[protected_id] != before[protected_id]:
            failures.append(
                f"event catalog rewrote existing event {protected_id}"
            )
    if set(before) - {event_id}:
        if current_catalog.get("schema_version") != baseline_catalog.get(
            "schema_version"
        ):
            failures.append("event catalog changed the existing cohort schema")
        if current_catalog.get("active_taxonomy") != baseline_catalog.get(
            "active_taxonomy"
        ):
            failures.append("event catalog changed the existing active taxonomy")
    return failures


def validate_candidate(
    root: Path,
    baseline: dict[str, Any],
    changes: Sequence[Change],
) -> tuple[dict[str, Any], list[str]]:
    event_id = baseline.get("event_id")
    format_id = baseline.get("format")
    failures: list[str] = []
    if baseline.get("schema_version") != SCHEMA_VERSION:
        failures.append("baseline has an unsupported schema_version")
    if not isinstance(event_id, str) or not event_id.isdecimal():
        failures.append("baseline has an invalid event_id")
    if not isinstance(format_id, str) or not format_id:
        failures.append("baseline has an invalid format")
    if failures:
        return {"changed_paths": len(changes)}, failures

    for change in changes:
        if "D" in change.status:
            failures.append(f"{change.path}: deletion is not allowed")
            continue
        if not _allowed_path(change.path, event_id, format_id):
            failures.append(f"{change.path}: outside the Melee candidate boundary")
            continue
        if change.path.startswith("data_raw/") and change.status != "??":
            failures.append(f"{change.path}: retained raw evidence is immutable")
            continue
        failures.extend(_validate_json_identity(root, change, event_id, format_id))
    failures.extend(_validate_catalog_cohort(root, baseline, event_id, format_id))
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "format": format_id,
        "changed_paths": len(changes),
    }, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--event-id", required=True)
    snapshot.add_argument("--format", required=True, dest="format_id")
    snapshot.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            changes = collect_changes(ROOT)
            if changes:
                raise MeleeCandidateError("baseline snapshot requires a clean checkout")
            state = snapshot_state(ROOT, args.event_id, args.format_id)
            args.output.write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n"
            )
            print(f"Melee candidate baseline PASS: {args.output}")
            return 0
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        report, failures = validate_candidate(ROOT, baseline, collect_changes(ROOT))
    except (MeleeCandidateError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Melee candidate validation ERROR: {exc}")
        return 2
    if failures:
        print(f"Melee candidate validation FAIL: failures={len(failures)}")
        for failure in failures:
            print(failure)
        return 1
    print(
        "Melee candidate validation PASS: "
        f"event={report['event_id']} changed_paths={report['changed_paths']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
