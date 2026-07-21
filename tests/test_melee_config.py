import copy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from mtgmeta.melee.config import (
    DisabledMeleeEventError,
    MeleeConfigError,
    UnknownMeleeEventError,
    load_melee_event_registry,
    parse_melee_event_text,
)


ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "configs/melee_events.yaml"


def _source_data():
    return yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))


def _text(data):
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _parse_data(data):
    return parse_melee_event_text(_text(data))


def test_loads_reference_event_for_inspection_without_authorizing_fetch():
    registry = load_melee_event_registry(WHITELIST)
    event = registry.get("434455")
    assert registry.schema_version == "3.0.0"
    assert event.reviewed_overrides == ()
    assert event.format == "modern"
    assert event.structure == "mixed"
    assert event.enabled is False
    assert event.phases[-1].id == "top8_draft"
    assert event.phases[-1].game_format == "limited"
    with pytest.raises(DisabledMeleeEventError, match="disabled for fetching"):
        registry.require_fetchable("434455")


def test_rejects_unknown_or_non_string_event_ids():
    registry = load_melee_event_registry(WHITELIST)
    with pytest.raises(UnknownMeleeEventError, match="not present"):
        registry.get("999999")
    with pytest.raises(UnknownMeleeEventError, match="decimal string"):
        registry.get(434455)  # type: ignore[arg-type]


def test_verified_enabled_event_becomes_fetchable():
    data = _source_data()
    data["events"][0]["enabled"] = True
    registry = _parse_data(data)
    assert registry.require_fetchable("434455").id == "434455"


def test_enabled_event_requires_verified_review_status():
    data = _source_data()
    data["events"][0]["enabled"] = True
    data["events"][0]["review_status"] = "pending"
    with pytest.raises(MeleeConfigError, match="must be verified"):
        _parse_data(data)


def test_rejects_duplicate_yaml_keys():
    text = """schema_version: \"1.0.0\"\nschema_version: \"1.0.0\"\nevents: []\n"""
    with pytest.raises(MeleeConfigError, match="duplicate key"):
        parse_melee_event_text(text)


def test_rejects_duplicate_event_ids_and_url_identity_mismatch():
    data = _source_data()
    data["events"].append(copy.deepcopy(data["events"][0]))
    with pytest.raises(MeleeConfigError, match="duplicate event IDs"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["url"] = "https://melee.gg/Tournament/View/999999"
    with pytest.raises(MeleeConfigError, match="must match the whitelist id"):
        _parse_data(data)


def test_rejects_reversed_dates_and_malformed_source_evidence():
    data = _source_data()
    data["events"][0]["date"] = {"start": "2026-07-20", "end": "2026-07-17"}
    with pytest.raises(MeleeConfigError, match="start must not be after end"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["source_evidence"] = ["http://example.test/evidence"]
    with pytest.raises(MeleeConfigError, match="must be an HTTPS URL"):
        _parse_data(data)


def test_rejects_duplicate_phase_identity_rounds_and_source_labels():
    data = _source_data()
    data["events"][0]["phases"][1]["id"] = "day1_draft"
    with pytest.raises(MeleeConfigError, match="duplicate phase IDs"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["phases"][1]["rounds"][0] = 1
    with pytest.raises(MeleeConfigError, match="one round to multiple phases"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["phases"][0]["source_labels"] = ["Finals"]
    with pytest.raises(MeleeConfigError, match="one source label to multiple phases"):
        _parse_data(data)


def test_rejects_wrong_format_assignments_and_unknown_enabled_phases():
    data = _source_data()
    data["events"][0]["phases"][0]["game_format"] = "modern"
    with pytest.raises(MeleeConfigError, match="draft phases must use limited"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["phases"][1]["game_format"] = "pioneer"
    with pytest.raises(MeleeConfigError, match="constructed phases must use"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["enabled"] = True
    data["events"][0]["phases"][0]["round_phase"] = "unknown"
    data["events"][0]["phases"][0]["game_format"] = "unknown"
    with pytest.raises(MeleeConfigError, match="must not contain unknown"):
        _parse_data(data)


def test_rejects_structure_and_statistics_boundary_mismatches():
    data = _source_data()
    data["events"][0]["mixed_format"] = False
    with pytest.raises(MeleeConfigError, match="must match the event structure"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["statistics"]["constructed_game_format"] = "pioneer"
    with pytest.raises(MeleeConfigError, match="must match the event format"):
        _parse_data(data)
    data = _source_data()
    data["events"][0]["statistics"]["include_playoffs"] = True
    with pytest.raises(MeleeConfigError, match="must be false"):
        _parse_data(data)


def test_returned_models_are_immutable_and_missing_files_are_descriptive(tmp_path):
    registry = load_melee_event_registry(WHITELIST)
    with pytest.raises(FrozenInstanceError):
        registry.events[0].enabled = True  # type: ignore[misc]
    with pytest.raises(MeleeConfigError, match="cannot read whitelist"):
        load_melee_event_registry(tmp_path / "missing.yaml")


def test_reviewed_overrides_require_evidence_and_consistent_results():
    data = _source_data()
    data["events"][0]["reviewed_overrides"] = [
        {
            "id": "official_correction",
            "source_match_id": "match-1",
            "review_status": "verified",
            "played": False,
            "competitors": [
                {
                    "source_participant_id": "player-1",
                    "result_type": "awarded_win_top8_lock",
                    "match_points": 3,
                }
            ],
            "reason": "Official Top 8 lock award.",
            "source_evidence": ["https://magic.gg/example"],
        }
    ]
    event = _parse_data(data).events[0]
    assert event.reviewed_overrides[0].id == "official_correction"

    data["events"][0]["reviewed_overrides"][0]["played"] = True
    with pytest.raises(MeleeConfigError, match="played must agree"):
        _parse_data(data)


def test_top8_lock_override_requires_explicit_event_support():
    data = _source_data()
    data["events"][0]["reviewed_overrides"] = [
        {
            "id": "official_correction",
            "source_match_id": "match-1",
            "review_status": "verified",
            "played": False,
            "competitors": [
                {
                    "source_participant_id": "player-1",
                    "result_type": "awarded_win_top8_lock",
                    "match_points": 3,
                }
            ],
            "reason": "Official Top 8 lock award.",
            "source_evidence": ["https://magic.gg/example"],
        }
    ]
    data["events"][0]["advancement"]["top8_lock_supported"] = False
    with pytest.raises(MeleeConfigError, match="require explicit advancement support"):
        _parse_data(data)


def test_reviewed_override_requires_verified_status_and_consistent_played_points():
    data = _source_data()
    override = {
        "id": "official_correction",
        "source_match_id": "match-1",
        "review_status": "pending",
        "played": True,
        "competitors": [
            {"source_participant_id": "player-1", "result_type": "played_win", "match_points": 3},
            {"source_participant_id": "player-2", "result_type": "played_loss", "match_points": 0},
        ],
        "reason": "Official correction.",
        "source_evidence": ["https://magic.gg/example"],
    }
    data["events"][0]["reviewed_overrides"] = [override]
    with pytest.raises(MeleeConfigError, match="must be verified"):
        _parse_data(data)

    override["review_status"] = "verified"
    override["competitors"][0]["match_points"] = 0
    with pytest.raises(MeleeConfigError, match="points must match"):
        _parse_data(data)
