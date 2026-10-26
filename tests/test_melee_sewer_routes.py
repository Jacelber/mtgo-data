"""Reviewed Sydney lists and independent parent-core/color boundaries."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/modern/melee_414849_sewer.json").read_text())["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/modern.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["player"])
def test_retained_sewer_routes(rules, case):
    result = classify_deck(rules, case)
    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == tuple(case["expected"])


@pytest.mark.parametrize("core", ["Sewer-veillance Cam", "Grinding Station"])
def test_emry_route_cannot_bypass_shared_core(rules, core):
    main, side = deck_to_counts(CASES[0])
    main.pop(core)
    result = classify_counts(rules, main, side)
    assert not any(m.archetype_id == "sewer-combo" for m in result.matched_rules)


def test_emry_route_uses_shared_sideboard_colors(rules):
    main, side = deck_to_counts(CASES[0])
    result = classify_counts(rules, main | {"Breeding Pool": 1}, side)
    assert (result.archetype_id, result.subtype_id) == ("sewer-combo", "mono-blue")
    result = classify_counts(rules, main | {"Breeding Pool": 1}, side | {"Nature's Claim": 1})
    assert (result.archetype_id, result.subtype_id) == ("sewer-combo", "simic")


def test_optional_urza_and_key_are_not_required(rules):
    main, side = deck_to_counts(CASES[0])
    main.pop("Urza, Lord High Artificer")
    main.pop("Key to the Side-Door")
    result = classify_counts(rules, main, side)
    assert (result.archetype_id, result.subtype_id) == ("sewer-combo", "mono-blue")
