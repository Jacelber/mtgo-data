"""Deterministic overview and deck statistics for one classified Melee event."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence

from ..config import RuleConfigError, load_rule_set
from ..consumer import identity_display_name, literal_match_record
from ..rules import RuleSet


EVENT_STATISTICS_SCHEMA_VERSION = "1.0.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
SCOPE_ORDER = ("day1", "day2", "all_constructed")
STRUCTURE_SCOPE_ORDER = {
    "mixed": SCOPE_ORDER,
    "constructed_day2": SCOPE_ORDER,
    "constructed_single_stage": ("all_constructed",),
}
PLAYED_RESULT_TYPES = frozenset({"played_win", "played_loss", "played_draw"})
COMPLETED_OR_EXEMPT_RESULT_TYPES = frozenset(
    {
        "played_win",
        "played_loss",
        "played_draw",
        "intentional_draw",
        "bye",
        "awarded_win_top8_lock",
    }
)
WILSON_Z = 1.959963984540054


class MeleeStatisticsError(ValueError):
    """Raised when event statistics cannot be generated without guessing."""


def _sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _read_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        document = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise MeleeStatisticsError(f"{path}: cannot read JSON object") from exc
    if not isinstance(document, dict):
        raise MeleeStatisticsError(f"{path}: top level must be an object")
    return document, payload


def _repository_relative(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise MeleeStatisticsError(f"{path}: path is outside repository root") from exc
    return relative.as_posix()


def _objects_by_id(
    values: Any,
    *,
    field: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise MeleeStatisticsError(f"{label} must be a list")
    result: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise MeleeStatisticsError(f"{label}[{index}] must be an object")
        identifier = value.get(field)
        if not isinstance(identifier, str) or not identifier:
            raise MeleeStatisticsError(
                f"{label}[{index}].{field} must be a non-empty string"
            )
        if identifier in result:
            raise MeleeStatisticsError(f"{label} contains duplicate ID {identifier}")
        result[identifier] = value
    return result


def _rounded_ratio(numerator: float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _high_score_threshold(rounds: int) -> int | None:
    if rounds <= 0:
        return None
    return 3 * (rounds // 2 + 1)


def _high_score_available(event_structure: str, scope: str) -> bool:
    return (
        event_structure == "mixed" and scope in {"day1", "day2"}
    ) or (
        event_structure == "constructed_single_stage"
        and scope == "all_constructed"
    )


def _record_from_result_types(result_types: Sequence[str]) -> dict[str, Any]:
    counts = Counter(result_types)
    wins = counts["played_win"]
    losses = counts["played_loss"]
    draws = counts["played_draw"]
    matches = wins + losses + draws
    win_rate = _rounded_ratio(wins + 0.5 * draws, matches)
    if matches == 0:
        interval = None
    else:
        proportion = (wins + 0.5 * draws) / matches
        denominator = 1 + WILSON_Z**2 / matches
        center = (proportion + WILSON_Z**2 / (2 * matches)) / denominator
        margin = (
            WILSON_Z
            * math.sqrt(
                proportion * (1 - proportion) / matches
                + WILSON_Z**2 / (4 * matches**2)
            )
            / denominator
        )
        interval = {
            "lower": round(max(0.0, center - margin), 6),
            "upper": round(min(1.0, center + margin), 6),
        }
    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "matches": matches,
        "win_rate": win_rate,
        "confidence_interval_95": interval,
    }


def _identity_keys(
    participant_documents: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    parents: dict[str, tuple[str, ...]] = {}
    leaves: dict[str, tuple[str, ...]] = {}
    for participant_id, participant in participant_documents.items():
        classification = participant.get("classification")
        if not isinstance(classification, Mapping):
            raise MeleeStatisticsError(
                f"ledger participant {participant_id} has no classification"
            )
        if classification.get("status") == "unknown":
            parents[participant_id] = ("unknown",)
            leaves[participant_id] = ("unknown",)
            continue
        archetype_id = classification.get("archetype_id")
        subtype_id = classification.get("subtype_id")
        if not isinstance(archetype_id, str):
            raise MeleeStatisticsError(
                f"ledger participant {participant_id} has invalid archetype identity"
            )
        parents[participant_id] = ("archetype", archetype_id)
        leaves[participant_id] = (
            ("subtype", archetype_id, subtype_id)
            if isinstance(subtype_id, str)
            else ("archetype", archetype_id)
        )
    return parents, leaves


def _match_record(
    opportunities: Sequence[Mapping[str, Any]],
    *,
    group_key: tuple[str, ...],
    identity_by_participant: Mapping[str, tuple[str, ...]],
) -> dict[str, Any]:
    eligible = [item for item in opportunities if item["win_rate_included"]]
    all_results = [str(item["result_type"]) for item in eligible]
    non_mirror = [
        item
        for item in eligible
        if identity_by_participant.get(str(item["opponent_participant_id"]))
        != group_key
    ]
    mirror_ids = {
        str(item["match_id"])
        for item in eligible
        if identity_by_participant.get(str(item["opponent_participant_id"]))
        == group_key
    }
    all_record = _record_from_result_types(all_results)
    non_mirror_record = _record_from_result_types(
        [str(item["result_type"]) for item in non_mirror]
    )
    for record in (all_record, non_mirror_record):
        record["literal_record"] = literal_match_record(
            record["wins"],
            record["losses"],
            record["draws"],
        )
    return {
        "all_matches": all_record,
        "non_mirror": non_mirror_record,
        "mirror_match_count": len(mirror_ids),
    }


def _result_counts(
    opportunities: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    return dict(
        sorted(Counter(str(item["result_type"]) for item in opportunities).items())
    )


def _participant_high_score(
    opportunities: Sequence[Mapping[str, Any]],
) -> tuple[int | None, int, bool | None]:
    effective_rounds = sum(
        bool(item["effective_theoretical_round"]) for item in opportunities
    )
    points = sum(int(item["constructed_points"]) for item in opportunities)
    threshold = _high_score_threshold(effective_rounds)
    return threshold, points, points >= threshold if threshold is not None else None


def _scope_population(
    participant_documents: Mapping[str, Mapping[str, Any]],
    scope: str,
) -> set[str]:
    if scope == "day1" or scope == "all_constructed":
        return set(participant_documents)
    return {
        participant_id
        for participant_id, participant in participant_documents.items()
        if participant.get("day2_participant") is True
    }


def _group_metrics(
    *,
    participant_ids: set[str],
    scope_population: set[str],
    scope_opportunities: Sequence[Mapping[str, Any]],
    scope: str,
    event_structure: str,
    total_high_score: int | None,
    group_key: tuple[str, ...],
    identity_by_participant: Mapping[str, tuple[str, ...]],
) -> dict[str, Any]:
    members = participant_ids & scope_population
    opportunities = [
        item
        for item in scope_opportunities
        if str(item["participant_id"]) in members
    ]
    constructed_points = sum(int(item["constructed_points"]) for item in opportunities)
    theoretical_rounds = sum(bool(item["theoretical_round"]) for item in opportunities)
    effective_rounds = sum(
        bool(item["effective_theoretical_round"]) for item in opportunities
    )
    completed_or_exempt = sum(
        str(item["result_type"]) in COMPLETED_OR_EXEMPT_RESULT_TYPES
        for item in opportunities
    )
    high_score_count: int | None = None
    high_score_share: float | None = None
    high_score_conversion: float | None = None
    day2_high_score_rate: float | None = None
    round_distribution: dict[str, int] | None = None
    high_score_available = _high_score_available(event_structure, scope)
    if high_score_available:
        high_score_count = 0
        distribution: Counter[int] = Counter()
        by_participant = {
            participant_id: [
                item
                for item in opportunities
                if item["participant_id"] == participant_id
            ]
            for participant_id in members
        }
        for participant_opportunities in by_participant.values():
            threshold, _points, qualifies = _participant_high_score(
                participant_opportunities
            )
            effective = sum(
                bool(item["effective_theoretical_round"])
                for item in participant_opportunities
            )
            distribution[effective] += 1
            if threshold is not None and qualifies:
                high_score_count += 1
        high_score_share = _rounded_ratio(
            high_score_count, int(total_high_score or 0)
        )
        if scope == "day1" or event_structure == "constructed_single_stage":
            high_score_conversion = _rounded_ratio(high_score_count, len(members))
        else:
            day2_high_score_rate = _rounded_ratio(high_score_count, len(members))
        round_distribution = {
            str(round_count): count
            for round_count, count in sorted(distribution.items())
        }

    result_counts = _result_counts(opportunities)
    result = {
        "deck_count": len(members),
        "metagame_share": _rounded_ratio(len(members), len(scope_population)),
        "constructed_points": constructed_points,
        "theoretical_rounds": theoretical_rounds,
        "effective_theoretical_rounds": effective_rounds,
        "average_points_per_effective_round": _rounded_ratio(
            constructed_points, effective_rounds
        ),
        "completed_or_officially_exempt_rounds": completed_or_exempt,
        "completion_rate": _rounded_ratio(completed_or_exempt, theoretical_rounds),
        "played_match_participations": sum(
            bool(item["win_rate_included"]) for item in opportunities
        ),
        "source_match_count": len(
            {
                item["match_id"]
                for item in opportunities
                if item["match_id"] is not None
            }
        ),
        "result_counts": result_counts,
        "drop_player_count": len(
            {
                item["participant_id"]
                for item in opportunities
                if item["result_type"] == "drop_unplayed"
            }
        ),
        "drop_unplayed_rounds": result_counts.get("drop_unplayed", 0),
        "intentional_draw_opportunities": result_counts.get("intentional_draw", 0),
        "bye_count": result_counts.get("bye", 0),
        "top8_lock_player_count": len(
            {
                item["participant_id"]
                for item in opportunities
                if item["result_type"] == "awarded_win_top8_lock"
            }
        ),
        "top8_lock_exemptions": result_counts.get("awarded_win_top8_lock", 0),
        "disqualified_player_count": len(
            {
                item["participant_id"]
                for item in opportunities
                if item["participant_status"] == "disqualified"
            }
        ),
        "high_score": (
            {
                "count": high_score_count,
                "field_share": high_score_share,
                "high_score_conversion": high_score_conversion,
                "day2_high_score_rate": day2_high_score_rate,
                "effective_round_distribution": round_distribution,
            }
            if high_score_available
            else None
        ),
        "match_record": _match_record(
            opportunities,
            group_key=group_key,
            identity_by_participant=identity_by_participant,
        ),
    }
    if event_structure == "constructed_day2" and scope == "day2":
        result["day2_conversion"] = _rounded_ratio(
            len(members), len(participant_ids)
        )
    return result


def _source_url(event: Mapping[str, Any], event_id: str) -> str:
    provenance = event.get("provenance")
    if isinstance(provenance, Mapping):
        urls = provenance.get("source_urls")
        if isinstance(urls, list):
            expected = f"https://melee.gg/Tournament/View/{event_id}"
            if expected in urls:
                return expected
    raise MeleeStatisticsError("event provenance has no approved tournament URL")


def _validate_inputs(
    event: Mapping[str, Any],
    classification: Mapping[str, Any],
    ledger: Mapping[str, Any],
    taxonomy: RuleSet,
    *,
    event_sha256: str,
    classification_sha256: str,
    ledger_sha256: str,
    taxonomy_sha256: str,
) -> tuple[
    str,
    str,
    Mapping[str, Any],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    metadata = event.get("metadata")
    if not isinstance(metadata, Mapping):
        raise MeleeStatisticsError("event.metadata must be an object")
    event_id = metadata.get("event_id")
    format_id = metadata.get("constructed_format")
    event_structure = event.get("event_structure")
    if metadata.get("source") != "melee":
        raise MeleeStatisticsError("event.metadata.source must be 'melee'")
    if event_structure not in STRUCTURE_SCOPE_ORDER:
        raise MeleeStatisticsError(
            f"unsupported event structure {event_structure!r}"
        )
    if not isinstance(event_id, str) or not EVENT_ID_PATTERN.fullmatch(event_id):
        raise MeleeStatisticsError("event.metadata.event_id must be numeric")
    if not isinstance(format_id, str) or not FORMAT_PATTERN.fullmatch(format_id):
        raise MeleeStatisticsError("event constructed format is invalid")
    event_quality = event.get("quality")
    if not isinstance(event_quality, Mapping) or event_quality.get("publishable") is not True:
        raise MeleeStatisticsError("normalized event is not publishable")

    if classification.get("event_id") != event_id or classification.get(
        "format"
    ) != format_id:
        raise MeleeStatisticsError("classification identity does not match event")
    classification_quality = classification.get("quality")
    if not isinstance(classification_quality, Mapping) or classification_quality.get(
        "blocking"
    ):
        raise MeleeStatisticsError("classification overlay is blocking")
    classification_input = classification.get("input")
    if (
        not isinstance(classification_input, Mapping)
        or classification_input.get("event_sha256") != event_sha256
    ):
        raise MeleeStatisticsError("classification does not hash the supplied event")

    if (
        ledger.get("event_id") != event_id
        or ledger.get("format") != format_id
        or ledger.get("event_structure") != event_structure
    ):
        raise MeleeStatisticsError("opportunity ledger identity does not match event")
    expected_scopes = STRUCTURE_SCOPE_ORDER[str(event_structure)]
    scope_summaries = ledger.get("scope_summaries")
    if not isinstance(scope_summaries, Mapping) or tuple(scope_summaries) != (
        expected_scopes
    ):
        raise MeleeStatisticsError(
            f"{event_structure} opportunity scopes do not match its structure"
        )
    ledger_input = ledger.get("input")
    if not isinstance(ledger_input, Mapping):
        raise MeleeStatisticsError("opportunity ledger input must be an object")
    if ledger_input.get("event_sha256") != event_sha256:
        raise MeleeStatisticsError("opportunity ledger event hash does not match")
    if ledger_input.get("classification_sha256") != classification_sha256:
        raise MeleeStatisticsError(
            "opportunity ledger classification hash does not match"
        )

    taxonomy_document = classification.get("taxonomy")
    if not isinstance(taxonomy_document, Mapping):
        raise MeleeStatisticsError("classification taxonomy must be an object")
    if taxonomy_document.get("rule_sha256") != taxonomy_sha256:
        raise MeleeStatisticsError("taxonomy hash does not match classification")
    if taxonomy.format != format_id:
        raise MeleeStatisticsError("taxonomy format does not match event")

    participants = _objects_by_id(
        event.get("participants"), field="id", label="event.participants"
    )
    standings = _objects_by_id(
        event.get("standings"), field="participant_id", label="event.standings"
    )
    decklists = _objects_by_id(
        event.get("decklists"), field="participant_id", label="event.decklists"
    )
    classifications = _objects_by_id(
        classification.get("records"),
        field="participant_id",
        label="classification.records",
    )
    ledger_participants = _objects_by_id(
        ledger.get("participants"),
        field="participant_id",
        label="ledger.participants",
    )
    participant_ids = set(participants)
    for label, values in (
        ("standings", standings),
        ("decklists", decklists),
        ("classifications", classifications),
        ("ledger participants", ledger_participants),
    ):
        if set(values) != participant_ids:
            raise MeleeStatisticsError(
                f"{label} must cover every event participant exactly once"
            )
    if not isinstance(ledger.get("opportunities"), list):
        raise MeleeStatisticsError("ledger.opportunities must be a list")
    if any(
        item.get("participant_id") not in participant_ids
        for item in ledger["opportunities"]
        if isinstance(item, Mapping)
    ):
        raise MeleeStatisticsError("opportunity references an unknown participant")
    if not ledger_sha256:
        raise MeleeStatisticsError("opportunity ledger hash is missing")
    return (
        event_id,
        format_id,
        metadata,
        participants,
        standings,
        decklists,
        ledger_participants,
    )


def _input_document(
    *,
    event_path: str,
    event_sha256: str,
    event_schema_version: Any,
    classification_path: str,
    classification_sha256: str,
    classification_schema_version: Any,
    opportunity_path: str,
    opportunity_sha256: str,
    opportunity_schema_version: Any,
    taxonomy_path: str,
    taxonomy_sha256: str,
    taxonomy_schema_version: str,
) -> dict[str, Any]:
    return {
        "event_path": event_path,
        "event_sha256": event_sha256,
        "event_schema_version": event_schema_version,
        "classification_path": classification_path,
        "classification_sha256": classification_sha256,
        "classification_schema_version": classification_schema_version,
        "opportunity_path": opportunity_path,
        "opportunity_sha256": opportunity_sha256,
        "opportunity_schema_version": opportunity_schema_version,
        "taxonomy_path": taxonomy_path,
        "taxonomy_sha256": taxonomy_sha256,
        "taxonomy_schema_version": taxonomy_schema_version,
    }


def _scope_documents(
    *,
    ledger: Mapping[str, Any],
    taxonomy: RuleSet,
    participant_documents: Mapping[str, Mapping[str, Any]],
    event_structure: str,
    scope_order: Sequence[str],
) -> dict[str, Any]:
    opportunities = ledger["opportunities"]
    parents, leaves = _identity_keys(participant_documents)
    parent_definitions = {item.id: item for item in taxonomy.archetypes}
    participant_ids_by_parent: dict[tuple[str, ...], set[str]] = {}
    participant_ids_by_leaf: dict[tuple[str, ...], set[str]] = {}
    for participant_id in participant_documents:
        participant_ids_by_parent.setdefault(parents[participant_id], set()).add(
            participant_id
        )
        participant_ids_by_leaf.setdefault(leaves[participant_id], set()).add(
            participant_id
        )

    scopes: dict[str, Any] = {}
    for scope in scope_order:
        population = _scope_population(participant_documents, scope)
        scope_opportunities = [
            item
            for item in opportunities
            if scope == "all_constructed" or item["scope"] == scope
        ]
        participant_opportunities = {
            participant_id: [
                item
                for item in scope_opportunities
                if item["participant_id"] == participant_id
            ]
            for participant_id in population
        }
        total_high_score: int | None = None
        if _high_score_available(event_structure, scope):
            total_high_score = sum(
                _participant_high_score(items)[2] is True
                for items in participant_opportunities.values()
            )

        rows = []
        known_parent_keys = sorted(
            (key for key in participant_ids_by_parent if key[0] == "archetype"),
            key=lambda key: (
                -len(participant_ids_by_parent[key] & population),
                parent_definitions[key[1]].name.casefold(),
                key[1],
            ),
        )
        for parent_key in known_parent_keys:
            parent_id = parent_key[1]
            parent = parent_definitions.get(parent_id)
            if parent is None:
                raise MeleeStatisticsError(
                    f"classification references unknown taxonomy parent {parent_id}"
                )
            children = []
            for subtype in parent.subtypes:
                leaf_key = ("subtype", parent_id, subtype.id)
                children.append(
                    {
                        "group_id": f"subtype:{parent_id}/{subtype.id}",
                        "subtype_id": subtype.id,
                        "subtype_name": subtype.name,
                        "display_name": identity_display_name(
                            parent.name,
                            subtype.name,
                        ),
                        **_group_metrics(
                            participant_ids=participant_ids_by_leaf.get(
                                leaf_key, set()
                            ),
                            scope_population=population,
                            scope_opportunities=scope_opportunities,
                            scope=scope,
                            event_structure=event_structure,
                            total_high_score=total_high_score,
                            group_key=leaf_key,
                            identity_by_participant=leaves,
                        ),
                    }
                )
            row = {
                "group_id": f"archetype:{parent_id}",
                "classification_status": "classified",
                "archetype_id": parent_id,
                "archetype_name": parent.name,
                "expandable": len(parent.subtypes) >= 2,
                **_group_metrics(
                    participant_ids=participant_ids_by_parent[parent_key],
                    scope_population=population,
                    scope_opportunities=scope_opportunities,
                    scope=scope,
                    event_structure=event_structure,
                    total_high_score=total_high_score,
                    group_key=parent_key,
                    identity_by_participant=parents,
                ),
                "subtypes": children,
            }
            if children:
                for field in (
                    "deck_count",
                    "constructed_points",
                    "theoretical_rounds",
                    "effective_theoretical_rounds",
                    "completed_or_officially_exempt_rounds",
                    "played_match_participations",
                ):
                    if row[field] != sum(child[field] for child in children):
                        raise MeleeStatisticsError(
                            f"{scope} {parent_id} subtype {field} does not conserve"
                        )
                for field in ("wins", "losses", "draws", "matches"):
                    if row["match_record"]["all_matches"][field] != sum(
                        child["match_record"]["all_matches"][field]
                        for child in children
                    ):
                        raise MeleeStatisticsError(
                            f"{scope} {parent_id} subtype all-match {field} "
                            "does not conserve"
                        )
                if row["high_score"] is not None and row["high_score"][
                    "count"
                ] != sum(child["high_score"]["count"] for child in children):
                    raise MeleeStatisticsError(
                        f"{scope} {parent_id} subtype high-score count "
                        "does not conserve"
                    )
            rows.append(row)

        unknown_key = ("unknown",)
        if unknown_key in participant_ids_by_parent:
            rows.append(
                {
                    "group_id": "unknown",
                    "classification_status": "unknown",
                    "archetype_id": None,
                    "archetype_name": "Unknown",
                    "expandable": False,
                    **_group_metrics(
                        participant_ids=participant_ids_by_parent[unknown_key],
                        scope_population=population,
                        scope_opportunities=scope_opportunities,
                        scope=scope,
                        event_structure=event_structure,
                        total_high_score=total_high_score,
                        group_key=unknown_key,
                        identity_by_participant=parents,
                    ),
                    "subtypes": [],
                }
            )
        if sum(row["deck_count"] for row in rows) != len(population):
            raise MeleeStatisticsError(f"{scope} archetype deck counts do not conserve")

        scope_summary = ledger["scope_summaries"][scope]
        scope_document = {
            "population": (
                "starting_field"
                if scope == "day1"
                or event_structure == "constructed_single_stage"
                else "qualified_field"
                if scope == "day2"
                else "starting_field_with_qualified_day2_opportunities"
            ),
            "selection_bias_warning": (
                event_structure == "mixed"
                and scope in {"day2", "all_constructed"}
            ),
            "participant_count": len(population),
            "known_deck_count": sum(
                row["deck_count"]
                for row in rows
                if row["classification_status"] == "classified"
            ),
            "unknown_deck_count": sum(
                row["deck_count"]
                for row in rows
                if row["classification_status"] == "unknown"
            ),
            "scheduled_round_count": scope_summary["scheduled_round_count"],
            "theoretical_rounds": scope_summary["theoretical_rounds"],
            "effective_theoretical_rounds": scope_summary[
                "effective_theoretical_rounds"
            ],
            "constructed_points": scope_summary["constructed_points"],
            "average_points_per_effective_round": _rounded_ratio(
                scope_summary["constructed_points"],
                scope_summary["effective_theoretical_rounds"],
            ),
            "source_match_count": scope_summary["source_match_count"],
            "eligible_match_count": scope_summary["win_rate_match_count"],
            "disqualified_matches_excluded": scope_summary[
                "disqualified_matches_excluded"
            ],
            "high_score_deck_count": total_high_score,
            "result_counts": scope_summary["result_counts"],
            "archetypes": rows,
        }
        if event_structure == "constructed_day2" and scope == "day2":
            scope_document["day2_conversion"] = _rounded_ratio(
                len(population), len(participant_documents)
            )
        scopes[scope] = scope_document
    return scopes


def _deck_scope(
    participant_id: str,
    scope: str,
    participant_document: Mapping[str, Any],
    opportunities: Sequence[Mapping[str, Any]],
    event_structure: str,
) -> dict[str, Any]:
    participates = (
        True
        if scope in {"day1", "all_constructed"}
        else participant_document.get("day2_participant") is True
    )
    items = [
        item
        for item in opportunities
        if item["participant_id"] == participant_id
        and (scope == "all_constructed" or item["scope"] == scope)
    ]
    if not participates and items:
        raise MeleeStatisticsError(
            f"{participant_id} has opportunities in a scope they did not enter"
        )
    points = sum(int(item["constructed_points"]) for item in items)
    theoretical = sum(bool(item["theoretical_round"]) for item in items)
    effective = sum(bool(item["effective_theoretical_round"]) for item in items)
    completed_or_exempt = sum(
        str(item["result_type"]) in COMPLETED_OR_EXEMPT_RESULT_TYPES for item in items
    )
    high_score = None
    if _high_score_available(event_structure, scope) and participates:
        threshold, _points, qualifies = _participant_high_score(items)
        high_score = {"threshold": threshold, "qualified": qualifies}
    result_counts = _result_counts(items)
    return {
        "participated": participates,
        "constructed_points": points,
        "theoretical_rounds": theoretical,
        "effective_theoretical_rounds": effective,
        "average_points_per_effective_round": _rounded_ratio(points, effective),
        "completed_or_officially_exempt_rounds": completed_or_exempt,
        "completion_rate": _rounded_ratio(completed_or_exempt, theoretical),
        "played_record": _record_from_result_types(
            [
                str(item["result_type"])
                for item in items
                if item["win_rate_included"]
            ]
        ),
        "high_score": high_score,
        "result_counts": result_counts,
    }


def _deck_documents(
    *,
    participants: Mapping[str, Mapping[str, Any]],
    standings: Mapping[str, Mapping[str, Any]],
    decklists: Mapping[str, Mapping[str, Any]],
    participant_documents: Mapping[str, Mapping[str, Any]],
    opportunities: Sequence[Mapping[str, Any]],
    event_structure: str,
    scope_order: Sequence[str],
) -> list[dict[str, Any]]:
    result = []
    for participant_id in sorted(
        participants,
        key=lambda identifier: (
            int(standings[identifier]["rank"]),
            identifier,
        ),
    ):
        participant = participants[participant_id]
        standing = standings[participant_id]
        decklist = decklists[participant_id]
        ledger_participant = participant_documents[participant_id]
        classification = ledger_participant["classification"]
        result.append(
            {
                "participant_id": participant_id,
                "player_name": participant["display_name"],
                "participant_status": participant["status"],
                "final_rank": standing["rank"],
                "overall_event_match_points": standing["match_points"],
                "overall_points_include_non_constructed_context": (
                    event_structure == "mixed"
                ),
                "day2_participant": ledger_participant["day2_participant"],
                "classification": classification,
                "decklist": {
                    "game_format": decklist["game_format"],
                    "status": decklist["status"],
                    "source_url": decklist["source_url"],
                    "cards": decklist["cards"],
                },
                "statistics_eligibility": {
                    "point_metrics_follow_opportunity_ledger": True,
                    "played_match_metrics_excluded": (
                        participant["status"] == "disqualified"
                    ),
                    "exclusion_reason": (
                        "disqualified_participant"
                        if participant["status"] == "disqualified"
                        else None
                    ),
                },
                "scopes": {
                    scope: _deck_scope(
                        participant_id,
                        scope,
                        ledger_participant,
                        opportunities,
                        event_structure,
                    )
                    for scope in scope_order
                },
            }
        )
    return result


def _quality_document(
    *,
    event: Mapping[str, Any],
    classification: Mapping[str, Any],
    ledger: Mapping[str, Any],
    scopes: Mapping[str, Any],
    participants: Mapping[str, Mapping[str, Any]],
    decklists: Mapping[str, Mapping[str, Any]],
    input_document: Mapping[str, Any],
) -> dict[str, Any]:
    rounds = event["rounds"]
    matches = event["matches"]
    opportunities = ledger["opportunities"]
    disqualified_ids = {
        participant_id
        for participant_id, participant in participants.items()
        if participant["status"] == "disqualified"
    }
    playoff_round_ids = {
        item["id"] for item in rounds if item["round_phase"] == "playoff"
    }
    playoff_participants = {
        competitor["participant_id"]
        for match in matches
        if match["round_id"] in playoff_round_ids
        for competitor in match["competitors"]
    }
    intentional_draw_match_ids = {
        item["match_id"]
        for item in opportunities
        if item["result_type"] == "intentional_draw" and item["match_id"] is not None
    }
    combined = ledger["scope_summaries"]["all_constructed"]
    checks = [
        {
            "id": "participant_coverage",
            "passed": len(participants) == len(decklists) == len(ledger["participants"]),
        },
        {
            "id": "classification_coverage",
            "passed": classification["summary"]["total_records"] == len(participants),
        },
        {
            "id": "scope_participant_conservation",
            "passed": scopes["day1"]["participant_count"] == len(participants)
            and scopes["day2"]["participant_count"]
            == ledger["scope_summaries"]["day2"]["participant_count"],
        },
        {
            "id": "scope_points_conservation",
            "passed": combined["constructed_points"]
            == ledger["scope_summaries"]["day1"]["constructed_points"]
            + ledger["scope_summaries"]["day2"]["constructed_points"],
        },
        {
            "id": "scope_opportunity_conservation",
            "passed": combined["theoretical_rounds"]
            == ledger["scope_summaries"]["day1"]["theoretical_rounds"]
            + ledger["scope_summaries"]["day2"]["theoretical_rounds"],
        },
        {
            "id": "eligible_match_conservation",
            "passed": combined["win_rate_match_count"]
            == scopes["all_constructed"]["eligible_match_count"],
        },
        {
            "id": "draft_and_playoff_excluded",
            "passed": all(
                item["scope"] in {"day1", "day2"} for item in opportunities
            ),
        },
    ]
    failed = [item["id"] for item in checks if not item["passed"]]
    if failed:
        raise MeleeStatisticsError(
            "quality reconciliation failed: " + ", ".join(failed)
        )
    issues = []
    if classification["summary"]["unknown"]:
        issues.append(
            {
                "code": "unknown_classifications",
                "severity": "warning",
                "count": classification["summary"]["unknown"],
                "message": "Valid submitted decks remain explicitly Unknown.",
            }
        )
    if disqualified_ids:
        issues.append(
            {
                "code": "disqualified_participant_matches_excluded",
                "severity": "warning",
                "count": combined["disqualified_matches_excluded"],
                "message": (
                    "Disqualified participant records are retained while every "
                    "affected match is excluded symmetrically from played-match statistics."
                ),
            }
        )
    issues.append(
        {
            "code": "mixed_event_day2_selection_bias",
            "severity": "warning",
            "count": scopes["day2"]["participant_count"],
            "message": (
                "Day 2 participants were selected using combined event performance, "
                "including Draft; Day 2 Modern statistics describe the qualified field."
            ),
        }
    )
    return {
        "schema_version": EVENT_STATISTICS_SCHEMA_VERSION,
        "document_type": "quality",
        "source": "melee",
        "event_id": ledger["event_id"],
        "format": ledger["format"],
        "event_structure": "mixed",
        "input": dict(input_document),
        "status": "warning" if issues else "ready",
        "blocking": False,
        "counts": {
            "participants": len(participants),
            "standings": len(event["standings"]),
            "submitted_decklists": sum(
                item["status"] == "submitted" for item in decklists.values()
            ),
            "missing_or_unavailable_decklists": sum(
                item["status"] != "submitted" for item in decklists.values()
            ),
            "classified_decks": classification["summary"]["classified"],
            "unknown_decks": classification["summary"]["unknown"],
            "classification_conflicts": classification["summary"]["conflicts"],
            "invalid_decks": classification["summary"]["invalid_decks"],
            "rounds": len(rounds),
            "unknown_rounds": sum(
                item["round_phase"] == "unknown" for item in rounds
            ),
            "source_matches": len(matches),
            "source_constructed_matches": combined["source_match_count"],
            "eligible_constructed_matches": combined["win_rate_match_count"],
            "unknown_result_opportunities": combined["result_counts"].get(
                "unknown", 0
            ),
            "bye_count": combined["result_counts"].get("bye", 0),
            "intentional_draw_match_count": len(intentional_draw_match_ids),
            "intentional_draw_opportunities": combined["result_counts"].get(
                "intentional_draw", 0
            ),
            "drop_player_count": len(
                {
                    item["participant_id"]
                    for item in opportunities
                    if item["result_type"] == "drop_unplayed"
                }
            ),
            "drop_unplayed_rounds": combined["result_counts"].get(
                "drop_unplayed", 0
            ),
            "disqualified_participant_count": len(disqualified_ids),
            "disqualified_matches_excluded": combined[
                "disqualified_matches_excluded"
            ],
            "top8_lock_player_count": len(
                {
                    item["participant_id"]
                    for item in opportunities
                    if item["result_type"] == "awarded_win_top8_lock"
                }
            ),
            "top8_lock_exemptions": combined["result_counts"].get(
                "awarded_win_top8_lock", 0
            ),
            "day2_participants": scopes["day2"]["participant_count"],
            "playoff_participants": len(playoff_participants),
            "no_show_opportunities": combined["result_counts"].get("no_show", 0),
        },
        "checks": checks,
        "issues": issues,
    }


def build_event_overview_and_decks(
    event: Mapping[str, Any],
    classification: Mapping[str, Any],
    ledger: Mapping[str, Any],
    taxonomy: RuleSet,
    *,
    event_path: str,
    event_sha256: str,
    classification_path: str,
    classification_sha256: str,
    opportunity_path: str,
    opportunity_sha256: str,
    taxonomy_path: str,
    taxonomy_sha256: str,
) -> dict[str, dict[str, Any]]:
    """Build deterministic overview and deck documents for one event structure."""

    (
        event_id,
        format_id,
        metadata,
        participants,
        standings,
        decklists,
        participant_documents,
    ) = _validate_inputs(
        event,
        classification,
        ledger,
        taxonomy,
        event_sha256=event_sha256,
        classification_sha256=classification_sha256,
        ledger_sha256=opportunity_sha256,
        taxonomy_sha256=taxonomy_sha256,
    )
    event_structure = str(event["event_structure"])
    scope_order = STRUCTURE_SCOPE_ORDER[event_structure]
    input_document = _input_document(
        event_path=event_path,
        event_sha256=event_sha256,
        event_schema_version=event.get("schema_version"),
        classification_path=classification_path,
        classification_sha256=classification_sha256,
        classification_schema_version=classification.get("schema_version"),
        opportunity_path=opportunity_path,
        opportunity_sha256=opportunity_sha256,
        opportunity_schema_version=ledger.get("schema_version"),
        taxonomy_path=taxonomy_path,
        taxonomy_sha256=taxonomy_sha256,
        taxonomy_schema_version=taxonomy.schema_version,
    )
    scopes = _scope_documents(
        ledger=ledger,
        taxonomy=taxonomy,
        participant_documents=participant_documents,
        event_structure=event_structure,
        scope_order=scope_order,
    )
    warnings = (
        [
            {
                "code": "mixed_event_day2_selection_bias",
                "scopes": ["day2", "all_constructed"],
                "message": (
                    "Day 2 participants were selected using combined event performance, "
                    "including Draft where applicable."
                ),
            },
            {
                "code": "overall_standings_include_non_constructed_results",
                "scopes": SCOPE_ORDER,
                "message": (
                    "Final rank and overall event points are context only and are not "
                    "used as Modern performance points."
                ),
            },
        ]
        if event_structure == "mixed"
        else []
    )
    overview = {
        "schema_version": EVENT_STATISTICS_SCHEMA_VERSION,
        "document_type": "overview",
        "source": "melee",
        "event_id": event_id,
        "format": format_id,
        "event_structure": event_structure,
        "input": input_document,
        "event": {
            "name": metadata["name"],
            "series": metadata["series"],
            "date": metadata["date"],
            "source_url": _source_url(event, event_id),
        },
        "scope_order": list(scope_order),
        "default_scope": "all_constructed",
    }
    if event_structure != "mixed":
        overview["advancement_metric"] = (
            "day2_conversion"
            if event_structure == "constructed_day2"
            else "high_score_conversion"
        )
    overview["scopes"] = scopes
    overview["warnings"] = warnings
    decks = {
        "schema_version": EVENT_STATISTICS_SCHEMA_VERSION,
        "document_type": "decks",
        "source": "melee",
        "event_id": event_id,
        "format": format_id,
        "event_structure": event_structure,
        "input": input_document,
        "scope_order": list(scope_order),
        "decks": _deck_documents(
            participants=participants,
            standings=standings,
            decklists=decklists,
            participant_documents=participant_documents,
            opportunities=ledger["opportunities"],
            event_structure=event_structure,
            scope_order=scope_order,
        ),
        "warnings": warnings,
    }
    return {"overview": overview, "decks": decks}


def build_event_statistics(
    event: Mapping[str, Any],
    classification: Mapping[str, Any],
    ledger: Mapping[str, Any],
    taxonomy: RuleSet,
    *,
    event_path: str,
    event_sha256: str,
    classification_path: str,
    classification_sha256: str,
    opportunity_path: str,
    opportunity_sha256: str,
    taxonomy_path: str,
    taxonomy_sha256: str,
) -> dict[str, dict[str, Any]]:
    """Build the existing mixed-event overview, decks, and quality bundle."""

    if event.get("event_structure") != "mixed":
        raise MeleeStatisticsError(
            "quality generation for pure structures belongs to P9-05"
        )
    documents = build_event_overview_and_decks(
        event,
        classification,
        ledger,
        taxonomy,
        event_path=event_path,
        event_sha256=event_sha256,
        classification_path=classification_path,
        classification_sha256=classification_sha256,
        opportunity_path=opportunity_path,
        opportunity_sha256=opportunity_sha256,
        taxonomy_path=taxonomy_path,
        taxonomy_sha256=taxonomy_sha256,
    )
    participants = _objects_by_id(
        event.get("participants"), field="id", label="event.participants"
    )
    decklists = _objects_by_id(
        event.get("decklists"), field="participant_id", label="event.decklists"
    )
    quality = _quality_document(
        event=event,
        classification=classification,
        ledger=ledger,
        scopes=documents["overview"]["scopes"],
        participants=participants,
        decklists=decklists,
        input_document=documents["overview"]["input"],
    )
    return {
        "overview": documents["overview"],
        "decks": documents["decks"],
        "quality": quality,
    }


def statistics_document_bytes(document: Mapping[str, Any]) -> bytes:
    """Return canonical, human-reviewable UTF-8 bytes."""

    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def build_event_statistics_from_paths(
    event_path: Path,
    classification_path: Path,
    opportunity_path: Path,
    taxonomy_path: Path,
    repository_root: Path,
) -> dict[str, dict[str, Any]]:
    """Load exact retained inputs and build deterministic event statistics."""

    root = repository_root.resolve()
    event, event_bytes = _read_json_object(event_path)
    classification, classification_bytes = _read_json_object(classification_path)
    ledger, ledger_bytes = _read_json_object(opportunity_path)
    try:
        taxonomy_bytes = taxonomy_path.read_bytes()
        taxonomy = load_rule_set(taxonomy_path)
    except (OSError, RuleConfigError) as exc:
        raise MeleeStatisticsError(f"{taxonomy_path}: cannot load taxonomy") from exc
    return build_event_statistics(
        event,
        classification,
        ledger,
        taxonomy,
        event_path=_repository_relative(event_path, root),
        event_sha256=_sha256_bytes(event_bytes),
        classification_path=_repository_relative(classification_path, root),
        classification_sha256=_sha256_bytes(classification_bytes),
        opportunity_path=_repository_relative(opportunity_path, root),
        opportunity_sha256=_sha256_bytes(ledger_bytes),
        taxonomy_path=_repository_relative(taxonomy_path, root),
        taxonomy_sha256=_sha256_bytes(taxonomy_bytes),
    )


def write_statistics_document(path: Path, payload: bytes) -> bool:
    """Atomically write one document and return whether identical bytes existed."""

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
        description="Generate deterministic overview and deck statistics for one Melee event."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", required=True, dest="format_id")
    parser.add_argument("--event-id", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="atomically write overview, decks, and quality; default mode is read-only",
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
    opportunity_path = (
        root
        / "data"
        / args.format_id
        / "melee"
        / "opportunities"
        / f"{args.event_id}.json"
    )
    taxonomy_path = root / "my_archetypes" / f"{args.format_id}.yaml"
    output_dir = (
        root
        / "stats"
        / args.format_id
        / "melee"
        / "events"
        / args.event_id
    )
    try:
        documents = build_event_statistics_from_paths(
            event_path,
            classification_path,
            opportunity_path,
            taxonomy_path,
            root,
        )
        reused = {}
        if args.execute:
            for name, document in documents.items():
                reused[name] = write_statistics_document(
                    output_dir / f"{name}.json",
                    statistics_document_bytes(document),
                )
        overview = documents["overview"]
        print(
            json.dumps(
                {
                    "event_id": args.event_id,
                    "format": args.format_id,
                    "mode": "execute" if args.execute else "dry-run",
                    "output_dir": (
                        _repository_relative(output_dir, root)
                        if args.execute
                        else None
                    ),
                    "reused": reused,
                    "participants": overview["scopes"]["day1"][
                        "participant_count"
                    ],
                    "day2_participants": overview["scopes"]["day2"][
                        "participant_count"
                    ],
                    "eligible_matches": overview["scopes"]["all_constructed"][
                        "eligible_match_count"
                    ],
                    "unknown_decks": overview["scopes"]["day1"][
                        "unknown_deck_count"
                    ],
                },
                sort_keys=True,
            )
        )
        return 0
    except (MeleeStatisticsError, OSError, ValueError) as exc:
        print(f"Melee event statistics ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
