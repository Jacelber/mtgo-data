"""P6-03 Modern taxonomy and P6-01 difference-contract tests."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for source_path in (ROOT, ROOT / "src"):
    source_text = str(source_path)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)

from mtgmeta.classifier import classify_counts
from mtgmeta.config import load_rule_set


RULE_PATH = ROOT / "my_archetypes" / "modern.yaml"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json"
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "modern" / "taxonomy_contract.json"


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_records():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["records"]


def test_taxonomy_structure_uses_stable_unique_identities_and_mainboard_rules():
    contract = load_contract()
    expected = contract["taxonomy"]
    rules = load_rule_set(RULE_PATH)
    all_rules = [rule for parent in rules.archetypes for rule in parent.rules]
    all_subtypes = [subtype for parent in rules.archetypes for subtype in parent.subtypes]

    assert rules.format == contract["format"] == "modern"
    assert hashlib.sha256(RULE_PATH.read_bytes()).hexdigest() == expected["rules_sha256"]
    assert len(rules.archetypes) == expected["parents_defined"] == 55
    assert len(all_rules) == expected["rules_defined"] == 100
    assert len(all_subtypes) == expected["subtypes_defined"] == 54
    assert len({parent.id for parent in rules.archetypes}) == len(rules.archetypes)
    assert len({rule.id for rule in all_rules}) == len(all_rules)
    assert len({rule.priority for rule in all_rules}) == len(all_rules)
    assert all(condition.zone == "main" for rule in all_rules for condition in rule.conditions)


def test_owner_approved_parent_and_subtype_boundaries_are_explicit():
    rules = load_rule_set(RULE_PATH)
    by_id = {parent.id: parent for parent in rules.archetypes}

    assert "energy" not in by_id
    assert {
        "boros-energy",
        "mardu-energy",
        "jeskai-energy",
        "azorius-energy",
        "selesnya-energy",
        "esper-energy",
    }.issubset(by_id)
    assert {subtype.id for subtype in by_id["broodscale-combo"].subtypes} == {
        "gruul",
        "mono-green",
        "golgari",
    }
    assert {subtype.id for subtype in by_id["prowess"].subtypes} == {
        "izzet",
        "temur",
        "grixis",
        "jeskai",
        "lessons",
    }
    assert {subtype.id for subtype in by_id["eldrazi-tron"].subtypes} == {
        "colorless",
        "mono-green",
        "mono-black",
    }
    assert {subtype.id for subtype in by_id["oculus-ritual"].subtypes} == {
        "sultai",
        "simic",
        "temur",
    }
    assert {subtype.id for subtype in by_id["persist-reanimator"].subtypes} == {
        "grixis",
        "golgari",
        "esper",
    }
    assert {"hardened-scales", "kethis-combo", "valakut"}.isdisjoint(by_id)


def test_full_corpus_matches_the_p6_03_difference_contract():
    contract = load_contract()
    expected = contract["taxonomy"]
    records = load_records()
    record_by_id = {record["id"]: record for record in records}
    rules = load_rule_set(RULE_PATH)
    reordered = replace(rules, archetypes=tuple(reversed(rules.archetypes)))
    parents = Counter()
    subtypes = Counter()
    transitions = Counter()
    multiple_matches = 0
    same_parent_multiple_subtype_matches = 0

    for record in records:
        main = dict(record["main"])
        side = dict(record["side"])
        result = classify_counts(rules, main, side)
        reordered_result = classify_counts(reordered, main, side)
        parent_name = result.archetype_name or "Unknown"
        parents[parent_name] += 1
        transitions[f"{record['expected']} -> {parent_name}"] += 1
        multiple_matches += len(result.matched_rules) > 1
        subtype_ids = {
            match.subtype_id
            for match in result.matched_rules
            if match.archetype_id == result.archetype_id and match.subtype_id is not None
        }
        same_parent_multiple_subtype_matches += len(subtype_ids) > 1
        if result.subtype_id is not None:
            subtypes[f"{result.archetype_id}/{result.subtype_id}"] += 1
        assert result.status in {"classified", "unknown"}
        assert reordered_result.archetype_id == result.archetype_id
        assert reordered_result.subtype_id == result.subtype_id
        assert reordered_result.selected_rule_id == result.selected_rule_id

    assert len(records) == expected["records"] == 5792
    assert parents["Unknown"] == expected["unknown"] == 128
    assert len(records) - parents["Unknown"] == expected["classified"] == 5664
    assert multiple_matches == expected["multiple_matches"] == 1519
    assert (
        same_parent_multiple_subtype_matches
        == expected["same_parent_multiple_subtype_matches"]
        == 132
    )
    assert sum(subtypes.values()) == expected["selected_subtypes"] == 2329
    assert dict(sorted(parents.items())) == contract["selected_parent_counts"]
    assert dict(sorted(subtypes.items())) == contract["selected_subtype_counts"]
    assert dict(sorted(transitions.items())) == contract["baseline_to_taxonomy_transitions"]

    for case in contract["representative_cases"].values():
        record = record_by_id[case["record_id"]]
        result = classify_counts(rules, dict(record["main"]), dict(record["side"]))
        assert result.archetype_id == case["archetype_id"]
        assert result.archetype_name == case["archetype_name"]
        assert result.subtype_id == case["subtype_id"]
        assert result.subtype_name == case["subtype_name"]
        assert result.selected_rule_id == case["selected_rule_id"]
