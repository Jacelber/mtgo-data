"""P2-05 tests for full-match shared classification and diagnostics."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.classifier import classify_counts, classify_deck, evaluate_matches
from mtgmeta.config import load_rule_set


RULE_FIXTURE = ROOT / "tests" / "fixtures" / "rules" / "valid_shared_rules.yaml"
STANDARD_RULES = ROOT / "my_archetypes" / "standard.yaml"
CORPUS = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"


def fixture_rules():
    return load_rule_set(RULE_FIXTURE)


def test_all_conditions_zones_and_bounds_must_match_with_evidence():
    rules = fixture_rules()
    matches = evaluate_matches(
        rules,
        {"Example Engine": 2, "Example Answer": 3},
        {"Example Answer": 1},
    )
    assert [match.rule_id for match in matches] == [
        "example-control-artifacts",
        "example-control-core",
    ]
    artifact, core = matches
    assert artifact.evidence[0].actual_count == 2
    assert (artifact.evidence[0].min_count, artifact.evidence[0].max_count) == (2, 4)
    assert core.evidence[0].actual_count == 4
    assert core.evidence[0].exact_count == 4

    assert evaluate_matches(rules, {"Example Engine": 5}, {}) == ()
    assert evaluate_matches(rules, {"Example Answer": 3}, {}) == ()
    assert [item.rule_id for item in evaluate_matches(rules, {}, {"Example Threat": 1})] == [
        "example-aggro-core"
    ]


def test_unknown_and_invalid_decks_are_distinct_sanitized_results():
    rules = fixture_rules()
    unknown = classify_counts(rules, {"Unrecognized": 4}, {})
    assert unknown.status == "unknown"
    assert unknown.archetype_id is None
    assert unknown.matched_rules == ()
    assert unknown.errors == ()

    invalid = classify_counts(rules, {"Example Threat": True}, {})
    assert invalid.status == "invalid_deck"
    assert invalid.errors == ("main: card quantities must be non-negative integers",)
    malformed = classify_deck(rules, {"main_deck": [{"qty": 1}]})
    assert malformed.status == "invalid_deck"
    assert malformed.errors == ("deck: cannot normalize input (KeyError)",)
    assert classify_deck(rules, None).errors == ("deck: must be a mapping",)


def test_higher_priority_selects_identity_and_retains_overridden_matches():
    result = classify_counts(
        fixture_rules(),
        {"Example Engine": 3, "Example Threat": 1},
        {},
    )
    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == (
        "example-control",
        "artifact-build",
    )
    assert result.selected_rule_id == "example-control-artifacts"
    assert [item.rule_id for item in result.matched_rules] == [
        "example-control-artifacts",
        "example-aggro-core",
    ]
    assert [item.rule_id for item in result.overridden_matches] == [
        "example-aggro-core"
    ]
    assert result.conflict_matches == ()


def test_equal_priority_parent_archetypes_are_not_silently_selected():
    rules = fixture_rules()
    aggro = rules.archetypes[1]
    tied_aggro = replace(
        aggro,
        rules=(replace(aggro.rules[0], priority=100),),
    )
    tied_rules = replace(rules, archetypes=(rules.archetypes[0], tied_aggro))
    result = classify_counts(
        tied_rules,
        {"Example Engine": 3, "Example Threat": 1},
        {},
    )
    assert result.status == "conflict"
    assert result.conflict_kind == "parent_archetype"
    assert result.archetype_id is None
    assert result.selected_rule_id is None
    assert {item.archetype_id for item in result.conflict_matches} == {
        "example-control",
        "example-aggro",
    }


def test_equal_priority_subtypes_preserve_parent_but_report_conflict():
    result = classify_counts(
        fixture_rules(),
        {"Example Engine": 3, "Example Answer": 4},
        {},
    )
    assert result.status == "conflict"
    assert result.conflict_kind == "subtype"
    assert result.archetype_id == "example-control"
    assert result.subtype_id is None
    assert result.selected_rule_id is None
    assert {item.subtype_id for item in result.conflict_matches} == {
        "artifact-build",
        None,
    }


def test_equivalent_identity_tie_is_deterministic_and_diagnostic():
    rules = fixture_rules()
    control = rules.archetypes[0]
    equivalent = replace(
        control.rules[1],
        subtype_id="artifact-build",
    )
    equivalent_rules = replace(
        rules,
        archetypes=(replace(control, rules=(control.rules[0], equivalent)), rules.archetypes[1]),
    )
    result = classify_counts(
        equivalent_rules,
        {"Example Engine": 3, "Example Answer": 4},
        {},
    )
    assert result.status == "classified"
    assert result.priority_tie is True
    assert result.conflict_kind is None
    assert result.selected_rule_id == "example-control-artifacts"
    assert len(result.top_priority_matches) == 2


def test_rule_and_archetype_collection_order_do_not_change_results():
    rules = fixture_rules()
    reversed_rules = replace(
        rules,
        archetypes=tuple(
            replace(archetype, rules=tuple(reversed(archetype.rules)))
            for archetype in reversed(rules.archetypes)
        ),
    )
    main = {"Example Engine": 3, "Example Threat": 1}
    assert classify_counts(reversed_rules, main, {}) == classify_counts(rules, main, {})


def test_standard_corpus_preserves_parent_results_quality_and_subtypes():
    rule_set = load_rule_set(STANDARD_RULES)
    records = json.loads(CORPUS.read_text(encoding="utf-8"))["records"]
    unknown = 0
    multiple = 0
    maximum = 0
    parent_differences = []
    selected_subtypes = Counter()
    same_parent_multiple_subtypes = 0

    for record in records:
        deck = {
            "main_deck": [
                {"name": name, "qty": quantity} for name, quantity in record["main"]
            ],
            "sideboard": [
                {"name": name, "qty": quantity} for name, quantity in record["side"]
            ],
        }
        result = classify_deck(rule_set, deck)
        maximum = max(maximum, len(result.matched_rules))
        multiple += len(result.matched_rules) > 1
        if result.status == "unknown":
            unknown += 1
            actual = "Unknown"
        else:
            assert result.status == "classified", record["id"]
            actual = result.archetype_name
            if result.subtype_id is not None:
                selected_subtypes[f"{result.archetype_id}/{result.subtype_id}"] += 1

        subtype_matches = defaultdict(set)
        for match in result.matched_rules:
            if match.subtype_id is not None:
                subtype_matches[match.archetype_id].add(match.subtype_id)
        same_parent_multiple_subtypes += any(
            len(subtypes) > 1 for subtypes in subtype_matches.values()
        )
        if actual != record["expected"]:
            parent_differences.append((record["id"], record["expected"], actual))

    assert len(records) == 3936
    assert parent_differences == []
    assert unknown == 71
    assert multiple == 947
    assert maximum == 3
    assert dict(sorted(selected_subtypes.items())) == {
        "4-color-control/inevitable-defeat": 1,
        "4-color-control/rakshasas-bargain": 4,
        "izzet-aggro/hired-claw": 32,
        "izzet-aggro/razorkin-needlehead": 8,
    }
    assert same_parent_multiple_subtypes == 21
