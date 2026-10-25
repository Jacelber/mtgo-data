"""Owner-approved tribal identity with substitutable functional components."""

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


def test_approved_rakdos_goblins_source_and_land_variation(rules):
    case = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_rakdos_goblins.json").read_text())["cases"][0]
    result = classify_deck(rules, case)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "rakdos-goblins", None)
    main, side = deck_to_counts(case)
    main["Swamp"] += main.pop("Blood Crypt") + main.pop("Haunted Ridge") + main.pop("Blazemire Verge")
    assert classify_counts(rules, main, side).archetype_id == "rakdos-goblins"


@pytest.mark.parametrize("payoff", ["Boggart Cursecrafter", "Boggart Mischief"])
@pytest.mark.parametrize("tribal", ["Howlsquad Heavy", "Mudbutton Cursetosser"])
def test_goblin_components_can_vary_but_both_roles_are_required(rules, payoff, tribal):
    main = {payoff: 3, tribal: 3, "Searslicer Goblin": 3, "Mountain": 8, "Swamp": 8}
    assert classify_counts(rules, main, {}).archetype_id == "rakdos-goblins"
    for core in (payoff, tribal):
        result = classify_counts(rules, {k: v for k, v in main.items() if k != core}, {})
        assert not any(m.archetype_id == "rakdos-goblins" for m in result.matched_rules)
    one_of_each = main | {payoff: 1, tribal: 1}
    assert not any(m.archetype_id == "rakdos-goblins" for m in classify_counts(rules, one_of_each, {}).matched_rules)


def test_goblin_colors_still_need_ordinary_support(rules):
    main = {"Boggart Cursecrafter": 3, "Howlsquad Heavy": 3, "Mountain": 12, "Starting Town": 4}
    result = classify_counts(rules, main, {})
    assert not any(m.archetype_id == "rakdos-goblins" for m in result.matched_rules)
    assert classify_counts(rules, main, {"Swamp": 1}).archetype_id == "rakdos-goblins"
    # A generic BR pile with no tribal core cannot become Goblins.
    generic = {"Swamp": 12, "Mountain": 12, "Duress": 4, "Abrade": 4}
    assert not any(m.archetype_id == "rakdos-goblins" for m in classify_counts(rules, generic, {}).matched_rules)


def test_goblins_name_and_mana():
    rows = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(r for r in rows if r["identity_key"] == "standard|rakdos-goblins|none")
    assert (row["english"], row["chinese"]) == ("Rakdos Goblins", "红黑鬼怪")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["rakdos-goblins"] == ("b", "r")
