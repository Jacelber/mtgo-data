"""Grixis reanimator and Spider-Man follow the Owner's explicit core boundary."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/classifier_standard_grixis_boundary.json").read_text(
        encoding="utf-8"
    )
)["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["reference"])
def test_complete_retained_lists_follow_the_boundary(rules, case):
    result = classify_deck(rules, case)
    assert {
        "status": result.status,
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
    } == case["expected"]


def test_removing_rewrite_returns_the_current_list_to_grixis_spider_man(rules):
    main, side = deck_to_counts(CASES[0])
    removed = main.pop("Rewrite Regrets")
    main["Stock Up"] = main.get("Stock Up", 0) + removed
    result = classify_counts(rules, main, side)
    assert (result.archetype_id, result.subtype_id) == ("dimir-spider-man", "grixis")


def test_reanimator_does_not_depend_on_three_copies_of_an_auxiliary_looter(rules):
    main, side = deck_to_counts(CASES[0])
    main["Stock Up"] = main.pop("Seasoned Cryomancer")
    main["Stock Up"] += main["Rewrite Regrets"] - 1
    main["Rewrite Regrets"] = 1
    result = classify_counts(rules, main, side)
    assert result.archetype_id == "grixis-reanimator"
    assert {match.archetype_id for match in result.top_priority_matches} == {"grixis-reanimator"}
