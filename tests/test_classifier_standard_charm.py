"""Owner-approved Frog use; adventure-face decisions remain separate."""

import json
from pathlib import Path

from mtgmeta.classifier import classify_deck
from mtgmeta.classifier_cards import deck_colors
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.rules import validate_rule_data

ROOT = Path(__file__).resolve().parents[1]


def frog(colors, name="Poison Dart Frog"):
    return next(c for c in colors.contributions if c.card == name)


def test_standard_fling_charm_is_scoped_and_does_not_delete_green():
    main = {
        "Callous Sell-Sword": 3,
        "Slickshot Show-Off": 4,
        "Wild Ride": 4,
        "Starting Town": 4,
        "Opt": 4,
        "Forest": 1,
        "Island": 8,
        "Mountain": 8,
    }
    side = {"Poison Dart Frog": 1}
    result = deck_colors(main, side, profile="standard-fling")
    assert not frog(result).colors
    assert frog(result).reason == "standard-fling:sideboard-charm"
    assert "green" not in result.colors
    assert "green" in deck_colors(main, side).colors
    # One real green spell still contributes; the exception is per card use.
    result = deck_colors(main, side | {"Nature's Claim": 1}, profile="standard-fling")
    assert "green" in result.colors
    assert not frog(result).colors
    # A different shell, main-deck Frog or more copies is outside this approval.
    for m, s in (
        ({k: v for k, v in main.items() if k != "Callous Sell-Sword"}, side),
        (main | {"Poison Dart Frog": 1}, {}),
        (main, {"Poison Dart Frog": 2}),
    ):
        assert frog(deck_colors(m, s, profile="standard-fling")).colors == ("green",)
    assert frog(deck_colors(
        main, side, profile="standard-fling", uses={"Poison Dart Frog": "normal_cast"}
    )).colors == ("green",)


def test_retained_standard_frog_decks_use_the_approved_profile_without_player_identity():
    rules = load_rule_set(ROOT / "my_archetypes/standard.yaml")
    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_charm.json").read_text())["cases"]
    for case in cases:
        result = classify_deck(rules, case)
        colors = dict(result.color_diagnostics)[case["parent_id"]]
        name = case.get("charm_card", "Poison Dart Frog")
        assert frog(colors, name).reason == "standard-fling:sideboard-charm"
        assert not frog(colors, name).colors
        # Subsequent Owner approval separately excludes the optional adventure
        # colors with zero/one extra source; Frog approval itself never did so.
        assert colors.colors == {"blue", "red"}
        renamed = classify_deck(rules, case | {"player": "unrelated-player"})
        assert renamed == result
        # These retained decks have only rainbow support for the charm color.
        # The corrected shared policy now excludes it even without this profile.
        main, side = deck_to_counts(case)
        default = deck_colors(main, side)
        assert not frog(default, name).colors
        assert frog(default, name).reason == "sideboard-without-land-color-support"
        # The explicitly approved use still matters when a dedicated land is
        # present: default casting counts it, the scoped charm use does not.
        land = "Plains" if name == "Quintorius Kand" else "Forest"
        supported = main | {land: 1}
        assert frog(deck_colors(supported, side), name).colors == tuple(case.get("charm_default_colors", ["green"]))
        assert not frog(deck_colors(supported, side, profile="standard-fling"), name).colors


def test_butler_charm_does_not_erase_normal_green_or_extend_to_multiple_charms():
    main = {"Callous Sell-Sword": 4, "Slickshot Show-Off": 4, "Wild Ride": 4, "Starting Town": 4, "Forest": 1, "Mountain": 8}
    side = {"Frog Butler": 1}
    assert not frog(deck_colors(main, side, profile="standard-fling"), "Frog Butler").colors
    result = deck_colors(main, side | {"Nature's Claim": 1}, profile="standard-fling")
    assert "green" in result.colors
    assert not frog(result, "Frog Butler").colors
    for m, s in ((main | side, {}), (main, {"Frog Butler": 2}), (main, side | {"Poison Dart Frog": 1})):
        assert frog(deck_colors(m, s, profile="standard-fling"), "Frog Butler").colors == ("green",)


def test_quintorius_charm_does_not_erase_normal_white_or_main_deck_use():
    main = {"Callous Sell-Sword": 4, "Slickshot Show-Off": 4, "Wild Ride": 4, "Starting Town": 4, "Plains": 1, "Mountain": 8}
    side = {"Quintorius Kand": 1}
    result = deck_colors(main, side | {"Rest in Peace": 1}, profile="standard-fling")
    assert "white" in result.colors
    assert not frog(result, "Quintorius Kand").colors
    for m, s in ((main | side, {}), (main, {"Quintorius Kand": 2})):
        assert frog(deck_colors(m, s, profile="standard-fling"), "Quintorius Kand").colors == ("white", "red")


def test_standard_profile_cannot_be_copied_into_other_formats():
    import yaml

    data = yaml.safe_load((ROOT / "my_archetypes/standard.yaml").read_text())
    for fmt in ("modern", "pauper", "pioneer"):
        failures = validate_rule_data(data | {"format": fmt})
        assert any(f.message == "profile is Standard-only" for f in failures)
