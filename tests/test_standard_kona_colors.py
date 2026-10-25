"""Retained Kona decks and independent normal-color/core variations."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.mana_identity import rendered_mana_identities, require_complete_mana_identities

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_kona.json").read_text())["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["record_id"])
def test_retained_kona_identity(rules, case):
    result = classify_deck(rules, case)
    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == tuple(case["expected"])


def test_sultai_normal_black_is_not_tied_to_a_wish_card_or_land_name(rules):
    case = next(c for c in CASES if c["expected"][1] == "sultai")
    main, side = deck_to_counts(case)
    without_black = {k: v for k, v in main.items() if k != "Extrapolate the Impossible"}
    assert classify_counts(rules, without_black, side).subtype_id == "simic"
    assert classify_counts(rules, without_black, side | {"Duress": 1}).subtype_id == "sultai"
    without_black["Swamp"] = without_black.pop("Watery Grave")
    assert classify_counts(rules, without_black, side | {"Duress": 1}).subtype_id == "sultai"
    without_source = {k: v for k, v in main.items() if k not in {"Watery Grave", "Susur Secundi, Void Altar"}}
    assert classify_counts(rules, without_source, side).subtype_id == "simic"


@pytest.mark.parametrize("subtype,spell,land", [("simic", "Opt", "Island"), ("temur", "Abrade", "Mountain"), ("bant", "Get Lost", "Plains"), ("sultai", "Duress", "Swamp")])
def test_all_kona_color_branches_inherit_main_core(rules, subtype, spell, land):
    main = {"Kona, Rescue Beastie": 3, "Omniscience": 3, "Uthros, Titanic Godcore": 3, "Forest": 8, "Island": 8}
    side = {spell: 1, land: 1}
    result = classify_counts(rules, main, side)
    assert (result.archetype_id, result.subtype_id) == ("kona-omniscience", subtype)
    for core in ("Kona, Rescue Beastie", "Omniscience"):
        result = classify_counts(rules, main | {core: 2}, side | {core: 1})
        assert not any(m.archetype_id == "kona-omniscience" for m in result.matched_rules)
    result = classify_counts(rules, main | {"Kona, Rescue Beastie": 1, "Omniscience": 1}, side)
    assert not any(m.archetype_id == "kona-omniscience" for m in result.matched_rules)


def test_sultai_kona_metadata():
    rows = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(r for r in rows if r["identity_key"] == "standard|kona-omniscience|sultai")
    assert (row["english"], row["chinese"]) == ("Sultai Kona Omniscience", "苏勒台全知")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["kona-omniscience/sultai"] == ("u", "b", "g")


def test_four_color_kona_uses_white_spells_not_a_specific_land(rules):
    case = next(c for c in CASES if c["expected"][1] == "four-color")
    main, side = deck_to_counts(case)
    without_voice = {k: v for k, v in main.items() if k != "Voice of Victory"}
    without_side_voice = {k: v for k, v in side.items() if k != "Voice of Victory"}
    assert classify_counts(rules, without_voice, without_side_voice).subtype_id == "temur"
    assert classify_counts(rules, without_voice, without_side_voice | {"Get Lost": 1}).subtype_id == "four-color"
    without_white_source = {k: v for k, v in side.items() if k != "Adagia, Windswept Bastion"}
    assert classify_counts(rules, main, without_white_source).subtype_id == "temur"
    assert classify_counts(rules, main, without_white_source | {"Plains": 1}).subtype_id == "four-color"
    for core in ("Kona, Rescue Beastie", "Omniscience"):
        result = classify_counts(rules, main | {core: 1}, side)
        assert not any(m.archetype_id == "kona-omniscience" for m in result.matched_rules)
    rows = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(r for r in rows if r["identity_key"] == "standard|kona-omniscience|four-color")
    assert (row["english"], row["chinese"]) == ("Four-Color Kona Omniscience", "四色全知")
    assert rendered_mana_identities(ROOT, "standard")["kona-omniscience/four-color"] == ("w", "u", "r", "g")
