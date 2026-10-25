"""Production integration of shared colors; fixtures are retained source decks.

Expected identities follow the agreed normal-spell/supported-sideboard policy
and existing named categories. They are not a frozen copy of replay output.
"""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.classifier_cards import deck_colors
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/classifier_round1_other_formats.json").read_text()
)["cases"]


@pytest.fixture(scope="module")
def rules():
    return {
        fmt: load_rule_set(ROOT / "my_archetypes" / f"{fmt}.yaml")
        for fmt in ("standard", "pauper", "pioneer", "modern")
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["record_id"])
def test_retained_decks_follow_normal_casting_policy(case, rules):
    if "expected_colors" in case:
        colors = deck_colors(*deck_to_counts(case))
        assert colors.colors == set(case["expected_colors"])
        frog = next(c for c in colors.contributions if c.card == "Poison Dart Frog")
        assert frog.reason == "sideboard-without-land-color-support"
    if "expected" in case:
        result = classify_deck(rules[case["format"]], case)
        assert result.status == "classified"
        assert (result.archetype_id, result.subtype_id) == tuple(case["expected"])
        assert result.color_diagnostics  # Production really evaluated colors.


def test_manufacturing_one_supported_sideboard_spell_changes_subtype(rules):
    main = {"Weapons Manufacturing": 3, "United Battlefront": 3, "Plains": 10, "Mountain": 10}
    classify = lambda m, s: classify_counts(rules["standard"], m, s)
    assert classify(main, {}).subtype_id == "boros"
    assert classify(main | {"Swamp": 1}, {}).subtype_id == "boros"
    assert classify(main, {"Duress": 1}).subtype_id == "boros"
    assert classify(main | {"Swamp": 1}, {"Duress": 1}).subtype_id == "mardu"
    for core in ("Weapons Manufacturing", "United Battlefront"):
        without_core = {k: v for k, v in main.items() if k != core}
        result = classify(without_core | {"Swamp": 1}, {"Duress": 1})
        assert not any(m.archetype_id == "boros-manufacturing" for m in result.matched_rules)


def test_dwarves_color_is_independent_of_named_dual_land(rules):
    main = {"Dwarven Mauler": 4, "Dwalin, Weaponmaster": 4, "Drake Hatcher": 1, "Mountain": 15}
    for land in ("Steam Vents", "Island", "Riverpyre Verge"):
        result = classify_counts(rules["standard"], main | {land: 1}, {})
        assert (result.archetype_id, result.subtype_id) == ("dwarves", "izzet")


def test_gardens_red_splash_does_not_require_vandalblast(rules):
    main = {"Khalni Garden": 3, "Fanatical Offering": 3, "Crypt Rats": 1, "Brave the Wilds": 1, "Swamp": 10, "Mountain": 1}
    ordinary = classify_counts(rules["pauper"], main, {})
    splash = classify_counts(rules["pauper"], main, {"Cast into the Fire": 1})
    assert (ordinary.archetype_id, ordinary.subtype_id) == ("golgari-gardens", "golgari")
    assert (splash.archetype_id, splash.subtype_id) == ("golgari-gardens", "jund")
    for core in ("Khalni Garden", "Fanatical Offering"):
        result = classify_counts(rules["pauper"], {k: v for k, v in main.items() if k != core}, {"Cast into the Fire": 1})
        assert not any(m.archetype_id == "golgari-gardens" for m in result.matched_rules)


def test_lotus_uses_spells_not_black_land_inventory(rules):
    main = {"Lotus Field": 4, "Scapeshift": 4, "Spelunking": 4, "The Wandering Minstrel": 4, "Breeding Pool": 4, "Underground Mortuary": 1}
    ordinary = classify_counts(rules["pioneer"], main, {})
    splash = classify_counts(rules["pioneer"], main, {"Duress": 1})
    assert (ordinary.archetype_id, ordinary.subtype_id) == ("lotus-scapeshift", "simic")
    assert (splash.archetype_id, splash.subtype_id) == ("lotus-scapeshift", "sultai")
    for core in ("Lotus Field", "Scapeshift", "Spelunking"):
        result = classify_counts(rules["pioneer"], {k: v for k, v in main.items() if k != core}, {"Duress": 1})
        assert not any(m.archetype_id == "lotus-scapeshift" for m in result.matched_rules)


def test_real_pioneer_frog_deck_uses_production_color_profile(rules):
    case = next(c for c in CASES if c["format"] == "pioneer" and "expected_colors" in c)
    result = classify_deck(rules["pioneer"], case)
    assert result.archetype_id == "rakdos-leyline"
    assert dict(result.color_diagnostics)["rakdos-leyline"].colors == {"black", "red"}


def test_owner_confirmed_sellsword_only_black_spell_remains_rakdos(rules):
    cases = json.loads(
        (ROOT / "tests/fixtures/classifier_round1_sellsword_black_use.json").read_text()
    )["cases"]
    for case in cases:
        main, side = deck_to_counts(case)
        assert main["Blood Crypt"] == 4
        # Same-color land substitutions must not turn this into a card-name rule.
        alternate = {k: v for k, v in main.items() if k != "Blood Crypt"}
        alternate["Sulfurous Springs"] = 4
        for counts in (main, alternate):
            result = classify_counts(rules["pioneer"], counts, side)
            assert (result.status, result.archetype_id) == ("classified", "rakdos-leyline")
            colors = dict(result.color_diagnostics)["rakdos-leyline"]
            assert colors.colors == {"black", "red"}
            assert {c.card for c in colors.contributions if "black" in c.colors} == {"Callous Sell-Sword"}


def test_pioneer_creativity_target_exception_keeps_other_black_spells(rules):
    case = next(c for c in CASES if c.get("expected") == ["temur-creativity", None])
    main, side = deck_to_counts(case)
    before = classify_counts(rules["pioneer"], main, side)
    colors = dict(before.color_diagnostics)["temur-creativity"]
    assert colors.colors == {"blue", "red", "green"}
    assert "black" not in deck_colors(main, side).colors
    # The target exception still matters if an ordinary black source is added;
    # rainbow-only support now independently fails the shared default.
    supported = main | {"Swamp": 1}
    assert "black" in deck_colors(supported, side).colors
    assert "black" not in dict(classify_counts(rules["pioneer"], supported, side).color_diagnostics)["temur-creativity"].colors
    after = classify_counts(rules["pioneer"], main | {"Swamp": 1}, side | {"Duress": 1})
    assert "black" in dict(after.color_diagnostics)["temur-creativity"].colors
    assert not any(m.archetype_id == "temur-creativity" for m in after.matched_rules)


def test_color_sources_alone_cannot_satisfy_old_synthetic_color_contracts(rules):
    main = {"Sazh's Chocobo": 4, "Fabled Passage": 4, "Earthbender Ascension": 3, "Temple Garden": 1}
    result = classify_counts(rules["standard"], main, {})
    assert result.archetype_id != "selesnya-landfall"
    result = classify_counts(rules["standard"], main | {"Sheltered by Ghosts": 1}, {})
    assert result.archetype_id == "selesnya-landfall"


def test_landfall_uses_normal_red_spells_instead_of_three_named_dual_lands(rules):
    case = json.loads((ROOT / "tests/fixtures/classifier_round1_gruul_landfall.json").read_text())
    main, side = deck_to_counts(case)
    assert main.get("Stomping Ground", 0) < 3
    result = classify_counts(rules["standard"], main, side)
    assert result.archetype_id == "gruul-landfall"
    # The same mana base without its red spell is green, not automatically Gruul.
    quantity = main.pop("Full Bore")
    main["Snakeskin Veil"] = main.get("Snakeskin Veil", 0) + quantity
    result = classify_counts(rules["standard"], main, side)
    assert result.archetype_id == "mono-green-landfall"


def test_approved_orzhov_screech_uses_shared_colors_and_original_core(rules):
    import yaml
    from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_pauper_orzhov_screech.json").read_text())["cases"]
    assert len(cases) == 5
    for case in cases:
        result = classify_deck(rules["pauper"], case)
        assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "battle-screech", "orzhov")
        main, side = deck_to_counts(case)
        # No named black spell, land or splash quantity is a new prerequisite.
        main["Swamp"] = main.pop("Orzhov Basilica")
        side = {k: v for k, v in side.items() if k not in {"Arms of Hadar", "Thorn of the Black Rose"}}
        result = classify_counts(rules["pauper"], main, side | {"Duress": 1})
        assert (result.archetype_id, result.subtype_id) == ("battle-screech", "orzhov")
        # Black lands alone do not choose this child.
        pure = classify_counts(rules["pauper"], main, side)
        assert (pure.archetype_id, pure.subtype_id) == ("battle-screech", "mono-white")
        del main["Battle Screech"]
        missing_core = classify_counts(rules["pauper"], main, side | {"Duress": 1})
        assert not any(m.archetype_id == "battle-screech" for m in missing_core.matched_rules)
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "pauper|battle-screech|orzhov")
    assert (row["english"], row["chinese"]) == ("Orzhov Battle Screech", "黑白战呼")
    # The existing approved visual identity already supplies W/B; reuse it.
    require_complete_mana_identities(ROOT, "pauper")
    assert rendered_mana_identities(ROOT, "pauper")["battle-screech/orzhov"] == ("w", "b")


def test_approved_sultai_garden_source_name_and_structure(rules):
    import yaml
    from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

    case = json.loads((ROOT / "tests/fixtures/classifier_round1_pauper_sultai_garden.json").read_text())
    result = classify_deck(rules["pauper"], case)
    assert (result.archetype_id, result.subtype_id, result.subtype_name) == ("golgari-gardens", "sultai", "Sultai Gardens")
    assert result.selected_rule_id == "golgari-gardens-artifact-blue-splash"
    main, side = deck_to_counts(case)
    # No particular blue payoff is required; one normal blue spell can suffice.
    for card in ("Kenku Artificer", "Cryogen Relic"):
        del main[card]
    for card in ("Bounce Off", "Relic's Roar"):
        del side[card]
    assert classify_counts(rules["pauper"], main, side).subtype_id == "golgari"
    assert classify_counts(rules["pauper"], main, side | {"Opt": 1}).subtype_id == "sultai"
    family = next(a for a in rules["pauper"].archetypes if a.id == "golgari-gardens")
    routes = {r.id: r for r in family.rules}
    for suffix in ("", "-artifact"):
        ordinary = routes["golgari-gardens" + suffix].conditions
        assert ordinary == routes["golgari-gardens" + suffix + "-red-splash"].conditions
        assert ordinary == routes["golgari-gardens" + suffix + "-blue-splash"].conditions
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "pauper|golgari-gardens|sultai")
    assert (row["english"], row["chinese"]) == ("Sultai Gardens", "苏勒台控制")
    require_complete_mana_identities(ROOT, "pauper")
    assert rendered_mana_identities(ROOT, "pauper")["golgari-gardens/sultai"] == ("u", "b", "g")


def test_approved_wubr_manufacturing_uses_normal_black_and_parent_core(rules):
    import yaml
    from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_wubr_manufacturing.json").read_text())["cases"]
    assert len(cases) == 3
    for case in cases:
        result = classify_deck(rules["standard"], case)
        assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "boros-manufacturing", "wubr")
        main, side = deck_to_counts(case)
        main = {k: v for k, v in main.items() if k not in {"Tithing Blade", "Tarrian's Journal"}}
        side = {k: v for k, v in side.items() if k != "Tithing Blade"}
        assert classify_counts(rules["standard"], main, side).subtype_id == "jeskai"
        assert classify_counts(rules["standard"], main, side | {"Duress": 1}).subtype_id == "wubr"
        main["Swamp"] = main.pop("Shattered Sanctum")
        assert classify_counts(rules["standard"], main, side | {"Duress": 1}).subtype_id == "wubr"
        for core in ("Weapons Manufacturing", "United Battlefront"):
            without = {k: v for k, v in main.items() if k != core}
            assert not any(m.archetype_id == "boros-manufacturing" for m in classify_counts(rules["standard"], without, side | {"Duress": 1}).matched_rules)
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "standard|boros-manufacturing|wubr")
    assert (row["english"], row["chinese"]) == ("WUBR Manufacturing", "四色武器（无绿）")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["boros-manufacturing/wubr"] == ("w", "u", "b", "r")
