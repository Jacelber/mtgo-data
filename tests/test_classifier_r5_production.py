from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import (
    _record_counts,
    diagnostic_flags,
    identity_signature,
    load_frozen_records,
    reordered_rule_set,
)
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from tools.build_classifier_r5_production_rules import (
    ACCEPTED_SHADOW_HASHES,
    BASELINE_HASHES,
    BASELINE_ROOT,
    EXPECTED_INVENTORIES,
    MANIFEST_PATH,
    MANIFEST_SHA256,
    PRODUCTION_ROOT,
    SHADOW_ROOT,
    accepted_shadow_document,
    render_production_rules,
    sha256_path,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FROZEN = {
    "modern": Counter(classified=5792),
    "standard": Counter(classified=3928, unknown=8),
}


def _corpus_path(format_id: str) -> Path:
    if format_id == "modern":
        return ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json"
    return ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"


def _standard_event_player(event_id: str, player_index: int) -> dict[str, object]:
    event_path = next((ROOT / "data" / "standard").glob(f"*_{event_id}.json"))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    return event["players"][player_index]


@pytest.mark.parametrize("format_id", ["modern", "standard"])
def test_production_preserves_r5_plus_authorized_standard_boundary(
    format_id: str,
) -> None:
    production_path = PRODUCTION_ROOT / f"{format_id}.yaml"
    shadow_path = SHADOW_ROOT / f"{format_id}.yaml"
    assert sha256_path(shadow_path) == ACCEPTED_SHADOW_HASHES[format_id]
    assert sha256_path(BASELINE_ROOT / f"{format_id}.yaml") == BASELINE_HASHES[format_id]
    assert sha256_path(MANIFEST_PATH) == MANIFEST_SHA256
    expected = deepcopy(accepted_shadow_document(format_id))
    if format_id == "standard":
        spellementals = next(
            item
            for item in expected["archetypes"]
            if item["id"] == "izzet-spellementals"
        )
        rule = next(
            item
            for item in spellementals["rules"]
            if item["id"] == "izzet-spellementals-primary"
        )
        rule["conditions"]["all"].append(
            {
                "card": "Stormchaser's Talent",
                "zone": "main",
                "exact_count": 0,
            }
        )
    else:
        assert production_path.read_bytes() == shadow_path.read_bytes()
        assert production_path.read_text(encoding="utf-8") == render_production_rules(
            format_id
        )
    assert yaml.safe_load(production_path.read_text(encoding="utf-8")) == expected

    rules = load_rule_set(production_path)
    assert (
        len(rules.archetypes),
        sum(len(item.subtypes) for item in rules.archetypes),
        sum(len(item.rules) for item in rules.archetypes),
    ) == EXPECTED_INVENTORIES[format_id]


@pytest.mark.parametrize("format_id", ["modern", "standard"])
def test_production_frozen_corpus_is_order_stable_and_fail_closed(
    format_id: str,
) -> None:
    rules = load_rule_set(PRODUCTION_ROOT / f"{format_id}.yaml")
    reordered = reordered_rule_set(rules)
    statuses: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    records = load_frozen_records(_corpus_path(format_id))

    for record in records:
        main, side = _record_counts(record)
        actual = classify_counts(rules, main, side)
        assert identity_signature(actual) == identity_signature(
            classify_counts(reordered, main, side)
        )
        statuses[actual.status] += 1
        flags.update(
            name
            for name, enabled in diagnostic_flags(actual, rules).items()
            if enabled
        )

    assert statuses == EXPECTED_FROZEN[format_id]
    assert flags["conflict"] == 0
    assert flags["invalid_deck"] == 0
    assert flags["residual_subtype"] == 0


def test_protected_event_434455_source_hash_is_unchanged() -> None:
    event_path = ROOT / "data" / "modern" / "melee" / "events" / "434455.json"
    assert sha256(event_path.read_bytes()).hexdigest() == (
        "0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710"
    )


def test_standard_spellementals_excludes_mainboard_talent_only() -> None:
    rules = load_rule_set(PRODUCTION_ROOT / "standard.yaml")

    for player_index in (9, 25):
        main, side = deck_to_counts(_standard_event_player("12851116", player_index))
        result = classify_counts(rules, main, side)
        assert result.archetype_id == "izzet-prowess"
        assert result.selected_rule_id == "izzet-prowess-primary"
        assert "izzet-spellementals-primary" not in {
            match.rule_id for match in result.matched_rules
        }

    main, side = deck_to_counts(_standard_event_player("12845647", 21))
    result = classify_counts(rules, main, side)
    assert main.get("Stormchaser's Talent", 0) == 0
    assert side.get("Stormchaser's Talent", 0) == 2
    assert result.archetype_id == "izzet-spellementals"
    assert result.selected_rule_id == "izzet-spellementals-primary"
