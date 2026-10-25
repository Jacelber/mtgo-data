"""Owner-approved Jeskai Looting and the shared existing looting core."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/classifier_round1_standard_jeskai_looting.json").read_text()
)["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


def test_approved_source_and_independent_white_spell_substitution(rules):
    for case in CASES:
        result = classify_deck(rules, case)
        assert (result.status, result.archetype_id, result.archetype_name) == (
            "classified", "jeskai-looting", "Jeskai Looting",
        )
        assert dict(result.color_diagnostics)["jeskai-looting"].colors == {"white", "blue", "red"}
        main, side = deck_to_counts(case)
        # This family is not defined by the observed white payoff's name.
        main = {k: v for k, v in main.items() if k != "Practiced Offense"}
        side = {k: v for k, v in side.items() if k not in {"Sage of the Skies", "Sheltered by Ghosts"}}
        assert classify_counts(rules, main | {"Rest in Peace": 4}, side).archetype_id == "jeskai-looting"


def test_lands_alone_do_not_add_white_but_one_normal_sideboard_spell_does(rules):
    main = {"Tiger-Seal": 2, "Duelist of the Mind": 4, "Fear of Missing Out": 4,
            "Island": 10, "Mountain": 10, "Hallowed Fountain": 4}
    assert classify_counts(rules, main, {}).archetype_id == "izzet-looting"
    assert classify_counts(rules, main, {"Rest in Peace": 1}).archetype_id == "jeskai-looting"
    alternate = {k: v for k, v in main.items() if k != "Hallowed Fountain"}
    assert classify_counts(rules, alternate | {"Plains": 4}, {"Rest in Peace": 1}).archetype_id == "jeskai-looting"


def test_both_families_inherit_the_same_required_core(rules):
    families = {a.id: a for a in rules.archetypes}
    assert families["jeskai-looting"].conditions == families["izzet-looting"].conditions
    main, side = deck_to_counts(CASES[0])
    for card in ("Tiger-Seal", "Duelist of the Mind", "Fear of Missing Out"):
        result = classify_counts(rules, {k: v for k, v in main.items() if k != card}, side)
        assert not any(m.archetype_id in {"jeskai-looting", "izzet-looting"} for m in result.matched_rules)


def test_approved_chinese_name_and_mana_identity():
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    name = next(n for n in names if n["identity_key"] == "standard|jeskai-looting|none")
    assert (name["english"], name["chinese"], name["review_status"]) == (
        "Jeskai Looting", "洁斯凯滤牌", "approved",
    )
    mana = yaml.safe_load((ROOT / "configs/archetype_mana_identities.yaml").read_text())
    assert mana["formats"]["standard"]["approved"]["jeskai-looting"] == ["w", "u", "r"]
