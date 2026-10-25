"""Owner-approved WUBG Lotus child, requiring normal spells and ordinary lands."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/classifier_round1_pioneer_wubg_lotus.json").read_text())["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/pioneer.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["record_id"])
def test_reviewed_decks_and_white_spell_substitution(rules, case):
    result = classify_deck(rules, case)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "lotus-scapeshift", "wubg")
    main, side = deck_to_counts(case)
    main.pop("Kenrith, the Returned King", None)
    assert classify_counts(rules, main, side).subtype_id == "wubg"
    # Dedicated white lands alone do not select WUBG. The normal spell need
    # not be one of the currently observed white tools.
    side.pop("Clarion Conqueror", None)
    side.pop("High Noon", None)
    assert classify_counts(rules, main, side).subtype_id == "sultai"
    assert classify_counts(rules, main, side | {"Get Lost": 1}).subtype_id == "wubg"


def test_wubg_child_cannot_bypass_lotus_parent_core(rules):
    main, side = deck_to_counts(CASES[0])
    for core in ("Lotus Field", "Scapeshift", "Spelunking"):
        without = {k: v for k, v in main.items() if k != core}
        assert not any(m.archetype_id == "lotus-scapeshift" for m in classify_counts(rules, without, side).matched_rules)


def test_rainbow_only_white_stays_sultai_and_normal_white_source_adds_color(rules):
    main = {"Lotus Field": 4, "Scapeshift": 4, "Spelunking": 4,
            "The Wandering Minstrel": 4, "Breeding Pool": 4,
            "Underground Mortuary": 1, "Starting Town": 4}
    assert classify_counts(rules, main, {}).subtype_id == "simic"
    side = {"Duress": 1, "Clarion Conqueror": 1}
    assert classify_counts(rules, main, side).subtype_id == "sultai"
    for land in ("Plains", "Lush Portico", "Urban Retreat"):
        result = classify_counts(rules, main | {land: 1}, side)
        assert (result.archetype_id, result.subtype_id) == ("lotus-scapeshift", "wubg")


def test_approved_name_and_rendered_white_blue_black_green():
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "pioneer|lotus-scapeshift|wubg")
    assert (row["english"], row["chinese"]) == ("WUBG Lotus Scapeshift", "四色变境（无红）")
    require_complete_mana_identities(ROOT, "pioneer")
    assert rendered_mana_identities(ROOT, "pioneer")["lotus-scapeshift/wubg"] == ("w", "u", "b", "g")
