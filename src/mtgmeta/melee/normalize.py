"""Evidence-based semantic normalization for assembled Melee snapshots.

P5-06 resolves phases, participant states, match results, and statistical
eligibility.  It never fetches data and never marks an event publishable;
publication readiness remains a separate P5-07 decision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .assembler import assemble_parsed_snapshot, stable_record_id
from .config import MeleeEventDefinition, MeleeMatchOverride
from .parser import ParsedMeleeSnapshot, SourceMatch, SourceRound, SourceStanding, parse_raw_snapshot


class MeleeNormalizationError(ValueError):
    """Raised when reviewed semantics conflict with source identities."""


PLAYED_RESULTS = frozenset({"played_win", "played_loss", "played_draw"})
NONPLAYED_RESULTS = frozenset(
    {
        "intentional_draw", "bye", "no_show", "unplayed_drop",
        "awarded_win_top8_lock", "administrative",
    }
)


def _records(snapshot: ParsedMeleeSnapshot, attribute: str) -> Iterable[Any]:
    for page in snapshot.pages:
        yield from getattr(page, attribute)


def _normalized_text(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("-", " ").split())


def _issue(
    code: str,
    entity_type: str,
    entity_id: str,
    message: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "error",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "message": message,
        "blocking": True,
        "source_evidence": evidence,
    }


def _phase_for_round(source: SourceRound, event: MeleeEventDefinition):
    matches = [
        phase
        for phase in event.phases
        if (source.number is not None and source.number in phase.rounds)
        or source.label in phase.source_labels
    ]
    if len(matches) > 1:
        raise MeleeNormalizationError(
            f"round {source.source_round_id!r} matches multiple configured phases"
        )
    return matches[0] if matches else None


def _participant_status(source: SourceStanding) -> str:
    status = _normalized_text(source.status_text)
    if status in {"active", "completed", "qualified", "finished"}:
        return "active"
    if status in {"drop", "dropped", "withdrawn"}:
        return "dropped"
    if status in {"no show", "noshow"}:
        return "no_show"
    return "unknown"


def _source_result(source: SourceMatch) -> tuple[bool, list[dict[str, Any]]] | None:
    status = _normalized_text(source.status_text)
    result = _normalized_text(source.result_text)
    competitors = source.competitor_results
    if tuple(item.source_participant_id for item in competitors) != source.competitor_source_ids:
        return None

    if status == "bye" or any(_normalized_text(item.outcome_text) == "bye" for item in competitors):
        if len(competitors) != 1:
            return None
        if competitors[0].match_points not in {None, 3}:
            return None
        return False, [
            {
                "source_participant_id": competitors[0].source_participant_id,
                "result_type": "bye",
                "match_points": competitors[0].match_points if competitors[0].match_points is not None else 3,
            }
        ]

    if status in {"intentional draw", "id"} or result == "0 0 3":
        if len(competitors) != 2:
            return None
        if any(item.match_points not in {None, 1} for item in competitors):
            return None
        return False, [
            {
                "source_participant_id": item.source_participant_id,
                "result_type": "intentional_draw",
                "match_points": item.match_points if item.match_points is not None else 1,
            }
            for item in competitors
        ]

    single_status_results = {
        "no show": "no_show",
        "dropped": "unplayed_drop",
        "unplayed": "unplayed_drop",
        "administrative": "administrative",
    }
    if len(competitors) == 1 and status in single_status_results:
        item = competitors[0]
        result_type = single_status_results[status]
        if result_type in {"no_show", "unplayed_drop"} and item.match_points not in {None, 0}:
            return None
        return False, [
            {
                "source_participant_id": item.source_participant_id,
                "result_type": result_type,
                "match_points": item.match_points if item.match_points is not None else 0,
            }
        ]

    outcome_map = {
        "win": "played_win",
        "winner": "played_win",
        "loss": "played_loss",
        "lose": "played_loss",
        "draw": "played_draw",
    }
    nonplayed_outcome_map = {
        "no show": "no_show",
        "dropped": "unplayed_drop",
        "unplayed": "unplayed_drop",
        "administrative": "administrative",
    }
    nonplayed_types = [
        nonplayed_outcome_map.get(_normalized_text(item.outcome_text)) for item in competitors
    ]
    if competitors and all(value is not None for value in nonplayed_types):
        if any(
            result_type in {"no_show", "unplayed_drop"}
            and item.match_points not in {None, 0}
            for item, result_type in zip(competitors, nonplayed_types, strict=True)
        ):
            return None
        return False, [
            {
                "source_participant_id": item.source_participant_id,
                "result_type": result_type,
                "match_points": item.match_points if item.match_points is not None else 0,
            }
            for item, result_type in zip(competitors, nonplayed_types, strict=True)
        ]
    result_types = [outcome_map.get(_normalized_text(item.outcome_text)) for item in competitors]
    if len(competitors) != 2 or any(value is None for value in result_types):
        return None
    if sorted(result_types) not in [["played_draw", "played_draw"], ["played_loss", "played_win"]]:
        return None
    default_points = {"played_win": 3, "played_loss": 0, "played_draw": 1}
    normalized_results = [
        {
            "source_participant_id": item.source_participant_id,
            "result_type": result_type,
            "match_points": item.match_points if item.match_points is not None else default_points[result_type],
        }
        for item, result_type in zip(competitors, result_types, strict=True)
    ]
    if any(item["match_points"] != default_points[item["result_type"]] for item in normalized_results):
        return None
    return True, normalized_results


def _override_result(
    source: SourceMatch,
    override: MeleeMatchOverride,
) -> tuple[bool, list[dict[str, Any]]]:
    if override.review_status != "verified":
        raise MeleeNormalizationError(f"reviewed override {override.id!r} is not verified")
    result_types = tuple(item.result_type for item in override.competitors)
    if override.played:
        if (
            len(override.competitors) != 2
            or sorted(result_types)
            not in [["played_draw", "played_draw"], ["played_loss", "played_win"]]
        ):
            raise MeleeNormalizationError(
                f"reviewed override {override.id!r} has inconsistent played results"
            )
        expected_points = {"played_win": 3, "played_loss": 0, "played_draw": 1}
        if any(
            item.match_points != expected_points[item.result_type]
            for item in override.competitors
        ):
            raise MeleeNormalizationError(
                f"reviewed override {override.id!r} has inconsistent played points"
            )
    else:
        if any(item.result_type not in NONPLAYED_RESULTS for item in override.competitors):
            raise MeleeNormalizationError(
                f"reviewed override {override.id!r} has unsupported nonplayed outcomes"
            )
        fixed_points = {"intentional_draw": 1, "bye": 3, "no_show": 0, "unplayed_drop": 0}
        if any(
            item.result_type in fixed_points
            and item.match_points != fixed_points[item.result_type]
            for item in override.competitors
        ):
            raise MeleeNormalizationError(
                f"reviewed override {override.id!r} has inconsistent nonplayed points"
            )
    source_ids = set(source.competitor_source_ids)
    override_ids = {item.source_participant_id for item in override.competitors}
    if source_ids != override_ids:
        raise MeleeNormalizationError(
            f"reviewed override {override.id!r} competitor identities do not match its source match"
        )
    return override.played, [
        {
            "source_participant_id": item.source_participant_id,
            "result_type": item.result_type,
            "match_points": item.match_points,
        }
        for item in override.competitors
    ]


def normalize_parsed_snapshot(
    snapshot: ParsedMeleeSnapshot,
    event: MeleeEventDefinition,
    *,
    normalized_at: str,
) -> dict[str, Any]:
    """Resolve P5-06 semantics while keeping publication explicitly disabled."""

    document = assemble_parsed_snapshot(snapshot, event, normalized_at=normalized_at)
    source_rounds = {item.source_round_id: item for item in _records(snapshot, "rounds")}
    source_matches = {item.source_match_id: item for item in _records(snapshot, "matches")}
    source_standings = {
        item.source_participant_id: item for item in _records(snapshot, "standings")
    }
    overrides = {item.source_match_id: item for item in event.reviewed_overrides}
    if any(
        competitor.result_type == "awarded_win_top8_lock"
        for override in overrides.values()
        for competitor in override.competitors
    ) and (event.advancement is None or event.advancement.top8_lock_supported is not True):
        raise MeleeNormalizationError("Top 8 lock override lacks explicit event support")
    missing_override_targets = sorted(set(overrides) - set(source_matches))
    if missing_override_targets:
        raise MeleeNormalizationError(
            f"reviewed overrides reference missing source matches {missing_override_targets!r}"
        )

    issues: list[dict[str, Any]] = []
    round_documents = {item["id"]: item for item in document["rounds"]}
    resolved_rounds: dict[str, Any] = {}
    for source_id, source in sorted(source_rounds.items()):
        normalized_id = stable_record_id("round", event.id, source_id)
        phase = _phase_for_round(source, event)
        if phase is None:
            issues.append(
                _issue(
                    "unknown_round_phase",
                    "round",
                    normalized_id,
                    "Round does not match any reviewed phase rule.",
                    [f"source_round_id={source_id}", f"source_label={source.label}"],
                )
            )
            continue
        round_documents[normalized_id].update(
            phase_id=phase.id,
            stage=phase.stage,
            round_phase=phase.round_phase,
            game_format=phase.game_format,
            swiss=phase.swiss,
        )
        resolved_rounds[source_id] = phase

    participant_documents = {item["source_id"]: item for item in document["participants"]}
    for source_id, source in sorted(source_standings.items()):
        status = _participant_status(source)
        participant_documents[source_id]["status"] = status
        if status == "unknown":
            issues.append(
                _issue(
                    "unknown_participant_status",
                    "participant",
                    participant_documents[source_id]["id"],
                    "Participant status is not covered by the reviewed status mapping.",
                    [f"source_participant_id={source_id}", f"status_text={source.status_text}"],
                )
            )

    for decklist in document["decklists"]:
        decklist["game_format"] = event.constructed_game_format

    match_documents = {item["source_record_id"]: item for item in document["matches"]}
    participant_ids = {
        item["source_id"]: item["id"] for item in document["participants"]
    }
    for source_id, source in sorted(source_matches.items()):
        target = match_documents[source_id]
        override = overrides.get(source_id)
        resolved = _override_result(source, override) if override else _source_result(source)
        if resolved is None:
            issues.append(
                _issue(
                    "unknown_result",
                    "match",
                    target["id"],
                    "Match lacks a complete, internally consistent result outcome.",
                    [
                        f"source_match_id={source_id}",
                        f"result_text={source.result_text}",
                        f"status_text={source.status_text}",
                    ],
                )
            )
            continue
        played, results = resolved
        target["played"] = played
        target["competitors"] = [
            {
                "participant_id": participant_ids[item["source_participant_id"]],
                "result_type": item["result_type"],
                "match_points": item["match_points"],
            }
            for item in results
        ]
        if override:
            target["evidence"].extend(
                [f"reviewed_override={override.id}", f"override_reason={override.reason}"]
            )
            target["evidence"].extend(f"override_source={url}" for url in override.source_evidence)
        phase = resolved_rounds.get(source.source_round_id)
        eligible = bool(
            played
            and phase is not None
            and phase.round_phase == "constructed"
            and phase.game_format == event.constructed_game_format
            and phase.swiss
            and all(item["result_type"] in PLAYED_RESULTS for item in results)
        )
        target["constructed_statistics_eligible"] = eligible
        target["matchup_eligible"] = eligible

    if not any(round_["phase_id"] == "unresolved" for round_ in document["rounds"]):
        document["phases"] = [phase for phase in document["phases"] if phase["id"] != "unresolved"]
    document["quality"] = {
        "status": "blocked" if issues else "valid",
        "publishable": False,
        "issues": issues,
    }
    return document


def normalize_raw_snapshot(
    snapshot_path: str | Path,
    event: MeleeEventDefinition,
    *,
    normalized_at: str,
) -> dict[str, Any]:
    """Parse and normalize a stored snapshot without network access."""

    return normalize_parsed_snapshot(
        parse_raw_snapshot(snapshot_path), event, normalized_at=normalized_at
    )


__all__ = [
    "MeleeNormalizationError",
    "normalize_parsed_snapshot",
    "normalize_raw_snapshot",
]
