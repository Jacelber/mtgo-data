"""Executable target contract for Phase 9 pure Constructed strategies."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "pure_constructed_contract.json"
SCHEMA_NAME = "melee-pure-constructed-contract.schema.json"


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _assert_literal_record(record: dict[str, Any]) -> None:
    matches = record["wins"] + record["losses"] + record["draws"]
    assert record["matches"] == matches
    assert record["win_rate"] == round(record["wins"] / matches, 6)
    assert record["win_rate_method"] == "wins_over_valid_matches"
    proportion = record["wins"] / matches
    z = 1.96
    denominator = 1 + z**2 / matches
    center = (proportion + z**2 / (2 * matches)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / matches
            + z**2 / (4 * matches**2)
        )
        / denominator
    )
    assert record["confidence_interval_95"] == {
        "lower": round(max(0.0, center - margin), 6),
        "upper": round(min(1.0, center + margin), 6),
    }


def test_contract_schema_accepts_fixture_and_is_not_a_production_mapping() -> None:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(_fixture(), loaded[SCHEMA_NAME], registry) == []
    manifest = json.loads((ROOT / "schemas" / "manifest.json").read_text("utf-8"))
    assert SCHEMA_NAME not in {item["schema"] for item in manifest["mappings"]}


def test_contract_generalizes_only_the_p9_03_and_p9_04_schemas() -> None:
    generalized = (
        "melee-opportunity-ledger.schema.json",
        "melee-event-overview.schema.json",
        "melee-event-decks.schema.json",
    )
    for schema_name in generalized:
        schema = json.loads((ROOT / "schemas" / schema_name).read_text("utf-8"))
        assert schema["properties"]["event_structure"] == {
            "enum": ["mixed", "constructed_day2", "constructed_single_stage"]
        }

    for schema_name in (
        "melee-event-matchup.schema.json",
        "melee-event-quality.schema.json",
        "melee-event-meta.schema.json",
        "melee-event-catalog.schema.json",
    ):
        schema = json.loads((ROOT / "schemas" / schema_name).read_text("utf-8"))
        if schema_name == "melee-event-catalog.schema.json":
            event_structure = schema["$defs"]["event"]["properties"][
                "event_structure"
            ]
        else:
            event_structure = schema["properties"]["event_structure"]
        assert event_structure == {"const": "mixed"}


def test_structure_scope_sets_and_advancement_metrics_are_exact() -> None:
    structures = _fixture()["structures"]
    day2 = structures["constructed_day2"]
    assert day2["supported_scopes"] == ["day1", "day2", "all_constructed"]
    assert list(day2["expected_scopes"]) == day2["supported_scopes"]
    assert day2["advancement_metric"] == "day2_conversion"
    assert day2["mixed_selection_bias_warning"] is False

    single = structures["constructed_single_stage"]
    assert single["supported_scopes"] == ["all_constructed"]
    assert list(single["expected_scopes"]) == single["supported_scopes"]
    assert single["advancement_metric"] == "high_score_conversion"
    assert single["mixed_selection_bias_warning"] is False


def test_shared_result_handling_preserves_existing_eligibility_rules() -> None:
    policies = _fixture()["shared_result_handling"]
    for result_type in ("played_win", "played_loss", "played_draw"):
        assert policies[result_type]["win_rate_eligible"] is True
        assert policies[result_type]["matchup_eligible"] is True
    for result_type in (
        "intentional_draw",
        "bye",
        "drop_unplayed",
        "awarded_win_top8_lock",
        "disqualified_match",
        "playoff_result",
    ):
        assert policies[result_type]["win_rate_eligible"] is False
        assert policies[result_type]["matchup_eligible"] is False
    assert policies["played_draw"]["constructed_points"] == 1
    assert policies["intentional_draw"]["constructed_points"] == 1
    assert policies["bye"]["constructed_points"] == 3
    assert policies["drop_unplayed"]["effective_theoretical_round"] is True
    assert policies["awarded_win_top8_lock"]["effective_theoretical_round"] is False
    assert policies["disqualified_match"]["retained"] is True
    assert policies["disqualified_match"]["symmetric_match_exclusion"] is True


def test_day2_membership_and_theoretical_rounds_use_evidence() -> None:
    day2 = _fixture()["structures"]["constructed_day2"]
    participants = day2["participants"]
    scopes = day2["expected_scopes"]
    starters = [item["id"] for item in participants]
    qualifiers = [
        item["id"] for item in participants if item["day2_participation_evidence"]
    ]

    assert scopes["day1"]["participant_ids"] == starters
    assert scopes["day2"]["participant_ids"] == qualifiers
    assert scopes["all_constructed"]["participant_ids"] == starters
    assert scopes["day1"]["theoretical_rounds"] == sum(
        item["day1_scheduled_rounds"] for item in participants
    )
    assert scopes["day2"]["theoretical_rounds"] == sum(
        item["day2_scheduled_rounds"] for item in participants
    )
    assert scopes["day2"]["effective_theoretical_rounds"] == sum(
        item["day2_effective_rounds"] for item in participants
    )
    assert scopes["all_constructed"]["theoretical_rounds"] == (
        scopes["day1"]["theoretical_rounds"]
        + scopes["day2"]["theoretical_rounds"]
    )
    assert scopes["all_constructed"]["effective_theoretical_rounds"] == (
        scopes["day1"]["effective_theoretical_rounds"]
        + scopes["day2"]["effective_theoretical_rounds"]
    )
    assert set(starters) - set(qualifiers) == {"player-b", "player-d"}
    assert all(
        item["day2_scheduled_rounds"] == 0
        for item in participants
        if item["id"] not in qualifiers
    )


def test_single_stage_uses_deterministic_high_score_and_no_day2() -> None:
    single = _fixture()["structures"]["constructed_single_stage"]
    scope = single["expected_scopes"]["all_constructed"]
    participants = single["participants"]
    round_counts = {item["single_stage_scheduled_rounds"] for item in participants}
    assert round_counts == {5}
    rounds = round_counts.pop()
    threshold = 3 * (math.floor(rounds / 2) + 1)
    assert scope["high_score_threshold"] == threshold == 9
    assert scope["high_score_count"] == sum(
        item["single_stage_points"] >= threshold for item in participants
    )
    assert scope["theoretical_rounds"] == sum(
        item["single_stage_scheduled_rounds"] for item in participants
    )
    assert all(not item["day2_participation_evidence"] for item in participants)
    assert scope["day2_conversion_status"] == "unavailable"
    assert scope["day2_conversion_unavailable_reason"] == "no_day2_cut"


def test_parent_and_subtype_counts_conserve_for_both_structures() -> None:
    structures = _fixture()["structures"]
    for group in structures["constructed_day2"]["group_conservation"]:
        assert group["initial_deck_count"] == sum(
            group["subtype_initial_deck_counts"].values()
        )
        assert group["day2_deck_count"] == sum(
            group["subtype_day2_deck_counts"].values()
        )
    for group in structures["constructed_single_stage"]["group_conservation"]:
        assert group["initial_deck_count"] == sum(
            group["subtype_initial_deck_counts"].values()
        )
        assert group["high_score_deck_count"] == sum(
            group["subtype_high_score_deck_counts"].values()
        )


def test_all_fixture_match_records_use_literal_draw_handling() -> None:
    for structure in _fixture()["structures"].values():
        for scope in structure["expected_scopes"].values():
            _assert_literal_record(scope["match_record"])


def test_multi_event_selection_forces_only_common_scope() -> None:
    policy = _fixture()["multi_event_selection"]
    assert policy == {
        "minimum_event_count": 2,
        "same_source_required": True,
        "same_format_required": True,
        "forced_scope": "all_constructed",
        "on_second_event_selected": "switch_to_all_constructed",
        "stage_controls_during_multi_selection": "disabled_with_explanation",
        "absent_single_event_scopes": "omitted",
        "single_event_restore_policy": "last_supported_scope_or_default",
        "aggregation_method": "sum_raw_wld_then_recalculate",
        "overview_aggregation": "prohibited",
        "aggregation_example": policy["aggregation_example"],
    }
    assert all(
        policy["forced_scope"] in structure["supported_scopes"]
        for structure in _fixture()["structures"].values()
    )
    example = policy["aggregation_example"]
    combined = example["combined_record"]
    assert combined["wins"] == sum(item["wins"] for item in example["event_records"])
    assert combined["losses"] == sum(
        item["losses"] for item in example["event_records"]
    )
    assert combined["draws"] == sum(
        item["draws"] for item in example["event_records"]
    )
    _assert_literal_record(combined)
    event_rates = [
        item["wins"] / (item["wins"] + item["losses"] + item["draws"])
        for item in example["event_records"]
    ]
    assert combined["win_rate"] != round(sum(event_rates) / len(event_rates), 6)


def test_schema_rejects_cross_structure_scope_and_metric_leakage() -> None:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    fixture = _fixture()
    fixture["structures"]["constructed_single_stage"]["supported_scopes"] = [
        "day1",
        "all_constructed",
    ]
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)

    fixture = _fixture()
    fixture["structures"]["constructed_day2"]["advancement_metric"] = (
        "high_score_conversion"
    )
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)

    fixture = copy.deepcopy(_fixture())
    fixture["multi_event_selection"]["forced_scope"] = "day2"
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)
