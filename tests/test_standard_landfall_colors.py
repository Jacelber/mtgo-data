"""Approved Landfall identity and legal variations, not replay-derived answers."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.mana_identity import rendered_mana_identities, require_complete_mana_identities

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


@pytest.fixture
def source():
    return json.loads((ROOT / "tests/fixtures/classifier_round1_standard_golgari_landfall.json").read_text())["cases"][0]


def test_approved_golgari_source_and_normal_splash_variations(rules, source):
    result = classify_deck(rules, source)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "golgari-landfall", None)
    main, side = deck_to_counts(source)
    without_spell = {k: v for k, v in side.items() if k != "Dark Knight's Greatsword"}
    assert classify_counts(rules, main, without_spell).archetype_id == "mono-green-landfall"
    without_land = {k: v for k, v in side.items() if k != "Swamp"}
    assert classify_counts(rules, main, without_land).archetype_id == "mono-green-landfall"
    assert classify_counts(rules, main, without_land | {"Starting Town": 4}).archetype_id == "mono-green-landfall"
    assert classify_counts(rules, main, without_spell | {"Duress": 1}).archetype_id == "golgari-landfall"
    assert classify_counts(rules, main, without_land | {"Overgrown Tomb": 1}).archetype_id == "golgari-landfall"
    assert classify_counts(rules, main | {"Swamp": 1}, without_land).archetype_id == "golgari-landfall"


@pytest.mark.parametrize("core,below", [("Mightform Harmonizer", 0), ("Sazh's Chocobo", 3), ("Fabled Passage", 3), ("Earthbender Ascension", 2)])
def test_golgari_cannot_bypass_existing_structure(rules, source, core, below):
    main, side = deck_to_counts(source)
    main[core] = below
    result = classify_counts(rules, main, side)
    assert not any(m.archetype_id == "golgari-landfall" for m in result.matched_rules)


def test_golgari_names_mana_and_shared_structure():
    data = yaml.safe_load((ROOT / "my_archetypes/standard.yaml").read_text())
    # The source YAML is a sequence of archetypes under the format ruleset.
    parents = data["archetypes"]
    conditions = [p["rules"][0]["conditions"] for p in parents if p["id"] in {"mono-green-landfall", "gruul-landfall", "golgari-landfall"}]
    assert len(conditions) == 3
    assert conditions[0] == conditions[1] == conditions[2]
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "standard|golgari-landfall|none")
    assert (row["english"], row["chinese"]) == ("Golgari Landfall", "黑绿地落")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["golgari-landfall"] == ("b", "g")


@pytest.fixture
def naya_source():
    return json.loads((ROOT / "tests/fixtures/classifier_round1_standard_naya_landfall.json").read_text())["cases"][0]


def test_approved_naya_source_and_normal_splash_variations(rules, naya_source):
    result = classify_deck(rules, naya_source)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "naya-landfall", None)
    main, side = deck_to_counts(naya_source)
    without_spell = {k: v for k, v in side.items() if k != "Fire Magic"}
    without_land = {k: v for k, v in side.items() if k != "Mountain"}
    assert classify_counts(rules, main, without_spell).archetype_id == "selesnya-landfall"
    assert classify_counts(rules, main, without_land).archetype_id == "selesnya-landfall"
    assert classify_counts(rules, main, without_land | {"Starting Town": 4}).archetype_id == "selesnya-landfall"
    assert classify_counts(rules, main, without_spell | {"Abrade": 1}).archetype_id == "naya-landfall"
    assert classify_counts(rules, main, without_land | {"Stomping Ground": 1}).archetype_id == "naya-landfall"
    assert classify_counts(rules, main | {"Mountain": 1}, without_land).archetype_id == "naya-landfall"


@pytest.mark.parametrize("core,below", [("Sazh's Chocobo", 3), ("Fabled Passage", 3), ("Earthbender Ascension", 2)])
def test_naya_cannot_bypass_primary_structure(rules, naya_source, core, below):
    main, side = deck_to_counts(naya_source)
    result = classify_counts(rules, main | {core: below}, side)
    assert not any(m.archetype_id == "naya-landfall" for m in result.matched_rules)


def test_naya_reuses_existing_sideboard_route_without_adding_primary_thresholds(rules):
    main = {"Earthbender Ascension": 1, "Mossborn Hydra": 1, "Icetill Explorer": 1, "Fabled Passage": 1, "Forest": 12, "Plains": 1}
    side = {"Sheltered by Ghosts": 1}
    assert classify_counts(rules, main, side).archetype_id == "selesnya-landfall"
    side |= {"Mountain": 1, "Abrade": 1}
    assert classify_counts(rules, main, side).archetype_id == "naya-landfall"
    for core in ("Earthbender Ascension", "Mossborn Hydra", "Icetill Explorer", "Fabled Passage"):
        result = classify_counts(rules, {k: v for k, v in main.items() if k != core}, side)
        assert not any(m.archetype_id == "naya-landfall" for m in result.matched_rules)
    result = classify_counts(rules, main, {k: v for k, v in side.items() if k != "Sheltered by Ghosts"})
    assert not any(m.archetype_id == "naya-landfall" for m in result.matched_rules)


def test_naya_names_mana_and_shared_branches():
    data = yaml.safe_load((ROOT / "my_archetypes/standard.yaml").read_text())
    parents = {p["id"]: p for p in data["archetypes"]}
    naya = parents["naya-landfall"]["rules"]
    selesnya = parents["selesnya-landfall"]["rules"]
    assert naya[0]["conditions"] == selesnya[0]["conditions"] == selesnya[1]["conditions"]
    assert naya[1]["conditions"] == selesnya[2]["conditions"]
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "standard|naya-landfall|none")
    assert (row["english"], row["chinese"]) == ("Naya Landfall", "纳雅地落")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["naya-landfall"] == ("w", "r", "g")
