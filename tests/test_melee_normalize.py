from dataclasses import replace
from pathlib import Path

import pytest

import validate_schemas as schemas
from mtgmeta.melee.config import MeleeMatchOverride, MeleeOverrideCompetitor, load_melee_event_registry
from mtgmeta.melee.normalize import (
    MeleeNormalizationError,
    normalize_parsed_snapshot,
    normalize_raw_snapshot,
)
from mtgmeta.melee.parser import SourceCompetitor, parse_raw_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "source_snapshot"
NORMALIZED_AT = "2026-07-21T14:00:00Z"


def event_definition():
    return load_melee_event_registry(ROOT / "configs" / "melee_events.yaml").events[0]


def parsed_snapshot():
    return parse_raw_snapshot(FIXTURE)


def normalized():
    return normalize_raw_snapshot(FIXTURE, event_definition(), normalized_at=NORMALIZED_AT)


def source_match(document, source_id):
    return next(item for item in document["matches"] if item["source_record_id"] == source_id)


def test_normalizes_reviewed_phase_status_format_and_result_semantics():
    document = normalized()
    rounds = {item["source_label"]: item for item in document["rounds"]}
    assert (rounds["Round 1"]["stage"], rounds["Round 1"]["round_phase"]) == ("day1", "draft")
    assert (rounds["Round 4"]["stage"], rounds["Round 4"]["game_format"]) == ("day1", "modern")
    assert rounds["Quarterfinals"]["phase_id"] == "top8_draft"
    assert rounds["Quarterfinals"]["swiss"] is False
    assert "unresolved" not in {item["id"] for item in document["phases"]}

    participants = {item["source_id"]: item for item in document["participants"]}
    assert participants["participant-101"]["status"] == "active"
    assert participants["participant-202"]["status"] == "dropped"
    assert {item["game_format"] for item in document["decklists"]} == {"modern"}

    draft = source_match(document, "match-source-1")
    assert draft["played"] is True
    assert [item["result_type"] for item in draft["competitors"]] == ["played_win", "played_loss"]
    assert draft["constructed_statistics_eligible"] is False

    bye = source_match(document, "match-source-4")
    assert bye["played"] is False
    assert bye["competitors"][0]["result_type"] == "bye"
    assert bye["matchup_eligible"] is False

    modern = source_match(document, "match-source-4-played")
    assert modern["played"] is True
    assert [item["result_type"] for item in modern["competitors"]] == ["played_win", "played_loss"]
    assert modern["constructed_statistics_eligible"] is True
    assert modern["matchup_eligible"] is True
    assert document["quality"] == {"status": "valid", "publishable": False, "issues": []}


def test_normalized_fixture_matches_schema_but_remains_non_publishable():
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    document = normalized()
    assert schemas.validate_instance(
        document, loaded["melee-event.schema.json"], registry
    ) == []
    assert document["quality"]["publishable"] is False


def test_competitor_order_never_determines_the_winner():
    document = normalized()
    modern = source_match(document, "match-source-4-played")
    participants = {item["id"]: item["source_id"] for item in document["participants"]}
    outcomes = {
        participants[item["participant_id"]]: item["result_type"]
        for item in modern["competitors"]
    }
    assert outcomes == {"participant-202": "played_win", "participant-101": "played_loss"}


def test_missing_outcome_and_unmapped_round_block_quality_without_guessing():
    snapshot = parsed_snapshot()
    page = snapshot.pages[0]
    match = page.matches[2]
    unknown_results = tuple(
        replace(item, outcome_text=None, match_points=None) for item in match.competitor_results
    )
    changed_match = replace(match, competitor_results=unknown_results)
    changed_round = replace(page.rounds[1], number=99, label="Unreviewed Round")
    changed_page = replace(
        page,
        rounds=(page.rounds[0], changed_round, page.rounds[2]),
        matches=(*page.matches[:2], changed_match),
    )
    document = normalize_parsed_snapshot(
        replace(snapshot, pages=(changed_page, snapshot.pages[1])),
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )
    assert document["quality"]["status"] == "blocked"
    assert document["quality"]["publishable"] is False
    assert {item["code"] for item in document["quality"]["issues"]} == {
        "unknown_round_phase",
        "unknown_result",
    }
    assert source_match(document, "match-source-4-played")["competitors"][0]["result_type"] == "unknown"


def test_reviewed_override_is_evidence_backed_and_forces_ineligibility():
    event = event_definition()
    override = MeleeMatchOverride(
        id="official_top8_lock",
        source_match_id="match-source-4-played",
        review_status="verified",
        played=False,
        competitors=(
            MeleeOverrideCompetitor("participant-202", "awarded_win_top8_lock", 3),
            MeleeOverrideCompetitor("participant-101", "administrative", 0),
        ),
        reason="Official pairing retained after the Top 8 lock.",
        source_evidence=("https://magic.gg/example",),
    )
    document = normalize_parsed_snapshot(
        parsed_snapshot(), replace(event, reviewed_overrides=(override,)), normalized_at=NORMALIZED_AT
    )
    match = source_match(document, "match-source-4-played")
    assert match["played"] is False
    assert match["constructed_statistics_eligible"] is False
    assert "reviewed_override=official_top8_lock" in match["evidence"]
    assert document["quality"]["status"] == "valid"
    assert document["quality"]["publishable"] is False


def test_reviewed_override_cannot_invent_or_target_missing_identities():
    event = event_definition()
    override = MeleeMatchOverride(
        id="bad_override",
        source_match_id="match-source-4-played",
        review_status="verified",
        played=False,
        competitors=(MeleeOverrideCompetitor("invented", "administrative", 0),),
        reason="Invalid test override.",
        source_evidence=("https://magic.gg/example",),
    )
    with pytest.raises(MeleeNormalizationError, match="identities do not match"):
        normalize_parsed_snapshot(
            parsed_snapshot(), replace(event, reviewed_overrides=(override,)), normalized_at=NORMALIZED_AT
        )

    inconsistent = replace(
        override,
        competitors=(
            MeleeOverrideCompetitor("participant-202", "played_win", 0),
            MeleeOverrideCompetitor("participant-101", "played_loss", 0),
        ),
        played=True,
    )
    with pytest.raises(MeleeNormalizationError, match="inconsistent played points"):
        normalize_parsed_snapshot(
            parsed_snapshot(),
            replace(event, reviewed_overrides=(inconsistent,)),
            normalized_at=NORMALIZED_AT,
        )
    with pytest.raises(MeleeNormalizationError, match="missing source matches"):
        normalize_parsed_snapshot(
            parsed_snapshot(),
            replace(event, reviewed_overrides=(replace(override, source_match_id="missing"),)),
            normalized_at=NORMALIZED_AT,
        )


def test_intentional_draw_and_explicit_no_show_are_nonplayed_and_ineligible():
    snapshot = parsed_snapshot()
    page = snapshot.pages[0]
    played = page.matches[2]
    intentional_draw = replace(
        played,
        result_text="0-0-3",
        status_text="Completed",
        competitor_results=tuple(replace(item, match_points=1) for item in played.competitor_results),
    )
    bye = page.matches[1]
    no_show = replace(
        bye,
        status_text="No Show",
        competitor_results=(SourceCompetitor("participant-101", "No Show", 0),),
    )
    changed_page = replace(page, matches=(page.matches[0], no_show, intentional_draw))
    document = normalize_parsed_snapshot(
        replace(snapshot, pages=(changed_page, snapshot.pages[1])),
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )
    normalized_draw = source_match(document, "match-source-4-played")
    assert normalized_draw["played"] is False
    assert {item["result_type"] for item in normalized_draw["competitors"]} == {"intentional_draw"}
    assert normalized_draw["constructed_statistics_eligible"] is False
    normalized_no_show = source_match(document, "match-source-4")
    assert normalized_no_show["competitors"][0]["result_type"] == "no_show"
    assert normalized_no_show["matchup_eligible"] is False


def test_inconsistent_source_points_block_the_match():
    snapshot = parsed_snapshot()
    page = snapshot.pages[0]
    played = page.matches[2]
    inconsistent = replace(
        played,
        competitor_results=(
            replace(played.competitor_results[0], match_points=0),
            played.competitor_results[1],
        ),
    )
    changed_page = replace(page, matches=(*page.matches[:2], inconsistent))
    document = normalize_parsed_snapshot(
        replace(snapshot, pages=(changed_page, snapshot.pages[1])),
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )
    assert document["quality"]["status"] == "blocked"
    assert {item["code"] for item in document["quality"]["issues"]} == {"unknown_result"}


def test_normalizer_has_no_network_or_statistics_dependency():
    source = (ROOT / "src" / "mtgmeta" / "melee" / "normalize.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "requests." not in source
    assert "from .stats" not in source
    assert "publishable\": True" not in source
