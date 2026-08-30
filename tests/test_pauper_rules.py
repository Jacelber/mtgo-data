from __future__ import annotations

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.config import load_rule_set


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "my_archetypes" / "pauper.yaml"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "pauper" / "rule_contract.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_case(case: dict[str, object]) -> None:
    rules = load_rule_set(RULES_PATH)
    expected = case["expected"]
    assert isinstance(expected, dict)
    result = classify_counts(rules, case["main"], {})

    assert result.status == expected["status"], case["id"]
    assert result.archetype_id == expected["archetype_id"], case["id"]
    assert result.subtype_id == expected["subtype_id"], case["id"]
    assert result.selected_rule_id == expected["selected_rule_id"], case["id"]
    assert result.conflict_matches == (), case["id"]


def test_pauper_rule_inventory_and_parent_boundaries() -> None:
    rules = load_rule_set(RULES_PATH)
    archetypes = {archetype.id: archetype for archetype in rules.archetypes}
    rule_ids = {
        rule.id for archetype in rules.archetypes for rule in archetype.rules
    }
    fixture_rule_ids = {
        case["expected"]["selected_rule_id"] for case in _fixture()["cases"]
    }

    assert rules.format == "pauper"
    assert len(archetypes) == 64
    assert len(rule_ids) == 89
    assert fixture_rule_ids == rule_ids
    assert "gates" not in archetypes
    assert {
        "selesnya-gates",
        "jeskai-caw-gates",
        "snacker-gates",
        "naya-gates",
        "naya-hawkeye",
        "synthesizer-gates",
        "packbeast-swarm",
        "mardu-synthesizer",
        "esper-midrange",
    }.issubset(archetypes)
    assert archetypes["green-tron"].name == "Monster Tron"
    assert {
        archetype.id: {subtype.id for subtype in archetype.subtypes}
        for archetype in rules.archetypes
        if archetype.subtypes
    } == {
        "ephemerate": {"four-color", "jeskai"},
        "battle-screech": {"boros", "mono-white", "orzhov"},
        "packbeast-swarm": {
            "boros",
            "esper",
            "mardu",
            "mono-white",
            "mono-white-learn",
        },
    }
    for archetype in rules.archetypes:
        if archetype.subtypes:
            assert all(rule.subtype_id is not None for rule in archetype.rules)


@pytest.mark.parametrize("case", _fixture()["cases"], ids=lambda case: case["id"])
def test_each_pauper_rule_has_a_bounded_representative(case: dict[str, object]) -> None:
    _assert_case(case)


@pytest.mark.parametrize(
    "case",
    _fixture()["boundary_cases"],
    ids=lambda case: case["id"],
)
def test_owner_accepted_pauper_boundaries(case: dict[str, object]) -> None:
    _assert_case(case)
