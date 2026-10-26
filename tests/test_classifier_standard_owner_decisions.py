"""Owner-approved full lists, distinct taxonomy boundaries and data policy."""

import json
from pathlib import Path

import pytest

from mtgmeta.classifier import NO_SIDEBOARD_REASON, classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.rules import ArchetypeDefinition, CardCondition, ClassificationRule, RuleSet


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/classifier_standard_440878_owner_decisions.json").read_text(
        encoding="utf-8"
    )
)["cases"]
BOUNDARIES = json.loads(
    (ROOT / "tests/fixtures/classifier_standard_440878_overlap_boundaries.json").read_text(
        encoding="utf-8"
    )
)["cases"]


@pytest.fixture(scope="module")
def standard_rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda case: str(case["rank"]))
def test_full_lists_follow_owner_decisions(standard_rules, case):
    result = classify_deck(standard_rules, case)
    assert {
        "status": result.status,
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
    } == case["expected"]


@pytest.mark.parametrize("case", BOUNDARIES, ids=lambda case: case["reference"])
def test_shared_auxiliary_cards_preserve_other_archetypes(standard_rules, case):
    result = classify_deck(standard_rules, case)
    assert {
        "status": result.status,
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
    } == case["expected"]


@pytest.mark.parametrize("format_id", ["standard", "modern", "pioneer", "pauper"])
def test_no_sideboard_policy_precedes_rule_matching_for_every_format(format_id):
    rule = ClassificationRule("core", 10, None, (CardCondition("Core", "main"),))
    rules = RuleSet("1.1.0", format_id, (ArchetypeDefinition("parent", "Parent", 10, (), (rule,)),))
    main = {"Core": 4, "Plains": 56}
    result = classify_counts(rules, main, {})
    assert result.status == "unknown"
    assert result.archetype_id is None
    assert result.matched_rules == ()
    assert result.errors == (NO_SIDEBOARD_REASON,)
    assert main == {"Core": 4, "Plains": 56}
    # The Owner specified exactly 60/0. A nonempty short sideboard and a
    # different main-deck size are not rejected by this policy alone.
    for other_main, side in [(main, {"Plains": 15}), (main, {"Plains": 4}),
                             ({"Core": 4, "Plains": 57}, {})]:
        assert classify_counts(rules, other_main, side).archetype_id == "parent"


def test_distinct_new_parents_require_their_core_in_main(standard_rules):
    for rank, core, parent in [
        (737, "Mutable Explorer", "changelings"),
        (764, "Scrawling Crawler", "dimir-crawler"),
        (622, "Accumulate Wisdom", "bant-lessons"),
    ]:
        case = next(case for case in CASES if case["rank"] == rank)
        main = {c["name"]: c["qty"] for c in case["main_deck"]}
        side = {c["name"]: c["qty"] for c in case["sideboard"]}
        amount = main.pop(core)
        main["Forest"] = main.get("Forest", 0) + amount
        side[core] = amount
        result = classify_counts(standard_rules, main, side)
        assert parent not in {match.archetype_id for match in result.matched_rules}
