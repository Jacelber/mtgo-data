"""P7-05 per-event overview, deck, and quality statistics contracts."""

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
from mtgmeta.config import load_rule_set
from mtgmeta.melee.stats import (
    MeleeStatisticsError,
    build_event_statistics,
    build_event_statistics_from_paths,
    statistics_document_bytes,
    write_statistics_document,
)


EVENT_ID = "434455"
EVENT_PATH = ROOT / "data/modern/melee/events" / f"{EVENT_ID}.json"
CLASSIFICATION_PATH = (
    ROOT / "data/modern/melee/classifications" / f"{EVENT_ID}.json"
)
OPPORTUNITY_PATH = ROOT / "data/modern/melee/opportunities" / f"{EVENT_ID}.json"
TAXONOMY_PATH = ROOT / "my_archetypes/modern.yaml"
OUTPUT_DIR = ROOT / "stats/modern/melee/events" / EVENT_ID
OUTPUT_SCHEMAS = {
    "overview": "melee-event-overview.schema.json",
    "decks": "melee-event-decks.schema.json",
    "quality": "melee-event-quality.schema.json",
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _committed_documents() -> dict[str, dict[str, object]]:
    return {name: _load(OUTPUT_DIR / f"{name}.json") for name in OUTPUT_SCHEMAS}


def test_committed_statistics_are_byte_reproducible_and_schema_valid():
    rebuilt = build_event_statistics_from_paths(
        EVENT_PATH,
        CLASSIFICATION_PATH,
        OPPORTUNITY_PATH,
        TAXONOMY_PATH,
        ROOT,
    )
    loaded, registry = schemas.load_schemas(ROOT / "schemas")

    for name, schema_name in OUTPUT_SCHEMAS.items():
        path = OUTPUT_DIR / f"{name}.json"
        assert statistics_document_bytes(rebuilt[name]) == path.read_bytes()
        assert (
            schemas.validate_instance(
                _load(path),
                loaded[schema_name],
                registry,
                path.relative_to(ROOT).as_posix(),
            )
            == []
        )


def test_reference_scope_totals_match_the_opportunity_ledger():
    overview = _committed_documents()["overview"]
    scopes = overview["scopes"]

    assert {
        scope: {
            field: scopes[scope][field]
            for field in (
                "participant_count",
                "known_deck_count",
                "unknown_deck_count",
                "constructed_points",
                "theoretical_rounds",
                "effective_theoretical_rounds",
                "eligible_match_count",
                "high_score_deck_count",
            )
        }
        for scope in overview["scope_order"]
    } == {
            "day1": {
                "participant_count": 362,
                "known_deck_count": 351,
                "unknown_deck_count": 11,
            "constructed_points": 2589,
            "theoretical_rounds": 1810,
            "effective_theoretical_rounds": 1810,
            "eligible_match_count": 861,
            "high_score_deck_count": 168,
        },
            "day2": {
                "participant_count": 220,
                "known_deck_count": 210,
                "unknown_deck_count": 10,
            "constructed_points": 1607,
            "theoretical_rounds": 1100,
            "effective_theoretical_rounds": 1093,
            "eligible_match_count": 533,
            "high_score_deck_count": 105,
        },
            "all_constructed": {
                "participant_count": 362,
                "known_deck_count": 351,
                "unknown_deck_count": 11,
            "constructed_points": 4196,
            "theoretical_rounds": 2910,
            "effective_theoretical_rounds": 2903,
            "eligible_match_count": 1394,
            "high_score_deck_count": None,
        },
    }
    assert scopes["all_constructed"]["constructed_points"] == (
        scopes["day1"]["constructed_points"]
        + scopes["day2"]["constructed_points"]
    )
    assert scopes["all_constructed"]["effective_theoretical_rounds"] == (
        scopes["day1"]["effective_theoretical_rounds"]
        + scopes["day2"]["effective_theoretical_rounds"]
    )


def test_parent_rows_and_unknown_bucket_conserve_every_scope():
    overview = _committed_documents()["overview"]

    for scope in overview["scopes"].values():
        rows = scope["archetypes"]
        assert sum(row["deck_count"] for row in rows) == scope["participant_count"]
        assert sum(row["constructed_points"] for row in rows) == scope[
            "constructed_points"
        ]
        assert sum(row["theoretical_rounds"] for row in rows) == scope[
            "theoretical_rounds"
        ]
        assert sum(row["effective_theoretical_rounds"] for row in rows) == scope[
            "effective_theoretical_rounds"
        ]
        assert sum(
            row["match_record"]["all_matches"]["matches"] for row in rows
        ) == 2 * scope["eligible_match_count"]
        assert sum(row["metagame_share"] for row in rows) == pytest.approx(
            1.0, abs=0.00001
        )
        unknown = next(row for row in rows if row["group_id"] == "unknown")
        assert unknown["classification_status"] == "unknown"
        assert unknown["archetype_id"] is None
        assert unknown["subtypes"] == []


def test_subtype_children_conserve_additive_parent_fields():
    overview = _committed_documents()["overview"]
    additive_fields = (
        "deck_count",
        "constructed_points",
        "theoretical_rounds",
        "effective_theoretical_rounds",
        "played_match_participations",
    )
    record_fields = ("wins", "losses", "draws", "matches")

    for scope in overview["scopes"].values():
        for parent in scope["archetypes"]:
            if not parent["subtypes"]:
                continue
            for field in additive_fields:
                assert parent[field] == sum(
                    child[field] for child in parent["subtypes"]
                )
            for field in record_fields:
                assert parent["match_record"]["all_matches"][field] == sum(
                    child["match_record"]["all_matches"][field]
                    for child in parent["subtypes"]
                )
            assert parent["expandable"] == (len(parent["subtypes"]) >= 2)


def test_day1_and_day2_high_score_use_per_player_effective_rounds():
    documents = _committed_documents()
    overview = documents["overview"]
    decks = documents["decks"]["decks"]

    assert overview["scopes"]["all_constructed"]["high_score_deck_count"] is None
    assert all(
        row["high_score"] is None
        for row in overview["scopes"]["all_constructed"]["archetypes"]
    )
    for deck in decks:
        for scope in ("day1", "day2"):
            stats = deck["scopes"][scope]
            if not stats["participated"]:
                assert stats["high_score"] is None
                continue
            effective = stats["effective_theoretical_rounds"]
            expected_threshold = 3 * (effective // 2 + 1) if effective else None
            assert stats["high_score"]["threshold"] == expected_threshold
            assert stats["high_score"]["qualified"] == (
                stats["constructed_points"] >= expected_threshold
                if expected_threshold is not None
                else None
            )


def test_disqualified_deck_is_retained_but_has_no_played_match_sample():
    documents = _committed_documents()
    disqualified = [
        deck
        for deck in documents["decks"]["decks"]
        if deck["participant_status"] == "disqualified"
    ]

    assert len(disqualified) == 1
    deck = disqualified[0]
    assert deck["statistics_eligibility"] == {
        "point_metrics_follow_opportunity_ledger": True,
        "played_match_metrics_excluded": True,
        "exclusion_reason": "disqualified_participant",
    }
    assert deck["scopes"]["all_constructed"]["constructed_points"] == 12
    assert deck["scopes"]["all_constructed"]["played_record"]["matches"] == 0
    assert deck["scopes"]["day1"]["high_score"]["qualified"] is True

    quality = documents["quality"]
    assert quality["counts"]["disqualified_participant_count"] == 1
    assert quality["counts"]["disqualified_matches_excluded"] == 6


def test_quality_reports_required_exclusions_and_no_unresolved_records():
    quality = _committed_documents()["quality"]

    assert quality["status"] == "warning"
    assert quality["blocking"] is False
    assert all(check["passed"] for check in quality["checks"])
    assert quality["counts"] == {
        "participants": 362,
        "standings": 362,
        "submitted_decklists": 362,
        "missing_or_unavailable_decklists": 0,
        "classified_decks": 351,
        "unknown_decks": 11,
        "classification_conflicts": 0,
        "invalid_decks": 0,
        "rounds": 19,
        "unknown_rounds": 0,
        "source_matches": 2296,
        "source_constructed_matches": 1416,
        "eligible_constructed_matches": 1394,
        "unknown_result_opportunities": 0,
        "bye_count": 7,
        "intentional_draw_match_count": 2,
        "intentional_draw_opportunities": 4,
        "drop_player_count": 48,
        "drop_unplayed_rounds": 88,
        "disqualified_participant_count": 1,
        "disqualified_matches_excluded": 6,
        "top8_lock_player_count": 5,
        "top8_lock_exemptions": 7,
        "day2_participants": 220,
        "playoff_participants": 8,
        "no_show_opportunities": 0,
    }
    assert {issue["code"] for issue in quality["issues"]} == {
        "unknown_classifications",
        "disqualified_participant_matches_excluded",
        "mixed_event_day2_selection_bias",
    }


def test_statistics_fail_closed_when_ledger_provenance_changes():
    event = _load(EVENT_PATH)
    classification = _load(CLASSIFICATION_PATH)
    ledger = _load(OPPORTUNITY_PATH)
    taxonomy = load_rule_set(TAXONOMY_PATH)
    ledger["input"]["classification_sha256"] = "0" * 64

    with pytest.raises(
        MeleeStatisticsError,
        match="opportunity ledger classification hash does not match",
    ):
        build_event_statistics(
            event,
            classification,
            ledger,
            taxonomy,
            event_path=EVENT_PATH.relative_to(ROOT).as_posix(),
            event_sha256=sha256(EVENT_PATH.read_bytes()).hexdigest(),
            classification_path=CLASSIFICATION_PATH.relative_to(ROOT).as_posix(),
            classification_sha256=sha256(
                CLASSIFICATION_PATH.read_bytes()
            ).hexdigest(),
            opportunity_path=OPPORTUNITY_PATH.relative_to(ROOT).as_posix(),
            opportunity_sha256=sha256(OPPORTUNITY_PATH.read_bytes()).hexdigest(),
            taxonomy_path=TAXONOMY_PATH.relative_to(ROOT).as_posix(),
            taxonomy_sha256=sha256(TAXONOMY_PATH.read_bytes()).hexdigest(),
        )


def test_bytes_and_atomic_writer_are_deterministic(tmp_path):
    document = _committed_documents()["quality"]
    first = statistics_document_bytes(document)
    second = statistics_document_bytes(deepcopy(document))
    destination = tmp_path / "quality.json"

    assert first == second
    assert write_statistics_document(destination, first) is False
    assert write_statistics_document(destination, second) is True
    assert destination.read_bytes() == first
    assert not list(destination.parent.glob("*.tmp"))
