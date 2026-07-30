"""P7-04 mixed-event Constructed-opportunity ledger contracts."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import validate_schemas as schemas
from mtgmeta.melee.opportunities import (
    MeleeOpportunityError,
    build_opportunity_ledger,
    build_opportunity_ledger_from_paths,
    opportunity_ledger_bytes,
    write_opportunity_ledger,
)


EVENT_ID = "434455"
EVENT_PATH = ROOT / "data/modern/melee/events" / f"{EVENT_ID}.json"
CLASSIFICATION_PATH = (
    ROOT / "data/modern/melee/classifications" / f"{EVENT_ID}.json"
)
LEDGER_PATH = ROOT / "data/modern/melee/opportunities" / f"{EVENT_ID}.json"
PURE_CONTRACT_PATH = ROOT / "tests/fixtures/melee/pure_constructed_contract.json"


def _participant(number: int, status: str) -> dict[str, object]:
    return {"id": f"participant-{'%064x' % number}", "status": status}


def _round(
    number: int,
    *,
    stage: str,
    round_phase: str,
    game_format: str,
    swiss: bool = True,
) -> dict[str, object]:
    return {
        "id": f"round-{'%064x' % number}",
        "number": number,
        "phase_id": f"{stage}_{round_phase}",
        "round_phase": round_phase,
        "game_format": game_format,
        "stage": stage,
        "swiss": swiss,
    }


def _match(
    number: int,
    round_: dict[str, object],
    competitors: list[tuple[str, str, int]],
    *,
    played: bool,
    eligible: bool,
) -> dict[str, object]:
    return {
        "id": f"match-{'%064x' % number}",
        "round_id": round_["id"],
        "played": played,
        "constructed_statistics_eligible": eligible,
        "matchup_eligible": eligible,
        "competitors": [
            {
                "participant_id": participant_id,
                "result_type": result_type,
                "match_points": match_points,
            }
            for participant_id, result_type, match_points in competitors
        ],
    }


def _fixture_inputs() -> tuple[dict[str, object], dict[str, object]]:
    active = _participant(1, "active")
    dropped = _participant(2, "dropped")
    disqualified = _participant(3, "disqualified")
    nonqualifier = _participant(4, "active")
    day1_draft = _round(
        1, stage="day1", round_phase="draft", game_format="limited"
    )
    day1_round4 = _round(
        4, stage="day1", round_phase="constructed", game_format="modern"
    )
    day1_round5 = _round(
        5, stage="day1", round_phase="constructed", game_format="modern"
    )
    day2_draft = _round(
        9, stage="day2", round_phase="draft", game_format="limited"
    )
    day2_round12 = _round(
        12, stage="day2", round_phase="constructed", game_format="modern"
    )
    day2_round13 = _round(
        13, stage="day2", round_phase="constructed", game_format="modern"
    )
    playoff = _round(
        17,
        stage="playoff",
        round_phase="playoff",
        game_format="limited",
        swiss=False,
    )
    event = {
        "schema_version": "2.2.0",
        "metadata": {
            "source": "melee",
            "event_id": "123",
            "constructed_format": "modern",
        },
        "event_structure": "mixed",
        "participants": [active, dropped, disqualified, nonqualifier],
        "rounds": [
            day1_draft,
            day1_round4,
            day1_round5,
            day2_draft,
            day2_round12,
            day2_round13,
            playoff,
        ],
        "matches": [
            _match(
                1,
                day1_draft,
                [
                    (active["id"], "played_win", 3),
                    (dropped["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                2,
                day1_round4,
                [
                    (active["id"], "played_win", 3),
                    (dropped["id"], "played_loss", 0),
                ],
                played=True,
                eligible=True,
            ),
            _match(
                3,
                day1_round4,
                [
                    (disqualified["id"], "played_win", 3),
                    (nonqualifier["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                4,
                day1_round5,
                [(active["id"], "bye", 3)],
                played=False,
                eligible=False,
            ),
            _match(
                5,
                day1_round5,
                [
                    (disqualified["id"], "intentional_draw", 1),
                    (nonqualifier["id"], "intentional_draw", 1),
                ],
                played=False,
                eligible=False,
            ),
            _match(
                6,
                day2_draft,
                [
                    (active["id"], "played_win", 3),
                    (disqualified["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                7,
                day2_round12,
                [
                    (active["id"], "played_win", 3),
                    (disqualified["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                8,
                day2_round13,
                [(active["id"], "awarded_win_top8_lock", 3)],
                played=False,
                eligible=False,
            ),
            _match(
                9,
                playoff,
                [
                    (active["id"], "played_win", 3),
                    (disqualified["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
        ],
    }
    event_hash = sha256(json.dumps(event).encode()).hexdigest()
    records = []
    for index, participant in enumerate(event["participants"]):
        records.append(
            {
                "participant_id": participant["id"],
                "classification_status": "classified" if index < 3 else "unknown",
                "selected": (
                    {
                        "archetype_id": "example",
                        "archetype_name": "Example",
                        "subtype_id": "alpha",
                        "subtype_name": "Alpha",
                    }
                    if index < 3
                    else None
                ),
            }
        )
    classification = {
        "schema_version": "1.0.0",
        "event_id": "123",
        "format": "modern",
        "input": {"event_sha256": event_hash},
        "quality": {"blocking": False},
        "records": records,
    }
    return event, classification


def _fixture_ledger() -> dict[str, object]:
    event, classification = _fixture_inputs()
    return build_opportunity_ledger(
        event,
        classification,
        event_path="data/modern/melee/events/123.json",
        event_sha256=classification["input"]["event_sha256"],
        classification_path="data/modern/melee/classifications/123.json",
        classification_sha256="b" * 64,
    )


def _classification_for_event(
    event: dict[str, object],
) -> dict[str, object]:
    event_hash = sha256(json.dumps(event).encode()).hexdigest()
    return {
        "schema_version": "1.0.0",
        "event_id": event["metadata"]["event_id"],
        "format": event["metadata"]["constructed_format"],
        "input": {"event_sha256": event_hash},
        "quality": {"blocking": False},
        "records": [
            {
                "participant_id": participant["id"],
                "classification_status": "classified",
                "selected": {
                    "archetype_id": "example",
                    "archetype_name": "Example",
                    "subtype_id": "alpha",
                    "subtype_name": "Alpha",
                },
            }
            for participant in event["participants"]
        ],
    }


def _pure_day2_inputs() -> tuple[dict[str, object], dict[str, object]]:
    active = _participant(11, "active")
    nonqualifier = _participant(12, "dropped")
    qualified_drop = _participant(13, "dropped")
    disqualified = _participant(14, "disqualified")
    day1_rounds = [
        _round(
            number,
            stage="day1",
            round_phase="constructed",
            game_format="modern",
        )
        for number in range(1, 4)
    ]
    day2_rounds = [
        _round(
            number,
            stage="day2",
            round_phase="constructed",
            game_format="modern",
        )
        for number in range(4, 6)
    ]
    event = {
        "schema_version": "2.2.0",
        "metadata": {
            "source": "melee",
            "event_id": "124",
            "constructed_format": "modern",
        },
        "event_structure": "constructed_day2",
        "participants": [
            active,
            nonqualifier,
            qualified_drop,
            disqualified,
        ],
        "rounds": [*day1_rounds, *day2_rounds],
        "matches": [
            _match(
                21,
                day1_rounds[0],
                [
                    (active["id"], "played_win", 3),
                    (nonqualifier["id"], "played_loss", 0),
                ],
                played=True,
                eligible=True,
            ),
            _match(
                22,
                day1_rounds[0],
                [
                    (qualified_drop["id"], "played_win", 3),
                    (disqualified["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                23,
                day1_rounds[1],
                [
                    (active["id"], "played_draw", 1),
                    (qualified_drop["id"], "played_draw", 1),
                ],
                played=True,
                eligible=True,
            ),
            _match(
                24,
                day1_rounds[1],
                [
                    (nonqualifier["id"], "played_win", 3),
                    (disqualified["id"], "played_loss", 0),
                ],
                played=True,
                eligible=False,
            ),
            _match(
                25,
                day1_rounds[2],
                [(active["id"], "bye", 3)],
                played=False,
                eligible=False,
            ),
            _match(
                26,
                day1_rounds[2],
                [
                    (nonqualifier["id"], "intentional_draw", 1),
                    (qualified_drop["id"], "intentional_draw", 1),
                ],
                played=False,
                eligible=False,
            ),
            _match(
                27,
                day2_rounds[0],
                [
                    (active["id"], "played_win", 3),
                    (qualified_drop["id"], "played_loss", 0),
                ],
                played=True,
                eligible=True,
            ),
            _match(
                28,
                day2_rounds[1],
                [(active["id"], "awarded_win_top8_lock", 3)],
                played=False,
                eligible=False,
            ),
        ],
    }
    return event, _classification_for_event(event)


def _single_stage_inputs() -> tuple[dict[str, object], dict[str, object]]:
    participants = [_participant(number, "active") for number in range(21, 25)]
    rounds = [
        _round(
            number,
            stage="other",
            round_phase="constructed",
            game_format="modern",
        )
        for number in range(1, 6)
    ]
    pairings = [
        ((0, 3), (1, 2)),
        ((0, 3), (1, 2)),
        ((0, 2), (1, 3)),
        ((0, 1), (2, 3)),
        ((2, 0), (3, 1)),
    ]
    matches = []
    match_number = 31
    for round_, round_pairings in zip(rounds, pairings, strict=True):
        for winner_index, loser_index in round_pairings:
            matches.append(
                _match(
                    match_number,
                    round_,
                    [
                        (participants[winner_index]["id"], "played_win", 3),
                        (participants[loser_index]["id"], "played_loss", 0),
                    ],
                    played=True,
                    eligible=True,
                )
            )
            match_number += 1
    event = {
        "schema_version": "2.2.0",
        "metadata": {
            "source": "melee",
            "event_id": "125",
            "constructed_format": "modern",
        },
        "event_structure": "constructed_single_stage",
        "participants": participants,
        "rounds": rounds,
        "matches": matches,
    }
    return event, _classification_for_event(event)


def _build_fixture_ledger(
    event: dict[str, object],
    classification: dict[str, object],
) -> dict[str, object]:
    event_id = event["metadata"]["event_id"]
    return build_opportunity_ledger(
        event,
        classification,
        event_path=f"data/modern/melee/events/{event_id}.json",
        event_sha256=classification["input"]["event_sha256"],
        classification_path=f"data/modern/melee/classifications/{event_id}.json",
        classification_sha256="b" * 64,
    )


def test_constructed_day2_dispatch_uses_evidenced_qualified_population():
    event, classification = _pure_day2_inputs()
    ledger = _build_fixture_ledger(event, classification)
    contract = json.loads(PURE_CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["structures"]["constructed_day2"]["expected_scopes"]
    loaded, registry = schemas.load_schemas(ROOT / "schemas")

    assert ledger["event_structure"] == "constructed_day2"
    assert list(ledger["scope_summaries"]) == [
        "day1",
        "day2",
        "all_constructed",
    ]
    for scope_id in ("day1", "day2", "all_constructed"):
        assert ledger["scope_summaries"][scope_id]["theoretical_rounds"] == (
            expected[scope_id]["theoretical_rounds"]
        )
        assert ledger["scope_summaries"][scope_id][
            "effective_theoretical_rounds"
        ] == expected[scope_id]["effective_theoretical_rounds"]
    participants = {item["participant_id"]: item for item in ledger["participants"]}
    assert sum(item["day2_participant"] for item in participants.values()) == 2
    assert participants[_participant(12, "dropped")["id"]][
        "day2_participant"
    ] is False
    expected_rows = {
        _participant(11, "active")["id"]: (5, 4),
        _participant(12, "dropped")["id"]: (3, 3),
        _participant(13, "dropped")["id"]: (5, 5),
        _participant(14, "disqualified")["id"]: (3, 3),
    }
    for participant_id, (theoretical, effective) in expected_rows.items():
        rows = [
            item
            for item in ledger["opportunities"]
            if item["participant_id"] == participant_id
        ]
        assert len(rows) == theoretical
        assert sum(item["effective_theoretical_round"] for item in rows) == effective
    assert schemas.validate_instance(
        ledger,
        loaded["melee-opportunity-ledger.schema.json"],
        registry,
    ) == []


def test_single_stage_dispatch_exposes_only_all_constructed():
    event, classification = _single_stage_inputs()
    ledger = _build_fixture_ledger(event, classification)
    contract = json.loads(PURE_CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["structures"]["constructed_single_stage"][
        "expected_scopes"
    ]["all_constructed"]
    loaded, registry = schemas.load_schemas(ROOT / "schemas")

    assert ledger["event_structure"] == "constructed_single_stage"
    assert list(ledger["scope_summaries"]) == ["all_constructed"]
    assert ledger["scope_summaries"]["all_constructed"] == {
        "participant_count": 4,
        "scheduled_round_count": 5,
        "theoretical_rounds": expected["theoretical_rounds"],
        "effective_theoretical_rounds": expected[
            "effective_theoretical_rounds"
        ],
        "constructed_points": 30,
        "source_match_count": 10,
        "win_rate_match_count": 10,
        "matchup_match_count": 10,
        "disqualified_matches_excluded": 0,
        "result_counts": {"played_loss": 10, "played_win": 10},
    }
    assert all(
        item["scope"] == "all_constructed"
        for item in ledger["opportunities"]
    )
    assert all(
        item["day1_participant"] is False
        and item["day2_participant"] is False
        for item in ledger["participants"]
    )
    expected_points = {
        participant["id"]: participant["single_stage_points"]
        for participant in contract["structures"]["constructed_single_stage"][
            "participants"
        ]
    }
    actual_points = {
        participant_id: sum(
            item["constructed_points"]
            for item in ledger["opportunities"]
            if item["participant_id"] == participant_id
        )
        for participant_id in (
            _participant(number, "active")["id"] for number in range(21, 25)
        )
    }
    assert list(actual_points.values()) == list(expected_points.values())
    assert schemas.validate_instance(
        ledger,
        loaded["melee-opportunity-ledger.schema.json"],
        registry,
    ) == []
    invalid = deepcopy(ledger)
    invalid["scope_summaries"]["day1"] = deepcopy(
        invalid["scope_summaries"]["all_constructed"]
    )
    assert schemas.validate_instance(
        invalid,
        loaded["melee-opportunity-ledger.schema.json"],
        registry,
    )


def test_structure_dispatch_rejects_undeclared_or_cross_structure_stages():
    event, classification = _single_stage_inputs()
    event["event_structure"] = "unknown"
    with pytest.raises(MeleeOpportunityError, match="unsupported event structure"):
        _build_fixture_ledger(event, classification)

    event, classification = _single_stage_inputs()
    event["rounds"][0]["stage"] = "day2"
    with pytest.raises(MeleeOpportunityError, match="does not support Day 2"):
        _build_fixture_ledger(event, classification)

    event, _ = _pure_day2_inputs()
    event["rounds"].append(
        _round(
            6,
            stage="day1",
            round_phase="draft",
            game_format="limited",
        )
    )
    classification = _classification_for_event(event)
    with pytest.raises(MeleeOpportunityError, match="contains a Draft round"):
        _build_fixture_ledger(event, classification)


def test_fixture_ledger_accounts_for_scopes_and_special_results():
    ledger = _fixture_ledger()

    assert ledger["scope_summaries"] == {
        "day1": {
            "participant_count": 4,
            "scheduled_round_count": 2,
            "theoretical_rounds": 8,
            "effective_theoretical_rounds": 8,
            "constructed_points": 11,
            "source_match_count": 4,
            "win_rate_match_count": 1,
            "matchup_match_count": 1,
            "disqualified_matches_excluded": 2,
            "result_counts": {
                "bye": 1,
                "drop_unplayed": 1,
                "intentional_draw": 2,
                "played_loss": 2,
                "played_win": 2,
            },
        },
        "day2": {
            "participant_count": 2,
            "scheduled_round_count": 2,
            "theoretical_rounds": 4,
            "effective_theoretical_rounds": 3,
            "constructed_points": 3,
            "source_match_count": 2,
            "win_rate_match_count": 0,
            "matchup_match_count": 0,
            "disqualified_matches_excluded": 1,
            "result_counts": {
                "administrative_result": 1,
                "awarded_win_top8_lock": 1,
                "played_loss": 1,
                "played_win": 1,
            },
        },
        "all_constructed": {
            "participant_count": 4,
            "scheduled_round_count": 4,
            "theoretical_rounds": 12,
            "effective_theoretical_rounds": 11,
            "constructed_points": 14,
            "source_match_count": 6,
            "win_rate_match_count": 1,
            "matchup_match_count": 1,
            "disqualified_matches_excluded": 3,
            "result_counts": {
                "administrative_result": 1,
                "awarded_win_top8_lock": 1,
                "bye": 1,
                "drop_unplayed": 1,
                "intentional_draw": 2,
                "played_loss": 3,
                "played_win": 3,
            },
        },
    }
    participants = {item["participant_id"]: item for item in ledger["participants"]}
    assert participants[_participant(4, "active")["id"]]["day2_participant"] is False
    nonqualifier_rows = [
        item
        for item in ledger["opportunities"]
        if item["participant_id"] == _participant(4, "active")["id"]
    ]
    assert all(item["scope"] == "day1" for item in nonqualifier_rows)


def test_disqualification_is_symmetric_but_official_points_are_retained():
    ledger = _fixture_ledger()
    disqualified_id = _participant(3, "disqualified")["id"]
    affected = [
        item
        for item in ledger["opportunities"]
        if "disqualified_participant" in item["exclusion_reasons"]
    ]

    assert len({item["match_id"] for item in affected}) == 3
    assert all(not item["win_rate_included"] for item in affected)
    assert all(not item["matchup_included"] for item in affected)
    assert sum(item["constructed_points"] for item in affected) == 8
    missing = next(
        item
        for item in ledger["opportunities"]
        if item["participant_id"] == disqualified_id and item["round_number"] == 13
    )
    assert missing["result_type"] == "administrative_result"
    assert missing["effective_theoretical_round"] is True
    assert missing["points_included"] is False


def test_drop_and_top8_lock_change_only_the_approved_fields():
    ledger = _fixture_ledger()
    dropped = next(
        item
        for item in ledger["opportunities"]
        if item["result_type"] == "drop_unplayed"
    )
    award = next(
        item
        for item in ledger["opportunities"]
        if item["result_type"] == "awarded_win_top8_lock"
    )

    assert dropped["constructed_points"] == 0
    assert dropped["theoretical_round"] is True
    assert dropped["effective_theoretical_round"] is True
    assert award["source_match_points"] == 3
    assert award["constructed_points"] == 0
    assert award["theoretical_round"] is True
    assert award["effective_theoretical_round"] is False


def test_ambiguous_absence_and_stale_classification_fail_closed():
    event, classification = _fixture_inputs()
    event["participants"][1]["status"] = "active"
    with pytest.raises(MeleeOpportunityError, match="non-terminal status"):
        build_opportunity_ledger(
            event,
            classification,
            event_path="data/modern/melee/events/123.json",
            event_sha256=classification["input"]["event_sha256"],
            classification_path="data/modern/melee/classifications/123.json",
            classification_sha256="b" * 64,
        )

    event, classification = _fixture_inputs()
    classification["input"]["event_sha256"] = "c" * 64
    with pytest.raises(MeleeOpportunityError, match="does not hash"):
        build_opportunity_ledger(
            event,
            classification,
            event_path="data/modern/melee/events/123.json",
            event_sha256="a" * 64,
            classification_path="data/modern/melee/classifications/123.json",
            classification_sha256="b" * 64,
        )


def test_bytes_and_atomic_writer_are_deterministic(tmp_path):
    document = _fixture_ledger()
    first = opportunity_ledger_bytes(document)
    second = opportunity_ledger_bytes(deepcopy(document))
    destination = tmp_path / "opportunities/123.json"

    assert first == second
    assert write_opportunity_ledger(destination, first) is False
    assert write_opportunity_ledger(destination, second) is True
    assert destination.read_bytes() == first
    assert not list(destination.parent.glob("*.tmp"))


def test_committed_reference_ledger_is_schema_valid_and_byte_reproducible():
    committed = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    rebuilt = build_opportunity_ledger_from_paths(
        EVENT_PATH,
        CLASSIFICATION_PATH,
        ROOT,
    )
    loaded, registry = schemas.load_schemas(ROOT / "schemas")

    assert opportunity_ledger_bytes(rebuilt) == LEDGER_PATH.read_bytes()
    assert schemas.validate_instance(
        committed,
        loaded["melee-opportunity-ledger.schema.json"],
        registry,
    ) == []


def test_reference_scopes_conserve_real_matches_points_and_opportunities():
    event = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    day1 = ledger["scope_summaries"]["day1"]
    day2 = ledger["scope_summaries"]["day2"]
    combined = ledger["scope_summaries"]["all_constructed"]

    for field in (
        "theoretical_rounds",
        "effective_theoretical_rounds",
        "constructed_points",
        "source_match_count",
        "win_rate_match_count",
        "matchup_match_count",
        "disqualified_matches_excluded",
    ):
        assert combined[field] == day1[field] + day2[field]
    assert combined == {
        "participant_count": 362,
        "scheduled_round_count": 10,
        "theoretical_rounds": 2910,
        "effective_theoretical_rounds": 2903,
        "constructed_points": 4196,
        "source_match_count": 1416,
        "win_rate_match_count": 1394,
        "matchup_match_count": 1394,
        "disqualified_matches_excluded": 6,
        "result_counts": {
            "administrative_result": 4,
            "awarded_win_top8_lock": 7,
            "bye": 7,
            "drop_unplayed": 88,
            "intentional_draw": 4,
            "played_draw": 58,
            "played_loss": 1371,
            "played_win": 1371,
        },
    }
    eligible_event_matches = {
        item["id"]
        for item in event["matches"]
        if item["constructed_statistics_eligible"]
    }
    eligible_ledger_matches = {
        item["match_id"]
        for item in ledger["opportunities"]
        if item["win_rate_included"]
    }
    assert eligible_ledger_matches == eligible_event_matches
    eligible_sides: dict[str, list[str]] = {}
    for item in ledger["opportunities"]:
        if item["win_rate_included"]:
            eligible_sides.setdefault(item["match_id"], []).append(
                item["result_type"]
            )
    assert len(eligible_sides) == 1394
    assert sum(len(results) for results in eligible_sides.values()) == 2788
    assert all(
        sorted(results)
        in (
            ["played_loss", "played_win"],
            ["played_draw", "played_draw"],
        )
        for results in eligible_sides.values()
    )


def test_reference_excludes_draft_playoff_and_both_dq_match_sides():
    event = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    round_ids = {item["round_id"] for item in ledger["rounds"]}
    event_rounds = {item["id"]: item for item in event["rounds"]}

    assert all(
        event_rounds[round_id]["round_phase"] == "constructed"
        and event_rounds[round_id]["swiss"]
        for round_id in round_ids
    )
    affected = [
        item
        for item in ledger["opportunities"]
        if "disqualified_participant" in item["exclusion_reasons"]
    ]
    assert len(affected) == 12
    assert len({item["match_id"] for item in affected}) == 6
    assert all(not item["win_rate_included"] for item in affected)
    assert all(not item["matchup_included"] for item in affected)
