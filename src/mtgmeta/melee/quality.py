"""Deterministic, fail-closed quality gates for normalized Melee events.

This module performs no network or filesystem writes.  It can produce canonical
publication bytes only after the normalized document passes its versioned JSON
Schema, cross-record checks, and the event's explicit whitelist authorization.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .config import MeleeEventDefinition


class MeleeQualityError(ValueError):
    """Raised when a normalized document cannot be assessed safely."""


class MeleePublicationBlocked(MeleeQualityError):
    """Raised when an assessed event is not authorized and safe to publish."""


NONPLAYED_RESULTS = frozenset(
    {
        "intentional_draw",
        "bye",
        "no_show",
        "unplayed_drop",
        "awarded_win_top8_lock",
        "administrative",
        "unknown",
    }
)
EXPECTED_POINTS = {"played_win": 3, "played_loss": 0, "played_draw": 1}
EXPECTED_NONPLAYED_POINTS = {
    "intentional_draw": 1,
    "bye": 3,
    "no_show": 0,
    "unplayed_drop": 0,
}
DEFAULT_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "melee-event.schema.json"


def _location(parts: Iterable[Any]) -> str:
    location = "$"
    for part in parts:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location


@lru_cache(maxsize=8)
def _validator(schema_path: str) -> Draft202012Validator:
    path = Path(schema_path)
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        raise MeleeQualityError(f"cannot load normalized Melee Schema: {exc}") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(document: Any, schema_path: Path) -> None:
    errors = sorted(
        _validator(str(schema_path.resolve())).iter_errors(document),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        details = "; ".join(
            f"{_location(error.absolute_path)}: {error.message}" for error in errors[:5]
        )
        if len(errors) > 5:
            details += f"; and {len(errors) - 5} more"
        raise MeleeQualityError(f"normalized Melee event failed Schema validation: {details}")


def _issue(
    code: str,
    entity_type: str,
    entity_id: str | None,
    message: str,
    evidence: Iterable[str],
    *,
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "error" if blocking else "warning",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "message": message,
        "blocking": blocking,
        "source_evidence": sorted(set(evidence)),
    }


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _played_pair_is_valid(competitors: list[dict[str, Any]]) -> bool:
    if len(competitors) != 2:
        return False
    result_types = sorted(item["result_type"] for item in competitors)
    if result_types not in [["played_draw", "played_draw"], ["played_loss", "played_win"]]:
        return False
    return all(
        item["match_points"] == EXPECTED_POINTS[item["result_type"]]
        for item in competitors
    )


def _semantic_issues(document: dict[str, Any], event: MeleeEventDefinition) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    metadata = document["metadata"]
    event_id = metadata["event_id"]

    if not event.enabled:
        issues.append(
            _issue(
                "event_not_enabled",
                "event",
                event_id,
                "The whitelist entry does not authorize publication.",
                [f"enabled={event.enabled}"],
            )
        )
    if event.review_status != "verified":
        issues.append(
            _issue(
                "event_not_verified",
                "event",
                event_id,
                "The whitelist entry has not completed review.",
                [f"review_status={event.review_status}"],
            )
        )

    expected_metadata = {
        "event_id": event.id,
        "name": event.name,
        "constructed_format": event.constructed_game_format,
        "series": event.series,
    }
    for field, expected in expected_metadata.items():
        actual = metadata[field]
        if actual != expected:
            issues.append(
                _issue(
                    "event_metadata_mismatch",
                    "event",
                    event_id,
                    "Normalized metadata does not match the reviewed whitelist entry.",
                    [f"{field}.actual={actual}", f"{field}.expected={expected}"],
                )
            )
    expected_dates = {"start": event.start_date.isoformat(), "end": event.end_date.isoformat()}
    for field, expected in expected_dates.items():
        actual = metadata["date"][field]
        if actual != expected:
            issues.append(
                _issue(
                    "event_metadata_mismatch",
                    "event",
                    event_id,
                    "Normalized metadata does not match the reviewed whitelist entry.",
                    [f"date.{field}.actual={actual}", f"date.{field}.expected={expected}"],
                )
            )
    if document["event_structure"] != event.structure:
        issues.append(
            _issue(
                "event_structure_mismatch",
                "event",
                event_id,
                "Normalized event structure does not match the reviewed whitelist entry.",
                [f"actual={document['event_structure']}", f"expected={event.structure}"],
            )
        )

    raw_artifacts = document["provenance"]["raw_artifacts"]
    if not raw_artifacts:
        issues.append(
            _issue(
                "missing_raw_artifacts",
                "event",
                event_id,
                "Event has no archived raw source artifacts.",
                [],
            )
        )
    for artifact in raw_artifacts:
        if "sha256" not in artifact:
            issues.append(
                _issue(
                    "raw_artifact_missing_sha256",
                    "event",
                    event_id,
                    "A raw source artifact has no integrity digest.",
                    [f"path={artifact['path']}"],
                )
            )
    for duplicate in sorted(_duplicates(item["path"] for item in raw_artifacts)):
        issues.append(
            _issue(
                "duplicate_raw_artifact",
                "event",
                event_id,
                "The same raw artifact path appears more than once.",
                [f"path={duplicate}"],
            )
        )

    phases = {item["id"]: item for item in document["phases"]}
    rounds = {item["id"]: item for item in document["rounds"]}
    participants = {item["id"]: item for item in document["participants"]}

    identity_groups = (
        ("duplicate_phase_id", "phase", [item["id"] for item in document["phases"]]),
        ("duplicate_round_id", "round", [item["id"] for item in document["rounds"]]),
        ("duplicate_participant_id", "participant", [item["id"] for item in document["participants"]]),
        ("duplicate_match_id", "match", [item["id"] for item in document["matches"]]),
    )
    for code, entity_type, values in identity_groups:
        for duplicate in sorted(_duplicates(values)):
            issues.append(
                _issue(code, entity_type, duplicate, "A normalized identity is duplicated.", [duplicate])
            )

    source_participant_ids = [
        item["source_id"] for item in document["participants"] if item["source_id"] is not None
    ]
    for duplicate in sorted(_duplicates(source_participant_ids)):
        issues.append(
            _issue(
                "duplicate_source_participant_id",
                "participant",
                duplicate,
                "A source participant identity maps to multiple normalized participants.",
                [duplicate],
            )
        )

    for round_ in document["rounds"]:
        phase = phases.get(round_["phase_id"])
        if phase is None:
            issues.append(
                _issue(
                    "dangling_phase_reference",
                    "round",
                    round_["id"],
                    "Round references a phase that is not present in the event.",
                    [f"phase_id={round_['phase_id']}"],
                )
            )
        elif any(round_[field] != phase[field] for field in ("stage", "round_phase", "game_format", "swiss")):
            issues.append(
                _issue(
                    "round_phase_mismatch",
                    "round",
                    round_["id"],
                    "Round semantics do not match its referenced phase.",
                    [f"phase_id={round_['phase_id']}"],
                )
            )
        if round_["round_phase"] == "unknown" or round_["game_format"] == "unknown":
            issues.append(
                _issue(
                    "unknown_round_phase",
                    "round",
                    round_["id"],
                    "Round phase or format remains unresolved.",
                    [f"source_label={round_['source_label']}"],
                )
            )

    if not document["participants"]:
        issues.append(_issue("missing_participants", "event", event_id, "Event has no participants.", []))
    if not document["standings"]:
        issues.append(_issue("missing_primary_standings", "event", event_id, "Event has no primary standings.", []))

    for participant in document["participants"]:
        if participant["status"] == "unknown":
            issues.append(
                _issue(
                    "unknown_participant_status",
                    "participant",
                    participant["id"],
                    "Participant status remains unresolved.",
                    [f"source_id={participant['source_id']}"],
                )
            )

    for collection, entity_type in ((document["standings"], "standing"), (document["decklists"], "decklist")):
        for record in collection:
            participant_id = record["participant_id"]
            if participant_id not in participants:
                issues.append(
                    _issue(
                        "dangling_participant_reference",
                        entity_type,
                        participant_id,
                        f"{entity_type.title()} references a participant that is not present.",
                        [f"participant_id={participant_id}"],
                    )
                )

    for duplicate in sorted(_duplicates(item["participant_id"] for item in document["standings"])):
        issues.append(
            _issue(
                "duplicate_standing",
                "standing",
                duplicate,
                "Participant has multiple primary standing records.",
                [f"participant_id={duplicate}"],
            )
        )
    decklist_participant_ids = [item["participant_id"] for item in document["decklists"]]
    for duplicate in sorted(_duplicates(decklist_participant_ids)):
        issues.append(
            _issue(
                "duplicate_decklist",
                "decklist",
                duplicate,
                "Participant has multiple normalized decklist records.",
                [f"participant_id={duplicate}"],
            )
        )
    for participant_id in sorted(set(participants) - set(decklist_participant_ids)):
        issues.append(
            _issue(
                "decklist_not_available",
                "decklist",
                participant_id,
                "Participant has no normalized decklist record; match records remain usable.",
                ["status=missing_record"],
                blocking=False,
            )
        )
    for decklist in document["decklists"]:
        if decklist["status"] in {"missing", "unavailable"}:
            issues.append(
                _issue(
                    "decklist_not_available",
                    "decklist",
                    decklist["participant_id"],
                    "Decklist is missing or unavailable; match records remain usable.",
                    [f"status={decklist['status']}"],
                    blocking=False,
                )
            )
        elif decklist["status"] == "unknown":
            issues.append(
                _issue(
                    "unknown_decklist_status",
                    "decklist",
                    decklist["participant_id"],
                    "Decklist availability remains unresolved.",
                    ["status=unknown"],
                )
            )
        if decklist["status"] == "submitted" and (
            not decklist["cards"] or decklist["source_url"] is None
        ):
            issues.append(
                _issue(
                    "invalid_submitted_decklist",
                    "decklist",
                    decklist["participant_id"],
                    "Submitted decklist lacks cards or its source URL.",
                    [
                        f"card_records={len(decklist['cards'])}",
                        f"source_url_present={decklist['source_url'] is not None}",
                    ],
                )
            )
        if decklist["game_format"] != event.constructed_game_format:
            issues.append(
                _issue(
                    "decklist_format_mismatch",
                    "decklist",
                    decklist["participant_id"],
                    "Decklist format does not match the event's Constructed format.",
                    [f"actual={decklist['game_format']}", f"expected={event.constructed_game_format}"],
                )
            )

    source_match_ids = [
        item["source_record_id"] for item in document["matches"] if item["source_record_id"] is not None
    ]
    for duplicate in sorted(_duplicates(source_match_ids)):
        issues.append(
            _issue(
                "duplicate_source_match_id",
                "match",
                duplicate,
                "A source match identity maps to multiple normalized matches.",
                [duplicate],
            )
        )

    eligible_count = 0
    for match in document["matches"]:
        round_ = rounds.get(match["round_id"])
        competitors = match["competitors"]
        if match["source_record_id"] is None:
            issues.append(
                _issue(
                    "missing_source_match_id",
                    "match",
                    match["id"],
                    "Match has no source record identity.",
                    [],
                )
            )
        competitor_ids = [item["participant_id"] for item in competitors]
        for participant_id in competitor_ids:
            if participant_id not in participants:
                issues.append(
                    _issue(
                        "dangling_participant_reference",
                        "match",
                        match["id"],
                        "Match references a participant that is not present.",
                        [f"participant_id={participant_id}"],
                    )
                )
        if len(competitor_ids) != len(set(competitor_ids)):
            issues.append(
                _issue(
                    "duplicate_match_competitor",
                    "match",
                    match["id"],
                    "Match contains the same participant more than once.",
                    competitor_ids,
                )
            )

        result_types = {item["result_type"] for item in competitors}
        played_pair = _played_pair_is_valid(competitors)
        if "unknown" in result_types:
            issues.append(
                _issue(
                    "unknown_result",
                    "match",
                    match["id"],
                    "Match result remains unresolved.",
                    [f"source_record_id={match['source_record_id']}"],
                )
            )
        if match["played"] != played_pair:
            issues.append(
                _issue(
                    "invalid_match_result",
                    "match",
                    match["id"],
                    "Played flag and per-competitor results are inconsistent.",
                    [f"played={match['played']}", f"result_types={','.join(sorted(result_types))}"],
                )
            )
        if not match["played"] and any(result_type not in NONPLAYED_RESULTS for result_type in result_types):
            issues.append(
                _issue(
                    "invalid_nonplayed_result",
                    "match",
                    match["id"],
                    "A nonplayed match contains a played result type.",
                    sorted(result_types),
                )
            )
        if not match["played"] and any(
            item["result_type"] in EXPECTED_NONPLAYED_POINTS
            and item["match_points"] != EXPECTED_NONPLAYED_POINTS[item["result_type"]]
            for item in competitors
        ):
            issues.append(
                _issue(
                    "invalid_match_result",
                    "match",
                    match["id"],
                    "Nonplayed result has inconsistent match points.",
                    [
                        f"{item['result_type']}={item['match_points']}"
                        for item in competitors
                    ],
                )
            )

        expected_eligible = bool(
            played_pair
            and round_ is not None
            and round_["round_phase"] == "constructed"
            and round_["game_format"] == event.constructed_game_format
            and round_["swiss"]
        )
        if (
            match["constructed_statistics_eligible"] != expected_eligible
            or match["matchup_eligible"] != expected_eligible
        ):
            issues.append(
                _issue(
                    "invalid_match_eligibility",
                    "match",
                    match["id"],
                    "Statistical eligibility does not match reviewed round and result semantics.",
                    [
                        f"expected={expected_eligible}",
                        f"constructed_statistics_eligible={match['constructed_statistics_eligible']}",
                        f"matchup_eligible={match['matchup_eligible']}",
                    ],
                )
            )
        if expected_eligible:
            eligible_count += 1
        if round_ is None:
            issues.append(
                _issue(
                    "dangling_round_reference",
                    "match",
                    match["id"],
                    "Match references a round that is not present.",
                    [f"round_id={match['round_id']}"],
                )
            )

    if eligible_count == 0:
        issues.append(
            _issue(
                "no_constructed_swiss_matches",
                "event",
                event_id,
                "Event has no verified played Constructed Swiss matches.",
                [],
            )
        )
    return issues


def _stable_issues(issues: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    severity_rank = {"info": 0, "warning": 1, "error": 2}
    for issue in issues:
        key = (issue["code"], issue["entity_type"], issue["entity_id"])
        if key not in unique:
            unique[key] = copy.deepcopy(issue)
            unique[key]["source_evidence"] = sorted(set(issue["source_evidence"]))
            continue
        current = unique[key]
        current["blocking"] = current["blocking"] or issue["blocking"]
        current["severity"] = max(
            (current["severity"], issue["severity"]), key=severity_rank.__getitem__
        )
        current["message"] = min(current["message"], issue["message"])
        current["source_evidence"] = sorted(
            set(current["source_evidence"]) | set(issue["source_evidence"])
        )
    return sorted(
        unique.values(),
        key=lambda issue: (
            issue["code"],
            issue["entity_type"],
            issue["entity_id"] or "",
            issue["message"],
            tuple(issue["source_evidence"]),
        ),
    )


def finalize_event_quality(
    document: dict[str, Any],
    event: MeleeEventDefinition,
    *,
    schema_path: str | Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    """Return a deep-copied event with deterministic quality and authorization state."""

    if not isinstance(document, dict):
        raise MeleeQualityError("normalized Melee event must be an object")
    result = copy.deepcopy(document)
    path = Path(schema_path)
    _validate(result, path)
    prior_issues = result["quality"]["issues"]
    issues = _stable_issues([*prior_issues, *_semantic_issues(result, event)])
    blocking = any(issue["blocking"] for issue in issues)
    result["quality"] = {
        "status": "blocked" if blocking else ("warning" if issues else "valid"),
        "publishable": not blocking,
        "issues": issues,
    }
    _validate(result, path)
    return result


def build_publication_payload(
    document: dict[str, Any],
    event: MeleeEventDefinition,
    *,
    schema_path: str | Path = DEFAULT_SCHEMA,
) -> bytes:
    """Build canonical JSON bytes or fail before any publication write can occur."""

    finalized = finalize_event_quality(document, event, schema_path=schema_path)
    if not finalized["quality"]["publishable"]:
        codes = sorted(
            {issue["code"] for issue in finalized["quality"]["issues"] if issue["blocking"]}
        )
        raise MeleePublicationBlocked(
            "normalized Melee event is blocked from publication: " + ", ".join(codes)
        )
    return (
        json.dumps(finalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


__all__ = [
    "MeleePublicationBlocked",
    "MeleeQualityError",
    "build_publication_payload",
    "finalize_event_quality",
]
