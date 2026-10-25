"""Approved Esper parent; existing control structures and Azorius identities."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/pioneer.yaml")


@pytest.mark.parametrize("suffix,spells,side,azorius_child", [
    ("primary", {"Teferi, Hero of Dominaria": 1, "No More Lies": 1}, {}, "non-yorion"),
    ("yorion-primary", {"Teferi, Hero of Dominaria": 1, "No More Lies": 1}, {"Yorion, Sky Nomad": 1}, "yorion"),
    ("yorion-dovins-veto", {"Teferi, Hero of Dominaria": 1, "Dovin's Veto": 1}, {"Yorion, Sky Nomad": 1}, "yorion"),
    ("no-teferi-non-yorion", {"No More Lies": 1, "The Wandering Emperor": 1, "March of Otherworldly Light": 1}, {}, "non-yorion"),
    ("no-teferi-yorion", {"No More Lies": 1, "The Wandering Emperor": 1, "March of Otherworldly Light": 1}, {"Yorion, Sky Nomad": 1}, "yorion"),
])
def test_shared_routes_preserve_azorius_and_accept_normal_black(rules, suffix, spells, side, azorius_child):
    main = {"Island": 8, "Plains": 8, "Swamp": 1} | spells
    ordinary = classify_counts(rules, main, side)
    assert (ordinary.archetype_id, ordinary.subtype_id) == ("azorius-control", azorius_child)
    for m, s in ((main | {"Duress": 1}, side), (main, side | {"Duress": 1})):
        result = classify_counts(rules, m, s)
        assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "esper-control", None)
        assert result.selected_rule_id == "esper-control-" + suffix
    # Neither ordinary black lands alone nor rainbow-only black casting changes
    # the existing Azorius identity.
    unsupported = {k: v for k, v in main.items() if k != "Swamp"}
    result = classify_counts(rules, unsupported | {"Starting Town": 4}, side | {"Duress": 1})
    assert (result.archetype_id, result.subtype_id) == ("azorius-control", azorius_child)


def test_source_and_no_teferi_variant_keep_approved_parent(rules):
    case = json.loads((ROOT / "tests/fixtures/classifier_round1_pioneer_esper_control.json").read_text())
    result = classify_deck(rules, case)
    assert (result.status, result.archetype_id, result.archetype_name, result.subtype_id) == (
        "classified", "esper-control", "Esper Control", None,
    )
    main, side = deck_to_counts(case)
    del main["Teferi, Hero of Dominaria"]
    result = classify_counts(rules, main, side)
    assert result.archetype_id == "esper-control"
    assert result.selected_rule_id == "esper-control-no-teferi-non-yorion"


def test_color_does_not_replace_structure_and_shared_conditions_are_identical(rules):
    families = {a.id: a for a in rules.archetypes}
    assert [r.conditions for r in families["azorius-control"].rules] == [r.conditions for r in families["esper-control"].rules]
    unrelated = {"Island": 8, "Plains": 8, "Swamp": 8,
                 "Opt": 4, "Thraben Inspector": 4, "Duress": 4}
    result = classify_counts(rules, unrelated, {})
    assert not any(m.archetype_id == "esper-control" for m in result.matched_rules)


def test_approved_esper_name_and_rendered_mana():
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "pioneer|esper-control|none")
    assert (row["english"], row["chinese"]) == ("Esper Control", "艾斯波控制")
    existing = next(n for n in names if n["identity_key"] == "pioneer|azorius-control|yorion")
    assert (existing["english"], existing["chinese"]) == ("Yorion Azorius Control", "约力昂蓝白控")
    require_complete_mana_identities(ROOT, "pioneer")
    assert rendered_mana_identities(ROOT, "pioneer")["esper-control"] == ("w", "u", "b")
