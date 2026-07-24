"""Validated retention of one complete Melee snapshot as normalized input.

This module never fetches data. It accepts only a complete immutable v2 raw
snapshot under the approved event path, verifies the manifest and every
artifact, applies semantic normalization and the publication quality gate, and
writes one canonical normalized event atomically. Re-running it with the same
snapshot reuses byte-identical output; it never silently replaces different
production input.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .config import MeleeConfigError, MeleeEventDefinition, load_melee_event_registry
from .normalize import normalize_parsed_snapshot
from .parser import MeleeSourceParseError, ParsedMeleeSnapshot, parse_raw_snapshot
from .quality import MeleePublicationBlocked, MeleeQualityError, build_publication_payload


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_SCHEMA = ROOT / "schemas" / "melee-raw-archive.schema.json"
SNAPSHOT_NAME_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9]{2,4}$")
REQUIRED_RESOURCE_TYPES = frozenset({"tournament", "standings", "matches", "decklist"})


class MeleeRetentionError(ValueError):
    """Raised when a snapshot cannot become canonical normalized input."""


@dataclass(frozen=True)
class MeleeRetentionResult:
    event_id: str
    snapshot_path: Path
    normalized_path: Path
    snapshot_manifest_sha256: str
    normalized_sha256: str
    response_count: int
    participant_count: int
    decklist_count: int
    round_count: int
    match_count: int
    eligible_constructed_match_count: int
    quality_status: str
    quality_issue_codes: tuple[str, ...]
    reused: bool


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MeleeRetentionError(f"manifest.json contains duplicate key {key!r}")
        result[key] = value
    return result


def _load_manifest(snapshot: Path, schema_path: Path) -> tuple[dict[str, Any], bytes]:
    manifest_path = snapshot / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MeleeRetentionError(f"could not read raw snapshot contract: {exc}") from exc
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(manifest),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        first = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in first.absolute_path
        )
        raise MeleeRetentionError(
            f"raw snapshot manifest failed Schema validation at {location}: {first.message}"
        )
    if manifest["schema_version"] != "2.0.0":
        raise MeleeRetentionError("production retention requires complete raw manifest 2.0.0")
    return manifest, manifest_bytes


def _validated_snapshot_path(
    snapshot_path: str | Path,
    raw_root: str | Path,
    event: MeleeEventDefinition,
) -> Path:
    snapshot = Path(snapshot_path)
    root = Path(raw_root)
    if snapshot.is_symlink():
        raise MeleeRetentionError("raw snapshot path must not be a symlink")
    try:
        resolved_root = root.resolve(strict=True)
        resolved_snapshot = snapshot.resolve(strict=True)
    except OSError as exc:
        raise MeleeRetentionError(f"raw snapshot path is unavailable: {exc}") from exc
    expected_parent = resolved_root / "melee" / event.id
    if (
        resolved_snapshot.parent != expected_parent
        or not SNAPSHOT_NAME_PATTERN.fullmatch(resolved_snapshot.name)
        or resolved_snapshot.is_symlink()
        or not resolved_snapshot.is_dir()
    ):
        raise MeleeRetentionError(
            "snapshot must be one direct immutable collection under "
            f"{expected_parent}"
        )
    return resolved_snapshot


def _validate_snapshot_contents(snapshot: Path, manifest: dict[str, Any]) -> None:
    responses = manifest["responses"]
    resource_types = [item["resource_type"] for item in responses]
    if set(resource_types) != REQUIRED_RESOURCE_TYPES:
        missing = sorted(REQUIRED_RESOURCE_TYPES - set(resource_types))
        unexpected = sorted(set(resource_types) - REQUIRED_RESOURCE_TYPES)
        raise MeleeRetentionError(
            f"complete snapshot resource coverage is invalid: missing={missing} unexpected={unexpected}"
        )
    if resource_types.count("tournament") != 1:
        raise MeleeRetentionError("complete snapshot must contain exactly one tournament response")
    expected_names = {"manifest.json", *(item["path"] for item in responses)}
    actual_names: set[str] = set()
    for path in snapshot.iterdir():
        if path.is_symlink() or not path.is_file():
            raise MeleeRetentionError(f"snapshot contains a non-regular entry: {path.name}")
        actual_names.add(path.name)
    if actual_names != expected_names:
        raise MeleeRetentionError(
            "snapshot files do not exactly match the manifest: "
            f"missing={sorted(expected_names - actual_names)} "
            f"unlisted={sorted(actual_names - expected_names)}"
        )


def _normalized_path(data_root: str | Path, event: MeleeEventDefinition) -> Path:
    return Path(data_root) / event.format / "melee" / "events" / f"{event.id}.json"


def _write_canonical(path: Path, payload: bytes) -> bool:
    if path.is_symlink():
        raise MeleeRetentionError("normalized event path must not be a symlink")
    if path.exists():
        if not path.is_file():
            raise MeleeRetentionError("normalized event path is not a regular file")
        if path.read_bytes() == payload:
            return True
        raise MeleeRetentionError(
            "normalized event already exists with different bytes; "
            "review the new snapshot instead of overwriting production input"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise MeleeRetentionError(f"stale normalized-event temporary path exists: {temporary}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
            path.parent.parent.rmdir()
            path.parent.parent.parent.rmdir()
        except OSError:
            pass
        raise
    return False


def retain_normalized_event(
    event: MeleeEventDefinition,
    snapshot_path: str | Path,
    *,
    raw_root: str | Path = "data_raw",
    data_root: str | Path = "data",
    raw_schema_path: str | Path = DEFAULT_RAW_SCHEMA,
) -> MeleeRetentionResult:
    """Validate and atomically retain one complete snapshot's normalized event."""

    if not event.enabled or event.review_status != "verified":
        raise MeleeRetentionError("production retention requires an enabled verified event")
    snapshot = _validated_snapshot_path(snapshot_path, raw_root, event)
    manifest, manifest_bytes = _load_manifest(snapshot, Path(raw_schema_path))
    if manifest["event_id"] != event.id or manifest["event_url"] != event.url:
        raise MeleeRetentionError("raw snapshot identity does not match the whitelist event")
    _validate_snapshot_contents(snapshot, manifest)
    try:
        parsed: ParsedMeleeSnapshot = parse_raw_snapshot(snapshot)
        normalized = normalize_parsed_snapshot(
            parsed,
            event,
            normalized_at=parsed.fetched_at,
            raw_artifact_prefix=f"data_raw/melee/{event.id}/{snapshot.name}",
        )
        payload = build_publication_payload(normalized, event)
    except (MeleeSourceParseError, MeleeQualityError, MeleePublicationBlocked) as exc:
        raise MeleeRetentionError(f"snapshot failed normalized-event retention: {exc}") from exc
    target = _normalized_path(data_root, event)
    reused = _write_canonical(target, payload)
    document = json.loads(payload)
    issue_codes = tuple(sorted({item["code"] for item in document["quality"]["issues"]}))
    return MeleeRetentionResult(
        event_id=event.id,
        snapshot_path=snapshot,
        normalized_path=target,
        snapshot_manifest_sha256=sha256(manifest_bytes).hexdigest(),
        normalized_sha256=sha256(payload).hexdigest(),
        response_count=len(manifest["responses"]),
        participant_count=len(document["participants"]),
        decklist_count=len(document["decklists"]),
        round_count=len(document["rounds"]),
        match_count=len(document["matches"]),
        eligible_constructed_match_count=sum(
            bool(match["constructed_statistics_eligible"])
            for match in document["matches"]
        ),
        quality_status=document["quality"]["status"],
        quality_issue_codes=issue_codes,
        reused=reused,
    )


def _result_payload(
    event: MeleeEventDefinition,
    snapshot: Path,
    data_root: Path,
    result: MeleeRetentionResult | None,
) -> dict[str, object]:
    if result is None:
        return {
            "event_id": event.id,
            "mode": "dry-run",
            "snapshot_path": str(snapshot),
            "normalized_path": str(_normalized_path(data_root, event)),
        }
    return {
        "event_id": result.event_id,
        "mode": "execute",
        "snapshot_path": str(result.snapshot_path),
        "normalized_path": str(result.normalized_path),
        "snapshot_manifest_sha256": result.snapshot_manifest_sha256,
        "normalized_sha256": result.normalized_sha256,
        "responses": result.response_count,
        "participants": result.participant_count,
        "decklists": result.decklist_count,
        "rounds": result.round_count,
        "matches": result.match_count,
        "eligible_constructed_matches": result.eligible_constructed_match_count,
        "quality_status": result.quality_status,
        "quality_issue_codes": list(result.quality_issue_codes),
        "reused": result.reused,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and retain one complete Melee raw snapshot as normalized input."
    )
    parser.add_argument("--event-id", required=True, help="Enabled verified Melee tournament ID")
    parser.add_argument("--snapshot", type=Path, required=True, help="Complete immutable v2 snapshot")
    parser.add_argument("--registry", type=Path, default=Path("configs/melee_events.yaml"))
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write canonical normalized input; without this flag only print the path plan",
    )
    args = parser.parse_args(argv)
    try:
        registry = load_melee_event_registry(args.registry)
        event = registry.require_fetchable(args.event_id)
        result = (
            retain_normalized_event(
                event,
                args.snapshot,
                raw_root=args.raw_root,
                data_root=args.data_root,
            )
            if args.execute
            else None
        )
    except (MeleeConfigError, MeleeRetentionError, OSError, ValueError) as exc:
        print(f"Melee retention ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            _result_payload(event, args.snapshot, args.data_root, result),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "MeleeRetentionError",
    "MeleeRetentionResult",
    "main",
    "retain_normalized_event",
]
