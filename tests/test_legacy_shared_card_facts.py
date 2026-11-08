"""Shared facts drive Legacy costs; accepted payment roles remain policy."""

from dataclasses import replace

import pytest

from mtgmeta.classifier_cards import (
    CardFace, card_facts, classifier_card_name, use_card_facts,
)
from mtgmeta.legacy_policy.card_data import known_neutral_payment
from mtgmeta.legacy_policy.colors import audit, front


def colors(main, side=None):
    return audit({"main": main, "side": side or {},
                  "candidate": {"parent": "azorius-control"}})


def test_shared_snapshot_is_the_only_printed_fact_authority():
    snapshot = card_facts()
    original = snapshot.cards["Absolute Grace"]
    # A changed scoped snapshot must affect even a previously known card;
    # a separate Legacy copy would incorrectly retain the original white cost.
    changed = replace(original, faces=(CardFace(
        original.name, "{1}{R}", "Enchantment", "", frozenset({"R"}),
    ),))
    with use_card_facts(replace(snapshot, cards={**snapshot.cards, original.key: changed})):
        assert front("Absolute Grace")["mana_cost"] == "{1}{R}"
        result = colors({"Absolute Grace": 1, "Mountain": 1})
        assert result["colors"] == "R" and not result["issues"]
    assert front("Absolute Grace")["mana_cost"] == "{1}{W}"


def test_shared_alias_preserves_retained_capitalization():
    assert classifier_card_name("Altar Of Dementia") == "Altar of Dementia"
    result = colors({"Altar Of Dementia": 1})
    assert result["colors"] == "" and not result["issues"]


def test_new_spell_costs_use_actual_support_and_not_card_name_guessing():
    result = colors({"Chandra, Chill of Compliance": 1, "Island": 1})
    assert result["colors"] == "U" and not result["issues"]
    result = colors({"Absolute Grace": 1, "Island": 1})
    assert result["issues"] == ["Absolute Grace：W费用但未找到法术力支持"]


def test_suspend_and_hybrid_payments_keep_their_actual_colors():
    result = colors({"Ancestral Vision": 1, "Island": 1})
    assert result["colors"] == "U" and not result["issues"]
    result = colors({"Spider-Woman, Stunning Savior": 1, "Plains": 1})
    assert result["colors"] == "W" and not result["issues"]
    result = colors({"Wear/Tear": 1, "Plateau": 1})
    assert result["colors"] == "WR" and not result["issues"]


@pytest.mark.parametrize("name", [
    "Snow-Covered Island", "Snow-Covered Swamp", "Flooded Strand",
    "Underground Sea", "Powder Keg",
])
def test_neutral_payment_is_proved_from_shared_text(name):
    assert known_neutral_payment(name)


@pytest.mark.parametrize("name", [
    "Unknown Future Tool", "Boseiju, Who Endures", "Mishra's Research Desk",
])
def test_unknown_and_colored_abilities_are_not_silently_neutral(name):
    assert not known_neutral_payment(name)


def test_missing_shared_fact_is_still_an_error():
    result = colors({"Unknown Future Tool": 1})
    assert result["issues"] == ["Unknown Future Tool：牌面缺失"]
