"""Focused regression tests for the unchanged legacy Standard classifier."""

import json
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
repository_root_text = str(REPOSITORY_ROOT)
if repository_root_text not in sys.path:
    sys.path.insert(0, repository_root_text)

from classify_standard import CARD_ALIASES, count_card, deck_to_counts, match_archetype, signature_card_met

ROOT = REPOSITORY_ROOT
FIXTURE = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"

def rules():
    return yaml.safe_load((ROOT / "my_archetypes" / "standard.yaml").read_text(encoding="utf-8"))["archetypes"]


def all_legacy_matches(main, side):
    return [rule["name"] for rule in rules() if rule.get("signatureCards") and all(signature_card_met(sig, main, side) for sig in rule["signatureCards"])]


def player(source, index):
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]
    record = next(item for item in records if item["source"] == source and item["index"] == index)
    return {"main_deck": [{"name": name, "qty": qty} for name, qty in record["main"]], "sideboard": [{"name": name, "qty": qty} for name, qty in record["side"]]}


def test_representative_legacy_results_cover_rule_order_and_unknown():
    cases = [
        ("Standard_Challenge_32_12838092.json", 2, "Monument Lessons"),
        ("Standard_Challenge_32_12838105.json", 3, "Mono-White Momo"),
        ("Standard_Challenge_32_12838092.json", 23, "Selesnya Rhythm"),
        ("Standard_Challenge_32_12839956.json", 8, None),
    ]
    for source, index, expected in cases:
        main, side = deck_to_counts(player(source, index))
        assert match_archetype(main, side, rules()) == expected


def test_aliases_default_zone_and_copy_boundaries_are_legacy_compatible():
    for old, new in CARD_ALIASES.items():
        main, side = deck_to_counts({"main_deck": [{"name": old, "qty": 2}], "sideboard": []})
        assert main == {new: 2} and side == {}
    main, side = {"Card": 2}, {"Card": 1}
    assert count_card("Card", "any", main, side) == 3
    assert count_card("Card", "main", main, side) == 2
    assert count_card("Card", "side", main, side) == 1
    for sig, value, expected in [
        ({"name": "Card", "minCopies": 3}, 3, True), ({"name": "Card", "minCopies": 3}, 2, False),
        ({"name": "Card", "maxCopies": 3}, 3, True), ({"name": "Card", "maxCopies": 3}, 4, False),
        ({"name": "Card", "exactCopies": 0}, 0, True),
    ]:
        assert signature_card_met(sig, {"Card": value}, {}) is expected


def test_multi_match_and_repeated_display_names_preserve_first_match_behavior():
    main, side = deck_to_counts(player("Standard_Challenge_32_12838092.json", 23))
    matches = all_legacy_matches(main, side)
    assert matches == ["Selesnya Rhythm", "Selesnya Midrange"]
    assert match_archetype(main, side, rules()) == "Selesnya Rhythm"
    names = [rule["name"] for rule in rules()]
    assert names.count("4-Color Control") == 2 and names.count("Izzet Aggro") == 2
