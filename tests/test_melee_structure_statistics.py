"""P9-04 structure-specific overview and deck-statistics contracts."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import validate_schemas as schemas
from mtgmeta.config import load_rule_set
from mtgmeta.melee.opportunities import build_opportunity_ledger
from mtgmeta.melee.matchup import MeleeMatchupError, build_event_matchup
from mtgmeta.melee.stats import (
    build_event_overview_and_decks,
    build_event_statistics,
    statistics_document_bytes,
)


TAXONOMY_PATH = ROOT / "my_archetypes/modern.yaml"


def _participant(number: int, status: str = "active") -> dict[str, Any]:
    participant_id = f"participant-{'%064x' % number}"
    return {
        "id": participant_id,
        "display_name": f"Player {number}",
        "status": status,
    }


def _round(number: int, stage: str) -> dict[str, Any]:
    return {
        "id": f"round-{'%064x' % number}",
        "number": number,
        "phase_id": f"{stage}_constructed",
        "round_phase": "constructed",
        "game_format": "modern",
        "stage": stage,
        "swiss": True,
    }


def _match(
    number: int,
    round_: dict[str, Any],
    competitors: list[tuple[str, str, int]],
    *,
    played: bool = True,
    eligible: bool = True,
) -> dict[str, Any]:
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


def _complete_event(
    *,
    event_id: str,
    event_structure: str,
    participants: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "2.2.0",
        "metadata": {
            "source": "melee",
            "event_id": event_id,
            "constructed_format": "modern",
            "name": f"Synthetic event {event_id}",
            "series": "test_event",
            "date": {"start": "2026-07-01", "end": "2026-07-02"},
        },
        "event_structure": event_structure,
        "quality": {"publishable": True},
        "provenance": {
            "source_urls": [f"https://melee.gg/Tournament/View/{event_id}"]
        },
        "participants": participants,
        "standings": [
            {
                "participant_id": participant["id"],
                "rank": index,
                "match_points": 0,
            }
            for index, participant in enumerate(participants, start=1)
        ],
        "decklists": [
            {
                "participant_id": participant["id"],
                "game_format": "modern",
                "status": "submitted",
                "source_url": None,
                "cards": [],
            }
            for participant in participants
        ],
        "rounds": rounds,
        "matches": matches,
    }


def _classification(
    event: dict[str, Any],
    identities: list[tuple[str, str]],
    taxonomy_sha256: str,
) -> tuple[dict[str, Any], str]:
    event_sha256 = sha256(json.dumps(event).encode()).hexdigest()
    taxonomy = load_rule_set(TAXONOMY_PATH)
    parents = {item.id: item for item in taxonomy.archetypes}
    records = []
    for participant, (archetype_id, subtype_id) in zip(
        event["participants"], identities, strict=True
    ):
        parent = parents[archetype_id]
        subtype = next(item for item in parent.subtypes if item.id == subtype_id)
        records.append(
            {
                "participant_id": participant["id"],
                "classification_status": "classified",
                "selected": {
                    "archetype_id": parent.id,
                    "archetype_name": parent.name,
                    "subtype_id": subtype.id,
                    "subtype_name": subtype.name,
                },
            }
        )
    return (
        {
            "schema_version": "1.0.0",
            "event_id": event["metadata"]["event_id"],
            "format": "modern",
            "input": {"event_sha256": event_sha256},
            "taxonomy": {"rule_sha256": taxonomy_sha256},
            "quality": {
                "blocking": False,
                "summary": {
                    "total_records": len(records),
                    "classified": len(records),
                    "unknown": 0,
                    "conflicts": 0,
                    "invalid_decks": 0,
                },
            },
            "summary": {
                "total_records": len(records),
                "classified": len(records),
                "unknown": 0,
                "conflicts": 0,
                "invalid_decks": 0,
            },
            "records": records,
        },
        event_sha256,
    )


def _build_inputs(
    event: dict[str, Any],
    identities: list[tuple[str, str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any, dict[str, str]]:
    taxonomy_bytes = TAXONOMY_PATH.read_bytes()
    taxonomy_sha256 = sha256(taxonomy_bytes).hexdigest()
    classification, event_sha256 = _classification(
        event, identities, taxonomy_sha256
    )
    classification_sha256 = "b" * 64
    ledger = build_opportunity_ledger(
        event,
        classification,
        event_path=f"data/modern/melee/events/{event['metadata']['event_id']}.json",
        event_sha256=event_sha256,
        classification_path=(
            "data/modern/melee/classifications/"
            f"{event['metadata']['event_id']}.json"
        ),
        classification_sha256=classification_sha256,
    )
    paths = {
        "event_path": f"data/modern/melee/events/{event['metadata']['event_id']}.json",
        "event_sha256": event_sha256,
        "classification_path": (
            "data/modern/melee/classifications/"
            f"{event['metadata']['event_id']}.json"
        ),
        "classification_sha256": classification_sha256,
        "opportunity_path": (
            "data/modern/melee/opportunities/"
            f"{event['metadata']['event_id']}.json"
        ),
        "opportunity_sha256": "c" * 64,
        "taxonomy_path": "my_archetypes/modern.yaml",
        "taxonomy_sha256": taxonomy_sha256,
    }
    return event, classification, ledger, load_rule_set(TAXONOMY_PATH), paths


def _build_documents(
    event: dict[str, Any],
    identities: list[tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    event, classification, ledger, taxonomy, paths = _build_inputs(
        event, identities
    )
    return build_event_overview_and_decks(
        event,
        classification,
        ledger,
        taxonomy,
        **paths,
    )


def _build_full_documents(
    event: dict[str, Any],
    identities: list[tuple[str, str]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    event, classification, ledger, taxonomy, paths = _build_inputs(
        event, identities
    )
    statistics = build_event_statistics(
        event,
        classification,
        ledger,
        taxonomy,
        **paths,
    )
    return statistics, build_event_matchup(statistics["overview"], ledger)


def _day2_event() -> tuple[dict[str, Any], list[tuple[str, str]]]:
    participants = [
        _participant(11),
        _participant(12, "dropped"),
        _participant(13, "dropped"),
        _participant(14, "disqualified"),
    ]
    day1 = [_round(number, "day1") for number in range(1, 4)]
    day2 = [_round(number, "day2") for number in range(4, 6)]
    matches = [
        _match(
            21,
            day1[0],
            [
                (participants[0]["id"], "played_win", 3),
                (participants[1]["id"], "played_loss", 0),
            ],
        ),
        _match(
            22,
            day1[0],
            [
                (participants[2]["id"], "played_win", 3),
                (participants[3]["id"], "played_loss", 0),
            ],
            eligible=False,
        ),
        _match(
            23,
            day1[1],
            [
                (participants[0]["id"], "played_draw", 1),
                (participants[2]["id"], "played_draw", 1),
            ],
        ),
        _match(
            24,
            day1[1],
            [
                (participants[1]["id"], "played_win", 3),
                (participants[3]["id"], "played_loss", 0),
            ],
            eligible=False,
        ),
        _match(
            25,
            day1[2],
            [(participants[0]["id"], "bye", 3)],
            played=False,
            eligible=False,
        ),
        _match(
            26,
            day1[2],
            [
                (participants[1]["id"], "intentional_draw", 1),
                (participants[2]["id"], "intentional_draw", 1),
            ],
            played=False,
            eligible=False,
        ),
        _match(
            27,
            day2[0],
            [
                (participants[0]["id"], "played_win", 3),
                (participants[2]["id"], "played_loss", 0),
            ],
        ),
        _match(
            28,
            day2[1],
            [(participants[0]["id"], "awarded_win_top8_lock", 3)],
            played=False,
            eligible=False,
        ),
    ]
    event = _complete_event(
        event_id="124",
        event_structure="constructed_day2",
        participants=participants,
        rounds=[*day1, *day2],
        matches=matches,
    )
    identities = [
        ("prowess", "izzet"),
        ("prowess", "izzet"),
        ("prowess", "grixis"),
        ("rakdos-hollow-one", "rakdos"),
    ]
    return event, identities


def _single_stage_event() -> tuple[dict[str, Any], list[tuple[str, str]]]:
    participants = [_participant(number) for number in range(21, 25)]
    rounds = [_round(number, "other") for number in range(1, 6)]
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
        for winner, loser in round_pairings:
            matches.append(
                _match(
                    match_number,
                    round_,
                    [
                        (participants[winner]["id"], "played_win", 3),
                        (participants[loser]["id"], "played_loss", 0),
                    ],
                )
            )
            match_number += 1
    event = _complete_event(
        event_id="125",
        event_structure="constructed_single_stage",
        participants=participants,
        rounds=rounds,
        matches=matches,
    )
    identities = [
        ("prowess", "izzet"),
        ("prowess", "grixis"),
        ("prowess", "izzet"),
        ("rakdos-hollow-one", "rakdos"),
    ]
    return event, identities


def _schema_errors(documents: dict[str, dict[str, Any]]) -> list[str]:
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    errors = [
        *schemas.validate_instance(
            documents["overview"],
            loaded["melee-event-overview.schema.json"],
            registry,
        ),
        *schemas.validate_instance(
            documents["decks"],
            loaded["melee-event-decks.schema.json"],
            registry,
        ),
    ]
    if "quality" in documents:
        errors.extend(
            schemas.validate_instance(
                documents["quality"],
                loaded["melee-event-quality.schema.json"],
                registry,
            )
        )
    if "matchup" in documents:
        errors.extend(
            schemas.validate_instance(
                documents["matchup"],
                loaded["melee-event-matchup.schema.json"],
                registry,
            )
        )
    return errors


def test_constructed_day2_overview_uses_conversion_without_mixed_bias():
    event, identities = _day2_event()
    documents = _build_documents(event, identities)
    overview = documents["overview"]

    assert overview["event_structure"] == "constructed_day2"
    assert overview["scope_order"] == ["day1", "day2", "all_constructed"]
    assert overview["advancement_metric"] == "day2_conversion"
    assert overview["warnings"] == []
    assert overview["scopes"]["day2"]["selection_bias_warning"] is False
    assert overview["scopes"]["day2"]["day2_conversion"] == 0.5
    assert all(
        scope["high_score_deck_count"] is None
        for scope in overview["scopes"].values()
    )

    prowess = next(
        row
        for row in overview["scopes"]["day2"]["archetypes"]
        if row["archetype_id"] == "prowess"
    )
    assert prowess["deck_count"] == 2
    assert prowess["day2_conversion"] == 0.666667
    assert {
        subtype["subtype_id"]: subtype["day2_conversion"]
        for subtype in prowess["subtypes"]
    }["izzet"] == 0.5
    day1_prowess = next(
        row
        for row in overview["scopes"]["day1"]["archetypes"]
        if row["archetype_id"] == "prowess"
    )
    assert day1_prowess["match_record"]["all_matches"] == {
        "wins": 1,
        "losses": 1,
        "draws": 2,
        "matches": 4,
        "win_rate": 0.5,
        "confidence_interval_95": {
            "lower": 0.150039,
            "upper": 0.849961,
        },
        "literal_record": {
            "wins": 1,
            "losses": 1,
            "draws": 2,
            "matches": 4,
            "win_rate": 0.25,
            "win_rate_method": "wins_over_valid_matches",
            "confidence_interval_95": {
                "lower": 0.045586,
                "upper": 0.699364,
            },
        },
    }
    assert _schema_errors(documents) == []


def test_single_stage_overview_exposes_only_combined_high_score_scope():
    event, identities = _single_stage_event()
    documents = _build_documents(event, identities)
    overview = documents["overview"]

    assert overview["event_structure"] == "constructed_single_stage"
    assert overview["scope_order"] == ["all_constructed"]
    assert overview["advancement_metric"] == "high_score_conversion"
    assert overview["warnings"] == []
    assert list(overview["scopes"]) == ["all_constructed"]
    combined = overview["scopes"]["all_constructed"]
    assert combined["population"] == "starting_field"
    assert combined["participant_count"] == 4
    assert combined["high_score_deck_count"] == 2
    assert combined["theoretical_rounds"] == 20
    assert combined["effective_theoretical_rounds"] == 20
    assert all(
        list(deck["scopes"]) == ["all_constructed"]
        and deck["overall_points_include_non_constructed_context"] is False
        for deck in documents["decks"]["decks"]
    )
    assert sorted(
        deck["scopes"]["all_constructed"]["constructed_points"]
        for deck in documents["decks"]["decks"]
    ) == [3, 6, 9, 12]
    assert sum(
        deck["scopes"]["all_constructed"]["high_score"]["qualified"]
        for deck in documents["decks"]["decks"]
    ) == 2
    rebuilt = _build_documents(event, identities)
    assert statistics_document_bytes(rebuilt["overview"]) == (
        statistics_document_bytes(documents["overview"])
    )
    assert statistics_document_bytes(rebuilt["decks"]) == (
        statistics_document_bytes(documents["decks"])
    )
    assert _schema_errors(documents) == []


def test_pure_parent_and_subtype_additive_fields_conserve():
    for fixture in (_day2_event, _single_stage_event):
        event, identities = fixture()
        overview = _build_documents(event, identities)["overview"]
        for scope in overview["scopes"].values():
            for parent in scope["archetypes"]:
                if not parent["subtypes"]:
                    continue
                for field in (
                    "deck_count",
                    "constructed_points",
                    "theoretical_rounds",
                    "effective_theoretical_rounds",
                    "played_match_participations",
                ):
                    assert parent[field] == sum(
                        child[field] for child in parent["subtypes"]
                    )
                for field in ("wins", "losses", "draws", "matches"):
                    assert parent["match_record"]["all_matches"][field] == sum(
                        child["match_record"]["all_matches"][field]
                        for child in parent["subtypes"]
                    )
                if parent["high_score"] is not None:
                    assert parent["high_score"]["count"] == sum(
                        child["high_score"]["count"]
                        for child in parent["subtypes"]
                    )


def test_constructed_day2_full_package_has_structure_aware_quality_and_matchups():
    event, identities = _day2_event()
    statistics, matchup = _build_full_documents(event, identities)
    quality = statistics["quality"]

    assert quality["event_structure"] == "constructed_day2"
    assert quality["status"] == "warning"
    assert [issue["code"] for issue in quality["issues"]] == [
        "disqualified_participant_matches_excluded"
    ]
    assert quality["counts"]["day2_participants"] == 2
    assert all(check["passed"] for check in quality["checks"])
    assert matchup["event_structure"] == "constructed_day2"
    assert matchup["scope_order"] == ["day1", "day2", "all_constructed"]
    assert list(matchup["scopes"]) == matchup["scope_order"]
    assert matchup["warnings"] == []
    assert _schema_errors({**statistics, "matchup": matchup}) == []


def test_single_stage_full_package_omits_fictional_stage_scopes():
    event, identities = _single_stage_event()
    statistics, matchup = _build_full_documents(event, identities)
    quality = statistics["quality"]

    assert quality["event_structure"] == "constructed_single_stage"
    assert quality["status"] == "ready"
    assert quality["issues"] == []
    assert "day2_participants" not in quality["counts"]
    assert all(check["passed"] for check in quality["checks"])
    assert matchup["event_structure"] == "constructed_single_stage"
    assert matchup["scope_order"] == ["all_constructed"]
    assert list(matchup["scopes"]) == ["all_constructed"]
    assert matchup["warnings"] == []
    assert _schema_errors({**statistics, "matchup": matchup}) == []


def test_matchup_rejects_scope_contract_that_disagrees_with_structure():
    event, identities = _single_stage_event()
    event, classification, ledger, taxonomy, paths = _build_inputs(
        event, identities
    )
    overview = build_event_statistics(
        event,
        classification,
        ledger,
        taxonomy,
        **paths,
    )["overview"]
    overview["scope_order"] = ["day1", "day2", "all_constructed"]

    with pytest.raises(MeleeMatchupError, match="scope order"):
        build_event_matchup(overview, ledger)
