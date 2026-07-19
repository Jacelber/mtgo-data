"""Format-independent full-match archetype classification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .deck import count_card, deck_to_counts
from .rules import CardCondition, ClassificationRule, RuleSet


ClassificationStatus = Literal["classified", "unknown", "conflict", "invalid_deck"]
ConflictKind = Literal["parent_archetype", "subtype"]


@dataclass(frozen=True)
class ConditionEvidence:
    card: str
    zone: str
    actual_count: int
    min_count: int | None
    max_count: int | None
    exact_count: int | None


@dataclass(frozen=True)
class RuleMatch:
    archetype_id: str
    archetype_name: str
    subtype_id: str | None
    subtype_name: str | None
    rule_id: str
    priority: int
    evidence: tuple[ConditionEvidence, ...]


@dataclass(frozen=True)
class ClassificationResult:
    status: ClassificationStatus
    archetype_id: str | None
    archetype_name: str | None
    subtype_id: str | None
    subtype_name: str | None
    selected_rule_id: str | None
    selected_priority: int | None
    matched_rules: tuple[RuleMatch, ...]
    top_priority_matches: tuple[RuleMatch, ...]
    overridden_matches: tuple[RuleMatch, ...]
    conflict_matches: tuple[RuleMatch, ...]
    conflict_kind: ConflictKind | None
    priority_tie: bool
    errors: tuple[str, ...] = ()


def _condition_evidence(
    condition: CardCondition,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> ConditionEvidence:
    return ConditionEvidence(
        card=condition.card,
        zone=condition.zone,
        actual_count=count_card(condition.card, condition.zone, main_counts, side_counts),
        min_count=condition.min_count,
        max_count=condition.max_count,
        exact_count=condition.exact_count,
    )


def condition_matches(evidence: ConditionEvidence) -> bool:
    if evidence.exact_count is not None:
        return evidence.actual_count == evidence.exact_count
    if evidence.min_count is not None and evidence.actual_count < evidence.min_count:
        return False
    if evidence.max_count is not None and evidence.actual_count > evidence.max_count:
        return False
    return True


def _rule_evidence(
    rule: ClassificationRule,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> tuple[ConditionEvidence, ...] | None:
    evidence = tuple(
        _condition_evidence(condition, main_counts, side_counts)
        for condition in rule.conditions
    )
    return evidence if all(condition_matches(item) for item in evidence) else None


def _match_sort_key(match: RuleMatch) -> tuple[int, str, str, str]:
    return (-match.priority, match.archetype_id, match.rule_id, match.subtype_id or "")


def evaluate_matches(
    rule_set: RuleSet,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> tuple[RuleMatch, ...]:
    """Return every matching rule in deterministic priority/identity order."""

    matches = []
    for archetype in rule_set.archetypes:
        subtype_names = {subtype.id: subtype.name for subtype in archetype.subtypes}
        for rule in archetype.rules:
            evidence = _rule_evidence(rule, main_counts, side_counts)
            if evidence is not None:
                matches.append(
                    RuleMatch(
                        archetype_id=archetype.id,
                        archetype_name=archetype.name,
                        subtype_id=rule.subtype_id,
                        subtype_name=subtype_names.get(rule.subtype_id),
                        rule_id=rule.id,
                        priority=rule.priority,
                        evidence=evidence,
                    )
                )
    return tuple(sorted(matches, key=_match_sort_key))


def _invalid_result(*errors: str) -> ClassificationResult:
    return ClassificationResult(
        status="invalid_deck",
        archetype_id=None,
        archetype_name=None,
        subtype_id=None,
        subtype_name=None,
        selected_rule_id=None,
        selected_priority=None,
        matched_rules=(),
        top_priority_matches=(),
        overridden_matches=(),
        conflict_matches=(),
        conflict_kind=None,
        priority_tie=False,
        errors=tuple(errors),
    )


def _count_errors(zone: str, counts: object) -> list[str]:
    if not isinstance(counts, Mapping):
        return [f"{zone}: must be a card-count mapping"]
    errors = []
    for card, quantity in counts.items():
        if not isinstance(card, str) or not card.strip():
            errors.append(f"{zone}: card names must be non-empty strings")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            errors.append(f"{zone}: card quantities must be non-negative integers")
    return errors


def classify_counts(
    rule_set: RuleSet,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> ClassificationResult:
    """Classify normalized counts without hiding matches, ties, or conflicts."""

    errors = _count_errors("main", main_counts) + _count_errors("side", side_counts)
    if errors:
        return _invalid_result(*dict.fromkeys(errors))

    matches = evaluate_matches(rule_set, main_counts, side_counts)
    if not matches:
        return ClassificationResult(
            status="unknown",
            archetype_id=None,
            archetype_name=None,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=None,
            matched_rules=(),
            top_priority_matches=(),
            overridden_matches=(),
            conflict_matches=(),
            conflict_kind=None,
            priority_tie=False,
        )

    selected_priority = matches[0].priority
    top = tuple(match for match in matches if match.priority == selected_priority)
    overridden = tuple(match for match in matches if match.priority < selected_priority)
    parent_ids = {match.archetype_id for match in top}
    if len(parent_ids) > 1:
        return ClassificationResult(
            status="conflict",
            archetype_id=None,
            archetype_name=None,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=selected_priority,
            matched_rules=matches,
            top_priority_matches=top,
            overridden_matches=overridden,
            conflict_matches=top,
            conflict_kind="parent_archetype",
            priority_tie=True,
        )

    subtype_ids = {match.subtype_id for match in top}
    if len(subtype_ids) > 1:
        parent = top[0]
        return ClassificationResult(
            status="conflict",
            archetype_id=parent.archetype_id,
            archetype_name=parent.archetype_name,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=selected_priority,
            matched_rules=matches,
            top_priority_matches=top,
            overridden_matches=overridden,
            conflict_matches=top,
            conflict_kind="subtype",
            priority_tie=True,
        )

    selected = top[0]
    return ClassificationResult(
        status="classified",
        archetype_id=selected.archetype_id,
        archetype_name=selected.archetype_name,
        subtype_id=selected.subtype_id,
        subtype_name=selected.subtype_name,
        selected_rule_id=selected.rule_id,
        selected_priority=selected.priority,
        matched_rules=matches,
        top_priority_matches=top,
        overridden_matches=overridden,
        conflict_matches=(),
        conflict_kind=None,
        priority_tie=len(top) > 1,
    )


def classify_deck(rule_set: RuleSet, deck: Mapping[str, Any]) -> ClassificationResult:
    """Normalize and classify one deck, returning a sanitized invalid result."""

    if not isinstance(deck, Mapping):
        return _invalid_result("deck: must be a mapping")
    try:
        main_counts, side_counts = deck_to_counts(deck)
    except (KeyError, TypeError, ValueError) as exc:
        return _invalid_result(f"deck: cannot normalize input ({type(exc).__name__})")
    return classify_counts(rule_set, main_counts, side_counts)
