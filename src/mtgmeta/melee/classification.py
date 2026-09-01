"""Deterministic classification overlays for normalized Melee events.

The normalized event remains immutable production input.  This module adapts
submitted Constructed decklists to the shared classifier and writes a separate
participant-keyed overlay for later event statistics.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from ..classifier import ClassificationResult, ConditionEvidence, RuleMatch, classify_deck
from ..card_names import front_face_card_name
from ..config import load_rule_set
from ..deck import deck_to_counts
from ..rules import RuleSet


CLASSIFICATION_OVERLAY_SCHEMA_VERSION = "1.0.0"
CLASSIFIER_CONTRACT_VERSION = "1.0.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
SUPPORTED_SECTIONS = frozenset({"main", "sideboard"})


class MeleeClassificationError(ValueError):
    """Raised when a normalized event cannot be classified safely."""


def _classifier_card_name(name: str) -> str:
    """Bridge reviewed split cards to the shared classifier's legacy spelling."""

    stripped = name.strip()
    reviewed_split_names = {
        "Dead // Gone": "Dead/Gone",
        "Fire // Ice": "Fire/Ice",
    }
    return reviewed_split_names.get(stripped, front_face_card_name(stripped))


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _read_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MeleeClassificationError(
            f"{path}: cannot read a valid JSON object ({type(exc).__name__})"
        ) from exc
    if not isinstance(value, dict):
        raise MeleeClassificationError(f"{path}: root must be an object")
    return value, payload


def _repository_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise MeleeClassificationError(f"path escapes repository root: {path}") from exc


def _condition_evidence(item: ConditionEvidence) -> dict[str, Any]:
    return {
        "card": item.card,
        "zone": item.zone,
        "actual_count": item.actual_count,
        "min_count": item.min_count,
        "max_count": item.max_count,
        "exact_count": item.exact_count,
    }


def _rule_match(item: RuleMatch) -> dict[str, Any]:
    return {
        "archetype_id": item.archetype_id,
        "archetype_name": item.archetype_name,
        "subtype_id": item.subtype_id,
        "subtype_name": item.subtype_name,
        "rule_id": item.rule_id,
        "priority": item.priority,
        "evidence": [_condition_evidence(evidence) for evidence in item.evidence],
    }


def _selected(result: ClassificationResult) -> dict[str, Any] | None:
    if result.status != "classified":
        return None
    return {
        "archetype_id": result.archetype_id,
        "archetype_name": result.archetype_name,
        "subtype_id": result.subtype_id,
        "subtype_name": result.subtype_name,
        "rule_id": result.selected_rule_id,
        "priority": result.selected_priority,
    }


def _card_list(counts: Mapping[str, int]) -> list[dict[str, Any]]:
    return [
        {"name": name, "quantity": quantity}
        for name, quantity in sorted(counts.items())
    ]


def _adapt_decklist(decklist: Mapping[str, Any]) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    cards = decklist.get("cards")
    if not isinstance(cards, list):
        return None, ("decklist.cards must be a list",)

    main: list[dict[str, Any]] = []
    side: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, card in enumerate(cards):
        if not isinstance(card, Mapping):
            errors.append(f"decklist.cards[{index}] must be an object")
            continue
        name = card.get("name")
        quantity = card.get("quantity")
        section = card.get("section")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"decklist.cards[{index}].name must be a non-empty string")
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 1
        ):
            errors.append(f"decklist.cards[{index}].quantity must be a positive integer")
        if section not in SUPPORTED_SECTIONS:
            errors.append(
                f"decklist.cards[{index}].section {section!r} is not classifiable"
            )
        if errors and (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 1
            or section not in SUPPORTED_SECTIONS
        ):
            continue
        target = main if section == "main" else side
        target.append({"name": _classifier_card_name(name), "qty": quantity})

    if not main:
        errors.append("decklist must contain at least one main-deck card")
    if errors:
        return None, tuple(dict.fromkeys(errors))
    return {"main_deck": main, "sideboard": side}, ()


def _invalid_record(participant_id: str, errors: Sequence[str]) -> dict[str, Any]:
    return {
        "participant_id": participant_id,
        "classification_status": "invalid_deck",
        "selected": None,
        "matched_rules": [],
        "top_priority_matches": [],
        "overridden_matches": [],
        "conflict_matches": [],
        "conflict_kind": None,
        "priority_tie": False,
        "errors": list(errors),
        "unknown_deck": None,
    }


def _classification_record(
    participant_id: str,
    result: ClassificationResult,
    deck: Mapping[str, Any],
) -> dict[str, Any]:
    unknown_deck = None
    if result.status == "unknown":
        main_counts, side_counts = deck_to_counts(deck)
        unknown_deck = {
            "main_deck": _card_list(main_counts),
            "sideboard": _card_list(side_counts),
        }
    return {
        "participant_id": participant_id,
        "classification_status": result.status,
        "selected": _selected(result),
        "matched_rules": [_rule_match(item) for item in result.matched_rules],
        "top_priority_matches": [
            _rule_match(item) for item in result.top_priority_matches
        ],
        "overridden_matches": [
            _rule_match(item) for item in result.overridden_matches
        ],
        "conflict_matches": [_rule_match(item) for item in result.conflict_matches],
        "conflict_kind": result.conflict_kind,
        "priority_tie": result.priority_tie,
        "errors": list(result.errors),
        "unknown_deck": unknown_deck,
    }


def _rule_counts(rule_set: RuleSet) -> tuple[int, int, int]:
    return (
        len(rule_set.archetypes),
        sum(len(archetype.rules) for archetype in rule_set.archetypes),
        sum(len(archetype.subtypes) for archetype in rule_set.archetypes),
    )


def build_classification_overlay(
    event: Mapping[str, Any],
    rule_set: RuleSet,
    *,
    event_path: str,
    event_sha256: str,
    rule_path: str,
    rule_sha256: str,
) -> dict[str, Any]:
    """Classify every submitted decklist for the rule-set format."""

    metadata = event.get("metadata")
    if not isinstance(metadata, Mapping):
        raise MeleeClassificationError("event.metadata must be an object")
    event_id = metadata.get("event_id")
    source = metadata.get("source")
    constructed_format = metadata.get("constructed_format")
    if not isinstance(event_id, str) or not EVENT_ID_PATTERN.fullmatch(event_id):
        raise MeleeClassificationError("event.metadata.event_id must be numeric")
    if source != "melee":
        raise MeleeClassificationError("event.metadata.source must be 'melee'")
    if constructed_format != rule_set.format:
        raise MeleeClassificationError(
            f"event format {constructed_format!r} does not match rules {rule_set.format!r}"
        )

    decklists = event.get("decklists")
    if not isinstance(decklists, list):
        raise MeleeClassificationError("event.decklists must be a list")
    participants = event.get("participants")
    if not isinstance(participants, list):
        raise MeleeClassificationError("event.participants must be a list")
    participant_ids_in_event = []
    for index, participant in enumerate(participants):
        if not isinstance(participant, Mapping):
            raise MeleeClassificationError(
                f"event.participants[{index}] must be an object"
            )
        participant_id = participant.get("id")
        if not isinstance(participant_id, str) or not participant_id:
            raise MeleeClassificationError(
                f"event.participants[{index}].id must be a non-empty string"
            )
        participant_ids_in_event.append(participant_id)
    if len(participant_ids_in_event) != len(set(participant_ids_in_event)):
        raise MeleeClassificationError("event participant IDs must be unique")
    participant_id_set = set(participant_ids_in_event)

    eligible: list[Mapping[str, Any]] = []
    excluded_count = 0
    for index, decklist in enumerate(decklists):
        if not isinstance(decklist, Mapping):
            raise MeleeClassificationError(f"event.decklists[{index}] must be an object")
        if (
            decklist.get("status") == "submitted"
            and decklist.get("game_format") == rule_set.format
        ):
            eligible.append(decklist)
        else:
            excluded_count += 1

    participant_ids = [item.get("participant_id") for item in eligible]
    if any(not isinstance(value, str) or not value for value in participant_ids):
        raise MeleeClassificationError(
            "every submitted format decklist must have a participant_id"
        )
    if len(participant_ids) != len(set(participant_ids)):
        raise MeleeClassificationError(
            "submitted format decklists must have unique participant_id values"
        )
    missing_participants = sorted(set(participant_ids) - participant_id_set)
    if missing_participants:
        raise MeleeClassificationError(
            "submitted format decklists reference unknown participants: "
            + ", ".join(missing_participants)
        )

    subtype_parents = {
        archetype.id for archetype in rule_set.archetypes if archetype.subtypes
    }
    statuses: Counter[str] = Counter()
    parents: Counter[str] = Counter()
    subtypes: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    multiple_matches = 0
    overridden_matches = 0
    same_parent_multiple_subtype_matches = 0
    residual_subtype_violations = 0

    for decklist in sorted(eligible, key=lambda item: str(item["participant_id"])):
        participant_id = str(decklist["participant_id"])
        deck, adapter_errors = _adapt_decklist(decklist)
        if deck is None:
            record = _invalid_record(participant_id, adapter_errors)
            statuses["invalid_deck"] += 1
            records.append(record)
            continue

        result = classify_deck(rule_set, deck)
        statuses[result.status] += 1
        if len(result.matched_rules) > 1:
            multiple_matches += 1
        if result.overridden_matches:
            overridden_matches += 1
        candidates: dict[str, set[str]] = {}
        for match in result.matched_rules:
            if match.subtype_id is not None:
                candidates.setdefault(match.archetype_id, set()).add(match.subtype_id)
        if any(len(values) > 1 for values in candidates.values()):
            same_parent_multiple_subtype_matches += 1
        if result.status == "classified":
            assert result.archetype_id is not None
            parents[result.archetype_id] += 1
            if result.subtype_id is None:
                if result.archetype_id in subtype_parents:
                    residual_subtype_violations += 1
            else:
                subtypes[f"{result.archetype_id}/{result.subtype_id}"] += 1
        records.append(_classification_record(participant_id, result, deck))

    classified = statuses["classified"]
    selected_subtypes = sum(subtypes.values())
    parent_only = classified - selected_subtypes
    blocking_reasons = []
    if statuses["conflict"]:
        blocking_reasons.append("classification_conflicts")
    if statuses["invalid_deck"]:
        blocking_reasons.append("invalid_decks")
    if residual_subtype_violations:
        blocking_reasons.append("residual_subtype_violations")

    archetype_count, rule_count, subtype_count = _rule_counts(rule_set)
    return {
        "schema_version": CLASSIFICATION_OVERLAY_SCHEMA_VERSION,
        "source": "melee",
        "event_id": event_id,
        "format": rule_set.format,
        "classifier": {
            "name": "shared-rule-classifier",
            "contract_version": CLASSIFIER_CONTRACT_VERSION,
        },
        "input": {
            "event_path": event_path,
            "event_sha256": event_sha256,
            "event_schema_version": event.get("schema_version"),
            "event_decklist_count": len(decklists),
            "submitted_format_decklist_count": len(eligible),
            "excluded_decklist_count": excluded_count,
        },
        "taxonomy": {
            "rule_path": rule_path,
            "rule_sha256": rule_sha256,
            "rule_schema_version": rule_set.schema_version,
            "archetype_count": archetype_count,
            "rule_count": rule_count,
            "subtype_count": subtype_count,
        },
        "summary": {
            "total_records": len(records),
            "classified": classified,
            "unknown": statuses["unknown"],
            "conflicts": statuses["conflict"],
            "invalid_decks": statuses["invalid_deck"],
            "multiple_matches": multiple_matches,
            "overridden_matches": overridden_matches,
            "selected_subtypes": selected_subtypes,
            "parent_only": parent_only,
            "same_parent_multiple_subtype_matches": (
                same_parent_multiple_subtype_matches
            ),
            "residual_subtype_violations": residual_subtype_violations,
            "selected_by_parent": dict(sorted(parents.items())),
            "selected_by_subtype": dict(sorted(subtypes.items())),
            "strict_validation": "fail" if blocking_reasons else "pass",
        },
        "quality": {
            "status": "blocked" if blocking_reasons else "pass",
            "blocking": bool(blocking_reasons),
            "blocking_reasons": blocking_reasons,
            "unknowns_blocking": False,
        },
        "records": records,
    }


def classification_overlay_bytes(document: Mapping[str, Any]) -> bytes:
    """Return canonical human-reviewable UTF-8 bytes."""

    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def build_classification_overlay_from_paths(
    event_path: Path,
    rule_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Load, hash, and classify one normalized event with one shared rule set."""

    root = repository_root.resolve()
    event, event_bytes = _read_json_object(event_path)
    try:
        rule_bytes = rule_path.read_bytes()
    except OSError as exc:
        raise MeleeClassificationError(f"{rule_path}: cannot read rules") from exc
    rule_set = load_rule_set(rule_path)
    return build_classification_overlay(
        event,
        rule_set,
        event_path=_repository_relative(event_path, root),
        event_sha256=_sha256_bytes(event_bytes),
        rule_path=_repository_relative(rule_path, root),
        rule_sha256=_sha256_bytes(rule_bytes),
    )


def write_classification_overlay(path: Path, payload: bytes) -> bool:
    """Atomically write bytes and return whether an identical file was reused."""

    if path.is_file() and path.read_bytes() == payload:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic shared-classifier overlay for one Melee event."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", required=True, dest="format_id")
    parser.add_argument("--event-id", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="atomically write the overlay; default mode is read-only",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail without writing when conflicts, invalid decks, or residual subtypes exist",
    )
    args = parser.parse_args(argv)

    if not FORMAT_PATTERN.fullmatch(args.format_id):
        parser.error("--format must be a lowercase hyphenated identifier")
    if not EVENT_ID_PATTERN.fullmatch(args.event_id):
        parser.error("--event-id must be a positive numeric identifier")

    root = args.root.resolve()
    event_path = root / "data" / args.format_id / "melee" / "events" / (
        f"{args.event_id}.json"
    )
    rule_path = root / "my_archetypes" / f"{args.format_id}.yaml"
    output_path = root / "data" / args.format_id / "melee" / "classifications" / (
        f"{args.event_id}.json"
    )
    try:
        document = build_classification_overlay_from_paths(
            event_path,
            rule_path,
            root,
        )
        payload = classification_overlay_bytes(document)
        summary = document["summary"]
        if args.strict and document["quality"]["blocking"]:
            print(
                "Melee classification strict validation FAIL: "
                + ", ".join(document["quality"]["blocking_reasons"]),
                file=sys.stderr,
            )
            return 1
        reused = False
        if args.execute:
            reused = write_classification_overlay(output_path, payload)
        print(
            json.dumps(
                {
                    "event_id": args.event_id,
                    "format": args.format_id,
                    "mode": "execute" if args.execute else "dry-run",
                    "output_path": (
                        _repository_relative(output_path, root) if args.execute else None
                    ),
                    "reused": reused,
                    "records": summary["total_records"],
                    "classified": summary["classified"],
                    "unknown": summary["unknown"],
                    "conflicts": summary["conflicts"],
                    "invalid_decks": summary["invalid_decks"],
                    "strict_validation": summary["strict_validation"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (MeleeClassificationError, OSError, ValueError) as exc:
        print(f"Melee classification ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
