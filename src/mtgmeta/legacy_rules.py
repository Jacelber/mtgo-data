"""Temporary adapters for legacy Standard classifier entry points."""

from __future__ import annotations

from .rules import CardCondition, RuleSet


def _condition_to_legacy(condition: CardCondition) -> dict[str, object]:
    legacy: dict[str, object] = {"name": condition.card}
    if condition.zone != "any":
        legacy["zone"] = condition.zone
    if condition.exact_count is not None:
        legacy["exactCopies"] = condition.exact_count
    else:
        if condition.min_count is not None:
            legacy["minCopies"] = condition.min_count
        if condition.max_count is not None:
            legacy["maxCopies"] = condition.max_count
    return legacy


def to_legacy_archetypes(rule_set: RuleSet) -> list[dict[str, object]]:
    """Flatten a versioned rule set for unchanged first-match legacy callers.

    Explicit rule priority, rather than YAML position, defines the compatibility
    order. Parent display names remain the only classification result exposed by
    this adapter; subtype selection belongs to the shared classifier in P2-05.
    """

    flattened = [
        (
            rule.priority,
            rule.id,
            {
                "name": archetype.name,
                "signatureCards": [
                    _condition_to_legacy(condition) for condition in rule.conditions
                ],
            },
        )
        for archetype in rule_set.archetypes
        for rule in archetype.rules
    ]
    return [item[2] for item in sorted(flattened, key=lambda item: (-item[0], item[1]))]
