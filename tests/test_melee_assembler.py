from dataclasses import replace
import json
from pathlib import Path

import pytest

import validate_schemas as schemas
from mtgmeta.melee.assembler import (
    MeleeAssemblyError,
    assemble_parsed_snapshot,
    assemble_raw_snapshot,
)
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.parser import parse_raw_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "source_snapshot"
NORMALIZED_AT = "2026-07-21T13:00:00Z"


def event_definition():
    return load_melee_event_registry(ROOT / "configs" / "melee_events.yaml").events[0]


def parsed_snapshot():
    return parse_raw_snapshot(FIXTURE)


def assembled():
    return assemble_parsed_snapshot(
        parsed_snapshot(),
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )


def test_fixture_assembles_one_schema_valid_blocked_event():
    document = assemble_raw_snapshot(
        FIXTURE,
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(document, loaded["melee-event.schema.json"], registry) == []
    assert document["metadata"]["event_id"] == "434455"
    assert document["event_structure"] == "mixed"
    assert document["quality"]["status"] == "blocked"
    assert document["quality"]["publishable"] is False
    assert {issue["code"] for issue in document["quality"]["issues"]} == {
        "unknown_round_phase",
        "unknown_result",
    }


def test_cross_resource_records_share_stable_participant_ids():
    document = assembled()
    participants = {item["source_id"]: item for item in document["participants"]}
    alpha_id = participants["participant-101"]["id"]
    beta_id = participants["participant-202"]["id"]

    assert {item["participant_id"] for item in document["standings"]} == {alpha_id, beta_id}
    assert {item["participant_id"] for item in document["decklists"]} == {alpha_id, beta_id}
    first_match = next(
        item for item in document["matches"] if item["source_record_id"] == "match-source-1"
    )
    assert [item["participant_id"] for item in first_match["competitors"]] == [alpha_id, beta_id]
    alpha_deck = next(item for item in document["decklists"] if item["participant_id"] == alpha_id)
    beta_deck = next(item for item in document["decklists"] if item["participant_id"] == beta_id)
    assert alpha_deck["status"] == "submitted"
    assert alpha_deck["source_url"] == "https://melee.gg/Decklist/View/9001"
    assert beta_deck == {
        "participant_id": beta_id,
        "game_format": "unknown",
        "status": "missing",
        "cards": [],
        "source_url": None,
    }


def test_assembly_preserves_source_evidence_without_interpreting_semantics():
    document = assembled()
    assert all(participant["status"] == "unknown" for participant in document["participants"])
    assert all(round_["phase_id"] == "unresolved" for round_ in document["rounds"])
    assert all(round_["round_phase"] == "unknown" for round_ in document["rounds"])
    assert all(match["played"] is False for match in document["matches"])
    assert all(match["constructed_statistics_eligible"] is False for match in document["matches"])
    assert all(match["matchup_eligible"] is False for match in document["matches"])
    assert all(
        competitor["result_type"] == "unknown"
        for match in document["matches"]
        for competitor in match["competitors"]
    )
    completed = next(
        item for item in document["matches"] if item["source_record_id"] == "match-source-1"
    )
    bye = next(item for item in document["matches"] if item["source_record_id"] == "match-source-4")
    assert completed["original_result"] == "2-1-0"
    assert "status_text=Completed" in completed["evidence"]
    assert bye["original_result"] == "Bye"
    assert "status_text=Bye" in bye["evidence"]


def test_output_is_deterministic_when_source_page_order_changes():
    snapshot = parsed_snapshot()
    first = assemble_parsed_snapshot(snapshot, event_definition(), normalized_at=NORMALIZED_AT)
    reversed_pages = replace(snapshot, pages=tuple(reversed(snapshot.pages)))
    second = assemble_parsed_snapshot(reversed_pages, event_definition(), normalized_at=NORMALIZED_AT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_internal_unresolved_phase_id_is_reserved():
    event = event_definition()
    changed_phase = replace(event.phases[0], id="unresolved")
    changed_event = replace(event, phases=(changed_phase, *event.phases[1:]))
    with pytest.raises(MeleeAssemblyError, match="reserved"):
        assemble_parsed_snapshot(parsed_snapshot(), changed_event, normalized_at=NORMALIZED_AT)


def test_participant_identity_does_not_depend_on_display_name():
    snapshot = parsed_snapshot()
    tournament_page, decklist_page = snapshot.pages
    changed_standing = replace(tournament_page.standings[0], display_name="Changed Fixture Name")
    changed_page = replace(
        tournament_page,
        standings=(changed_standing, *tournament_page.standings[1:]),
    )
    changed_snapshot = replace(snapshot, pages=(changed_page, decklist_page))
    original = assembled()
    changed = assemble_parsed_snapshot(
        changed_snapshot,
        event_definition(),
        normalized_at=NORMALIZED_AT,
    )
    original_ids = {item["source_id"]: item["id"] for item in original["participants"]}
    changed_ids = {item["source_id"]: item["id"] for item in changed["participants"]}
    assert changed_ids == original_ids
    assert changed["participants"][0]["display_name"] == "Changed Fixture Name"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda page: replace(
                page,
                matches=(replace(page.matches[0], source_round_id="missing-round"), *page.matches[1:]),
            ),
            "unknown round",
        ),
        (
            lambda page: replace(
                page,
                matches=(
                    replace(page.matches[0], competitor_source_ids=("missing-participant",)),
                    *page.matches[1:],
                ),
            ),
            "unknown participants",
        ),
        (
            lambda page: replace(
                page,
                decklist_references=(
                    replace(page.decklist_references[0], source_participant_id="missing-participant"),
                ),
            ),
            "unknown participant",
        ),
    ],
)
def test_dangling_cross_resource_references_fail_closed(mutation, message):
    snapshot = parsed_snapshot()
    changed = replace(snapshot, pages=(mutation(snapshot.pages[0]), snapshot.pages[1]))
    with pytest.raises(MeleeAssemblyError, match=message):
        assemble_parsed_snapshot(changed, event_definition(), normalized_at=NORMALIZED_AT)


def test_decklist_requires_matching_reference_and_owner():
    snapshot = parsed_snapshot()
    tournament_page, decklist_page = snapshot.pages
    without_reference = replace(tournament_page, decklist_references=())
    with pytest.raises(MeleeAssemblyError, match="no source reference"):
        assemble_parsed_snapshot(
            replace(snapshot, pages=(without_reference, decklist_page)),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )

    conflicting_deck = replace(
        decklist_page.decklists[0],
        source_participant_id="participant-202",
    )
    with pytest.raises(MeleeAssemblyError, match="participant conflicts"):
        assemble_parsed_snapshot(
            replace(snapshot, pages=(tournament_page, replace(decklist_page, decklists=(conflicting_deck,)))),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )


def test_conflicting_duplicate_records_across_pages_fail_closed():
    snapshot = parsed_snapshot()
    tournament_page = snapshot.pages[0]
    conflicting = replace(tournament_page.standings[0], rank=2)
    duplicate_page = replace(
        tournament_page,
        tournament=None,
        standings=(conflicting,),
        decklist_references=(),
        rounds=(),
        matches=(),
    )
    with pytest.raises(MeleeAssemblyError, match="conflicting standing records"):
        assemble_parsed_snapshot(
            replace(snapshot, pages=(*snapshot.pages, duplicate_page)),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )


def test_missing_round_population_fails_during_assembly():
    snapshot = parsed_snapshot()
    tournament_page, decklist_page = snapshot.pages
    without_rounds = replace(tournament_page, rounds=(), matches=())
    with pytest.raises(MeleeAssemblyError, match="does not contain round records"):
        assemble_parsed_snapshot(
            replace(snapshot, pages=(without_rounds, decklist_page)),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )


def test_snapshot_and_whitelist_identity_must_match():
    snapshot = parsed_snapshot()
    with pytest.raises(MeleeAssemblyError, match="event ID"):
        assemble_parsed_snapshot(
            replace(snapshot, event_id="999999"),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )
    with pytest.raises(MeleeAssemblyError, match="event URL"):
        assemble_parsed_snapshot(
            replace(snapshot, event_url="https://melee.gg/Tournament/View/999999"),
            event_definition(),
            normalized_at=NORMALIZED_AT,
        )


@pytest.mark.parametrize("value", ["", "2026-07-21T13:00:00", "not-a-date"])
def test_normalized_timestamp_must_be_explicit_and_timezone_aware(value):
    with pytest.raises(MeleeAssemblyError, match="normalized_at"):
        assemble_parsed_snapshot(parsed_snapshot(), event_definition(), normalized_at=value)


def test_assembly_does_not_modify_the_source_snapshot_or_import_network_code():
    before = {path.name: path.read_bytes() for path in FIXTURE.iterdir()}
    assemble_raw_snapshot(FIXTURE, event_definition(), normalized_at=NORMALIZED_AT)
    after = {path.name: path.read_bytes() for path in FIXTURE.iterdir()}
    assert after == before
    source = (ROOT / "src" / "mtgmeta" / "melee" / "assembler.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "requests." not in source
    assert "datetime.now" not in source
