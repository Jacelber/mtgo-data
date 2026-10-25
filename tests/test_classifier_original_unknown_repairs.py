"""Specific omissions explained by card roles, with independent core guards."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/classifier_round1_original_unknown_repairs.json").read_text())["cases"]


@pytest.fixture(scope="module")
def rules():
    return {fmt: load_rule_set(ROOT / "my_archetypes" / f"{fmt}.yaml") for fmt in ("standard", "modern")}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["record_id"])
def test_real_sources_follow_existing_archetype_meanings(rules, case):
    result = classify_deck(rules[case["format"]], case)
    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == tuple(case["expected"])


def test_amalia_core_does_not_require_one_auxiliary_package(rules):
    case = next(c for c in CASES if c["expected"][0] == "amalia-combo" and not any(x["name"] == "Guide of Souls" for x in c["main_deck"]))
    main, side = deck_to_counts(case)
    main.pop("Lunarch Veteran")
    main.pop("Prosperous Innkeeper")
    main["Soul Warden"] = 4
    assert classify_counts(rules["modern"], main, side).archetype_id == "amalia-combo"
    for core in ("Amalia Benavides Aguirre", "Wildgrowth Walker"):
        result = classify_counts(rules["modern"], main | {core: 1}, side | {core: 3})
        assert not any(m.archetype_id == "amalia-combo" for m in result.matched_rules)
    # Preserve the original main-core threshold rather than lowering all counts.
    main |= {"Amalia Benavides Aguirre": 3, "Wildgrowth Walker": 3}
    assert classify_counts(rules["modern"], main, side).archetype_id == "amalia-combo"


def test_mill_routes_still_require_crabs_and_a_substantial_mill_package(rules):
    main = {"Hedron Crab": 2, "Island": 8, "Swamp": 8}
    for package in ({"Archive Trap": 3}, {"Fractured Sanity": 3, "Glimpse the Unthinkable": 3}):
        assert classify_counts(rules["modern"], main | package, {}).archetype_id == "dimir-mill"
        result = classify_counts(rules["modern"], main | package | {"Hedron Crab": 1}, {})
        assert not any(m.archetype_id == "dimir-mill" for m in result.matched_rules)
    for package in ({"Fractured Sanity": 3}, {"Glimpse the Unthinkable": 3}, {"Fractured Sanity": 2, "Glimpse the Unthinkable": 3}):
        result = classify_counts(rules["modern"], main | package, {})
        assert not any(m.archetype_id == "dimir-mill" for m in result.matched_rules)


def test_theorist_route_keeps_its_control_evidence(rules):
    main = {"Countersculpt": 1, "The Theorist, Jace Beleren": 1, "No More Lies": 1,
            "Day of Judgment": 1, "Hallowed Fountain": 1, "Island": 8, "Plains": 8}
    assert classify_counts(rules["standard"], main, {}).archetype_id == "azorius-control"
    assert classify_counts(rules["standard"], main | {"Jace's Machinations": 1}, {}).archetype_id == "azorius-control"
    for core in ("Countersculpt", "The Theorist, Jace Beleren", "No More Lies", "Day of Judgment"):
        result = classify_counts(rules["standard"], {k: v for k, v in main.items() if k != core}, {})
        assert "azorius-control-theorist" not in {m.rule_id for m in result.matched_rules}
