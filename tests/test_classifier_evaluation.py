"""Pure-condition short circuit must retain every successful rule's evidence."""
from mtgmeta.classifier import evaluate_matches
from mtgmeta.rules import ArchetypeDefinition, CardCondition, ClassificationRule, RuleSet


def test_failed_conditions_do_not_hide_later_matches_or_truncate_successful_evidence():
    rules = (
        ClassificationRule("insufficient-main", 40, None, (CardCondition("A", "main", min_count=3), CardCondition("B", "side"))),
        ClassificationRule("two-conditions", 30, None, (CardCondition("A", "main", min_count=2), CardCondition("B", "side", exact_count=1))),
        ClassificationRule("forbidden-side", 20, None, (CardCondition("B", "side", min_count=None, max_count=0),)),
        ClassificationRule("combined-zones", 10, None, (CardCondition("A", "any", exact_count=3),)),
    )
    rule_set = RuleSet("1.1.0", "synthetic", (ArchetypeDefinition("a", "A", 1, (), rules),))
    matches = evaluate_matches(rule_set, {"A": 2}, {"A": 1, "B": 1})
    assert [item.rule_id for item in matches] == ["two-conditions", "combined-zones"]
    assert [(item.card, item.zone, item.actual_count) for item in matches[0].evidence] == [("A", "main", 2), ("B", "side", 1)]
    assert matches[1].evidence[0].actual_count == 3
