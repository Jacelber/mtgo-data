from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from mtgmeta.melee.multi_event_matchup import (
    ERROR_CODES,
    MultiEventMatchupError,
    aggregate_multi_event_matchups,
)


CANONICAL_HIERARCHY = {
    "parents": [
        {
            "id": "alpha",
            "name": "Alpha",
            "expandable": False,
            "subtype_ids": [],
        },
        {
            "id": "beta",
            "name": "Beta",
            "expandable": True,
            "subtype_ids": ["beta/one", "beta/two"],
        },
        {
            "id": "unknown",
            "name": "Unknown",
            "expandable": False,
            "subtype_ids": [],
        },
    ],
    "leaves": [
        {
            "id": "alpha",
            "kind": "archetype",
            "name": "Alpha",
            "display_name": "Alpha",
            "parent_id": "alpha",
            "subtype_id": None,
        },
        {
            "id": "beta/one",
            "kind": "subtype",
            "name": "One",
            "display_name": "One Beta",
            "parent_id": "beta",
            "subtype_id": "one",
        },
        {
            "id": "beta/two",
            "kind": "subtype",
            "name": "Two",
            "display_name": "Two Beta",
            "parent_id": "beta",
            "subtype_id": "two",
        },
        {
            "id": "unknown",
            "kind": "unknown",
            "name": "Unknown",
            "display_name": "Unknown",
            "parent_id": "unknown",
            "subtype_id": None,
        },
    ],
}


def _counts(wins: int = 0, losses: int = 0, draws: int = 0) -> dict[str, int]:
    return {"wins": wins, "losses": losses, "draws": draws}


def _matrix(leaf_ids: list[str]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        row_id: {column_id: _counts() for column_id in leaf_ids}
        for row_id in leaf_ids
    }


def _event_input(
    event_id: str,
    leaf_ids: list[str],
    directed_cells: dict[tuple[str, str], tuple[int, int, int]],
) -> dict[str, Any]:
    canonical_parents = {
        item["id"]: item for item in CANONICAL_HIERARCHY["parents"]
    }
    canonical_leaves = {
        item["id"]: item for item in CANONICAL_HIERARCHY["leaves"]
    }
    parent_ids = [
        parent["id"]
        for parent in CANONICAL_HIERARCHY["parents"]
        if any(canonical_leaves[leaf_id]["parent_id"] == parent["id"] for leaf_id in leaf_ids)
    ]
    parents = []
    for parent_id in parent_ids:
        parent = deepcopy(canonical_parents[parent_id])
        parent["subtype_ids"] = [
            leaf_id
            for leaf_id in leaf_ids
            if canonical_leaves[leaf_id]["parent_id"] == parent_id
            and canonical_leaves[leaf_id]["kind"] == "subtype"
        ]
        parents.append(parent)
    leaves = [deepcopy(canonical_leaves[leaf_id]) for leaf_id in leaf_ids]
    matrix = _matrix(leaf_ids)
    for (row_id, column_id), (wins, losses, draws) in directed_cells.items():
        matrix[row_id][column_id] = _counts(wins, losses, draws)

    directed_observations = sum(
        sum(cell.values()) for columns in matrix.values() for cell in columns.values()
    )
    assert directed_observations % 2 == 0
    included_matches = directed_observations // 2
    meta = {
        "schema_version": "1.0.0",
        "document_type": "meta",
        "source": "melee",
        "product": "tabletop-major-events",
        "event_id": event_id,
        "format": "modern",
        "event": {"name": f"Synthetic {event_id}"},
        "input": {
            "taxonomy_schema_version": "1.1.0",
            "taxonomy_sha256": "a" * 64,
        },
        "scope_order": ["all_constructed"],
        "quality": {"status": "pass", "blocking": False},
    }
    matchup = {
        "schema_version": "1.0.0",
        "document_type": "matchup",
        "source": "melee",
        "event_id": event_id,
        "format": "modern",
        "input": deepcopy(meta["input"]),
        "event": deepcopy(meta["event"]),
        "scope_order": ["all_constructed"],
        "hierarchy": {"parents": parents, "leaves": leaves},
        "scopes": {
            "all_constructed": {
                "source_match_count": included_matches,
                "included_match_count": included_matches,
                "excluded_match_count": 0,
                "directed_observation_count": directed_observations,
                "excluded_match_counts": {
                    "bye": 0,
                    "intentional_draw": 0,
                    "no_show": 0,
                    "awarded_win_top8_lock": 0,
                    "administrative_result": 0,
                    "disqualified_participant": 0,
                    "unknown": 0,
                },
                "parent_order": parent_ids,
                "leaf_order": leaf_ids,
                "leaf_matrix": matrix,
            }
        },
    }
    return {"meta": meta, "matchup": matchup}


def _compatible_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    event_20 = _event_input(
        "20",
        ["alpha", "beta/one", "unknown"],
        {
            ("alpha", "alpha"): (1, 1, 0),
            ("alpha", "beta/one"): (8, 2, 2),
            ("beta/one", "alpha"): (2, 8, 2),
            ("alpha", "unknown"): (3, 1, 0),
            ("unknown", "alpha"): (1, 3, 0),
        },
    )
    event_10 = _event_input(
        "10",
        ["alpha", "beta/two"],
        {
            ("alpha", "beta/two"): (1, 9, 0),
            ("beta/two", "alpha"): (9, 1, 0),
            ("beta/two", "beta/two"): (0, 0, 2),
        },
    )
    return event_20, event_10


def _use_event_presentation_order(
    event_input: dict[str, Any],
    *,
    parent_order: list[str],
    leaf_order: list[str],
) -> None:
    hierarchy = event_input["matchup"]["hierarchy"]
    parent_by_id = {item["id"]: item for item in hierarchy["parents"]}
    leaf_by_id = {item["id"]: item for item in hierarchy["leaves"]}
    hierarchy["parents"] = [parent_by_id[identity_id] for identity_id in parent_order]
    hierarchy["leaves"] = [leaf_by_id[identity_id] for identity_id in leaf_order]
    scope = event_input["matchup"]["scopes"]["all_constructed"]
    scope["parent_order"] = parent_order
    scope["leaf_order"] = leaf_order


def _error_code(
    inputs: list[dict[str, Any]],
    hierarchy: dict[str, Any] | None = None,
) -> str:
    with pytest.raises(MultiEventMatchupError) as caught:
        aggregate_multi_event_matchups(
            inputs,
            canonical_hierarchy=hierarchy or CANONICAL_HIERARCHY,
        )
    return caught.value.code


def test_aggregates_raw_counts_with_identity_union_and_reconciliation() -> None:
    event_20, event_10 = _compatible_inputs()
    _use_event_presentation_order(
        event_20,
        parent_order=["unknown", "alpha", "beta"],
        leaf_order=["unknown", "alpha", "beta/one"],
    )

    result = aggregate_multi_event_matchups(
        [event_20, event_10, deepcopy(event_20)],
        canonical_hierarchy=CANONICAL_HIERARCHY,
    )

    assert result["event_ids"] == ["10", "20"]
    assert result["event_names"] == ["Synthetic 10", "Synthetic 20"]
    assert result["leaf_order"] == ["alpha", "beta/one", "beta/two", "unknown"]
    assert result["parent_order"] == ["alpha", "beta", "unknown"]
    assert result["included_match_count"] == 28
    assert result["directed_observation_count"] == 56

    alpha_beta = result["parent_matrix"]["alpha"]["beta"]
    assert alpha_beta["wins"] == 9
    assert alpha_beta["losses"] == 11
    assert alpha_beta["draws"] == 2
    assert alpha_beta["matches"] == 22
    assert alpha_beta["win_rate"] == round(9 / 22, 6)
    assert alpha_beta["win_rate"] != round(((8 / 12) + (1 / 10)) / 2, 6)
    assert alpha_beta["confidence_interval_95"] == {
        "lower": 0.232556,
        "upper": 0.612655,
    }
    assert alpha_beta["low_sample"] is False
    assert alpha_beta["contributing_event_ids"] == ["10", "20"]

    inverse = result["parent_matrix"]["beta"]["alpha"]
    assert (inverse["wins"], inverse["losses"], inverse["draws"]) == (11, 9, 2)
    assert result["parent_matrix"]["alpha"]["alpha"]["mirror"] is True
    assert result["parent_overall"]["alpha"] == {
        "wins": 12,
        "losses": 12,
        "draws": 2,
        "matches": 26,
        "win_rate": round(12 / 26, 6),
        "win_rate_method": "wins_over_valid_matches",
        "confidence_interval_95": {"lower": 0.287556, "upper": 0.645424},
        "mirror": False,
        "low_sample": False,
        "contributing_event_ids": ["10", "20"],
    }
    assert result["leaf_matrix"]["unknown"]["alpha"]["matches"] == 4
    assert result["leaf_matrix"]["unknown"]["alpha"]["low_sample"] is True
    assert result["leaf_matrix"]["unknown"]["alpha"][
        "contributing_event_ids"
    ] == ["20"]
    assert result["parent_matrix"]["beta"]["beta"]["draws"] == 2

    parent_observations = sum(
        cell["matches"]
        for columns in result["parent_matrix"].values()
        for cell in columns.values()
    )
    assert parent_observations == result["directed_observation_count"]
    assert result["excluded_match_count"] == sum(
        result["excluded_match_counts"].values()
    )


def test_duplicate_only_selection_is_rejected_after_deduplication() -> None:
    event_20, _ = _compatible_inputs()

    assert _error_code([event_20, deepcopy(event_20)]) == "too_few_events"


def test_error_vocabulary_is_explicit_and_stable() -> None:
    assert ERROR_CODES == {
        "blocking_quality",
        "duplicate_event_conflict",
        "event_identity_mismatch",
        "format_mismatch",
        "identity_metadata_mismatch",
        "invalid_event_input",
        "matrix_invariant_failed",
        "missing_all_constructed_scope",
        "product_mismatch",
        "source_mismatch",
        "taxonomy_digest_mismatch",
        "taxonomy_version_mismatch",
        "too_few_events",
        "unsupported_matchup_schema",
    }


def test_low_sample_warning_changes_at_twenty_matches() -> None:
    event_20 = _event_input(
        "20",
        ["alpha", "beta/one"],
        {
            ("alpha", "beta/one"): (10, 0, 0),
            ("beta/one", "alpha"): (0, 10, 0),
        },
    )
    event_10 = _event_input(
        "10",
        ["alpha", "beta/one"],
        {
            ("alpha", "beta/one"): (9, 0, 0),
            ("beta/one", "alpha"): (0, 9, 0),
        },
    )
    result_19 = aggregate_multi_event_matchups(
        [event_20, event_10],
        canonical_hierarchy=CANONICAL_HIERARCHY,
    )
    assert result_19["leaf_matrix"]["alpha"]["beta/one"]["low_sample"] is True

    event_10["matchup"]["scopes"]["all_constructed"]["leaf_matrix"]["alpha"][
        "beta/one"
    ]["wins"] = 10
    event_10["matchup"]["scopes"]["all_constructed"]["leaf_matrix"]["beta/one"][
        "alpha"
    ]["losses"] = 10
    scope = event_10["matchup"]["scopes"]["all_constructed"]
    scope["included_match_count"] = 10
    scope["source_match_count"] = 10
    scope["directed_observation_count"] = 20
    result_20 = aggregate_multi_event_matchups(
        [event_20, event_10],
        canonical_hierarchy=CANONICAL_HIERARCHY,
    )
    assert result_20["leaf_matrix"]["alpha"]["beta/one"]["low_sample"] is False


def test_conflicting_duplicate_event_is_rejected() -> None:
    event_20, event_10 = _compatible_inputs()
    conflicting = deepcopy(event_20)
    conflicting["meta"]["event"]["name"] = "Different"

    assert (
        _error_code([event_20, conflicting, event_10])
        == "duplicate_event_conflict"
    )


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda item: item["matchup"].__setitem__("source", "mtgo"),
            "source_mismatch",
        ),
        (
            lambda item: item["meta"].__setitem__("product", "other"),
            "product_mismatch",
        ),
        (
            lambda item: (
                item["meta"].__setitem__("format", "standard"),
                item["matchup"].__setitem__("format", "standard"),
            ),
            "format_mismatch",
        ),
    ],
)
def test_source_product_and_format_fail_closed(mutate: Any, expected: str) -> None:
    event_20, event_10 = _compatible_inputs()
    mutate(event_10)

    assert _error_code([event_20, event_10]) == expected


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("taxonomy_schema_version", "2.0.0", "taxonomy_version_mismatch"),
        ("taxonomy_sha256", "b" * 64, "taxonomy_digest_mismatch"),
    ],
)
def test_taxonomy_compatibility_fails_closed(
    field: str,
    value: str,
    expected: str,
) -> None:
    event_20, event_10 = _compatible_inputs()
    event_10["meta"]["input"][field] = value
    event_10["matchup"]["input"][field] = value

    assert _error_code([event_20, event_10]) == expected


def test_identity_metadata_mismatch_fails_closed() -> None:
    event_20, event_10 = _compatible_inputs()
    event_10["matchup"]["hierarchy"]["leaves"][1]["display_name"] = "Changed"

    assert _error_code([event_20, event_10]) == "identity_metadata_mismatch"


def test_unsupported_matchup_schema_fails_closed() -> None:
    event_20, event_10 = _compatible_inputs()
    event_10["matchup"]["schema_version"] = "2.0.0"

    assert _error_code([event_20, event_10]) == "unsupported_matchup_schema"


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda item: item["meta"]["quality"].__setitem__("blocking", True),
            "blocking_quality",
        ),
        (
            lambda item: (
                item["meta"].__setitem__("scope_order", ["day1"]),
                item["matchup"].__setitem__("scope_order", ["day1"]),
                item["matchup"]["scopes"].pop("all_constructed"),
            ),
            "missing_all_constructed_scope",
        ),
    ],
)
def test_quality_and_scope_fail_closed(mutate: Any, expected: str) -> None:
    event_20, event_10 = _compatible_inputs()
    mutate(event_10)

    assert _error_code([event_20, event_10]) == expected


def test_inverse_and_match_conservation_fail_closed() -> None:
    event_20, event_10 = _compatible_inputs()
    event_10["matchup"]["scopes"]["all_constructed"]["leaf_matrix"]["alpha"][
        "beta/two"
    ]["wins"] += 1

    assert _error_code([event_20, event_10]) == "matrix_invariant_failed"
