"""P7-06 hierarchical per-event matchup contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import validate_schemas as schemas
from mtgmeta.melee.matchup import (
    MeleeMatchupError,
    build_event_matchup,
    build_event_matchup_from_paths,
)
from mtgmeta.melee.stats import statistics_document_bytes, write_statistics_document


EVENT_ID = "434455"
EVENT_PATH = ROOT / "data/modern/melee/events" / f"{EVENT_ID}.json"
CLASSIFICATION_PATH = (
    ROOT / "data/modern/melee/classifications" / f"{EVENT_ID}.json"
)
OPPORTUNITY_PATH = ROOT / "data/modern/melee/opportunities" / f"{EVENT_ID}.json"
TAXONOMY_PATH = ROOT / "my_archetypes/modern.yaml"
OVERVIEW_PATH = ROOT / "stats/modern/melee/events" / EVENT_ID / "overview.json"
MATCHUP_PATH = ROOT / "stats/modern/melee/events" / EVENT_ID / "matchup.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _record_counts(record: dict[str, object]) -> tuple[int, int, int, int]:
    return (
        record["wins"],
        record["losses"],
        record["draws"],
        record["matches"],
    )


def test_committed_matchup_is_byte_reproducible_and_schema_valid():
    rebuilt = build_event_matchup_from_paths(
        EVENT_PATH,
        CLASSIFICATION_PATH,
        OPPORTUNITY_PATH,
        TAXONOMY_PATH,
        ROOT,
    )
    assert statistics_document_bytes(rebuilt) == MATCHUP_PATH.read_bytes()

    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert (
        schemas.validate_instance(
            _load(MATCHUP_PATH),
            loaded["melee-event-matchup.schema.json"],
            registry,
            MATCHUP_PATH.relative_to(ROOT).as_posix(),
        )
        == []
    )


def test_scope_counts_rounds_and_exclusions_match_the_ledger():
    document = _load(MATCHUP_PATH)
    assert document["scope_order"] == ["day1", "day2", "all_constructed"]
    assert document["default_scope"] == "all_constructed"
    assert document["rate_method"]["low_sample_threshold"] is None

    expected = {
        "day1": {
            "round_numbers": [4, 5, 6, 7, 8],
            "source_match_count": 870,
            "included_match_count": 861,
            "excluded_match_count": 9,
            "directed_observation_count": 1722,
            "excluded_match_counts": {
                "bye": 4,
                "intentional_draw": 0,
                "no_show": 0,
                "awarded_win_top8_lock": 0,
                "administrative_result": 0,
                "disqualified_participant": 5,
                "unknown": 0,
            },
        },
        "day2": {
            "round_numbers": [12, 13, 14, 15, 16],
            "source_match_count": 546,
            "included_match_count": 533,
            "excluded_match_count": 13,
            "directed_observation_count": 1066,
            "excluded_match_counts": {
                "bye": 3,
                "intentional_draw": 2,
                "no_show": 0,
                "awarded_win_top8_lock": 7,
                "administrative_result": 0,
                "disqualified_participant": 1,
                "unknown": 0,
            },
        },
        "all_constructed": {
            "round_numbers": [4, 5, 6, 7, 8, 12, 13, 14, 15, 16],
            "source_match_count": 1416,
            "included_match_count": 1394,
            "excluded_match_count": 22,
            "directed_observation_count": 2788,
            "excluded_match_counts": {
                "bye": 7,
                "intentional_draw": 2,
                "no_show": 0,
                "awarded_win_top8_lock": 7,
                "administrative_result": 0,
                "disqualified_participant": 6,
                "unknown": 0,
            },
        },
    }
    for scope, values in expected.items():
        assert {
            key: document["scopes"][scope][key] for key in values
        } == values


def test_hierarchy_matches_the_overview_and_retains_empty_subtypes():
    document = _load(MATCHUP_PATH)
    overview = _load(OVERVIEW_PATH)
    parent_rows = overview["scopes"]["all_constructed"]["archetypes"]

    assert len(document["hierarchy"]["parents"]) == 32
    assert len(document["hierarchy"]["leaves"]) == 58
    assert document["scopes"]["all_constructed"]["parent_order"] == [
        "unknown" if row["group_id"] == "unknown" else row["archetype_id"]
        for row in parent_rows
    ]
    assert "unknown" in document["scopes"]["all_constructed"]["leaf_order"]
    assert all(
        len(scope["parent_order"]) == 32 and len(scope["leaf_order"]) == 58
        for scope in document["scopes"].values()
    )
    assert any(
        all(
            scope["leaf_overall"][leaf_id]["matches"] == 0
            for scope in document["scopes"].values()
        )
        for leaf_id in document["scopes"]["all_constructed"]["leaf_order"]
    )


@pytest.mark.parametrize("scope_id", ["day1", "day2", "all_constructed"])
def test_every_scope_is_full_inverse_and_count_conserving(scope_id):
    scope = _load(MATCHUP_PATH)["scopes"][scope_id]

    for level in ("parent", "leaf"):
        order = scope[f"{level}_order"]
        matrix = scope[f"{level}_matrix"]
        assert list(matrix) == order
        assert all(list(matrix[row_id]) == order for row_id in order)

        observations = 0
        for row_id in order:
            for column_id in order:
                cell = matrix[row_id][column_id]
                inverse = matrix[column_id][row_id]
                assert cell["wins"] == inverse["losses"]
                assert cell["losses"] == inverse["wins"]
                assert cell["draws"] == inverse["draws"]
                assert cell["matches"] == (
                    cell["wins"] + cell["losses"] + cell["draws"]
                )
                assert cell["mirror"] == (row_id == column_id)
                observations += cell["matches"]
        assert observations == scope["directed_observation_count"]


def test_leaf_counts_roll_up_independently_to_every_parent_cell():
    document = _load(MATCHUP_PATH)
    leaf_to_parent = {
        leaf["id"]: leaf["parent_id"] for leaf in document["hierarchy"]["leaves"]
    }

    for scope in document["scopes"].values():
        leaf_matrix = scope["leaf_matrix"]
        for row_parent in scope["parent_order"]:
            row_leaves = [
                leaf_id
                for leaf_id, parent_id in leaf_to_parent.items()
                if parent_id == row_parent
            ]
            for column_parent in scope["parent_order"]:
                column_leaves = [
                    leaf_id
                    for leaf_id, parent_id in leaf_to_parent.items()
                    if parent_id == column_parent
                ]
                expected = tuple(
                    sum(
                        leaf_matrix[row_leaf][column_leaf][field]
                        for row_leaf in row_leaves
                        for column_leaf in column_leaves
                    )
                    for field in ("wins", "losses", "draws", "matches")
                )
                assert (
                    _record_counts(scope["parent_matrix"][row_parent][column_parent])
                    == expected
                )


def test_all_constructed_is_the_cellwise_sum_of_day1_and_day2():
    scopes = _load(MATCHUP_PATH)["scopes"]

    for level in ("parent", "leaf"):
        matrix_key = f"{level}_matrix"
        order = scopes["all_constructed"][f"{level}_order"]
        for row_id in order:
            for column_id in order:
                for field in ("wins", "losses", "draws", "matches"):
                    assert scopes["all_constructed"][matrix_key][row_id][column_id][
                        field
                    ] == sum(
                        scopes[scope_id][matrix_key][row_id][column_id][field]
                        for scope_id in ("day1", "day2")
                    )


def test_parent_non_mirror_overall_matches_p7_05_exactly():
    document = _load(MATCHUP_PATH)
    overview = _load(OVERVIEW_PATH)

    for scope_id in document["scope_order"]:
        matchup_scope = document["scopes"][scope_id]
        overview_rows = overview["scopes"][scope_id]["archetypes"]
        for row in overview_rows:
            identity = (
                "unknown" if row["group_id"] == "unknown" else row["archetype_id"]
            )
            assert _record_counts(matchup_scope["parent_overall"][identity]) == (
                _record_counts(row["match_record"]["non_mirror"])
            )
            assert matchup_scope["parent_overall"][identity]["win_rate"] == row[
                "match_record"
            ]["non_mirror"]["win_rate"]
            assert matchup_scope["parent_overall"][identity][
                "confidence_interval_95"
            ] == row["match_record"]["non_mirror"]["confidence_interval_95"]


def test_sibling_subtypes_are_leaf_opponents_but_parent_mirrors():
    document = _load(MATCHUP_PATH)
    scope = document["scopes"]["all_constructed"]
    hierarchy = document["hierarchy"]

    sibling_observations = {}
    for parent in hierarchy["parents"]:
        subtype_ids = parent["subtype_ids"]
        count = sum(
            scope["leaf_matrix"][row_id][column_id]["matches"]
            for row_id in subtype_ids
            for column_id in subtype_ids
            if row_id != column_id
        )
        if count:
            sibling_observations[parent["id"]] = count

    assert sibling_observations
    for parent_id, count in sibling_observations.items():
        assert scope["parent_matrix"][parent_id][parent_id]["matches"] >= count
        assert sum(
            scope["leaf_overall"][leaf_id]["matches"]
            for leaf_id in next(
                parent["subtype_ids"]
                for parent in hierarchy["parents"]
                if parent["id"] == parent_id
            )
        ) >= count


def test_one_sided_matchup_inclusion_fails_closed():
    overview = _load(OVERVIEW_PATH)
    ledger = _load(OPPORTUNITY_PATH)
    included = next(
        item for item in ledger["opportunities"] if item["matchup_included"]
    )
    partner = next(
        item
        for item in ledger["opportunities"]
        if item["match_id"] == included["match_id"]
        and item["participant_id"] != included["participant_id"]
    )
    partner["matchup_included"] = False

    with pytest.raises(MeleeMatchupError, match="included on both sides"):
        build_event_matchup(overview, ledger)


def test_bytes_and_atomic_writer_are_deterministic(tmp_path):
    document = _load(MATCHUP_PATH)
    first = statistics_document_bytes(document)
    second = statistics_document_bytes(deepcopy(document))
    destination = tmp_path / "matchup.json"

    assert first == second
    assert write_statistics_document(destination, first) is False
    assert write_statistics_document(destination, second) is True
    assert destination.read_bytes() == first
