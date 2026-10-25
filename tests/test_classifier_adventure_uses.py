"""Face-policy mechanics, not approval of a specific deck naming convention."""

import pytest

from mtgmeta.classifier_cards import deck_colors
from mtgmeta.rules import validate_rule_data


def test_chosen_basic_land_type_does_not_establish_a_specific_splash():
    main = {"Island": 18, "Opt": 4, "Multiversal Passage": 2}
    assert deck_colors(main, {}).colors == {"blue"}
    assert deck_colors(main, {}).mana_support == {"blue"}
    assert deck_colors(main, {"Nature's Claim": 1}).colors == {"blue"}
    assert deck_colors(main | {"Forest": 1}, {"Nature's Claim": 1}).colors == {"blue", "green"}
    # Ordinary fetches still need targets; a missing produced_mana field alone
    # is never interpreted as the ability to produce every color.
    assert deck_colors({"Island": 18, "Opt": 4, "Fabled Passage": 2}, {"Nature's Claim": 1}).colors == {"blue"}


def test_adventure_face_selection_preserves_other_normal_color_contributions():
    main = {"Blood Crypt": 4, "Breeding Pool": 4, "Callous Sell-Sword": 4, "Elusive Otter": 4}
    assert deck_colors(main, {}).colors == {"black", "red", "blue", "green"}
    uses = {"Callous Sell-Sword": "adventure_only", "Elusive Otter": "front_only"}
    selected = deck_colors(main, {}, uses=uses)
    assert selected.colors == {"red", "blue"}
    assert len(selected.contributions) == 4  # Entity and quantity remain intact.
    assert next(c for c in selected.contributions if c.card == "Callous Sell-Sword").quantity == 4
    assert deck_colors(main, {"Duress": 1, "Nature's Claim": 1}, uses=uses).colors == {"black", "red", "blue", "green"}
    # No production policy is changed by requesting a scoped hypothetical use.
    assert deck_colors(main, {}).colors == {"black", "red", "blue", "green"}


@pytest.mark.parametrize("use", ["front_only", "adventure_only"])
def test_face_selection_requires_an_adventure_card(use):
    with pytest.raises(ValueError, match="known adventure"):
        deck_colors({"Opt": 1}, {}, uses={"Opt": use})
    with pytest.raises(ValueError, match="known adventure"):
        deck_colors({}, {}, uses={"Missing Adventure": use})
    data = {
        "schema_version": "1.2.0",
        "card_facts_sha256": "a" * 64,
        "format": "standard",
        "semantic_features": {"manifest_path": "configs/features.yaml", "manifest_sha256": "b" * 64},
        "archetypes": [{"id": "family", "name": "Family", "priority": 1,
                        "color_profile": "default", "card_uses": {"Opt": use},
                        "rules": [{"id": "route", "priority": 1,
                                   "conditions": {"all": [{"card": "Opt"}]}}]}],
    }
    assert any(f.message == "face selection requires a known adventure card" for f in validate_rule_data(data))
