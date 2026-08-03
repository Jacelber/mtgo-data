"""Focused regression tests for the package Standard classifier API."""

import json
from pathlib import Path

from mtgmeta.card_names import normalize_card_name
from mtgmeta.classifier import classify_counts, evaluate_matches
from mtgmeta.config import load_rule_set
from mtgmeta.deck import count_card, deck_to_counts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
RULES = ROOT / "my_archetypes" / "standard.yaml"


def rules():
    return load_rule_set(RULES)


def player(source, index):
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]
    record = next(
        item for item in records if item["source"] == source and item["index"] == index
    )
    return {
        "main_deck": [{"name": name, "qty": qty} for name, qty in record["main"]],
        "sideboard": [{"name": name, "qty": qty} for name, qty in record["side"]],
    }


def test_representative_results_cover_priority_and_unknown():
    cases = [
        ("Standard_Challenge_32_12838092.json", 2, "Monument Lessons"),
        ("Standard_Challenge_32_12838105.json", 3, "Mono-White Momo"),
        ("Standard_Challenge_32_12838092.json", 23, "Selesnya Rhythm"),
        ("Standard_Challenge_32_12839956.json", 8, None),
    ]
    rule_set = rules()
    for source, index, expected in cases:
        result = classify_counts(rule_set, *deck_to_counts(player(source, index)))
        assert result.archetype_name == expected


def test_card_aliases_and_zone_counts_remain_compatible():
    for old, new in {
        "Kavaero, Mind-Bitten": "Superior Spider-Man",
        "Leyline Weaver": "Spider Manifestation",
    }.items():
        main, side = deck_to_counts(
            {"main_deck": [{"name": old, "qty": 2}], "sideboard": []}
        )
        assert normalize_card_name(old) == new
        assert main == {new: 2} and side == {}
    main, side = {"Card": 2}, {"Card": 1}
    assert count_card("Card", "any", main, side) == 3
    assert count_card("Card", "main", main, side) == 2
    assert count_card("Card", "side", main, side) == 1


def test_multi_match_and_repeated_display_names_preserve_priority_selection():
    rule_set = rules()
    main, side = deck_to_counts(player("Standard_Challenge_32_12838092.json", 23))
    matches = evaluate_matches(rule_set, main, side)
    assert [match.archetype_name for match in matches] == [
        "Selesnya Rhythm",
        "Selesnya Midrange",
    ]
    assert classify_counts(rule_set, main, side).archetype_name == "Selesnya Rhythm"
    names = [
        archetype.name
        for archetype in rule_set.archetypes
        for _rule in archetype.rules
    ]
    assert names.count("4-Color Control") == 2
    assert names.count("Izzet Aggro") == 2
