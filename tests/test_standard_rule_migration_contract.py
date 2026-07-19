"""P2-01 migration contract tests for the legacy Standard classifier."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_text = str(ROOT)
if root_text not in sys.path:
    sys.path.insert(0, root_text)

from classify_standard import deck_to_counts, load_rules as load_production_rules, signature_card_met
from mtgmeta.config import load_rule_set
from mtgmeta.legacy_rules import to_legacy_archetypes


CONTRACT_PATH = ROOT / "tests" / "fixtures" / "standard" / "rule_migration_contract.json"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
RULE_PATH = ROOT / "my_archetypes" / "standard.yaml"
CLASSIFIER_PATH = ROOT / "classify_standard.py"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_rules():
    return load_production_rules()


def canonical_digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalized_text_sha256(path):
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def matched_rule_indexes(record, legacy_rules):
    player = {
        "main_deck": [{"name": name, "qty": qty} for name, qty in record["main"]],
        "sideboard": [{"name": name, "qty": qty} for name, qty in record["side"]],
    }
    main, side = deck_to_counts(player)
    return [
        index
        for index, rule in enumerate(legacy_rules)
        if rule.get("signatureCards")
        and all(signature_card_met(card, main, side) for card in rule["signatureCards"])
    ]


def test_contract_identity_and_phase_1_baseline_remains_frozen_after_migration():
    contract = load_contract()
    baseline = contract["legacy_baseline"]
    assert contract["schema_version"] == "1.0.0"
    assert contract["format"] == "standard"
    assert baseline["tag"] == "phase-1-standard-baseline"
    assert baseline["commit"] == "baf71f4522447b85e30c8c9cb37455e034d27259"
    production = load_rule_set(RULE_PATH)
    assert production.schema_version == "1.0.0"
    assert production.format == "standard"
    assert normalized_text_sha256(RULE_PATH) != baseline["production_rule_content_sha256"]
    assert baseline["legacy_classifier_content_sha256"] == "a69753e60a493ec7775112fa9c378d48dec06fef9cb2b99d737b6353398e437d"
    assert normalized_text_sha256(CORPUS_PATH) == baseline["frozen_corpus_content_sha256"]


def test_all_legacy_rules_have_one_stable_complete_mapping():
    contract = load_contract()
    legacy_rules = load_rules()
    mappings = contract["rules"]
    assert len(legacy_rules) == len(mappings) == 76
    assert [mapping["legacy_index"] for mapping in mappings] == list(range(76))
    assert len({mapping["rule_id"] for mapping in mappings}) == 76
    assert all(ID_PATTERN.fullmatch(mapping["archetype_id"]) for mapping in mappings)
    assert all(ID_PATTERN.fullmatch(mapping["rule_id"]) for mapping in mappings)
    for index, (legacy, mapping) in enumerate(zip(legacy_rules, mappings, strict=True)):
        assert mapping["legacy_index"] == index
        assert mapping["legacy_display_name"] == legacy["name"]
        assert mapping["priority"] == (76 - index) * 10
        assert mapping["legacy_signature_sha256"] == canonical_digest(legacy["signatureCards"])


def test_versioned_production_rules_implement_every_frozen_identity_and_priority():
    contract = load_contract()
    rule_set = load_rule_set(RULE_PATH)
    actual_archetypes = {archetype.id: archetype for archetype in rule_set.archetypes}
    actual_rules = {
        rule.id: (archetype.id, rule)
        for archetype in rule_set.archetypes
        for rule in archetype.rules
    }

    assert len(actual_archetypes) == 74
    assert len(actual_rules) == 76
    assert set(actual_archetypes) == {item["id"] for item in contract["archetypes"]}
    assert set(actual_rules) == {item["rule_id"] for item in contract["rules"]}

    for expected in contract["archetypes"]:
        actual = actual_archetypes[expected["id"]]
        assert (actual.name, actual.priority) == (
            expected["legacy_display_name"], expected["priority"]
        )
        assert [(item.id, item.name) for item in actual.subtypes] == [
            (item["id"], item["name"]) for item in expected["subtypes"]
        ]

    for expected in contract["rules"]:
        archetype_id, actual = actual_rules[expected["rule_id"]]
        assert archetype_id == expected["archetype_id"]
        assert actual.priority == expected["priority"]
        expected_subtype = expected["subtype"]
        assert actual.subtype_id == (
            None if expected_subtype is None else expected_subtype["id"]
        )


def test_legacy_adapter_uses_explicit_priority_not_yaml_collection_order():
    rule_set = load_rule_set(RULE_PATH)
    reordered = replace(
        rule_set,
        archetypes=tuple(
            replace(archetype, rules=tuple(reversed(archetype.rules)))
            for archetype in reversed(rule_set.archetypes)
        ),
    )
    assert to_legacy_archetypes(reordered) == to_legacy_archetypes(rule_set)


def test_archetype_and_subtype_scope_is_exactly_the_owner_approved_migration():
    contract = load_contract()
    archetypes = contract["archetypes"]
    mappings = contract["rules"]
    assert len(archetypes) == 74
    assert len({item["id"] for item in archetypes}) == 74
    assert contract["approved_initial_subtype_groups"] == ["4-color-control", "izzet-aggro"]

    subtype_mappings = [mapping for mapping in mappings if mapping["subtype"] is not None]
    assert {(mapping["archetype_id"], mapping["subtype"]["id"]) for mapping in subtype_mappings} == {
        ("4-color-control", "inevitable-defeat"),
        ("4-color-control", "rakshasas-bargain"),
        ("izzet-aggro", "razorkin-needlehead"),
        ("izzet-aggro", "hired-claw"),
    }
    assert all(ID_PATTERN.fullmatch(mapping["subtype"]["id"]) for mapping in subtype_mappings)
    assert len({mapping["rule_id"] for mapping in subtype_mappings}) == 4
    assert all(
        mapping["subtype"] is None
        for mapping in mappings
        if mapping["archetype_id"] not in contract["approved_initial_subtype_groups"]
    )
    archetype_subtypes = {item["id"]: item["subtypes"] for item in archetypes}
    assert len(archetype_subtypes["4-color-control"]) == 2
    assert len(archetype_subtypes["izzet-aggro"]) == 2
    assert all(
        subtypes == []
        for archetype_id, subtypes in archetype_subtypes.items()
        if archetype_id not in contract["approved_initial_subtype_groups"]
    )


def test_explicit_priorities_preserve_all_3936_parent_archetypes_and_quality_counts():
    contract = load_contract()
    mappings = contract["rules"]
    legacy_rules = load_rules()
    records = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["records"]
    parent_differences = []
    unknown = 0
    multiple = 0
    maximum_matches = 0
    selected_subtypes = Counter()
    same_parent_multi_subtype = 0

    for record in records:
        indexes = matched_rule_indexes(record, legacy_rules)
        maximum_matches = max(maximum_matches, len(indexes))
        multiple += len(indexes) > 1
        if not indexes:
            unknown += 1
            selected_name = "Unknown"
        else:
            candidates = [mappings[index] for index in reversed(indexes)]
            selected = max(candidates, key=lambda item: item["priority"])
            selected_name = selected["legacy_display_name"]
            if selected["subtype"] is not None:
                selected_subtypes[f"{selected['archetype_id']}/{selected['subtype']['id']}"] += 1
            subtype_matches = defaultdict(set)
            for index in indexes:
                match = mappings[index]
                if match["subtype"] is not None:
                    subtype_matches[match["archetype_id"]].add(match["subtype"]["id"])
            same_parent_multi_subtype += any(len(values) > 1 for values in subtype_matches.values())
        if selected_name != record["expected"]:
            parent_differences.append((record["id"], record["expected"], selected_name))

    assert len(records) == 3936
    assert parent_differences == []
    assert unknown == 71
    assert multiple == 947
    assert maximum_matches == 3
    assert dict(sorted(selected_subtypes.items())) == contract["observed_subtype_selection_counts"] == {
        "4-color-control/inevitable-defeat": 1,
        "4-color-control/rakshasas-bargain": 4,
        "izzet-aggro/hired-claw": 32,
        "izzet-aggro/razorkin-needlehead": 8,
    }
    assert same_parent_multi_subtype == contract["same_archetype_multiple_subtype_match_records"] == 21
    expected_baseline_counts = {
        "records": 3936,
        "rules": 76,
        "archetypes": 74,
        "unknown": 71,
        "multiple_matches": 947,
        "maximum_matches_per_deck": 3,
        "parent_archetype_differences": 0,
    }
    assert {
        key: contract["legacy_baseline"][key]
        for key in expected_baseline_counts
    } == expected_baseline_counts


def test_contract_contains_no_player_or_deck_records():
    contract_text = CONTRACT_PATH.read_text(encoding="utf-8")
    contract = json.loads(contract_text)
    assert "records" not in contract
    assert all("player" not in mapping and "deck" not in mapping for mapping in contract["rules"])
    assert len(contract_text) < 100_000
