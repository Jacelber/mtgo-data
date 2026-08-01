"""Create and validate bounded MTGO fetch-resume checkpoints.

The scheduled workflow stores this small manifest alongside a temporary
artifact containing only fetched inputs.  A checkpoint is valid only for the
same repository commit and the same configured collection plan; it is never a
publication input.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
EVENT_PREFIX = "events/"
MATCH_PREFIX = "matches/"


class CheckpointError(ValueError):
    """Raised when a checkpoint is malformed or incompatible."""


def _formats(value: str) -> list[str]:
    formats = value.split()
    if not formats or any(not item.isidentifier() for item in formats):
        raise CheckpointError("formats must be non-empty lowercase identifiers")
    if len(formats) != len(set(formats)):
        raise CheckpointError("formats must not contain duplicates")
    return formats


def expected_operations(event_formats: list[str], match_formats: list[str]) -> list[str]:
    return [
        *(f"{EVENT_PREFIX}{format_id}" for format_id in event_formats),
        *(f"{MATCH_PREFIX}{format_id}" for format_id in match_formats),
    ]


def new_checkpoint(repository: str, commit: str, event_formats: list[str], match_formats: list[str]) -> dict[str, Any]:
    if not repository or "/" not in repository:
        raise CheckpointError("repository must be an owner/name value")
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.lower()):
        raise CheckpointError("commit must be a full hexadecimal SHA-1")
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "commit": commit.lower(),
        "event_formats": event_formats,
        "match_formats": match_formats,
        "operations": {operation: "pending" for operation in expected_operations(event_formats, match_formats)},
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"cannot read checkpoint: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckpointError("checkpoint must be a JSON object")
    return value


def validate_checkpoint(
    value: dict[str, Any], repository: str, commit: str, event_formats: list[str], match_formats: list[str]
) -> None:
    expected = new_checkpoint(repository, commit, event_formats, match_formats)
    for key in ("schema_version", "repository", "commit", "event_formats", "match_formats"):
        if value.get(key) != expected[key]:
            raise CheckpointError(f"checkpoint {key} does not match this run")
    operations = value.get("operations")
    if not isinstance(operations, dict) or set(operations) != set(expected["operations"]):
        raise CheckpointError("checkpoint operation plan does not match this run")
    if any(status not in {"pending", "complete"} for status in operations.values()):
        raise CheckpointError("checkpoint operation state is invalid")


def _arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--event-formats", required=True)
    parser.add_argument("--match-formats", required=True)


def _expected_from_args(args: argparse.Namespace) -> tuple[str, str, list[str], list[str]]:
    return args.repository, args.commit, _formats(args.event_formats), _formats(args.match_formats)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("initialize", help="write a fresh pending checkpoint")
    _arguments(initialize)
    validate = commands.add_parser("validate", help="reject incompatible or malformed checkpoints")
    _arguments(validate)
    complete = commands.add_parser("complete", help="mark one planned operation complete")
    _arguments(complete)
    complete.add_argument("--operation", required=True)
    status = commands.add_parser("is-complete", help="exit zero only when one operation is complete")
    _arguments(status)
    status.add_argument("--operation", required=True)
    args = parser.parse_args(argv)
    try:
        repository, commit, event_formats, match_formats = _expected_from_args(args)
        if args.command == "initialize":
            _write(args.checkpoint, new_checkpoint(repository, commit, event_formats, match_formats))
            print(f"Initialized MTGO fetch checkpoint: {args.checkpoint}")
            return 0
        checkpoint = _load(args.checkpoint)
        validate_checkpoint(checkpoint, repository, commit, event_formats, match_formats)
        if args.command == "validate":
            print(f"MTGO fetch checkpoint PASS: {args.checkpoint}")
            return 0
        operations = checkpoint["operations"]
        if args.operation not in operations:
            raise CheckpointError(f"operation is not in the current plan: {args.operation}")
        if args.command == "complete":
            operations[args.operation] = "complete"
            _write(args.checkpoint, checkpoint)
            print(f"Completed MTGO fetch operation: {args.operation}")
            return 0
        return 0 if operations[args.operation] == "complete" else 1
    except CheckpointError as exc:
        print(f"MTGO fetch checkpoint ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
