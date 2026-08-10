"""Integration tests for Standard package classification consumers."""

from __future__ import annotations

from pathlib import Path

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.mtgo import stats


ROOT = Path(__file__).resolve().parents[1]
STANDARD_RULES = ROOT / "my_archetypes" / "standard.yaml"
CONFLICT_RULES = ROOT / "tests" / "fixtures" / "rules" / "valid_shared_rules.yaml"


def monument_player():
    return {
        "main_deck": [
            {"name": "Gran-Gran", "qty": 3},
            {"name": "Accumulate Wisdom", "qty": 3},
            {"name": "Monument to Endurance", "qty": 3},
        ],
        "sideboard": [],
    }


def test_loaded_rules_and_full_result_use_package_apis():
    rule_set = load_rule_set(STANDARD_RULES)
    assert len(rule_set.archetypes) == 72
    assert sum(len(archetype.rules) for archetype in rule_set.archetypes) == 82

    result = classify_deck(rule_set, monument_player())
    assert result.status == "classified"
    assert result.archetype_id == "monument-lessons"
    assert result.archetype_name == "Monument Lessons"


def test_standard_stats_process_event_uses_shared_classifier(monkeypatch):
    calls = []
    shared = stats.classify_deck

    def recording_classifier(rule_set, player):
        calls.append(rule_set)
        return shared(rule_set, player)

    monkeypatch.setattr(stats, "classify_deck", recording_classifier)
    event = {
        "player_count": 32,
        "starttime": "2026-01-01T00:00:00Z",
        "description": "Integration fixture",
        "players": [
            dict(monument_player(), swiss_score=12, final_rank=1, player="Fixture")
        ],
    }
    rule_set = load_rule_set(STANDARD_RULES)
    processed = stats.process_event(event, rule_set)
    assert processed["records"][0]["archetype"] == "Monument Lessons"
    assert calls == [rule_set]


def test_selected_subtype_is_available_without_changing_parent_string():
    result = classify_counts(
        load_rule_set(STANDARD_RULES),
        {
            "Kona, Rescue Beastie": 4,
            "Omniscience": 4,
            "Uthros, Titanic Godcore": 3,
        },
        {},
    )
    assert (result.archetype_id, result.subtype_id) == (
        "kona-omniscience",
        "simic",
    )
    assert result.archetype_name == "Kona Omniscience"


def test_conflict_and_invalid_input_are_explicit_package_results():
    rule_set = load_rule_set(CONFLICT_RULES)
    conflict = classify_counts(
        rule_set,
        {"Example Engine": 3, "Example Answer": 4},
        {},
    )
    assert conflict.status == "conflict"
    assert conflict.conflict_kind == "subtype"

    invalid = classify_counts(rule_set, {"Example Threat": True}, {})
    assert invalid.status == "invalid_deck"
