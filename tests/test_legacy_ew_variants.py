"""Owner-reviewed card structures, independent of event/player identifiers."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/legacy/accepted_ew_variants.json").read_text()
)
REMAINING = json.loads(
    (ROOT / "tests/fixtures/legacy/accepted_ew_remaining.json").read_text()
)
CASES += REMAINING


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case"])
def test_reviewed_variants_and_rule_order(rules, case):
    for selected_rules in (rules, reordered_rule_set(rules)):
        result = classify_counts(selected_rules, case["main"], case["side"])
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified",
            case["parent"],
            case["subtype"],
        )


def test_one_forge_does_not_turn_artifact_big_mana_into_forge_combo(rules):
    case = next(c for c in CASES if c["case"] == "single-forge-artifact-big-mana")
    # Conversely, the full draw engine and key package belongs to Forge.
    combo = next(c for c in CASES if c["case"] == "forge-keys-without-saga")
    assert classify_counts(rules, case["main"], case["side"]).archetype_id == "tron"
    assert (
        classify_counts(rules, combo["main"], combo["side"]).archetype_id
        == "mystic-forge-combo"
    )


def test_colored_main_plan_is_not_hidden_by_sideboard_tool_exception(rules):
    case = next(c for c in CASES if c["case"] == "voltaic-toolbox-black-sideboard")
    result = classify_counts(
        rules, {**case["main"], "Barrowgoyf": 3, "Swamp": 2}, case["side"]
    )
    assert (result.archetype_id, result.subtype_id) != ("tron", "colorless")


@pytest.mark.parametrize(
    "extra,subtype",
    [
        ({"Plateau": 1}, "colorless"),
        ({"Plateau": 1, "Lightning Bolt": 4, "Swords to Plowshares": 4}, "boros"),
        ({"Lightning Bolt": 4, "Swords to Plowshares": 4}, "multicolor"),
        ({"Boseiju, Who Endures": 1}, "colorless"),
        ({"Boseiju, Who Endures": 1, "Forest": 1}, "mono-green"),
    ],
)
def test_tron_subtypes_require_a_paid_plan_and_dedicated_sources(rules, extra, subtype):
    from mtgmeta.classifier_cards import use_card_facts
    from mtgmeta.legacy_policy.tron import audit_subtype

    main = {
        "Planar Nexus": 4,
        "Urza's Tower": 4,
        "Grim Monolith": 4,
        "Karn, the Great Creator": 4,
        "The One Ring": 4,
        "Kozilek's Command": 4,
    }
    with use_card_facts(rules.facts):
        result = audit_subtype(rules, "tron", {**main, **extra}, {})
    assert result["subtype"] == subtype
    assert not result["issues"]


def test_generic_rainbow_payment_does_not_change_deck_color(rules):
    from mtgmeta.classifier_cards import use_card_facts
    from mtgmeta.legacy_policy.colors import audit

    with use_card_facts(rules.facts):
        for added, expected in [({}, "U"), ({"Swamp": 1}, "UB")]:
            result = audit(
                {
                    "main": {
                        "Island": 3,
                        "Brainstorm": 4,
                        "Lotus Petal": 4,
                        "Thoughtseize": 4,
                        **added,
                    },
                    "side": {},
                    "candidate": {"parent": "dimir-tempo"},
                }
            )
            assert result["colors"] == expected
            assert not result["issues"]


def test_blue_tron_firespout_does_not_expand_either_reviewed_branch(rules):
    pure = next(
        c
        for c in REMAINING
        if c["parent"] == "blue-tron" and c["subtype"] == "mono-blue"
    )
    mixed = next(
        c
        for c in REMAINING
        if c["parent"] == "blue-tron" and c["subtype"] == "multicolor"
    )
    for case in (pure, mixed):
        side = {**case["side"], "Firespout": 3}
        for counts in (case["main"], dict(reversed(list(case["main"].items())))):
            result = classify_counts(rules, counts, side)
            assert (result.archetype_id, result.subtype_id) == (
                case["parent"],
                case["subtype"],
            )


def test_reviewed_new_engines_need_their_distinguishing_cards(rules):
    for parent, card in [
        ("simic-beanstalk", "Up the Beanstalk"),
        ("devoted-reconfiguration", "Swift Reconfiguration"),
        ("worldgorger-combo", "Worldgorger Dragon"),
    ]:
        case = next(c for c in REMAINING if c["parent"] == parent)
        main = {n: q for n, q in case["main"].items() if n != card}
        assert classify_counts(rules, main, case["side"]).archetype_id != parent
