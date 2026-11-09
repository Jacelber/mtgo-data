"""Reviewed zero-point absences never invent matches or terminal statuses."""

from copy import deepcopy
from pathlib import Path

import pytest

from mtgmeta.melee.config import (
    MeleeConfigError,
    load_melee_event_registry,
    parse_melee_event_text,
)
from mtgmeta.melee.opportunities import MeleeOpportunityError, build_opportunity_ledger
from mtgmeta.melee.parser import SourceArtifact, _real_matches
from validate_schemas import load_schemas, validate_instance

ROOT = Path(__file__).resolve().parents[1]
PID = "participant-" + "a" * 64
RID = "round-" + "b" * 64


def inputs():
    event = {
        "schema_version": "2.3.0",
        "metadata": {
            "source": "melee",
            "event_id": "999001",
            "constructed_format": "legacy",
        },
        "event_structure": "constructed_single_stage",
        "participants": [{"id": PID, "status": "active"}],
        "decklists": [{"participant_id": PID, "status": "missing"}],
        "rounds": [
            {
                "id": RID,
                "number": 1,
                "round_phase": "constructed",
                "game_format": "legacy",
                "swiss": True,
                "stage": "day1",
                "phase_id": "day1_legacy",
            },
            {
                "id": "round-" + "c" * 64,
                "number": 2,
                "round_phase": "constructed",
                "game_format": "legacy",
                "swiss": True,
                "stage": "day1",
                "phase_id": "day1_legacy",
            },
        ],
        "matches": [],
        "reviewed_unplayed_rounds": [
            {
                "id": "accepted_zero",
                "participant_id": PID,
                "round_id": r,
                "match_points": 0,
                "reason": "Reviewed zero points; cause unknown",
                "source_evidence": ["https://melee.gg/Tournament/View/999001"],
            }
            for r in [RID, "round-" + "c" * 64]
        ],
    }
    classification = {
        "schema_version": "1.0.0",
        "event_id": "999001",
        "format": "legacy",
        "input": {"event_sha256": "d" * 64},
        "quality": {"blocking": False},
        "records": [],
    }
    return event, classification


def build(event, classification):
    return build_opportunity_ledger(
        event,
        classification,
        event_path="data/legacy/melee/events/999001.json",
        event_sha256="d" * 64,
        classification_path="data/legacy/melee/classifications/999001.json",
        classification_sha256="e" * 64,
    )


def test_reviewed_zero_preserves_denominators_without_match_or_status_guess():
    event, classification = inputs()
    ledger = build(event, classification)
    assert ledger["participants"][0]["participant_status"] == "active"
    summary = ledger["scope_summaries"]["all_constructed"]
    assert (
        summary["constructed_points"],
        summary["theoretical_rounds"],
        summary["effective_theoretical_rounds"],
    ) == (0, 2, 2)
    assert summary["win_rate_match_count"] == summary["matchup_match_count"] == 0
    for item in ledger["opportunities"]:
        assert item["result_type"] == "reviewed_unplayed"
        assert item["match_id"] is None and item["opponent_participant_id"] is None
        assert item["points_included"] and not item["source_played"]
        assert not item["win_rate_included"] and not item["matchup_included"]
    schemas, registry = load_schemas(ROOT / "schemas")
    assert not validate_instance(
        ledger, schemas["melee-opportunity-ledger.schema.json"], registry
    )


@pytest.mark.parametrize(
    "change",
    [
        "unreviewed",
        "duplicate",
        "unknown_round",
        "unknown_participant",
        "positive_points",
        "existing_match",
    ],
)
def test_review_scope_cannot_suppress_missing_or_actual_source_results(change):
    event, classification = inputs()
    item = event["reviewed_unplayed_rounds"][0]
    if change == "unreviewed":
        event["reviewed_unplayed_rounds"] = []
    elif change == "duplicate":
        event["reviewed_unplayed_rounds"].append(deepcopy(item))
    elif change == "unknown_round":
        item["round_id"] = "round-" + "f" * 64
    elif change == "unknown_participant":
        item["participant_id"] = "participant-" + "f" * 64
    elif change == "positive_points":
        item["match_points"] = 3
    elif change == "existing_match":
        event["matches"] = [
            {
                "id": "match-" + "f" * 64,
                "round_id": RID,
                "competitors": [
                    {"participant_id": PID, "result_type": "bye", "match_points": 3}
                ],
            }
        ]
    with pytest.raises(MeleeOpportunityError):
        build(event, classification)


@pytest.mark.parametrize(
    "loss,bye,expected",
    [
        ("Forfeited", None, ("Administrative", 0)),
        (None, "Bye", ("Bye", 3)),
        (None, "Qualified", ("Qualified", 3)),
        ("Unrecognized", None, (None, None)),
        ("Forfeited", "Bye", (None, None)),
    ],
)
def test_single_competitor_loss_reason_never_becomes_a_bye(loss, bye, expected):
    artifact = SourceArtifact(
        "matches",
        "matches",
        1,
        "https://melee.gg/Match/GetRoundMatches/1",
        "response.json",
        "json",
        "a" * 64,
        1,
        source_round_id="1",
    )
    payload = {
        "data": [
            {
                "Guid": "source-match",
                "RoundId": 1,
                "HasResult": True,
                "ByeReasonDescription": bye,
                "LossReasonDescription": loss,
                "Competitors": [
                    {
                        "Team": {"Players": [{"ID": 10, "DisplayName": "Player"}]},
                        "GameWins": None,
                        "GameByes": None,
                    }
                ],
            }
        ]
    }
    result = _real_matches(payload, artifact).matches[0].competitor_results[0]
    assert (result.outcome_text, result.match_points) == expected


def test_event_decision_is_limited_to_two_verified_rounds_and_four_forfeits():
    registry = load_melee_event_registry(ROOT / "configs/melee_events.yaml")
    event = registry.get("491103")
    assert len(event.reviewed_unplayed_rounds) == 1
    assert event.reviewed_unplayed_rounds[0].rounds == (1, 2)
    assert len(event.reviewed_overrides) == 4
    assert all(
        not o.played
        and o.competitors[0].result_type == "administrative"
        and o.competitors[0].match_points == 0
        for o in event.reviewed_overrides
    )
    text = (
        (ROOT / "configs/melee_events.yaml")
        .read_text()
        .replace("rounds:\n      - 1\n      - 2", "rounds: [99]", 1)
    )
    with pytest.raises(MeleeConfigError):
        parse_melee_event_text(text)
