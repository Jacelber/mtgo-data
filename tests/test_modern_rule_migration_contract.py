"""P6-01 compatibility tests for the pinned j6e Modern rule baseline."""

from __future__ import annotations

import hashlib
import json
import re
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


CONTRACT_PATH = ROOT / "tests" / "fixtures" / "modern" / "rule_migration_contract.json"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json"
RULE_PATH = ROOT / "tests" / "fixtures" / "modern" / "p6_01_rules.yaml"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RECORD_ID_PATTERN = re.compile(r"^modern-baseline-[0-9]{4}$")


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def text_sha256(path):
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def canonical_digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_shape(rule):
    conditions = []
    for condition in rule.conditions:
        item = {"name": condition.card}
        if condition.exact_count is not None:
            item["exactCopies"] = condition.exact_count
        else:
            item["minCopies"] = condition.min_count
        conditions.append(item)
    return conditions


def test_pinned_upstream_identity_and_frozen_input_contract():
    contract = load_contract()
    upstream = contract["upstream_reference"]
    snapshot = contract["source_snapshot"]

    assert contract["schema_version"] == "1.0.0"
    assert contract["format"] == "modern"
    assert upstream["repository"] == "https://github.com/j6e/mtg-meta-analyzer"
    assert upstream["commit"] == "0ecd26bd734cedc6c40e7c753115f796613a32ba"
    assert upstream["rule_path"] == "data/archetypes/modern.yaml"
    assert upstream["rule_date"] == "2026-07-08"
    assert upstream["rule_content_sha256"] == "8fe5a21cdff855d515cea47a92f928810157c7255aefb996d3b70ff2f9910655"
    assert upstream["content_license"] == "CC BY 4.0"
    assert snapshot["repository_commit"] == "cb1a510dc8e03472ea16b18c95630eac0ee3d6fe"
    assert snapshot["eligible_format"] == "CMODERN"
    assert snapshot["eligible_event_files"] == 181
    assert snapshot["excluded_format_event_files"] == {"CPREMODERN": 2}
    assert snapshot["records"] == 5792
    assert snapshot["eligible_date_min"] == "2026-04-01"
    assert snapshot["eligible_date_max"] == "2026-07-20"
    assert text_sha256(CORPUS_PATH) == snapshot["frozen_corpus_content_sha256"]
    assert text_sha256(RULE_PATH) == contract["production_rule_content_sha256"]


def test_every_upstream_rule_has_one_stable_complete_shared_mapping():
    contract = load_contract()
    mappings = contract["rules"]
    rule_set = load_rule_set(RULE_PATH)
    actual = {
        rule.id: (archetype, rule)
        for archetype in rule_set.archetypes
        for rule in archetype.rules
    }

    assert len(mappings) == len(rule_set.archetypes) == len(actual) == 38
    assert [item["source_index"] for item in mappings] == list(range(38))
    assert len({item["archetype_id"] for item in mappings}) == 38
    assert len({item["rule_id"] for item in mappings}) == 38

    for mapping in mappings:
        archetype, rule = actual[mapping["rule_id"]]
        expected_priority = (
            mapping["signature_condition_count"] * 1000
            + (38 - mapping["source_index"]) * 10
        )
        assert ID_PATTERN.fullmatch(mapping["archetype_id"])
        assert ID_PATTERN.fullmatch(mapping["rule_id"])
        assert archetype.id == mapping["archetype_id"]
        assert archetype.name == mapping["display_name"]
        assert archetype.priority == rule.priority == mapping["priority"] == expected_priority
        assert archetype.subtypes == ()
        assert rule.subtype_id is None
        assert len(rule.conditions) == mapping["signature_condition_count"]
        assert all(condition.zone == "main" for condition in rule.conditions)
        assert canonical_digest(source_shape(rule)) == mapping["source_signature_sha256"]


def test_priorities_encode_most_conditions_then_upstream_order_without_ties():
    contract = load_contract()
    mappings = contract["rules"]
    priorities = [item["priority"] for item in mappings]

    assert len(priorities) == len(set(priorities))
    for left in mappings:
        for right in mappings:
            expected = (
                left["signature_condition_count"],
                -left["source_index"],
            ) > (
                right["signature_condition_count"],
                -right["source_index"],
            )
            assert (left["priority"] > right["priority"]) == expected


def test_full_frozen_corpus_preserves_all_parent_results_and_quality_counts():
    contract = load_contract()
    expected_quality = contract["compatibility_result"]
    records = load_corpus()["records"]
    rule_set = load_rule_set(RULE_PATH)
    reordered = replace(rule_set, archetypes=tuple(reversed(rule_set.archetypes)))
    selected_counts = Counter()
    differences = []
    multiple_matches = 0
    maximum_matches = 0

    for record in records:
        main = dict(record["main"])
        side = dict(record["side"])
        result = classify_counts(rule_set, main, side)
        reordered_result = classify_counts(reordered, main, side)
        actual = result.archetype_name or "Unknown"
        selected_counts[actual] += 1
        multiple_matches += len(result.matched_rules) > 1
        maximum_matches = max(maximum_matches, len(result.matched_rules))
        if actual != record["expected"]:
            differences.append((record["id"], record["expected"], actual))
        assert reordered_result.archetype_name == result.archetype_name
        assert reordered_result.selected_rule_id == result.selected_rule_id
        assert result.status in {"classified", "unknown"}
        assert result.subtype_id is None

    assert len(records) == expected_quality["records"] == 5792
    assert differences == []
    assert selected_counts["Unknown"] == expected_quality["unknown"] == 635
    assert len(records) - selected_counts["Unknown"] == expected_quality["classified"] == 5157
    assert multiple_matches == expected_quality["multiple_matches"] == 324
    assert maximum_matches == expected_quality["maximum_matches_per_deck"] == 3
    assert dict(sorted(selected_counts.items())) == expected_quality["selected_counts"]
    assert expected_quality["parent_archetype_differences"] == 0
    assert expected_quality["subtypes_defined"] == 0
    assert set(selected_counts) == {
        "Unknown",
        *(item["display_name"] for item in contract["rules"]),
    }


def test_mainboard_scope_does_not_promote_sideboard_only_signature_cards():
    rule_set = load_rule_set(RULE_PATH)
    main_result = classify_counts(rule_set, {"Living End": 3}, {})
    side_result = classify_counts(rule_set, {}, {"Living End": 3})

    assert main_result.archetype_name == "Living End"
    assert side_result.status == "unknown"
    assert side_result.archetype_name is None


def test_centroid_fallback_and_new_subtypes_are_outside_p6_01():
    contract = load_contract()
    semantics = contract["reference_semantics"]
    rule_set = load_rule_set(RULE_PATH)

    assert semantics["card_scope"] == "mainboard_only"
    assert semantics["winner_resolution"] == (
        "greatest signature-condition count, then earliest upstream list position"
    )
    assert semantics["centroid_fallback_migrated"] is False
    assert semantics["unmatched_result"] == "Unknown"
    assert all(not archetype.subtypes for archetype in rule_set.archetypes)
    assert all(
        rule.subtype_id is None
        for archetype in rule_set.archetypes
        for rule in archetype.rules
    )


def test_frozen_corpus_is_deidentified_and_contains_only_synthetic_records():
    corpus = load_corpus()
    records = corpus["records"]

    assert set(corpus) == {"schema_version", "format", "privacy", "records"}
    assert corpus["schema_version"] == "1.0.0"
    assert corpus["format"] == "modern"
    assert len(records) == 5792
    assert all(set(record) == {"id", "main", "side", "expected"} for record in records)
    assert all(RECORD_ID_PATTERN.fullmatch(record["id"]) for record in records)
    assert len({record["id"] for record in records}) == len(records)
    assert all(
        isinstance(card, str) and isinstance(quantity, int) and quantity >= 0
        for record in records
        for zone in ("main", "side")
        for card, quantity in record[zone]
    )
    forbidden_keys = {"player", "loginid", "decklist", "event", "source", "standing"}
    assert all(forbidden_keys.isdisjoint(record) for record in records)
