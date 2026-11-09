"""Owner-reviewed card structures, independent of event/player identifiers."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/legacy/accepted_ew_variants.json").read_text())


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case"])
def test_reviewed_variants_and_rule_order(rules, case):
    for selected_rules in (rules, reordered_rule_set(rules)):
        result = classify_counts(selected_rules, case["main"], case["side"])
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified", case["parent"], case["subtype"],
        )


def test_one_forge_does_not_turn_artifact_big_mana_into_forge_combo(rules):
    case = next(c for c in CASES if c["case"] == "single-forge-artifact-big-mana")
    # Conversely, the full draw engine and key package belongs to Forge.
    combo = next(c for c in CASES if c["case"] == "forge-keys-without-saga")
    assert classify_counts(rules, case["main"], case["side"]).archetype_id == "tron"
    assert classify_counts(rules, combo["main"], combo["side"]).archetype_id == "mystic-forge-combo"


def test_colored_main_plan_is_not_hidden_by_sideboard_tool_exception(rules):
    case = next(c for c in CASES if c["case"] == "voltaic-toolbox-black-sideboard")
    result = classify_counts(rules, {**case["main"], "Barrowgoyf": 3, "Swamp": 2}, case["side"])
    assert (result.archetype_id, result.subtype_id) != ("tron", "colorless")
