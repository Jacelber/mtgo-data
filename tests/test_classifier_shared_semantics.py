"""Owner-confirmed boundaries; expected identities do not come from replay output."""

from dataclasses import replace

from mtgmeta.classifier import classify_counts, classifier_digest
from mtgmeta.classifier_cards import card_facts, classifier_card_name, deck_colors
from mtgmeta.deck import deck_to_counts
from mtgmeta.melee.classification import _adapt_decklist
from mtgmeta.rules import (
    AnyCondition,
    ArchetypeDefinition,
    CardCondition,
    ClassificationRule,
    RuleSet,
    SubtypeDefinition,
)


def family(*, core=(), colors=("blue",), conditions=(), profile="default"):
    branch = ClassificationRule("branch", 20, "blue", tuple(conditions), colors)
    parent = ArchetypeDefinition(
        "family",
        "Family",
        1,
        (SubtypeDefinition("blue", "Blue", "family"),),
        (branch,),
        tuple(core),
        profile,
        True,
    )
    return RuleSet("1.2.0", "modern", (parent,))


def test_source_identity_keeps_all_faces_and_counts_entity_once():
    adapted, errors = _adapt_decklist(
        {
            "cards": [
                {"name": "Wear // Tear", "quantity": 1, "section": "sideboard"},
                {
                    "name": "Delver of Secrets // Insectile Aberration",
                    "quantity": 4,
                    "section": "main",
                },
            ]
        }
    )
    assert not errors
    mtgo = {
        "main_deck": [{"name": "Delver of Secrets", "qty": 4}],
        "sideboard": [{"name": "Wear/Tear", "qty": 1}],
    }
    assert deck_to_counts(adapted) == deck_to_counts(mtgo)
    assert sum(deck_to_counts(adapted)[1].values()) == 1
    assert len(card_facts().cards["Wear/Tear"].castable_faces) == 2
    assert classifier_card_name("SP//dr, Piloted by Peni") == "SP//dr, Piloted by Peni"
    assert (
        classifier_card_name("Unregistered // Spelling") == "Unregistered // Spelling"
    )


def test_land_and_mite_do_not_add_green_but_one_sideboard_spell_does():
    main = {"Counterspell": 4, "Island": 8, "Breeding Pool": 1, "Haywire Mite": 1}
    assert deck_colors(main, {}).colors == {"blue"}
    assert deck_colors(main, {"Nature's Claim": 1}).colors == {"blue", "green"}
    assert deck_colors(main | {"Nature's Claim": 1}, {}).colors == {"blue", "green"}


def test_unsupported_sideboard_spell_does_not_define_a_splash():
    main = {"Counterspell": 4, "Island": 20}
    for card in ["Poison Dart Frog", "Tifa Lockhart", "Nature's Claim", "Wailing Ghoul"]:
        result = deck_colors(main, {card: 1})
        assert result.colors == {"blue"}
        contribution = next(c for c in result.contributions if c.card == card)
        assert contribution.reason == "sideboard-without-land-color-support"
    # No card blacklist: a single supported sideboard spell still adds its color.
    assert deck_colors(main | {"Breeding Pool": 1}, {"Poison Dart Frog": 1}).colors == {"blue", "green"}
    assert deck_colors(main, {"Forest": 1, "Tifa Lockhart": 1}).colors == {"blue", "green"}
    assert deck_colors(main | {"Watery Grave": 1}, {"Wailing Ghoul": 1}).colors == {"blue", "black"}


def test_mana_creature_cannot_bootstrap_itself_or_optional_colored_payments():
    main = {"Counterspell": 4, "Island": 20, "Mutagenic Growth": 4}
    side = {"Poison Dart Frog": 1, "Gilded Goose": 1, "Nature's Claim": 1}
    result = deck_colors(main, side)
    assert result.colors == {"blue"}
    assert result.mana_support == {"blue"}
    supported = deck_colors(main | {"Breeding Pool": 1}, side)
    assert supported.colors == {"blue", "green"}
    # The creature's rainbow ability alone does not establish a black splash.
    assert deck_colors(main | {"Breeding Pool": 1}, side | {"Fatal Push": 1}).colors == {"blue", "green"}


def test_incidental_sources_do_not_establish_a_sideboard_splash():
    main = {"Forest": 10, "Basking Broodscale": 4}
    for source in ["Springleaf Drum", "Mox Opal", "The Mycosynth Gardens", "Gemstone Caverns", "Cavern of Souls", "Reflecting Pool"]:
        assert deck_colors(main | {source: 1}, {"Wailing Ghoul": 2}).colors == {"green"}
    assert deck_colors(main | {"Overgrown Tomb": 1}, {"Wailing Ghoul": 2}).colors == {"green", "black"}


def test_complete_decks_follow_confirmed_incidental_sideboard_policy():
    import json
    from pathlib import Path
    from mtgmeta.classifier import classify_deck
    from mtgmeta.config import load_rule_set

    root = Path(__file__).resolve().parents[1]
    rules = load_rule_set(root / "my_archetypes/modern.yaml")
    cases = json.loads((root / "tests/fixtures/modern/classifier_round1_incidental_sideboard.json").read_text())["cases"]
    for case in cases:
        colors = deck_colors(*deck_to_counts(case))
        assert colors.colors == set(case["expected_colors"]), case["source_locator"]
        if "expected" in case:
            result = classify_deck(rules, case)
            assert (result.archetype_id, result.subtype_id) == tuple(case["expected"])


def test_goryos_exception_does_not_delete_other_green_contributions():
    main = {
        "Goryo's Vengeance": 4,
        "Atraxa, Grand Unifier": 4,
        "Psychic Frog": 4,
        "Ephemerate": 4,
        "Hallowed Fountain": 2,
        "Watery Grave": 2,
        "Hedge Maze": 1,
    }
    assert deck_colors(main, {}, profile="modern-goryos").colors == {
        "white",
        "blue",
        "black",
    }
    assert (
        "green"
        in deck_colors(main, {"Nature's Claim": 1}, profile="modern-goryos").colors
    )
    assert "green" in deck_colors(main, {}, profile="default").colors


def test_prismatic_ending_does_not_use_color_identity_or_land_colors():
    assert deck_colors(
        {
            "Prismatic Ending": 2,
            "Counterspell": 4,
            "Hallowed Fountain": 3,
            "Steam Vents": 1,
            "Breeding Pool": 1,
        },
        {},
    ).colors == {"white", "blue"}


def test_flashback_casting_color_is_distinct_from_activation_and_land_color():
    main = {"Plains": 10, "Mountain": 1, "Battle Screech": 4}
    assert deck_colors(main, {}).colors == {"white"}
    assert deck_colors(main | {"Rally the Peasants": 1}, {}).colors == {"white", "red"}
    assert deck_colors({"Plains": 10, "Rally the Peasants": 1}, {}).colors == {"white"}
    assert deck_colors({"Island": 10, "Swamp": 1, "Mystical Teachings": 1}, {}).colors == {"blue", "black"}
    assert deck_colors({"Island": 10, "Mystical Teachings": 1}, {}).colors == {"blue"}
    # Land and activated mana costs still do not add colors on their own.
    assert deck_colors(main | {"Forest": 1, "Haywire Mite": 1}, {}).colors == {"white"}


def test_supported_kicker_and_mana_spent_effects_contribute_their_colors():
    main = {"Forest": 10, "Tear Asunder": 1}
    assert deck_colors(main, {}).colors == {"green"}
    assert deck_colors(main | {"Swamp": 1}, {}).colors == {"green", "black"}
    main = {"Island": 10, "Counterspell": 4, "Wistfulness": 1}
    assert deck_colors(main, {}).colors == {"blue"}
    assert deck_colors(main | {"Breeding Pool": 1}, {}).colors == {"blue", "green"}


def test_scoped_noncast_use_does_not_blacklist_the_card_or_other_spells():
    main = {"Plains": 10, "Mountain": 2, "Battle Screech": 4, "Sneaky Snacker": 4}
    uses = {"Sneaky Snacker": "noncast_without_support"}
    assert deck_colors(main, {}, uses=uses).colors == {"white"}
    # The shared default now also requires ordinary land support in both zones.
    assert deck_colors(main, {}).colors == {"white"}
    assert deck_colors(main | {"Island": 1, "Swamp": 1}, {}).colors == {"white", "blue", "black"}
    assert deck_colors(main | {"Island": 1, "Swamp": 1}, {}, uses=uses).colors == {"white", "blue", "black"}
    assert deck_colors(main | {"Island": 1, "Opt": 1}, {}, uses=uses).colors == {"white", "blue"}


def test_opening_hand_leyline_does_not_define_a_color_without_other_casting_use():
    main = {"Lotus Field": 4, "Breeding Pool": 4, "Scapeshift": 4, "Opt": 4}
    assert deck_colors(main, {"Leyline of Sanctity": 4}).colors == {"blue", "green"}
    assert deck_colors(main | {"Get Lost": 1}, {"Leyline of Sanctity": 4}).colors == {"blue", "green"}
    assert deck_colors(main | {"Get Lost": 1, "Plains": 1}, {"Leyline of Sanctity": 4}).colors == {"white", "blue", "green"}
    assert deck_colors(main, {"Leyline of Sanctity": 4}, uses={"Leyline of Sanctity": "normal_cast"}).colors == {"white", "blue", "green"}


def test_noncast_usage_is_conditional_on_supported_casting_route():
    for card in ["Surgical Extraction", "Faerie Macabre", "Leyline of the Void"]:
        assert deck_colors({"Island": 10, "Counterspell": 4}, {card: 1}).colors == {
            "blue"
        }
        assert deck_colors({"Swamp": 10, "Fatal Push": 1}, {card: 1}).colors == {
            "black"
        }


def test_missing_card_cannot_pass_a_color_exclusion_or_fall_to_other_parent():
    rules = family(core=(CardCondition("Counterspell"),))
    fallback = ArchetypeDefinition(
        "fallback",
        "Fallback",
        1,
        (),
        (ClassificationRule("fallback", 1, None, (CardCondition("Counterspell"),)),),
    )
    result = classify_counts(
        replace(rules, archetypes=rules.archetypes + (fallback,)),
        {"Counterspell": 4, "Unregistered New Spell": 1},
        {},
    )
    assert result.status == "unknown"
    assert "missing card facts" in result.errors[0]
    assert [m.rule_id for m in result.matched_rules] == ["fallback"]


def test_parent_core_cannot_be_bypassed_and_evidence_remembers_scope():
    rules = family(
        core=(
            CardCondition("Basking Broodscale", min_count=3),
            CardCondition("Blade of the Bloodchief", min_count=2),
        ),
        colors=("green",),
    )
    assert (
        classify_counts(
            rules, {"Basking Broodscale": 3, "Blade of the Bloodchief": 2, "Forest": 8}, {}
        ).status
        == "classified"
    )
    for main in [
        {"Basking Broodscale": 3},
        {"Blade of the Bloodchief": 2},
        {"Basking Broodscale": 1, "Blade of the Bloodchief": 1},
    ]:
        assert classify_counts(rules, main | {"Forest": 8}, {}).status == "unknown"
    result = classify_counts(
        rules, {"Basking Broodscale": 3, "Blade of the Bloodchief": 2, "Forest": 8}, {}
    )
    assert all(e.scope == "parent" for e in result.matched_rules[0].evidence[:2])


def test_any_routes_are_anded_with_parent_and_total_count_deduplicates_aliases():
    rules = family(
        core=(CardCondition("Island"),),
        conditions=(
            AnyCondition(
                (
                    (CardCondition("Counterspell", min_count=4),),
                    (
                        CardCondition(
                            "total_count",
                            min_count=2,
                            cards=("Wear/Tear", "Wear // Tear"),
                        ),
                    ),
                )
            ),
        ),
    )
    assert (
        classify_counts(rules, {"Island": 1, "Counterspell": 4}, {}).status
        == "classified"
    )
    assert classify_counts(rules, {"Counterspell": 4}, {}).status == "unknown"
    assert classify_counts(rules, {"Island": 1, "Wear/Tear": 1}, {}).status == "unknown"


def test_digest_ignores_parent_rule_order_but_includes_semantics():
    rules = family()
    parent = rules.archetypes[0]
    other = replace(
        parent, id="other", rules=(replace(parent.rules[0], id="other-rule"),)
    )
    both = replace(rules, archetypes=(parent, other))
    assert classifier_digest(both) == classifier_digest(
        replace(both, archetypes=(other, parent))
    )
    assert classify_counts(both, {"Counterspell": 1}, {}) == classify_counts(replace(both, archetypes=(other, parent)), {"Counterspell": 1}, {})
    assert classifier_digest(rules) != classifier_digest(
        replace(
            rules, archetypes=(replace(parent, conditions=(CardCondition("Island"),)),)
        )
    )


def test_complete_reviewed_decks_survive_confirmed_one_card_variants():
    import json
    from pathlib import Path
    from mtgmeta.config import load_rule_set

    root = Path(__file__).resolve().parents[1]
    rules = load_rule_set(root / "my_archetypes/modern.yaml")
    cases = json.loads(
        (root / "tests/fixtures/modern/classifier_round1_boundaries.json").read_text()
    )["cases"]
    for case in cases:
        main = case["main"]
        changed = dict(main)
        removed, added = case["replace"]
        changed[removed] -= 1
        changed[added] = changed.get(added, 0) + 1
        for counts in (main, changed):
            result = classify_counts(rules, counts, case["side"])
            assert (result.status, result.archetype_id, result.subtype_id) == (
                "classified",
                *case["expected"],
            ), case["case"]


def test_sewer_shared_route_selects_color_without_requiring_rumble():
    from pathlib import Path
    from mtgmeta.config import load_rule_set

    rules = load_rule_set(
        Path(__file__).resolve().parents[1] / "my_archetypes/modern.yaml"
    )
    main = {
        "Mox Opal": 4,
        "Urza's Saga": 4,
        "Mishra's Bauble": 4,
        "Sewer-veillance Cam": 3,
        "Grinding Station": 3,
        "Loki, God of Mischief": 4,
        "Breeding Pool": 1,
        "Haywire Mite": 1,
    }
    for side, expected in [({}, "mono-blue"), ({"Nature's Claim": 1}, "simic")]:
        result = classify_counts(rules, main, side)
        assert (result.archetype_id, result.subtype_id) == ("sewer-combo", expected)
    for core in ["Sewer-veillance Cam", "Grinding Station"]:
        result = classify_counts(rules, main | {core: 0}, {"Nature's Claim": 1})
        assert result.archetype_id != "sewer-combo"


def test_creativity_domain_convention_is_scoped_and_does_not_change_spell_facts():
    rules = family(
        core=(CardCondition("Indomitable Creativity"),),
        colors=("white", "blue", "black", "red", "green"),
        profile="modern-creativity",
    )
    main = {
        "Indomitable Creativity": 4,
        "Archon of Cruelty": 2,
        "Leyline Binding": 4,
        "Steam Vents": 1,
        "Temple Garden": 1,
        "Blood Crypt": 1,
    }
    result = classify_counts(rules, main, {})
    assert result.status == "classified"
    assert "black" not in result.color_diagnostics[0][1].colors
    assert result.matched_rules[0].evidence[-1].scope == "binding-domain-convention"
    assert classify_counts(rules, main | {"Leyline Binding": 0}, {}).status == "unknown"


def test_optional_cost_colors_are_not_created_by_rainbow_mana():
    main = {"Counterspell": 4, "Mox Opal": 4, "Island": 10}
    assert deck_colors(
        main, {"Surgical Extraction": 1, "Ashiok, Dream Render": 1}
    ).colors == {"blue"}
    result = deck_colors(main | {"Fatal Push": 1, "Watery Grave": 1}, {"Surgical Extraction": 1})
    assert result.colors == {"blue", "black"}
    assert next(
        c for c in result.contributions if c.card == "Surgical Extraction"
    ).colors == ("black",)


def test_explicit_normal_cast_overrides_default_optional_payment_use():
    assert deck_colors(
        {"Swamp": 2},
        {"Surgical Extraction": 1},
        uses={"Surgical Extraction": "normal_cast"},
    ).colors == {"black"}
    colors = deck_colors(
        {"Atraxa, Grand Unifier": 1, "Forest": 1},
        {},
        profile="modern-goryos",
        uses={"Atraxa, Grand Unifier": "normal_cast"},
    )
    assert colors.colors == {"white", "blue", "black", "green"}
    assert deck_colors(
        {"Fatal Push": 1, "Swamp": 1},
        {"Surgical Extraction": 1},
        uses={"Surgical Extraction": "noncast"},
    ).colors == {"black"}


def test_new_rule_parser_rejects_ambiguous_color_mappings_and_old_version_opt_in():
    from copy import deepcopy
    from mtgmeta.rules import validate_rule_data, build_rule_set

    base = {
        "schema_version": "1.2.0",
        "format": "modern",
        "card_facts_sha256": card_facts().digest,
        "semantic_features": {
            "manifest_path": "configs/old.yaml",
            "manifest_sha256": "0" * 64,
        },
        "archetypes": [
            {
                "id": "a",
                "name": "A",
                "priority": 1,
                "conditions": {"all": [{"card": "Counterspell"}]},
                "color_profile": "default",
                "require_color_subtype": True,
                "color_subtypes": {"blue": ["blue"]},
                "subtypes": [{"id": "blue", "name": "Blue"}],
                "rules": [
                    {
                        "id": "route",
                        "priority": 1,
                        "subtype_id": None,
                        "conditions": {
                            "all": [
                                {
                                    "any": [
                                        {"all": [{"card": "Island"}]},
                                        {
                                            "all": [
                                                {
                                                    "total_count": [
                                                        "Island",
                                                        "Breeding Pool",
                                                    ],
                                                    "min_count": 2,
                                                }
                                            ]
                                        },
                                    ]
                                }
                            ]
                        },
                    }
                ],
            }
        ],
    }
    assert validate_rule_data(base) == []
    assert (
        classify_counts(
            build_rule_set(base), {"Counterspell": 1, "Island": 2}, {}
        ).status
        == "invalid_deck"
    )  # referenced manifest not loaded
    bad = deepcopy(base)
    bad["archetypes"][0]["color_subtypes"]["other"] = ["blue"]
    assert validate_rule_data(bad)
    bad = deepcopy(base)
    bad["schema_version"] = "1.1.0"
    assert validate_rule_data(bad)
    bad = deepcopy(base)
    bad["archetypes"][0]["conditions"]["all"] = []
    assert validate_rule_data(bad)


def test_noncast_graveyard_hate_does_not_use_incidental_rainbow_mana_as_splash():
    main = {"Basking Broodscale": 3, "Forest": 4, "Talisman of Resilience": 3}
    for card in ["Faerie Macabre", "Leyline of the Void"]:
        assert deck_colors(main, {card: 2}).colors == {"green"}
        assert deck_colors(main | {"Fatal Push": 1}, {card: 2}).colors == {"green"}
        assert deck_colors(main | {"Fatal Push": 1, "Swamp": 1}, {card: 2}).colors == {
            "green",
            "black",
        }


def test_unknown_color_reports_preserve_reason_and_lower_matches_and_validate():
    from pathlib import Path
    from mtgmeta.reports import build_classification_reports
    from mtgmeta.melee.classification import _classification_record
    from validate_schemas import load_schemas, validate_instance

    rules = family(core=(CardCondition("Counterspell"),))
    fallback = ArchetypeDefinition(
        "fallback", "Fallback", 1, (),
        (ClassificationRule("fallback", 1, None, (CardCondition("Counterspell"),)),),
    )
    rules = replace(rules, archetypes=rules.archetypes + (fallback,))
    deck = {"main_deck": [{"name": "Counterspell", "qty": 4},
                          {"name": "Unregistered New Spell", "qty": 1}], "sideboard": []}
    result = classify_counts(rules, *deck_to_counts(deck))
    assert result.status == "unknown"
    reports = build_classification_reports([("data/modern/event.json", {
        "event_id": "123", "starttime": "2026-10-01T00:00:00Z", "players": [deck],
    })], rules)
    unknown = reports["unknown_decks"]
    record = unknown["records"][0]
    assert record["errors"] and record["color_diagnostics"][0]["missing"] == ["Unregistered New Spell"]
    assert record["matched_rules"][0]["rule_id"] == "fallback"
    schemas, registry = load_schemas(Path(__file__).resolve().parents[1] / "schemas", {
        "classification-report.schema.json", "melee-classification.schema.json",
    })
    assert not validate_instance(unknown, schemas["classification-report.schema.json"], registry)
    melee = _classification_record("participant-synthetic", result, deck)
    schema = schemas["melee-classification.schema.json"]
    record_schema = {"$ref": schema["$id"] + "#/$defs/classification_record"}
    assert not validate_instance(melee, record_schema, registry)
    assert melee["color_diagnostics"] == record["color_diagnostics"]
    melee.pop("color_diagnostics")
    assert validate_instance(melee, record_schema, registry)
    record.pop("color_diagnostics")
    assert validate_instance(unknown, schemas["classification-report.schema.json"], registry)


def test_approved_color_subtypes_on_complete_source_decks():
    import json
    from pathlib import Path
    from mtgmeta.classifier import classify_deck
    from mtgmeta.config import load_rule_set

    root = Path(__file__).resolve().parents[1]
    rules = load_rule_set(root / "my_archetypes/modern.yaml")
    cases = json.loads((root / "tests/fixtures/modern/classifier_round1_color_decisions.json").read_text())["cases"]
    for case in cases:
        result = classify_deck(rules, case)
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified", *case["expected"],
        ), case["source_locator"]
        if "expected_normal_colors" in case:
            # Family naming must not manufacture a black spell contribution.
            colors = deck_colors(*deck_to_counts(case), profile="modern-creativity")
            assert colors.colors == set(case["expected_normal_colors"])


def test_firespout_counts_supported_effect_color_without_counting_all_hybrid_options():
    main = {"Counterspell": 4, "Lightning Bolt": 4, "Steam Vents": 2}
    assert deck_colors(main, {"Firespout": 1}).colors == {"blue", "red"}
    assert deck_colors(main | {"Breeding Pool": 1}, {"Firespout": 1}).colors == {"blue", "red", "green"}
    assert deck_colors({"Fatal Push": 1, "Watery Grave": 1}, {"Ashiok, Dream Render": 1}).colors == {"black"}


def test_explicit_reviewed_subtype_name_is_not_duplicated_by_hyphenated_parent():
    from mtgmeta.mtgo.landing_editorial import _display_english

    assert _display_english("Izzet Steel-Cutter", "Temur Steel Cutter") == "Temur Steel Cutter"
    assert _display_english("Izzet Steel-Cutter", "Jeskai") == "Jeskai Steel-Cutter"
    assert _display_english("Esper Goryo's", "WUBG") == "WUBG Goryo's"
