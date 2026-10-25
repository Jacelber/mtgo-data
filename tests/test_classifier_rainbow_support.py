"""Owner clarification: rainbow capability alone is not stable color support."""

import pytest

from mtgmeta.classifier_cards import card_facts, deck_colors


@pytest.mark.parametrize("source", [
    "Starting Town", "Lotus Field", "Crumbling Vestige",
    "Multiversal Passage", "Mana Confluence", "Springleaf Drum",
])
def test_rainbow_sources_do_not_establish_main_or_sideboard_splashes(source):
    assert source in card_facts().cards
    main = {"Island": 8, "Forest": 8, "Opt": 4, "Arboreal Grazer": 4, source: 4}
    for m, s in ((main | {"Kenrith, the Returned King": 1, "Thoughtseize": 1}, {}),
                 (main, {"Kenrith, the Returned King": 1, "Thoughtseize": 1})):
        result = deck_colors(m, s)
        assert result.colors == {"blue", "green"}
        assert result.mana_support == {"blue", "green"}
    # One ordinary source plus a normal spell still counts; no global source
    # quantity threshold is imported from the two adventure-card exceptions.
    assert deck_colors(main | {"Swamp": 1}, {"Thoughtseize": 1}).colors == {"blue", "black", "green"}
    assert deck_colors(main | {"Underground Mortuary": 1}, {"Thoughtseize": 1}).colors == {"blue", "black", "green"}
    assert deck_colors(main | {"Swamp": 1}, {}).colors == {"blue", "green"}


def test_generic_rainbow_support_is_not_reintroduced_by_hybrid_or_kicker():
    main = {"Island": 8, "Forest": 8, "Opt": 4, "Arboreal Grazer": 4, "Lotus Field": 4}
    assert deck_colors(main, {"Vibrance": 1, "Tear Asunder": 2}).colors == {"blue", "green"}
    assert deck_colors(main | {"Mountain": 1}, {"Vibrance": 1}).colors == {"blue", "red", "green"}
    assert deck_colors(main | {"Swamp": 1}, {"Tear Asunder": 2}).colors == {"blue", "black", "green"}


def test_fixed_part_of_optional_five_color_sources_remains_normal_support():
    main = {"Citadel Gate": 4, "Cliffgate": 4, "Thraben Inspector": 4, "Lightning Bolt": 4}
    result = deck_colors(main, {"Nature's Claim": 1})
    assert result.colors == {"white", "red"}
    assert result.mana_support == {"white", "red"}
    # A restricted second ability does not erase an ordinary first ability.
    result = deck_colors({"Arena of Glory": 4, "Lightning Bolt": 4}, {})
    assert result.colors == {"red"}


def test_approved_gates_grudge_source_uses_only_the_reviewed_flashback_exception():
    import json
    from pathlib import Path
    from mtgmeta.classifier import classify_counts, classify_deck
    from mtgmeta.config import load_rule_set
    from mtgmeta.deck import deck_to_counts

    root = Path(__file__).resolve().parents[1]
    case = json.loads((root / "tests/fixtures/classifier_round1_pauper_gates_grudge.json").read_text())["cases"][0]
    rules = load_rule_set(root / "my_archetypes/pauper.yaml")
    result = classify_deck(rules, case)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "battle-screech", "naya")
    main, side = deck_to_counts(case)
    # The default remains unchanged for other families and formats.
    colors = deck_colors(main, side)
    assert colors.colors == {"white", "red"}
    assert colors.mana_support == {"white", "red"}
    assert not colors.missing
    # This is not a global exclusion of Ancient Grudge's flashback color.
    assert deck_colors(main, side | {"Forest": 1}).colors == {"white", "red", "green"}
    # Fixed green land without a green use does not establish a splash either.
    without_grudge = {k: v for k, v in side.items() if k != "Ancient Grudge"}
    assert deck_colors(main, without_grudge | {"Forest": 1}).colors == {"white", "red"}
    profile = "pauper-battle-screech"
    colors = deck_colors(main, side, profile=profile)
    assert colors.colors == {"white", "red", "green"}
    grudge = next(c for c in colors.contributions if c.card == "Ancient Grudge")
    assert set(grudge.colors) == {"red", "green"}
    assert grudge.reason == "pauper-battle-screech:gates-grudge-flashback-support"
    assert classify_counts(rules, main, without_grudge).subtype_id == "boros"
    assert classify_counts(rules, main, without_grudge | {"Forest": 1, "Nature's Claim": 1}).subtype_id == "naya"
    assert classify_counts(rules, main | {"Ancient Grudge": 1}, without_grudge).subtype_id == "naya"
    # Do not freeze the source deck's quantities or grant green to other cards.
    assert classify_counts(rules, main | {"Citadel Gate": 2, "Cliffgate": 3}, without_grudge | {"Ancient Grudge": 1}).subtype_id == "naya"
    with_claim = deck_colors(main, side | {"Nature's Claim": 1}, profile=profile)
    claim = next(c for c in with_claim.contributions if c.card == "Nature's Claim")
    assert not claim.colors
    assert deck_colors(main, without_grudge | {"Nature's Claim": 1}, profile=profile).colors == {"white", "red"}
    for gate in ("Citadel Gate", "Cliffgate"):
        without_gate = {k: v for k, v in main.items() if k != gate}
        assert deck_colors(without_gate, side, profile=profile).colors == {"white", "red"}
        assert deck_colors(without_gate, side | {gate: 4}, profile=profile).colors == {"white", "red"}
    assert deck_colors(main, side, profile=profile, uses={"Ancient Grudge": "noncast"}).colors == {"white", "red"}
    without_core = {k: v for k, v in main.items() if k != "Battle Screech"}
    assert not any(m.archetype_id == "battle-screech" for m in classify_counts(rules, without_core, side).matched_rules)


def test_naya_screech_names_and_mana():
    from pathlib import Path
    import yaml
    from mtgmeta.mana_identity import rendered_mana_identities, require_complete_mana_identities

    root = Path(__file__).resolve().parents[1]
    names = yaml.safe_load((root / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "pauper|battle-screech|naya")
    assert (row["english"], row["chinese"]) == ("Naya Battle Screech", "纳雅战呼")
    require_complete_mana_identities(root, "pauper")
    assert rendered_mana_identities(root, "pauper")["battle-screech/naya"] == ("w", "r", "g")


def test_screech_profile_is_pauper_only():
    from pathlib import Path
    import yaml
    from mtgmeta.rules import validate_rule_data

    root = Path(__file__).resolve().parents[1]
    data = yaml.safe_load((root / "my_archetypes/pauper.yaml").read_text())
    data["archetypes"] = [a for a in data["archetypes"] if a["id"] == "battle-screech"]
    assert not validate_rule_data(data)
    for fmt in ("standard", "modern", "pioneer"):
        assert any(f.message == "profile is Pauper-only" for f in validate_rule_data(data | {"format": fmt}))


def test_reviewed_normal_cast_override_remains_explicit_and_per_card():
    main = {"Island": 8, "Opt": 4, "Starting Town": 4, "Kenrith, the Returned King": 1}
    result = deck_colors(main, {"Thoughtseize": 1}, uses={"Kenrith, the Returned King": "normal_cast"})
    assert result.colors == {"blue", "white"}
    assert "black" not in result.colors
    # An explicit adventure use is not undone by the ordinary support filter.
    result = deck_colors(main | {"Elusive Otter": 1}, {}, uses={"Elusive Otter": "normal_cast"})
    assert result.colors == {"blue", "green"}


def test_packbeast_burn_exception_is_red_only_and_requires_the_main_route():
    main = {"Salt Road Packbeast": 4, "Plains": 8, "Lightning Bolt": 4,
            "Galvanic Blast": 4, "Holdout Settlement": 4, "Mardu Devotee": 4}
    profile = "pauper-packbeast"
    assert deck_colors(main, {}).colors == {"white"}
    result = deck_colors(main, {"Duress": 1, "Nature's Claim": 1}, profile=profile)
    assert result.colors == {"white", "red"}
    assert result.mana_support == {"white", "red"}
    assert next(c for c in result.contributions if c.card == "Holdout Settlement").reason == "pauper-packbeast:main-burn-red-support"
    # It is a route, not a frozen 75: a quantity change retains its meaning.
    assert deck_colors(main | {"Lightning Bolt": 3}, {}, profile=profile).colors == {"white", "red"}
    for card in ("Lightning Bolt", "Galvanic Blast", "Holdout Settlement"):
        reduced = {k: v for k, v in main.items() if k != card}
        assert deck_colors(reduced, {card: 1}, profile=profile).colors == {"white"}
    assert deck_colors(main | {"Swamp": 1}, {"Duress": 1}, profile=profile).colors == {"white", "red", "black"}


def test_packbeast_profile_is_not_portable_to_other_formats():
    from pathlib import Path
    import yaml
    from mtgmeta.rules import validate_rule_data

    root = Path(__file__).resolve().parents[1]
    data = yaml.safe_load((root / "my_archetypes/pauper.yaml").read_text())
    for fmt in ("modern", "standard", "pioneer"):
        assert any(f.message == "profile is Pauper-only" for f in validate_rule_data(data | {"format": fmt}))


def test_packbeast_main_winding_way_exception_keeps_other_colors_scoped():
    main = {"Salt Road Packbeast": 4, "Plains": 10,
            "Winding Way": 4, "Springleaf Drum": 4}
    profile = "pauper-packbeast"
    assert deck_colors(main, {}).colors == {"white"}
    result = deck_colors(main, {"Duress": 1, "Lightning Bolt": 1, "Opt": 1}, profile=profile)
    assert result.colors == {"white", "green"}
    assert next(c for c in result.contributions if c.card == "Winding Way").reason == "pauper-packbeast:main-winding-way-green-support"
    assert deck_colors(main | {"Winding Way": 3}, {}, profile=profile).colors == {"white", "green"}
    for card in ("Winding Way", "Springleaf Drum"):
        reduced = {k: v for k, v in main.items() if k != card}
        assert deck_colors(reduced, {card: 4}, profile=profile).colors == {"white"}
    assert deck_colors(main | {"Swamp": 1}, {"Duress": 1}, profile=profile).colors == {"white", "green", "black"}


def test_sideboard_only_learn_targets_do_not_use_family_mana_exceptions():
    main = {"Salt Road Packbeast": 4, "Plains": 10, "Guiding Voice": 4,
            "Mardu Devotee": 4, "Springleaf Drum": 4}
    side = {"Dai Li Indoctrination": 2, "Firebending Lesson": 2, "It'll Quench Ya!": 1}
    profile = "pauper-packbeast"
    result = deck_colors(main, side, profile=profile)
    assert result.colors == {"white"}
    assert all(c.reason == "learn:sideboard-lesson-without-ordinary-land-support"
               for c in result.contributions if c.zone == "side")
    # A non-Lesson normal spell still uses the approved mana package.
    assert deck_colors(main, side | {"Flaring Pain": 2}, profile=profile).colors == {"white", "red"}
    assert deck_colors(main, side | {"Duress": 1}, profile=profile).colors == {"white", "black"}
    assert deck_colors(main | {"Swamp": 1}, side, profile=profile).colors == {"white", "black"}
    # It is a use exception, not a global blacklist of Lesson spells.
    assert deck_colors(main | {"Dai Li Indoctrination": 1}, side, profile=profile).colors == {"white", "black"}
    no_learn = {k: v for k, v in main.items() if k != "Guiding Voice"}
    assert deck_colors(no_learn, side, profile=profile).colors == {"white", "black", "red"}
    assert deck_colors(main, side, profile=profile, uses={"Dai Li Indoctrination": "normal_cast"}).colors == {"white", "black"}
    # An excluded Lesson cannot establish black for an optional life payment.
    assert deck_colors(main | {"Dismember": 1}, side, profile=profile).colors == {"white"}


def test_packbeast_devotee_drum_package_supports_normal_black_red_only():
    main = {"Salt Road Packbeast": 4, "Plains": 10,
            "Mardu Devotee": 4, "Springleaf Drum": 4}
    profile = "pauper-packbeast"
    # Support never assigns a color without a normally used spell.
    assert deck_colors(main, {}, profile=profile).colors == {"white"}
    assert deck_colors(main, {}, profile=profile).mana_support == {"white", "black", "red"}
    for spells in ({"Refurbished Familiar": 4, "Galvanic Blast": 4},
                   {"Foul-Tongue Shriek": 2, "Fling": 1}):
        assert deck_colors(main | spells, {}, profile=profile).colors == {"white", "black", "red"}
        assert deck_colors(main, spells, profile=profile).colors == {"white", "black", "red"}
        assert deck_colors(main | spells, {}).colors == {"white"}
    # No Encampment/particular payoff requirement, or grant of green/blue.
    result = deck_colors(main, {"Duress": 1, "Lightning Bolt": 1,
                               "Nature's Claim": 1, "Opt": 1}, profile=profile)
    assert result.colors == {"white", "black", "red"}
    assert next(c for c in result.contributions if c.card == "Springleaf Drum").reason == "pauper-packbeast:devotee-drum-black-red-support"
    # Do not quietly widen the reviewed package to incidental components.
    for name in ("Mardu Devotee", "Springleaf Drum"):
        reduced = main | {name: 1}
        assert deck_colors(reduced, {"Duress": 1, "Fling": 1}, profile=profile).colors == {"white"}
    assert deck_colors(main | {"Forest": 1}, {"Nature's Claim": 1}, profile=profile).colors == {"white", "green"}


def test_approved_mardu_source_keeps_identity_without_named_payoff_or_encampment():
    import json
    from pathlib import Path
    from mtgmeta.classifier import classify_counts, classify_deck
    from mtgmeta.config import load_rule_set
    from mtgmeta.deck import deck_to_counts

    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "tests/fixtures/classifier_round1_other_formats.json").read_text())["cases"]
    case = next(c for c in cases if c["record_id"] == "mtgo:pauper:12843381:30")
    rules = load_rule_set(root / "my_archetypes/pauper.yaml")
    result = classify_deck(rules, case)
    assert (result.archetype_id, result.subtype_id) == ("packbeast-swarm", "mardu")
    main, side = deck_to_counts(case)
    main["Plains"] += main.pop("Survivors' Encampment")
    del main["Refurbished Familiar"]
    assert classify_counts(rules, main, side).subtype_id == "mardu"
    del main["Salt Road Packbeast"]
    assert not any(m.archetype_id == "packbeast-swarm" for m in classify_counts(rules, main, side).matched_rules)


def test_retained_source_decks_follow_reviewed_support_not_old_labels():
    import json
    from pathlib import Path
    from mtgmeta.classifier import classify_counts, classify_deck
    from mtgmeta.config import load_rule_set
    from mtgmeta.deck import deck_to_counts

    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "tests/fixtures/classifier_round1_rainbow_support.json").read_text())["cases"]
    rules = {fmt: load_rule_set(root / "my_archetypes" / f"{fmt}.yaml") for fmt in ("modern", "pioneer", "pauper")}
    for case in cases:
        result = classify_deck(rules[case["format"]], case)
        assert (result.status, result.archetype_id, result.subtype_id) == tuple(case["expected"]), case["record_id"]
        colors = dict(result.color_diagnostics)[case["color_parent"]]
        assert colors.colors == set(case["expected_colors"]), case["record_id"]
        assert not colors.missing
        if case["format"] == "pauper":
            main, side = deck_to_counts(case)
            if case["record_id"] == "mtgo:pauper:12843392:18":
                assert result.selected_rule_id == "boros-learn-packbeast-swarm"
                without_pain = {k: v for k, v in side.items() if k != "Flaring Pain"}
                pure = classify_counts(rules["pauper"], main, without_pain)
                assert (pure.archetype_id, pure.subtype_id) == ("packbeast-swarm", "mono-white-learn")
                family = next(a for a in rules["pauper"].archetypes if a.id == "packbeast-swarm")
                routes = {r.id: r for r in family.rules}
                assert routes["mono-white-learn-packbeast-swarm"].conditions == routes["boros-learn-packbeast-swarm"].conditions
            del main["Salt Road Packbeast"]
            without_core = classify_counts(rules["pauper"], main, side)
            assert not any(m.archetype_id == "packbeast-swarm" for m in without_core.matched_rules)
