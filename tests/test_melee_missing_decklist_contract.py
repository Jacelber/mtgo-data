from pathlib import Path
from typing import Any

from mtgmeta.config import load_rule_set
from mtgmeta.melee.matchup import build_event_matchup
from mtgmeta.melee.opportunities import build_opportunity_ledger
from mtgmeta.melee.stats import build_event_statistics
from validate_schemas import load_schemas, validate_instance


ROOT = Path(__file__).resolve().parents[1]
EVENT_SHA256 = "a" * 64
CLASSIFICATION_SHA256 = "b" * 64
OPPORTUNITY_SHA256 = "c" * 64
TAXONOMY_SHA256 = "d" * 64
KNOWN_ID = "participant-" + "1" * 64
UNAVAILABLE_ID = "participant-" + "2" * 64
ROUND_1_ID = "round-" + "3" * 64
ROUND_2_ID = "round-" + "4" * 64
MATCH_1_ID = "match-" + "5" * 64
MATCH_2_ID = "match-" + "6" * 64


def _event() -> dict[str, Any]:
    return {
        "schema_version": "2.2.0",
        "event_structure": "constructed_single_stage",
        "metadata": {
            "source": "melee",
            "event_id": "999001",
            "constructed_format": "modern",
            "name": "Synthetic missing-decklist contract",
            "series": "synthetic",
            "date": {"start": "2026-08-31", "end": "2026-08-31"},
        },
        "participants": [
            {"id": KNOWN_ID, "display_name": "Known", "status": "active"},
            {
                "id": UNAVAILABLE_ID,
                "display_name": "Unavailable",
                "status": "active",
            },
        ],
        "standings": [
            {"participant_id": KNOWN_ID, "rank": 1, "match_points": 3},
            {
                "participant_id": UNAVAILABLE_ID,
                "rank": 2,
                "match_points": 0,
            },
        ],
        "decklists": [
            {
                "participant_id": KNOWN_ID,
                "game_format": "modern",
                "status": "submitted",
                "source_url": "https://melee.gg/Decklist/View/known",
                "cards": [],
            },
            {
                "participant_id": UNAVAILABLE_ID,
                "game_format": "modern",
                "status": "unavailable",
                "source_url": None,
                "cards": [],
            },
        ],
        "phases": [],
        "rounds": [
            {
                "id": ROUND_1_ID,
                "number": 1,
                "phase_id": "constructed",
                "round_phase": "constructed",
                "game_format": "modern",
                "stage": "day1",
                "swiss": True,
            },
            {
                "id": ROUND_2_ID,
                "number": 2,
                "phase_id": "constructed",
                "round_phase": "constructed",
                "game_format": "modern",
                "stage": "day1",
                "swiss": True,
            },
        ],
        "matches": [
            {
                "id": MATCH_1_ID,
                "round_id": ROUND_1_ID,
                "played": True,
                "constructed_statistics_eligible": True,
                "matchup_eligible": True,
                "competitors": [
                    {
                        "participant_id": KNOWN_ID,
                        "result_type": "played_win",
                        "match_points": 3,
                    },
                    {
                        "participant_id": UNAVAILABLE_ID,
                        "result_type": "played_loss",
                        "match_points": 0,
                    },
                ],
            },
            {
                "id": MATCH_2_ID,
                "round_id": ROUND_2_ID,
                "played": True,
                "constructed_statistics_eligible": True,
                "matchup_eligible": True,
                "competitors": [
                    {
                        "participant_id": KNOWN_ID,
                        "result_type": "played_win",
                        "match_points": 3,
                    },
                    {
                        "participant_id": UNAVAILABLE_ID,
                        "result_type": "played_loss",
                        "match_points": 0,
                    },
                ],
            },
        ],
        "provenance": {
            "source_urls": ["https://melee.gg/Tournament/View/999001"]
        },
        "quality": {"status": "warning", "publishable": True, "issues": []},
    }


def _classification() -> dict[str, Any]:
    return {
        "schema_version": "1.1.0",
        "source": "melee",
        "event_id": "999001",
        "format": "modern",
        "input": {
            "event_sha256": EVENT_SHA256,
            "event_decklist_count": 2,
            "submitted_format_decklist_count": 1,
            "excluded_decklist_count": 1,
        },
        "taxonomy": {
            "rule_path": "my_archetypes/modern.yaml",
            "rule_sha256": TAXONOMY_SHA256,
            "rule_schema_version": "1.1.0",
        },
        "summary": {
            "total_records": 1,
            "classified": 1,
            "unknown": 0,
            "conflicts": 0,
            "invalid_decks": 0,
        },
        "quality": {"status": "pass", "blocking": False},
        "records": [
            {
                "participant_id": KNOWN_ID,
                "classification_status": "classified",
                "selected": {
                    "archetype_id": "mono-blue-selective-memory",
                    "archetype_name": "Mono-Blue Selective Memory",
                    "subtype_id": None,
                    "subtype_name": None,
                },
            }
        ],
    }


def _documents() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    event = _event()
    classification = _classification()
    ledger = build_opportunity_ledger(
        event,
        classification,
        event_path="data/modern/melee/events/999001.json",
        event_sha256=EVENT_SHA256,
        classification_path="data/modern/melee/classifications/999001.json",
        classification_sha256=CLASSIFICATION_SHA256,
    )
    statistics = build_event_statistics(
        event,
        classification,
        ledger,
        load_rule_set(ROOT / "my_archetypes" / "modern.yaml"),
        event_path="data/modern/melee/events/999001.json",
        event_sha256=EVENT_SHA256,
        classification_path="data/modern/melee/classifications/999001.json",
        classification_sha256=CLASSIFICATION_SHA256,
        opportunity_path="data/modern/melee/opportunities/999001.json",
        opportunity_sha256=OPPORTUNITY_SHA256,
        taxonomy_path="my_archetypes/modern.yaml",
        taxonomy_sha256=TAXONOMY_SHA256,
    )
    return ledger, statistics, build_event_matchup(statistics["overview"], ledger)


def test_participant_coverage_accepts_submitted_and_unavailable_decklists() -> None:
    participant_ids = [f"participant-{index:064x}" for index in range(5)]
    event = {
        "schema_version": "2.2.0",
        "event_structure": "constructed_single_stage",
        "metadata": {
            "source": "melee",
            "event_id": "999002",
            "constructed_format": "modern",
        },
        "participants": [
            {"id": participant_id, "status": "dropped"}
            for participant_id in participant_ids
        ],
        "decklists": [
            {
                "participant_id": participant_id,
                "game_format": "modern",
                "status": "submitted" if index < 2 else "unavailable",
            }
            for index, participant_id in enumerate(participant_ids)
        ],
        "rounds": [
            {
                "id": ROUND_1_ID,
                "number": 1,
                "phase_id": "constructed",
                "round_phase": "constructed",
                "game_format": "modern",
                "stage": "day1",
                "swiss": True,
            }
        ],
        "matches": [],
    }
    classification = {
        "schema_version": "1.1.0",
        "event_id": "999002",
        "format": "modern",
        "input": {"event_sha256": EVENT_SHA256},
        "quality": {"blocking": False},
        "records": [
            {
                "participant_id": participant_id,
                "classification_status": "classified",
                "selected": {
                    "archetype_id": "mono-blue-selective-memory",
                    "archetype_name": "Mono-Blue Selective Memory",
                    "subtype_id": None,
                    "subtype_name": None,
                },
            }
            for participant_id in participant_ids[:2]
        ],
    }

    ledger = build_opportunity_ledger(
        event,
        classification,
        event_path="data/modern/melee/events/999002.json",
        event_sha256=EVENT_SHA256,
        classification_path="data/modern/melee/classifications/999002.json",
        classification_sha256=CLASSIFICATION_SHA256,
    )

    statuses = [item["classification"]["status"] for item in ledger["participants"]]
    assert len(statuses) == 5
    assert statuses.count("classified") == 2
    assert statuses.count("unknown") == 0
    assert statuses.count("unavailable") == 3


def test_unavailable_decklist_is_not_fabricated_as_unknown() -> None:
    ledger, statistics, _matchup = _documents()

    classifications = {
        item["participant_id"]: item["classification"]
        for item in ledger["participants"]
    }
    assert classifications[KNOWN_ID]["status"] == "classified"
    assert classifications[UNAVAILABLE_ID] == {
        "status": "unavailable",
        "archetype_id": None,
        "archetype_name": None,
        "subtype_id": None,
        "subtype_name": None,
    }
    assert statistics["quality"]["counts"]["unknown_decks"] == 0
    assert statistics["quality"]["counts"]["missing_or_unavailable_decklists"] == 1


def test_deck_share_and_matchup_use_only_available_classification_identities() -> None:
    ledger, statistics, matchup = _documents()
    scope = statistics["overview"]["scopes"]["all_constructed"]

    assert scope["participant_count"] == 2
    assert scope["submitted_deck_count"] == 1
    assert scope["known_deck_count"] == 1
    assert scope["unknown_deck_count"] == 0
    assert scope["unavailable_deck_count"] == 1
    assert scope["archetypes"][0]["deck_count"] == 1
    assert scope["archetypes"][0]["metagame_share"] == 1.0
    assert ledger["scope_summaries"]["all_constructed"]["source_match_count"] == 2
    assert ledger["scope_summaries"]["all_constructed"]["win_rate_match_count"] == 2

    matchup_scope = matchup["scopes"]["all_constructed"]
    assert matchup_scope["source_match_count"] == 2
    assert matchup_scope["included_match_count"] == 0
    assert matchup_scope["excluded_match_counts"]["decklist_unavailable"] == 2


def test_no_show_after_played_round_is_a_terminal_status() -> None:
    event = _event()
    for participant in event["participants"]:
        participant["status"] = "no_show"
    event["matches"] = event["matches"][:1]

    ledger = build_opportunity_ledger(
        event,
        _classification(),
        event_path="data/modern/melee/events/999001.json",
        event_sha256=EVENT_SHA256,
        classification_path="data/modern/melee/classifications/999001.json",
        classification_sha256=CLASSIFICATION_SHA256,
    )

    missing_round = [
        item for item in ledger["opportunities"] if item["round_id"] == ROUND_2_ID
    ]
    assert len(missing_round) == 2
    assert all(item["participant_status"] == "no_show" for item in missing_round)
    assert all(item["result_type"] == "no_show" for item in missing_round)
    assert all(item["source_played"] is False for item in missing_round)
    assert all(item["points_included"] is True for item in missing_round)
    assert all(item["constructed_points"] == 0 for item in missing_round)
    assert all(item["theoretical_round"] is True for item in missing_round)
    assert all(item["effective_theoretical_round"] is True for item in missing_round)
    assert all(item["win_rate_included"] is False for item in missing_round)
    assert all(item["matchup_included"] is False for item in missing_round)
    assert all(item["exclusion_reasons"] == ["no_show"] for item in missing_round)
    assert ledger["scope_summaries"]["all_constructed"]["result_counts"] == {
        "no_show": 2,
        "played_loss": 1,
        "played_win": 1,
    }

    statistics = build_event_statistics(
        event,
        _classification(),
        ledger,
        load_rule_set(ROOT / "my_archetypes" / "modern.yaml"),
        event_path="data/modern/melee/events/999001.json",
        event_sha256=EVENT_SHA256,
        classification_path="data/modern/melee/classifications/999001.json",
        classification_sha256=CLASSIFICATION_SHA256,
        opportunity_path="data/modern/melee/opportunities/999001.json",
        opportunity_sha256=OPPORTUNITY_SHA256,
        taxonomy_path="my_archetypes/modern.yaml",
        taxonomy_sha256=TAXONOMY_SHA256,
    )
    assert statistics["quality"]["counts"]["no_show_opportunities"] == 2
    assert statistics["quality"]["counts"]["drop_player_count"] == 0
    assert statistics["quality"]["counts"]["drop_unplayed_rounds"] == 0
    assert all(
        deck["scopes"]["all_constructed"][
            "completed_or_officially_exempt_rounds"
        ]
        == 1
        for deck in statistics["decks"]["decks"]
    )


def test_new_documents_validate_against_public_schemas() -> None:
    ledger, statistics, matchup = _documents()
    schemas, registry = load_schemas(ROOT / "schemas")
    documents = {
        "melee-opportunity-ledger.schema.json": ledger,
        "melee-event-overview.schema.json": statistics["overview"],
        "melee-event-decks.schema.json": statistics["decks"],
        "melee-event-quality.schema.json": statistics["quality"],
        "melee-event-matchup.schema.json": matchup,
    }

    for schema_name, document in documents.items():
        assert not validate_instance(document, schemas[schema_name], registry)
