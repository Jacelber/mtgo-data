"""P2-06 tests for routing legacy Standard entry points through the shared classifier."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import classify_standard
import cluster_unknown
import dump_unknown_highperf
import event_report
import stats_matchup
import stats_standard
from mtgmeta.config import load_rule_set
from mtgmeta.legacy_rules import LegacyArchetypeRules, to_legacy_archetypes


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


def test_loaded_legacy_view_retains_rule_set_and_shared_full_result():
    rules = classify_standard.load_rules()
    assert isinstance(rules, LegacyArchetypeRules)
    assert len(rules) == 76
    assert len(rules.rule_set.archetypes) == 74

    main, side = classify_standard.deck_to_counts(monument_player())
    result = classify_standard.classify_standard_result(main, side, rules)
    assert result.status == "classified"
    assert result.archetype_id == "monument-lessons"
    assert result.archetype_name == "Monument Lessons"
    assert classify_standard.match_archetype(main, side, rules) == "Monument Lessons"


def test_compatibility_match_calls_shared_classifier(monkeypatch):
    calls = []
    shared = classify_standard.classify_counts

    def recording_classifier(rule_set, main, side):
        calls.append((rule_set, main, side))
        return shared(rule_set, main, side)

    monkeypatch.setattr(classify_standard, "classify_counts", recording_classifier)
    rules = classify_standard.load_rules()
    main, side = classify_standard.deck_to_counts(monument_player())
    assert classify_standard.match_archetype(main, side, rules) == "Monument Lessons"
    assert len(calls) == 1
    assert calls[0][0] is rules.rule_set


def test_standard_stats_process_event_uses_shared_compatibility_path(monkeypatch):
    calls = []
    shared = classify_standard.classify_counts

    def recording_classifier(rule_set, main, side):
        calls.append(rule_set)
        return shared(rule_set, main, side)

    monkeypatch.setattr(classify_standard, "classify_counts", recording_classifier)
    event = {
        "player_count": 32,
        "starttime": "2026-01-01T00:00:00Z",
        "description": "Integration fixture",
        "players": [dict(monument_player(), swiss_score=12, final_rank=1, player="Fixture")],
    }
    rules = classify_standard.load_rules()
    processed = stats_standard.process_event(event, rules)
    assert processed["records"][0]["archetype"] == "Monument Lessons"
    assert calls == [rules.rule_set]


def test_selected_subtype_is_available_without_changing_parent_string():
    rules = classify_standard.load_rules()
    main = {
        "Scalding Viper": 3,
        "Razorkin Needlehead": 3,
        "Spirebluff Canal": 1,
    }
    result = classify_standard.classify_standard_result(main, {}, rules)
    assert (result.archetype_id, result.subtype_id) == (
        "izzet-aggro",
        "razorkin-needlehead",
    )
    assert classify_standard.match_archetype(main, {}, rules) == "Izzet Aggro"


def test_conflict_and_invalid_input_fail_explicitly_in_legacy_string_api():
    rules = to_legacy_archetypes(load_rule_set(CONFLICT_RULES))
    with pytest.raises(classify_standard.StandardClassificationConflict) as conflict:
        classify_standard.match_archetype(
            {"Example Engine": 3, "Example Answer": 4},
            {},
            rules,
        )
    assert conflict.value.result.status == "conflict"
    assert conflict.value.result.conflict_kind == "subtype"

    with pytest.raises(classify_standard.StandardInvalidDeck) as invalid:
        classify_standard.match_archetype({"Example Threat": True}, {}, rules)
    assert invalid.value.result.status == "invalid_deck"


def test_plain_legacy_lists_remain_supported_for_external_compatibility():
    rules = [
        {"name": "Legacy", "signatureCards": [{"name": "Card", "minCopies": 2}]}
    ]
    assert classify_standard.match_archetype({"Card": 2}, {}, rules) == "Legacy"
    assert classify_standard.match_archetype({"Card": 1}, {}, rules) is None


def test_auxiliary_entry_points_share_the_central_match_function():
    assert event_report.match_archetype is classify_standard.match_archetype
    assert stats_standard.match_archetype is classify_standard.match_archetype
    assert stats_matchup.match_archetype is classify_standard.match_archetype
    rules = classify_standard.load_rules()
    main, side = classify_standard.deck_to_counts(monument_player())
    assert cluster_unknown.is_unknown(main, side, rules) is False
    assert dump_unknown_highperf.is_unknown(main, side, rules) is False
