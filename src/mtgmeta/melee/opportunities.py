"""Deterministic Constructed-opportunity ledger for one classified Melee event."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence


OPPORTUNITY_LEDGER_SCHEMA_VERSION = "1.0.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
POINT_RESULT_TYPES = frozenset(
    {"played_win", "played_loss", "played_draw", "intentional_draw", "bye"}
)
PLAYED_RESULT_TYPES = frozenset({"played_win", "played_loss", "played_draw"})
EVENT_STRUCTURES = frozenset(
    {"mixed", "constructed_day2", "constructed_single_stage"}
)


class MeleeOpportunityError(ValueError):
    """Raised when an opportunity ledger cannot be built without guessing."""


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _read_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        document = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise MeleeOpportunityError(f"{path}: cannot read JSON object") from exc
    if not isinstance(document, dict):
        raise MeleeOpportunityError(f"{path}: top level must be an object")
    return document, payload


def _repository_relative(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise MeleeOpportunityError(f"{path}: path is outside repository root") from exc
    return relative.as_posix()


def _objects_by_id(
    values: Any,
    *,
    field: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise MeleeOpportunityError(f"{label} must be a list")
    result: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise MeleeOpportunityError(f"{label}[{index}] must be an object")
        identifier = value.get(field)
        if not isinstance(identifier, str) or not identifier:
            raise MeleeOpportunityError(
                f"{label}[{index}].{field} must be a non-empty string"
            )
        if identifier in result:
            raise MeleeOpportunityError(f"{label} contains duplicate ID {identifier}")
        result[identifier] = value
    return result


def _classification_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    status = record.get("classification_status")
    selected = record.get("selected")
    if status == "classified":
        if not isinstance(selected, Mapping):
            raise MeleeOpportunityError(
                "classified records must contain a selected classification"
            )
        return {
            "status": "classified",
            "archetype_id": selected.get("archetype_id"),
            "archetype_name": selected.get("archetype_name"),
            "subtype_id": selected.get("subtype_id"),
            "subtype_name": selected.get("subtype_name"),
        }
    if status != "unknown" or selected is not None:
        raise MeleeOpportunityError(
            "opportunity ledger requires classified or explicit Unknown records"
        )
    return {
        "status": "unknown",
        "archetype_id": None,
        "archetype_name": None,
        "subtype_id": None,
        "subtype_name": None,
    }


def _scope_for_round(
    round_: Mapping[str, Any],
    event_structure: str,
) -> str:
    if event_structure == "constructed_single_stage":
        return "all_constructed"
    stage = round_.get("stage")
    if stage not in {"day1", "day2"}:
        raise MeleeOpportunityError(
            f"Constructed Swiss round {round_.get('id')} has unsupported stage {stage!r}"
        )
    return str(stage)


def _opponent_id(
    competitors: Sequence[Mapping[str, Any]],
    participant_id: str,
) -> str | None:
    opponents = [
        item.get("participant_id")
        for item in competitors
        if item.get("participant_id") != participant_id
    ]
    if not opponents:
        return None
    if len(opponents) != 1 or not isinstance(opponents[0], str):
        raise MeleeOpportunityError(
            f"match for {participant_id} does not identify exactly one opponent"
        )
    return opponents[0]


def _exclusion_reasons(
    *,
    result_type: str,
    win_rate_included: bool,
    matchup_included: bool,
    disqualified_match: bool,
) -> list[str]:
    reasons: list[str] = []
    if disqualified_match:
        reasons.append("disqualified_participant")
    if result_type == "intentional_draw":
        reasons.append("intentional_draw")
    elif result_type == "bye":
        reasons.append("bye")
    elif result_type == "awarded_win_top8_lock":
        reasons.append("top8_lock_exemption")
    elif result_type == "no_show":
        reasons.append("no_show")
    elif result_type in {"administrative_result", "unknown"}:
        reasons.append(result_type)
    if result_type in PLAYED_RESULT_TYPES and not (
        win_rate_included and matchup_included
    ) and not disqualified_match:
        reasons.append("source_match_ineligible")
    return reasons


def _source_opportunity(
    *,
    participant_id: str,
    participant_status: str,
    round_: Mapping[str, Any],
    match: Mapping[str, Any],
    competitors: Sequence[Mapping[str, Any]],
    competitor: Mapping[str, Any],
    disqualified_ids: set[str],
    event_structure: str,
) -> dict[str, Any]:
    result_type = competitor.get("result_type")
    source_points = competitor.get("match_points")
    if not isinstance(result_type, str):
        raise MeleeOpportunityError(
            f"match {match.get('id')} has a missing competitor result_type"
        )
    if not isinstance(source_points, int) or isinstance(source_points, bool):
        raise MeleeOpportunityError(
            f"match {match.get('id')} has a non-integer competitor match_points"
        )
    competitor_ids = {str(item.get("participant_id")) for item in competitors}
    disqualified_match = bool(competitor_ids & disqualified_ids)
    win_rate_included = bool(match.get("constructed_statistics_eligible"))
    matchup_included = bool(match.get("matchup_eligible"))
    if disqualified_match and (win_rate_included or matchup_included):
        raise MeleeOpportunityError(
            f"match {match.get('id')} involving a disqualified participant is eligible"
        )
    if result_type not in PLAYED_RESULT_TYPES:
        win_rate_included = False
        matchup_included = False

    points_included = result_type in POINT_RESULT_TYPES
    constructed_points = source_points if points_included else 0
    effective = result_type != "awarded_win_top8_lock"
    return {
        "participant_id": participant_id,
        "participant_status": participant_status,
        "round_id": round_["id"],
        "round_number": round_["number"],
        "scope": _scope_for_round(round_, event_structure),
        "match_id": match["id"],
        "opponent_participant_id": _opponent_id(competitors, participant_id),
        "result_type": result_type,
        "source_played": bool(match.get("played")),
        "source_match_points": source_points,
        "points_included": points_included,
        "constructed_points": constructed_points,
        "theoretical_round": True,
        "effective_theoretical_round": effective,
        "win_rate_included": win_rate_included,
        "matchup_included": matchup_included,
        "exclusion_reasons": _exclusion_reasons(
            result_type=result_type,
            win_rate_included=win_rate_included,
            matchup_included=matchup_included,
            disqualified_match=disqualified_match,
        ),
    }


def _unplayed_opportunity(
    *,
    participant_id: str,
    participant_status: str,
    round_: Mapping[str, Any],
    event_structure: str,
) -> dict[str, Any]:
    if participant_status == "dropped":
        result_type = "drop_unplayed"
        reason = "unplayed_after_drop"
        points_included = True
    elif participant_status == "disqualified":
        result_type = "administrative_result"
        reason = "unplayed_after_disqualification"
        points_included = False
    else:
        raise MeleeOpportunityError(
            f"{participant_id} is missing round {round_['number']} "
            f"with non-terminal status {participant_status!r}"
        )
    return {
        "participant_id": participant_id,
        "participant_status": participant_status,
        "round_id": round_["id"],
        "round_number": round_["number"],
        "scope": _scope_for_round(round_, event_structure),
        "match_id": None,
        "opponent_participant_id": None,
        "result_type": result_type,
        "source_played": False,
        "source_match_points": None,
        "points_included": points_included,
        "constructed_points": 0,
        "theoretical_round": True,
        "effective_theoretical_round": True,
        "win_rate_included": False,
        "matchup_included": False,
        "exclusion_reasons": [reason],
    }


def _scope_summary(
    opportunities: Sequence[Mapping[str, Any]],
    participant_count: int,
    scheduled_round_count: int,
) -> dict[str, Any]:
    match_ids = {
        item["match_id"]
        for item in opportunities
        if item["match_id"] is not None
    }
    win_rate_match_ids = {
        item["match_id"] for item in opportunities if item["win_rate_included"]
    }
    matchup_match_ids = {
        item["match_id"] for item in opportunities if item["matchup_included"]
    }
    disqualified_match_ids = {
        item["match_id"]
        for item in opportunities
        if item["match_id"] is not None
        and "disqualified_participant" in item["exclusion_reasons"]
    }
    result_counts = Counter(str(item["result_type"]) for item in opportunities)
    return {
        "participant_count": participant_count,
        "scheduled_round_count": scheduled_round_count,
        "theoretical_rounds": sum(
            bool(item["theoretical_round"]) for item in opportunities
        ),
        "effective_theoretical_rounds": sum(
            bool(item["effective_theoretical_round"]) for item in opportunities
        ),
        "constructed_points": sum(
            int(item["constructed_points"]) for item in opportunities
        ),
        "source_match_count": len(match_ids),
        "win_rate_match_count": len(win_rate_match_ids),
        "matchup_match_count": len(matchup_match_ids),
        "disqualified_matches_excluded": len(disqualified_match_ids),
        "result_counts": dict(sorted(result_counts.items())),
    }


def build_opportunity_ledger(
    event: Mapping[str, Any],
    classification: Mapping[str, Any],
    *,
    event_path: str,
    event_sha256: str,
    classification_path: str,
    classification_sha256: str,
) -> dict[str, Any]:
    """Build one explicit participant-round ledger from retained production input."""

    metadata = event.get("metadata")
    if not isinstance(metadata, Mapping):
        raise MeleeOpportunityError("event.metadata must be an object")
    event_id = metadata.get("event_id")
    format_id = metadata.get("constructed_format")
    event_structure = event.get("event_structure")
    if metadata.get("source") != "melee":
        raise MeleeOpportunityError("event.metadata.source must be 'melee'")
    if event_structure not in EVENT_STRUCTURES:
        raise MeleeOpportunityError(
            f"unsupported event structure {event_structure!r}"
        )
    if not isinstance(event_id, str) or not EVENT_ID_PATTERN.fullmatch(event_id):
        raise MeleeOpportunityError("event.metadata.event_id must be numeric")
    if not isinstance(format_id, str) or not FORMAT_PATTERN.fullmatch(format_id):
        raise MeleeOpportunityError("event constructed format is invalid")
    if classification.get("event_id") != event_id:
        raise MeleeOpportunityError("classification event_id does not match event")
    if classification.get("format") != format_id:
        raise MeleeOpportunityError("classification format does not match event")
    classification_input = classification.get("input")
    if not isinstance(classification_input, Mapping):
        raise MeleeOpportunityError("classification.input must be an object")
    if classification_input.get("event_sha256") != event_sha256:
        raise MeleeOpportunityError(
            "classification does not hash the supplied normalized event"
        )
    classification_quality = classification.get("quality")
    if not isinstance(classification_quality, Mapping) or classification_quality.get(
        "blocking"
    ):
        raise MeleeOpportunityError("classification overlay is blocking")

    participants = _objects_by_id(
        event.get("participants"), field="id", label="event.participants"
    )
    rounds = _objects_by_id(event.get("rounds"), field="id", label="event.rounds")
    matches = _objects_by_id(event.get("matches"), field="id", label="event.matches")
    classification_records = _objects_by_id(
        classification.get("records"),
        field="participant_id",
        label="classification.records",
    )
    if set(classification_records) != set(participants):
        raise MeleeOpportunityError(
            "classification records must cover every event participant exactly once"
        )

    constructed_rounds = sorted(
        (
            round_
            for round_ in rounds.values()
            if round_.get("round_phase") == "constructed"
            and round_.get("game_format") == format_id
            and round_.get("swiss") is True
        ),
        key=lambda item: int(item["number"]),
    )
    if not constructed_rounds:
        raise MeleeOpportunityError("event contains no Constructed Swiss rounds")
    if event_structure != "mixed" and any(
        item.get("round_phase") == "draft" for item in rounds.values()
    ):
        raise MeleeOpportunityError(
            f"{event_structure} contains a Draft round"
        )
    day1_rounds = [item for item in constructed_rounds if item.get("stage") == "day1"]
    day2_rounds = [item for item in constructed_rounds if item.get("stage") == "day2"]
    if event_structure == "constructed_single_stage":
        if day2_rounds:
            raise MeleeOpportunityError(
                "constructed_single_stage does not support Day 2 rounds"
            )
        if any(
            item.get("stage") not in {"day1", "other"}
            for item in constructed_rounds
        ):
            raise MeleeOpportunityError(
                "constructed_single_stage has an unsupported Constructed stage"
            )
    else:
        if not day1_rounds or not day2_rounds:
            raise MeleeOpportunityError(
                f"{event_structure} requires Day 1 and Day 2 Constructed"
            )
        if len(day1_rounds) + len(day2_rounds) != len(constructed_rounds):
            raise MeleeOpportunityError(
                f"{event_structure} contains a cross-structure Constructed stage"
            )
    constructed_round_ids = {str(item["id"]) for item in constructed_rounds}

    matches_by_participant_round: dict[
        tuple[str, str],
        tuple[
            Mapping[str, Any],
            Sequence[Mapping[str, Any]],
            Mapping[str, Any],
        ],
    ] = {}
    day2_participants: set[str] = set()
    disqualified_ids = {
        participant_id
        for participant_id, participant in participants.items()
        if participant.get("status") == "disqualified"
    }
    for match in matches.values():
        round_id = match.get("round_id")
        round_ = rounds.get(str(round_id))
        if round_ is None:
            raise MeleeOpportunityError(
                f"match {match.get('id')} references unknown round {round_id}"
            )
        competitors = match.get("competitors")
        if not isinstance(competitors, list) or not competitors:
            raise MeleeOpportunityError(
                f"match {match.get('id')} must contain competitors"
            )
        for competitor in competitors:
            if not isinstance(competitor, Mapping):
                raise MeleeOpportunityError(
                    f"match {match.get('id')} contains a non-object competitor"
                )
            participant_id = competitor.get("participant_id")
            if participant_id not in participants:
                raise MeleeOpportunityError(
                    f"match {match.get('id')} references unknown participant"
                )
            if (
                event_structure != "constructed_single_stage"
                and round_.get("stage") == "day2"
                and round_.get("swiss") is True
            ):
                day2_participants.add(str(participant_id))
            if str(round_id) not in constructed_round_ids:
                continue
            key = (str(participant_id), str(round_id))
            if key in matches_by_participant_round:
                raise MeleeOpportunityError(
                    f"{participant_id} has multiple matches in round {round_.get('number')}"
                )
            matches_by_participant_round[key] = (match, competitors, competitor)

    day1_participants = set(participants)
    if (
        event_structure != "constructed_single_stage"
        and not day2_participants
    ):
        raise MeleeOpportunityError("Day 2 population cannot be established")
    if not day2_participants <= day1_participants:
        raise MeleeOpportunityError("Day 2 population is not a subset of Day 1")

    participant_documents = []
    opportunities = []
    for participant_id in sorted(participants):
        participant = participants[participant_id]
        participant_status = participant.get("status")
        if participant_status not in {"active", "dropped", "disqualified", "no_show"}:
            raise MeleeOpportunityError(
                f"{participant_id} has unsupported status {participant_status!r}"
            )
        participant_documents.append(
            {
                "participant_id": participant_id,
                "participant_status": participant_status,
                "day1_participant": (
                    event_structure != "constructed_single_stage"
                ),
                "day2_participant": participant_id in day2_participants,
                "classification": _classification_summary(
                    classification_records[participant_id]
                ),
            }
        )
        if event_structure == "constructed_single_stage":
            scheduled = list(constructed_rounds)
        else:
            scheduled = list(day1_rounds)
            if participant_id in day2_participants:
                scheduled.extend(day2_rounds)
        for round_ in scheduled:
            match_data = matches_by_participant_round.get(
                (participant_id, str(round_["id"]))
            )
            if match_data is None:
                opportunity = _unplayed_opportunity(
                    participant_id=participant_id,
                    participant_status=str(participant_status),
                    round_=round_,
                    event_structure=str(event_structure),
                )
            else:
                match, competitors, competitor = match_data
                opportunity = _source_opportunity(
                    participant_id=participant_id,
                    participant_status=str(participant_status),
                    round_=round_,
                    match=match,
                    competitors=competitors,
                    competitor=competitor,
                    disqualified_ids=disqualified_ids,
                    event_structure=str(event_structure),
                )
            opportunities.append(opportunity)

    if event_structure == "constructed_single_stage":
        scope_summaries = {
            "all_constructed": _scope_summary(
                opportunities,
                len(day1_participants),
                len(constructed_rounds),
            )
        }
    else:
        day1_opportunities = [
            item for item in opportunities if item["scope"] == "day1"
        ]
        day2_opportunities = [
            item for item in opportunities if item["scope"] == "day2"
        ]
        scope_summaries = {
            "day1": _scope_summary(
                day1_opportunities,
                len(day1_participants),
                len(day1_rounds),
            ),
            "day2": _scope_summary(
                day2_opportunities,
                len(day2_participants),
                len(day2_rounds),
            ),
            "all_constructed": _scope_summary(
                opportunities,
                len(day1_participants),
                len(constructed_rounds),
            ),
        }
    return {
        "schema_version": OPPORTUNITY_LEDGER_SCHEMA_VERSION,
        "source": "melee",
        "event_id": event_id,
        "format": format_id,
        "event_structure": event_structure,
        "input": {
            "event_path": event_path,
            "event_sha256": event_sha256,
            "event_schema_version": event.get("schema_version"),
            "classification_path": classification_path,
            "classification_sha256": classification_sha256,
            "classification_schema_version": classification.get("schema_version"),
        },
        "rounds": [
            {
                "round_id": round_["id"],
                "round_number": round_["number"],
                "stage": round_["stage"],
                "phase_id": round_["phase_id"],
            }
            for round_ in constructed_rounds
        ],
        "scope_summaries": scope_summaries,
        "participants": participant_documents,
        "opportunities": opportunities,
    }


def opportunity_ledger_bytes(document: Mapping[str, Any]) -> bytes:
    """Return canonical, human-reviewable UTF-8 bytes."""

    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def build_opportunity_ledger_from_paths(
    event_path: Path,
    classification_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Load exact retained inputs and build their deterministic ledger."""

    root = repository_root.resolve()
    event, event_bytes = _read_json_object(event_path)
    classification, classification_bytes = _read_json_object(classification_path)
    return build_opportunity_ledger(
        event,
        classification,
        event_path=_repository_relative(event_path, root),
        event_sha256=_sha256_bytes(event_bytes),
        classification_path=_repository_relative(classification_path, root),
        classification_sha256=_sha256_bytes(classification_bytes),
    )


def write_opportunity_ledger(path: Path, payload: bytes) -> bool:
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
        description="Build one deterministic Constructed-opportunity ledger."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", required=True, dest="format_id")
    parser.add_argument("--event-id", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="atomically write the ledger; default mode is read-only",
    )
    args = parser.parse_args(argv)
    if not FORMAT_PATTERN.fullmatch(args.format_id):
        parser.error("--format must be a lowercase hyphenated identifier")
    if not EVENT_ID_PATTERN.fullmatch(args.event_id):
        parser.error("--event-id must be a positive numeric identifier")

    root = args.root.resolve()
    event_path = (
        root
        / "data"
        / args.format_id
        / "melee"
        / "events"
        / f"{args.event_id}.json"
    )
    classification_path = (
        root
        / "data"
        / args.format_id
        / "melee"
        / "classifications"
        / f"{args.event_id}.json"
    )
    output_path = (
        root
        / "data"
        / args.format_id
        / "melee"
        / "opportunities"
        / f"{args.event_id}.json"
    )
    try:
        document = build_opportunity_ledger_from_paths(
            event_path,
            classification_path,
            root,
        )
        payload = opportunity_ledger_bytes(document)
        reused = False
        if args.execute:
            reused = write_opportunity_ledger(output_path, payload)
        all_summary = document["scope_summaries"]["all_constructed"]
        print(
            json.dumps(
                {
                    "event_id": args.event_id,
                    "format": args.format_id,
                    "mode": "execute" if args.execute else "dry-run",
                    "output_path": (
                        _repository_relative(output_path, root)
                        if args.execute
                        else None
                    ),
                    "reused": reused,
                    "participants": len(document["participants"]),
                    "opportunities": all_summary["theoretical_rounds"],
                    "effective_opportunities": all_summary[
                        "effective_theoretical_rounds"
                    ],
                    "win_rate_matches": all_summary["win_rate_match_count"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (MeleeOpportunityError, OSError, ValueError) as exc:
        print(f"Melee opportunity ledger ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
