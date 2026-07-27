"""Executable contract tests for the P8-04 target public payload fragments."""

from __future__ import annotations

import copy
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase8_public_contract.json"
SCHEMA_NAME = "phase8-public-contract.schema.json"


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _assert_literal_record(record: dict[str, Any]) -> None:
    matches = record["wins"] + record["losses"] + record["draws"]
    assert record["matches"] == matches
    expected = None if matches == 0 else round(record["wins"] / matches, 6)
    assert record["win_rate"] == expected
    assert record["win_rate_method"] == "wins_over_valid_matches"
    if matches == 0:
        assert record["confidence_interval_95"] is None
        return
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


def test_target_contract_schema_accepts_fixture_and_is_not_production_mapped() -> None:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(_fixture(), loaded[SCHEMA_NAME], registry) == []
    manifest = json.loads((ROOT / "schemas" / "manifest.json").read_text(encoding="utf-8"))
    assert SCHEMA_NAME not in {item["schema"] for item in manifest["mappings"]}


def test_target_contract_rejects_legacy_rate_method_and_unreviewed_fields() -> None:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    fixture = _fixture()
    fixture["literal_match_record"]["win_rate_method"] = "draws_as_half_win"
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)
    fixture = _fixture()
    fixture["literal_match_record"]["browser_derived"] = True
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)


def test_literal_records_use_wins_over_all_valid_matches_and_literal_wilson() -> None:
    fixture = _fixture()
    _assert_literal_record(fixture["literal_match_record"])
    for scope in fixture["tabletop_event"]["scope_summaries"]:
        _assert_literal_record(scope["match_record"]["all_matches"])
        _assert_literal_record(scope["match_record"]["non_mirror"])


def test_videre_coverage_reconciles_expected_buckets_and_excludes_outside_events() -> None:
    coverage = _fixture()["matchup_coverage"]
    assert coverage["expected_event_count"] == (
        coverage["available_event_count"]
        + coverage["deferred_event_count"]
        + coverage["missing_event_count"]
    )
    assert coverage["available_event_count"] == len(coverage["available_event_ids"])
    assert coverage["deferred_event_count"] == len(coverage["deferred_event_ids"])
    assert coverage["missing_event_count"] == len(coverage["missing_event_ids"])
    assert coverage["excluded_event_count"] == len(coverage["excluded_events"])
    assert coverage["completeness_rate"] == round(
        coverage["available_event_count"] / coverage["expected_event_count"],
        6,
    )


def test_high_score_expectation_sums_unrounded_event_models_before_display_rounding() -> None:
    completeness = _fixture()["high_score_decklist_completeness"]
    expected_total = 0.0
    observed_total = 0
    for event in completeness["events"]:
        probability = sum(
            math.comb(event["round_count"], wins)
            / 2 ** event["round_count"]
            for wins in range(
                event["minimum_decisive_wins"],
                event["round_count"] + 1,
            )
        )
        expected = event["player_count"] * probability
        assert 3 * event["minimum_decisive_wins"] >= event["high_score_threshold"]
        assert (
            3 * (event["minimum_decisive_wins"] - 1)
            < event["high_score_threshold"]
        )
        assert event["expected_decklist_count"] == expected
        expected_total += expected
        observed_total += event["observed_decklist_count"]
    assert completeness["eligible_event_count"] == len(completeness["events"])
    assert completeness["unsupported_event_count"] == len(
        completeness["unsupported_events"]
    )
    assert completeness["expected_decklist_count"] == expected_total
    assert completeness["expected_decklist_count_display"] == math.floor(
        expected_total + 0.5
    )
    assert completeness["observed_decklist_count"] == observed_total == 97
    assert completeness["completeness_rate"] == round(
        min(1.0, observed_total / expected_total),
        6,
    )
    assert completeness["exceeds_model"] is (observed_total > expected_total)
    incomplete = completeness["unsupported_events"][0]
    assert incomplete["event_id"] == "12847150"
    assert incomplete["reason"] == "missing_swiss_scores"
    assert "official event page contains the missing data" in incomplete["note"]


def test_top8_contract_has_exact_ranks_and_fail_closed_missing_decks() -> None:
    week = _fixture()["top8_week"]
    start = date.fromisoformat(week["week"]["start"])
    end = date.fromisoformat(week["week"]["end"])
    assert start.weekday() == 0
    assert (end - start).days == 6
    event = week["events"][0]
    assert [item["rank"] for item in event["placements"]] == list(range(1, 9))
    for placement in event["placements"]:
        if placement["deck_status"] == "available":
            assert placement["identity"]
            assert placement["exact_deck"]
            assert placement["comparison"]
        else:
            assert placement["identity"] is None
            assert placement["exact_deck"] is None
            assert placement["comparison"] is None


def test_top8_schema_rejects_data_attached_to_a_missing_placement() -> None:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    fixture = _fixture()
    fixture["top8_week"]["events"][0]["placements"][1]["identity"] = copy.deepcopy(
        fixture["top8_week"]["events"][0]["placements"][0]["identity"]
    )
    assert schemas.validate_instance(fixture, loaded[SCHEMA_NAME], registry)


def test_tabletop_contract_exposes_direct_overall_scopes_and_compatibility() -> None:
    event = _fixture()["tabletop_event"]
    scopes = [item["scope"] for item in event["scope_summaries"]]
    assert scopes == event["supported_scopes"]
    assert event["default_scope"] in scopes
    combined = event["scope_summaries"][-1]
    assert combined["scope"] == "all_constructed"
    assert combined["high_score_status"] == "unavailable"
    assert combined["high_score_deck_count"] is None
    compatibility = event["matchup_compatibility"]
    assert compatibility["format"] == event["format"]
    assert compatibility["supported_scopes"] == event["supported_scopes"]
