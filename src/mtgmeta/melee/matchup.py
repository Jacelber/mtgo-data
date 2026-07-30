"""Deterministic hierarchical matchup statistics for one Melee event."""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

from ..consumer import identity_display_name, literal_match_record
from .stats import (
    MeleeStatisticsError,
    STRUCTURE_SCOPE_ORDER,
    build_event_statistics_from_paths,
    statistics_document_bytes,
    write_statistics_document,
)


MATCHUP_SCHEMA_VERSION = "1.0.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
WILSON_Z = 1.959963984540054
RESULT_FIELD = {
    "played_win": "wins",
    "played_loss": "losses",
    "played_draw": "draws",
}
INVERSE_RESULT = {
    "played_win": "played_loss",
    "played_loss": "played_win",
    "played_draw": "played_draw",
}
EXCLUSION_KEYS = (
    "bye",
    "intentional_draw",
    "no_show",
    "awarded_win_top8_lock",
    "administrative_result",
    "disqualified_participant",
    "unknown",
)


class MeleeMatchupError(ValueError):
    """Raised when a Melee matchup matrix cannot be built without guessing."""


def _read_json_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        document = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise MeleeMatchupError(f"{path}: cannot read JSON object") from exc
    if not isinstance(document, dict):
        raise MeleeMatchupError(f"{path}: top level must be an object")
    return document, payload


def _blank_counts() -> dict[str, int]:
    return {"wins": 0, "losses": 0, "draws": 0}


def _hierarchy_from_overview(
    overview: Mapping[str, Any],
    scope_order: Sequence[str],
) -> tuple[dict[str, Any], list[str], list[str], dict[str, str]]:
    scopes = overview.get("scopes")
    if not isinstance(scopes, Mapping):
        raise MeleeMatchupError("overview.scopes must be an object")
    combined = scopes.get("all_constructed")
    if not isinstance(combined, Mapping):
        raise MeleeMatchupError("overview has no all_constructed scope")
    rows = combined.get("archetypes")
    if not isinstance(rows, list) or not rows:
        raise MeleeMatchupError("overview has no archetype rows")

    parents: list[dict[str, Any]] = []
    leaves: list[dict[str, Any]] = []
    parent_order: list[str] = []
    leaf_order: list[str] = []
    leaf_to_parent: dict[str, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MeleeMatchupError(f"overview archetype row {index} is invalid")
        if row.get("group_id") == "unknown":
            parent_id = "unknown"
            parent = {
                "id": parent_id,
                "name": str(row.get("archetype_name", "Unknown")),
                "expandable": False,
                "subtype_ids": [],
            }
            leaf = {
                "id": parent_id,
                "kind": "unknown",
                "name": parent["name"],
                "display_name": parent["name"],
                "parent_id": parent_id,
                "subtype_id": None,
            }
            parent_order.append(parent_id)
            leaf_order.append(parent_id)
            leaf_to_parent[parent_id] = parent_id
            parents.append(parent)
            leaves.append(leaf)
            continue

        parent_id = row.get("archetype_id")
        parent_name = row.get("archetype_name")
        subtypes = row.get("subtypes")
        if (
            not isinstance(parent_id, str)
            or not isinstance(parent_name, str)
            or not isinstance(subtypes, list)
        ):
            raise MeleeMatchupError(f"overview archetype row {index} is invalid")
        subtype_ids: list[str] = []
        for subtype in subtypes:
            if not isinstance(subtype, Mapping):
                raise MeleeMatchupError(
                    f"overview subtype under {parent_id} is invalid"
                )
            subtype_id = subtype.get("subtype_id")
            subtype_name = subtype.get("subtype_name")
            if not isinstance(subtype_id, str) or not isinstance(
                subtype_name, str
            ):
                raise MeleeMatchupError(
                    f"overview subtype under {parent_id} has no identity"
                )
            leaf_id = f"{parent_id}/{subtype_id}"
            subtype_ids.append(leaf_id)
            leaf_order.append(leaf_id)
            leaf_to_parent[leaf_id] = parent_id
            leaves.append(
                {
                    "id": leaf_id,
                    "kind": "subtype",
                    "name": subtype_name,
                    "display_name": identity_display_name(
                        parent_name,
                        subtype_name,
                    ),
                    "parent_id": parent_id,
                    "subtype_id": subtype_id,
                }
            )
        if not subtype_ids:
            leaf_order.append(parent_id)
            leaf_to_parent[parent_id] = parent_id
            leaves.append(
                {
                    "id": parent_id,
                    "kind": "archetype",
                    "name": parent_name,
                    "display_name": parent_name,
                    "parent_id": parent_id,
                    "subtype_id": None,
                }
            )
        parents.append(
            {
                "id": parent_id,
                "name": parent_name,
                "expandable": row.get("expandable") is True,
                "subtype_ids": subtype_ids,
            }
        )
        parent_order.append(parent_id)

    if len(set(parent_order)) != len(parent_order):
        raise MeleeMatchupError("overview contains duplicate parent identities")
    if len(set(leaf_order)) != len(leaf_order):
        raise MeleeMatchupError("overview contains duplicate leaf identities")
    expected = set(parent_order)
    for scope_id in scope_order:
        scope = scopes.get(scope_id)
        scope_rows = scope.get("archetypes") if isinstance(scope, Mapping) else None
        if not isinstance(scope_rows, list):
            raise MeleeMatchupError(f"overview scope {scope_id} has no rows")
        actual = [
            "unknown" if row.get("group_id") == "unknown" else row.get("archetype_id")
            for row in scope_rows
            if isinstance(row, Mapping)
        ]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise MeleeMatchupError(
                f"overview scope {scope_id} uses a different parent set"
            )
    return (
        {"parents": parents, "leaves": leaves},
        parent_order,
        leaf_order,
        leaf_to_parent,
    )


def _participant_leaf_ids(
    ledger: Mapping[str, Any], leaf_to_parent: Mapping[str, str]
) -> dict[str, str]:
    participants = ledger.get("participants")
    if not isinstance(participants, list):
        raise MeleeMatchupError("ledger.participants must be a list")
    identities: dict[str, str] = {}
    for index, participant in enumerate(participants):
        if not isinstance(participant, Mapping):
            raise MeleeMatchupError(f"ledger participant {index} is invalid")
        participant_id = participant.get("participant_id")
        classification = participant.get("classification")
        if not isinstance(participant_id, str) or not isinstance(
            classification, Mapping
        ):
            raise MeleeMatchupError(f"ledger participant {index} is invalid")
        if classification.get("status") == "unknown":
            leaf_id = "unknown"
        else:
            archetype_id = classification.get("archetype_id")
            subtype_id = classification.get("subtype_id")
            if not isinstance(archetype_id, str):
                raise MeleeMatchupError(
                    f"ledger participant {participant_id} has no parent identity"
                )
            leaf_id = (
                f"{archetype_id}/{subtype_id}"
                if isinstance(subtype_id, str)
                else archetype_id
            )
        if leaf_id not in leaf_to_parent:
            raise MeleeMatchupError(
                f"ledger participant {participant_id} uses unknown leaf {leaf_id}"
            )
        if participant_id in identities:
            raise MeleeMatchupError(
                f"ledger contains duplicate participant {participant_id}"
            )
        identities[participant_id] = leaf_id
    return identities


def _source_match_groups(
    ledger: Mapping[str, Any],
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    opportunities = ledger.get("opportunities")
    if not isinstance(opportunities, list):
        raise MeleeMatchupError("ledger.opportunities must be a list")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for index, opportunity in enumerate(opportunities):
        if not isinstance(opportunity, Mapping):
            raise MeleeMatchupError(f"ledger opportunity {index} is invalid")
        match_id = opportunity.get("match_id")
        if match_id is not None:
            if not isinstance(match_id, str):
                raise MeleeMatchupError(
                    f"ledger opportunity {index} has invalid match ID"
                )
            grouped[match_id].append(opportunity)
        elif opportunity.get("matchup_included"):
            raise MeleeMatchupError(
                f"ledger opportunity {index} is included without a match ID"
            )
    return {
        match_id: tuple(rows) for match_id, rows in sorted(grouped.items())
    }


def _match_scope(match_id: str, rows: Sequence[Mapping[str, Any]]) -> str:
    scopes = {row.get("scope") for row in rows}
    if len(scopes) != 1 or next(iter(scopes)) not in {
        "day1",
        "day2",
        "all_constructed",
    }:
        raise MeleeMatchupError(f"match {match_id} has inconsistent scope")
    return str(next(iter(scopes)))


def _eligible_pair(
    match_id: str, rows: Sequence[Mapping[str, Any]]
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    included = [row.get("matchup_included") is True for row in rows]
    if not any(included):
        return None
    if len(rows) != 2 or not all(included):
        raise MeleeMatchupError(
            f"match {match_id} must be included on both sides exactly once"
        )
    first, second = rows
    first_id = first.get("participant_id")
    second_id = second.get("participant_id")
    if (
        not isinstance(first_id, str)
        or not isinstance(second_id, str)
        or first_id == second_id
        or first.get("opponent_participant_id") != second_id
        or second.get("opponent_participant_id") != first_id
    ):
        raise MeleeMatchupError(f"match {match_id} has inconsistent competitors")
    first_result = first.get("result_type")
    second_result = second.get("result_type")
    if (
        not isinstance(first_result, str)
        or first_result not in RESULT_FIELD
        or INVERSE_RESULT[first_result] != second_result
    ):
        raise MeleeMatchupError(f"match {match_id} has non-inverse results")
    _match_scope(match_id, rows)
    return first, second


def _exclusion_category(rows: Sequence[Mapping[str, Any]]) -> str:
    reasons = {
        reason
        for row in rows
        for reason in row.get("exclusion_reasons", [])
        if isinstance(reason, str)
    }
    results = {
        row.get("result_type")
        for row in rows
        if isinstance(row.get("result_type"), str)
    }
    if "disqualified_participant" in reasons:
        return "disqualified_participant"
    for result in (
        "bye",
        "intentional_draw",
        "no_show",
        "awarded_win_top8_lock",
        "administrative_result",
    ):
        if results == {result}:
            return result
    return "unknown"


def _empty_matrix(order: Sequence[str]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        row_id: {column_id: _blank_counts() for column_id in order}
        for row_id in order
    }


def _accumulate_pair(
    matrix: dict[str, dict[str, dict[str, int]]],
    pair: tuple[Mapping[str, Any], Mapping[str, Any]],
    participant_leaf: Mapping[str, str],
) -> None:
    for row in pair:
        participant_id = str(row["participant_id"])
        opponent_id = str(row["opponent_participant_id"])
        try:
            row_id = participant_leaf[participant_id]
            column_id = participant_leaf[opponent_id]
        except KeyError as exc:
            raise MeleeMatchupError(
                f"match references participant without classification: {exc.args[0]}"
            ) from exc
        matrix[row_id][column_id][RESULT_FIELD[str(row["result_type"])]] += 1


def _roll_up(
    leaf_matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    parent_order: Sequence[str],
    leaf_to_parent: Mapping[str, str],
) -> dict[str, dict[str, dict[str, int]]]:
    parent_matrix = _empty_matrix(parent_order)
    for row_id, columns in leaf_matrix.items():
        parent_row = leaf_to_parent[row_id]
        for column_id, cell in columns.items():
            target = parent_matrix[parent_row][leaf_to_parent[column_id]]
            for field in ("wins", "losses", "draws"):
                target[field] += int(cell[field])
    return parent_matrix


def _validate_matrix(
    matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    order: Sequence[str],
    physical_matches: int,
    *,
    label: str,
) -> None:
    observations = 0
    if tuple(matrix) != tuple(order):
        raise MeleeMatchupError(f"{label} matrix row order is inconsistent")
    for row_id in order:
        if tuple(matrix[row_id]) != tuple(order):
            raise MeleeMatchupError(f"{label} matrix column order is inconsistent")
        for column_id in order:
            cell = matrix[row_id][column_id]
            inverse = matrix[column_id][row_id]
            if (
                cell["wins"] != inverse["losses"]
                or cell["losses"] != inverse["wins"]
                or cell["draws"] != inverse["draws"]
            ):
                raise MeleeMatchupError(
                    f"{label} matrix cell {row_id}/{column_id} is not inverse"
                )
            observations += sum(int(cell[field]) for field in RESULT_FIELD.values())
    if observations != physical_matches * 2:
        raise MeleeMatchupError(
            f"{label} matrix observations do not conserve physical matches"
        )


def _emit_record(counts: Mapping[str, int], *, mirror: bool) -> dict[str, Any]:
    wins = int(counts["wins"])
    losses = int(counts["losses"])
    draws = int(counts["draws"])
    matches = wins + losses + draws
    if matches == 0:
        win_rate = None
        interval = None
    else:
        proportion = (wins + 0.5 * draws) / matches
        win_rate = round(proportion, 6)
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
        "mirror": mirror,
        "literal_record": literal_match_record(wins, losses, draws),
    }


def _emit_matrix(
    matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    order: Sequence[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        row_id: {
            column_id: _emit_record(
                matrix[row_id][column_id],
                mirror=row_id == column_id,
            )
            for column_id in order
        }
        for row_id in order
    }


def _emit_overall(
    matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    order: Sequence[str],
) -> dict[str, dict[str, Any]]:
    emitted: dict[str, dict[str, Any]] = {}
    for row_id in order:
        counts = _blank_counts()
        for column_id in order:
            if row_id == column_id:
                continue
            for field in ("wins", "losses", "draws"):
                counts[field] += int(matrix[row_id][column_id][field])
        emitted[row_id] = _emit_record(counts, mirror=False)
    return emitted


def _round_numbers(
    ledger: Mapping[str, Any],
    scope_id: str,
    event_structure: str,
) -> list[int]:
    rounds = ledger.get("rounds")
    if not isinstance(rounds, list):
        raise MeleeMatchupError("ledger.rounds must be a list")
    stages = {"day1"} if scope_id == "day1" else {"day2"}
    if scope_id == "all_constructed":
        stages = (
            {"day1", "other"}
            if event_structure == "constructed_single_stage"
            else {"day1", "day2"}
        )
    numbers = sorted(
        {
            int(item["round_number"])
            for item in rounds
            if isinstance(item, Mapping)
            and item.get("stage") in stages
            and isinstance(item.get("round_number"), int)
        }
    )
    if not numbers:
        raise MeleeMatchupError(f"ledger has no rounds for {scope_id}")
    return numbers


def _scope_document(
    *,
    scope_id: str,
    event_structure: str,
    ledger: Mapping[str, Any],
    groups: Mapping[str, tuple[Mapping[str, Any], ...]],
    participant_leaf: Mapping[str, str],
    parent_order: Sequence[str],
    leaf_order: Sequence[str],
    leaf_to_parent: Mapping[str, str],
) -> dict[str, Any]:
    stages = {"day1"} if scope_id == "day1" else {"day2"}
    if scope_id == "all_constructed":
        stages = (
            {"all_constructed"}
            if event_structure == "constructed_single_stage"
            else {"day1", "day2"}
        )
    scoped_groups = {
        match_id: rows
        for match_id, rows in groups.items()
        if _match_scope(match_id, rows) in stages
    }
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    exclusions = {key: 0 for key in EXCLUSION_KEYS}
    for match_id, rows in scoped_groups.items():
        pair = _eligible_pair(match_id, rows)
        if pair is None:
            exclusions[_exclusion_category(rows)] += 1
        else:
            pairs.append(pair)

    summaries = ledger.get("scope_summaries")
    summary = summaries.get(scope_id) if isinstance(summaries, Mapping) else None
    if not isinstance(summary, Mapping):
        raise MeleeMatchupError(f"ledger has no scope summary for {scope_id}")
    source_count = len(scoped_groups)
    if source_count != summary.get("source_match_count"):
        raise MeleeMatchupError(
            f"{scope_id} source matches do not reconcile with ledger summary"
        )
    if len(pairs) != summary.get("matchup_match_count"):
        raise MeleeMatchupError(
            f"{scope_id} included matches do not reconcile with ledger summary"
        )
    if source_count - len(pairs) != sum(exclusions.values()):
        raise MeleeMatchupError(f"{scope_id} excluded matches do not reconcile")

    leaf_matrix = _empty_matrix(leaf_order)
    for pair in pairs:
        _accumulate_pair(leaf_matrix, pair, participant_leaf)
    parent_matrix = _roll_up(leaf_matrix, parent_order, leaf_to_parent)
    _validate_matrix(
        leaf_matrix,
        leaf_order,
        len(pairs),
        label=f"{scope_id} leaf",
    )
    _validate_matrix(
        parent_matrix,
        parent_order,
        len(pairs),
        label=f"{scope_id} parent",
    )
    return {
        "round_numbers": _round_numbers(ledger, scope_id, event_structure),
        "source_match_count": source_count,
        "included_match_count": len(pairs),
        "excluded_match_count": source_count - len(pairs),
        "directed_observation_count": 2 * len(pairs),
        "excluded_match_counts": exclusions,
        "parent_order": list(parent_order),
        "parent_overall": _emit_overall(parent_matrix, parent_order),
        "parent_matrix": _emit_matrix(parent_matrix, parent_order),
        "leaf_order": list(leaf_order),
        "leaf_overall": _emit_overall(leaf_matrix, leaf_order),
        "leaf_matrix": _emit_matrix(leaf_matrix, leaf_order),
    }


def build_event_matchup(
    overview: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one deterministic hierarchical event matchup document."""

    event_structure = overview.get("event_structure")
    if (
        overview.get("document_type") != "overview"
        or overview.get("source") != "melee"
        or event_structure not in STRUCTURE_SCOPE_ORDER
    ):
        raise MeleeMatchupError("matchup generation requires a supported Melee overview")
    scope_order = STRUCTURE_SCOPE_ORDER[str(event_structure)]
    if overview.get("scope_order") != list(scope_order):
        raise MeleeMatchupError("overview scope order does not match event structure")
    if (
        ledger.get("source") != "melee"
        or ledger.get("event_id") != overview.get("event_id")
        or ledger.get("format") != overview.get("format")
        or ledger.get("event_structure") != event_structure
    ):
        raise MeleeMatchupError("opportunity ledger identity does not match overview")
    summaries = ledger.get("scope_summaries")
    if not isinstance(summaries, Mapping) or list(summaries) != list(scope_order):
        raise MeleeMatchupError(
            "opportunity ledger scopes do not match event structure"
        )
    input_document = overview.get("input")
    event_document = overview.get("event")
    if not isinstance(input_document, Mapping) or not isinstance(
        event_document, Mapping
    ):
        raise MeleeMatchupError("overview metadata is incomplete")

    (
        hierarchy,
        parent_order,
        leaf_order,
        leaf_to_parent,
    ) = _hierarchy_from_overview(overview, scope_order)
    participant_leaf = _participant_leaf_ids(ledger, leaf_to_parent)
    groups = _source_match_groups(ledger)
    scopes = {
        scope_id: _scope_document(
            scope_id=scope_id,
            event_structure=str(event_structure),
            ledger=ledger,
            groups=groups,
            participant_leaf=participant_leaf,
            parent_order=parent_order,
            leaf_order=leaf_order,
            leaf_to_parent=leaf_to_parent,
        )
        for scope_id in scope_order
    }
    warnings = [
        dict(warning)
        for warning in overview.get("warnings", [])
        if isinstance(warning, Mapping)
        and warning.get("code") == "mixed_event_day2_selection_bias"
    ]
    return {
        "schema_version": MATCHUP_SCHEMA_VERSION,
        "document_type": "matchup",
        "source": "melee",
        "event_id": overview["event_id"],
        "format": overview["format"],
        "event_structure": event_structure,
        "input": dict(input_document),
        "event": dict(event_document),
        "scope_order": list(scope_order),
        "default_scope": "all_constructed",
        "hierarchical": True,
        "canonical_level": "leaf",
        "rate_method": {
            "draw_weight": 0.5,
            "literal_win_rate_method": "wins_over_valid_matches",
            "confidence_interval": "wilson_95",
            "low_sample_threshold": None,
        },
        "hierarchy": hierarchy,
        "scopes": scopes,
        "warnings": warnings,
    }


def build_event_matchup_from_paths(
    event_path: Path,
    classification_path: Path,
    opportunity_path: Path,
    taxonomy_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Load validated per-event inputs and build one matchup document."""

    statistics = build_event_statistics_from_paths(
        event_path,
        classification_path,
        opportunity_path,
        taxonomy_path,
        repository_root,
    )
    overview = statistics["overview"]
    ledger, ledger_bytes = _read_json_object(opportunity_path)
    expected_hash = overview["input"]["opportunity_sha256"]
    if sha256(ledger_bytes).hexdigest() != expected_hash:
        raise MeleeMatchupError("opportunity ledger changed during generation")
    return build_event_matchup(overview, ledger)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate hierarchical matchup statistics for one Melee event."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", required=True, dest="format_id")
    parser.add_argument("--event-id", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="atomically write matchup.json; default mode is read-only",
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
    try:
        document = build_event_matchup_from_paths(
            event_path,
            classification_path,
            opportunity_path,
            taxonomy_path,
            root,
        )
        destination = (
            root
            / "stats"
            / args.format_id
            / "melee"
            / "events"
            / args.event_id
            / "matchup.json"
        )
        reused = None
        if args.execute:
            reused = write_statistics_document(
                destination,
                statistics_document_bytes(document),
            )
        print(
            json.dumps(
                {
                    "event_id": args.event_id,
                    "format": args.format_id,
                    "mode": "execute" if args.execute else "dry-run",
                    "output": (
                        destination.relative_to(root).as_posix()
                        if args.execute
                        else None
                    ),
                    "included_matches": {
                        scope_id: document["scopes"][scope_id][
                            "included_match_count"
                        ]
                        for scope_id in document["scope_order"]
                    },
                    "parents": len(document["hierarchy"]["parents"]),
                    "leaves": len(document["hierarchy"]["leaves"]),
                    "reused": reused,
                },
                sort_keys=True,
            )
        )
    except (MeleeMatchupError, MeleeStatisticsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
