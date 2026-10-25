"""Owner-approved optional uses, not a global splash-source threshold."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.classifier_cards import deck_colors
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.rules import validate_rule_data

ROOT = Path(__file__).resolve().parents[1]
USES = {"Callous Sell-Sword": "fling_secondary", "Elusive Otter": "fling_secondary"}


@pytest.mark.parametrize("card,land,other,color,primary", [
    ("Callous Sell-Sword", "Blood Crypt", "Duress", "black", "red"),
    ("Elusive Otter", "Breeding Pool", "Nature's Claim", "green", "blue"),
])
@pytest.mark.parametrize("quantity", [0, 1, 2])
def test_optional_uses_are_symmetric_and_do_not_remove_other_spells(card, land, other, color, primary, quantity):
    primary_land = "Mountain" if primary == "red" else "Island"
    main = {card: 4, "Starting Town": 4, "Multiversal Passage": 3, primary_land: 8, land: quantity}
    result = deck_colors(main, {}, uses=USES)
    assert result.colors == {primary}
    contribution = next(c for c in result.contributions if c.card == card)
    assert contribution.reason == f"fling-secondary:optional-face:fixed-sources={quantity}"
    # Both main and side normal spells preserve the shared one-spell rule.
    expected = {primary, color} if quantity else {primary}
    assert deck_colors(main, {other: 1}, uses=USES).colors == expected
    assert deck_colors(main | {other: 1}, {}, uses=USES).colors == expected
    # No exception without explicit family opt-in; an explicit normal use wins.
    assert deck_colors(main, {}).colors == expected
    assert deck_colors(main, {}, uses={card: "normal_cast"}).colors == {primary, color}


@pytest.mark.parametrize("card,land,colors", [
    ("Callous Sell-Sword", "Blood Crypt", {"black", "red"}),
    ("Callous Sell-Sword", "Sulfurous Springs", {"black", "red"}),
    ("Elusive Otter", "Breeding Pool", {"blue", "green"}),
])
def test_established_secondary_casting_is_not_permanently_excluded(card, land, colors):
    result = deck_colors({card: 4, land: 4}, {}, uses=USES)
    assert result.colors == colors


def test_missing_facts_are_not_zero_sources_and_sideboard_uses_follow_same_policy():
    result = deck_colors({"Callous Sell-Sword": 4, "Blood Crypt": 1, "Unregistered Source": 1}, {}, uses=USES)
    assert result.missing == ("Unregistered Source",)
    assert "black" in result.colors
    assert deck_colors({"Breeding Pool": 1}, {"Elusive Otter": 1}, uses=USES).colors == {"blue"}
    assert deck_colors({"Breeding Pool": 1}, {"Elusive Otter": 1, "Nature's Claim": 1}, uses=USES).colors == {"blue", "green"}


@pytest.mark.parametrize("quantity", [3])
def test_intermediate_sources_are_visible_as_unreviewed_not_an_approved_threshold(quantity):
    result = deck_colors({"Callous Sell-Sword": 4, "Blood Crypt": quantity}, {}, uses=USES)
    contribution = next(c for c in result.contributions if c.card == "Callous Sell-Sword")
    assert contribution.reason == f"fling-secondary:unreviewed-source-count:fixed-sources={quantity}"
    assert result.unresolved_uses == ("Callous Sell-Sword",)
    # No classification identity is approved by this diagnostic assertion.


@pytest.fixture(scope="module")
def standard():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


def test_retained_single_source_decks_and_normal_sideboard_splashes(standard):
    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_optional_adventures.json").read_text())["cases"]
    for case in cases:
        main, side = deck_to_counts(case)
        result = classify_deck(standard, case)
        if main.get("Blazemire Verge"):
            assert (result.archetype_id, result.subtype_id) == ("leyline-aggro", "mono-red")
            assert dict(result.color_diagnostics)["leyline-aggro"].colors == {"red"}
            # Same land, one real black spell: existing Rakdos child must win.
            splash = classify_counts(standard, main, side | {"Duress": 1})
            assert (splash.archetype_id, splash.subtype_id) == ("leyline-aggro", "rakdos")
        else:
            assert dict(result.color_diagnostics)["izzet-prowess"].colors == {"blue", "red"}
            splash = classify_counts(standard, main, side | {"Nature's Claim": 1})
            assert dict(splash.color_diagnostics)["izzet-prowess"].colors == {"blue", "red", "green"}


def test_leyline_parent_core_cannot_be_bypassed_and_lands_alone_do_not_choose_child(standard):
    main = {"Leyline of Resonance": 4, "Slickshot Show-Off": 4, "Callous Sell-Sword": 4, "Mountain": 16, "Blazemire Verge": 1}
    assert classify_counts(standard, main, {}).subtype_id == "mono-red"
    assert classify_counts(standard, main | {"Island": 1}, {}).subtype_id == "mono-red"
    assert classify_counts(standard, main | {"Island": 1}, {"Opt": 1}).subtype_id == "izzet"
    for core in ("Leyline of Resonance", "Slickshot Show-Off"):
        result = classify_counts(standard, {k: v for k, v in main.items() if k != core}, {})
        assert not any(m.archetype_id == "leyline-aggro" for m in result.matched_rules)


def test_approved_otter_pair_sources_remain_izzet_and_other_green_is_screened(standard):
    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_otter_pair_sources.json").read_text())["cases"]
    assert len(cases) == 28
    for case in cases:
        result = classify_deck(standard, case)
        assert (result.status, result.archetype_id) == ("classified", "izzet-prowess")
        assert dict(result.color_diagnostics)["izzet-prowess"].colors == {"blue", "red"}
    main, side = deck_to_counts(cases[0])
    result = classify_counts(standard, main, side | {"Nature's Claim": 1})
    assert dict(result.color_diagnostics)["izzet-prowess"].colors == {"blue", "red", "green"}
    assert not any(m.archetype_id == "izzet-prowess" for m in result.matched_rules)
    assert result.archetype_id == "temur-prowess"


def test_approved_standard_temur_prowess_does_not_require_quandrix_charm(standard):
    fixture = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_temur_prowess.json").read_text())
    cases = fixture["cases"]
    for case in cases:
        result = classify_deck(standard, case)
        assert (result.status, result.archetype_id, result.archetype_name) == (
            "classified", "temur-prowess", "Temur Prowess",
        )
        main, side = deck_to_counts(case)
        assert side.get("Quandrix Charm") == 2
        alternative = {k: v for k, v in side.items() if k != "Quandrix Charm"}
        alternative["Nature's Claim"] = 2
        assert classify_counts(standard, main, alternative).archetype_id == "temur-prowess"
    # The same inherited structural definitions apply to both color routes.
    families = {a.id: a for a in standard.archetypes}
    assert [r.conditions for r in families["izzet-prowess"].rules] == [
        r.conditions for r in families["temur-prowess"].rules
    ]
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    name = next(n for n in names if n["identity_key"] == "standard|temur-prowess|none")
    assert (name["english"], name["chinese"]) == ("Temur Prowess", "铁木尔灵技")
    mana = yaml.safe_load((ROOT / "configs/archetype_mana_identities.yaml").read_text())
    assert mana["formats"]["standard"]["approved"]["temur-prowess"] == ["u", "r", "g"]
    # The broad cantrip structure can overlap the established Vitality engine.
    # Preserve its specific family instead of silently reassigning that deck.
    for case in fixture["preserve_cases"]:
        result = classify_deck(standard, case)
        assert result.archetype_id == "temur-otters"
        assert {"temur-otters", "temur-prowess"} <= {m.archetype_id for m in result.matched_rules}


def test_izzet_looting_does_not_catch_a_normal_white_splash(standard):
    main = {"Tiger-Seal": 2, "Duelist of the Mind": 4, "Fear of Missing Out": 4,
            "Island": 10, "Mountain": 10, "Hallowed Fountain": 4}
    assert classify_counts(standard, main, {}).archetype_id == "izzet-looting"
    result = classify_counts(standard, main | {"Practiced Offense": 4}, {})
    assert not any(m.archetype_id == "izzet-looting" for m in result.matched_rules)
    assert dict(result.color_diagnostics)["izzet-looting"].colors == {"white", "blue", "red"}


def test_unsettled_three_source_use_blocks_color_selection_only_when_it_matters(standard):
    main = {"Stormchaser's Talent": 4, "Boomerang Basics": 4,
            "Elusive Otter": 4, "Slickshot Show-Off": 4,
            "Breeding Pool": 3, "Island": 8, "Mountain": 8}
    result = classify_counts(standard, main, {})
    assert result.status == "unknown"
    assert "izzet-prowess: unresolved card uses: Elusive Otter" in result.errors
    with_normal_green = classify_counts(standard, main, {"Nature's Claim": 1})
    assert not dict(with_normal_green.color_diagnostics)["izzet-prowess"].unresolved_uses
    assert not any("unresolved card uses" in error for error in with_normal_green.errors)


def test_optional_mode_rejects_unrelated_cards_and_formats():
    with pytest.raises(ValueError, match="requires Sell-Sword or Otter"):
        deck_colors({"Opt": 1}, {}, uses={"Opt": "fling_secondary"})
    data = yaml.safe_load((ROOT / "my_archetypes/pioneer.yaml").read_text())
    for fmt in ("modern", "pauper"):
        assert any("fling_secondary is limited" in f.message for f in validate_rule_data(data | {"format": fmt}))
