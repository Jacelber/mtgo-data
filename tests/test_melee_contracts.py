import copy
import json
from pathlib import Path

import yaml

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]


def _contracts():
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    return loaded, registry


def _whitelist():
    return yaml.safe_load((ROOT / "configs/melee_events.yaml").read_text(encoding="utf-8"))


def _event_fixture():
    return json.loads((ROOT / "tests/fixtures/melee/reference_event_contract.json").read_text(encoding="utf-8"))


def test_reference_whitelist_contract_is_valid_and_fetch_disabled():
    loaded, registry = _contracts()
    whitelist = _whitelist()
    assert schemas.validate_instance(whitelist, loaded["melee-events.schema.json"], registry) == []
    event = whitelist["events"][0]
    assert event["id"] == "434455"
    assert event["format"] == "modern"
    assert event["structure"] == "mixed"
    assert event["enabled"] is False


def test_enabled_event_requires_verified_review_status():
    loaded, registry = _contracts()
    whitelist = _whitelist()
    whitelist["events"][0]["enabled"] = True
    whitelist["events"][0]["review_status"] = "pending"
    assert schemas.validate_instance(whitelist, loaded["melee-events.schema.json"], registry)
    whitelist["events"][0]["review_status"] = "verified"
    assert schemas.validate_instance(whitelist, loaded["melee-events.schema.json"], registry) == []


def test_whitelist_rejects_wrong_source_and_structure_flags():
    loaded, registry = _contracts()
    whitelist = _whitelist()
    wrong_url = copy.deepcopy(whitelist)
    wrong_url["events"][0]["url"] = "https://example.test/Tournament/View/434455"
    assert schemas.validate_instance(wrong_url, loaded["melee-events.schema.json"], registry)
    wrong_mixed_flag = copy.deepcopy(whitelist)
    wrong_mixed_flag["events"][0]["mixed_format"] = False
    assert schemas.validate_instance(wrong_mixed_flag, loaded["melee-events.schema.json"], registry)


def test_normalized_reference_fixture_passes_contract():
    loaded, registry = _contracts()
    fixture = _event_fixture()
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry) == []


def test_draft_top8_keeps_stage_phase_and_game_format_separate():
    fixture = _event_fixture()
    top8 = next(round_ for round_ in fixture["rounds"] if round_["id"] == "quarterfinals")
    assert top8 == {
        "id": "quarterfinals",
        "source_label": "Quarterfinals",
        "number": None,
        "phase_id": "top8_draft",
        "stage": "playoff",
        "round_phase": "playoff",
        "game_format": "limited",
        "swiss": False,
    }
    playoff_match = next(match for match in fixture["matches"] if match["round_id"] == "quarterfinals")
    assert playoff_match["constructed_statistics_eligible"] is False
    assert playoff_match["matchup_eligible"] is False


def test_unknown_round_requires_explicit_quality_issue():
    loaded, registry = _contracts()
    fixture = _event_fixture()
    fixture["rounds"][0]["round_phase"] = "unknown"
    fixture["rounds"][0]["game_format"] = "unknown"
    failures = schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry)
    assert failures
    fixture["quality"]["status"] = "blocked"
    fixture["quality"]["issues"].append(
        {
            "code": "unknown_round_phase",
            "severity": "error",
            "entity_type": "round",
            "entity_id": "round-1",
            "message": "Fixture round phase is unresolved.",
            "blocking": True,
            "source_evidence": ["fixture"],
        }
    )
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry) == []


def test_unknown_result_requires_explicit_quality_issue():
    loaded, registry = _contracts()
    fixture = _event_fixture()
    fixture["matches"][0]["competitors"][0]["result_type"] = "unknown"
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry)
    fixture["quality"]["status"] = "blocked"
    fixture["quality"]["issues"].append(
        {
            "code": "unknown_result",
            "severity": "error",
            "entity_type": "match",
            "entity_id": "match-round-1",
            "message": "Fixture result is unresolved.",
            "blocking": True,
            "source_evidence": ["fixture"],
        }
    )
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry) == []


def test_normalized_event_requires_provenance_and_blocks_blocked_publication():
    loaded, registry = _contracts()
    fixture = _event_fixture()
    fixture.pop("provenance")
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry)
    fixture = _event_fixture()
    fixture["quality"]["status"] = "blocked"
    fixture["quality"]["publishable"] = True
    assert schemas.validate_instance(fixture, loaded["melee-event.schema.json"], registry)
