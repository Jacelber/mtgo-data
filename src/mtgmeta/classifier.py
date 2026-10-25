"""Format-independent full-match archetype classification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Any, Literal

from .classifier_features import SemanticFeatureError, augment_semantic_counts
from .deck import count_card, deck_to_counts
from .rules import AnyCondition, CardCondition, RuleSet
from .classifier_cards import (
    card_facts,
    classifier_card_name,
    normalize_counts,
    deck_colors,
    DeckColors,
    IDENTITY_CONTRACT_VERSION,
    color_policy_subject,
)
from .card_names import CARD_ALIASES, equivalent_basic_land_names


ClassificationStatus = Literal["classified", "unknown", "conflict", "invalid_deck"]
ConflictKind = Literal["parent_archetype", "subtype"]

# Bump this only when classifier evaluation semantics change.  Rule and
# semantic-feature changes are independently included in each rule digest.
CLASSIFIER_ENGINE_VERSION = "1.2.2"


def classifier_digest(rules: RuleSet) -> str:
    """Hash every rule input plus the explicit classifier engine contract."""

    def canonical(value: Any) -> Any:
        if isinstance(value, (set, frozenset)):
            return sorted(value)
        if isinstance(value, dict):
            return {k: canonical(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [canonical(v) for v in value]
        return value

    parents = []
    for parent in sorted(rules.archetypes, key=lambda p: p.id):
        item = asdict(parent)
        item["rules"] = [asdict(r) for r in sorted(parent.rules, key=lambda r: r.id)]
        item["subtypes"] = [
            asdict(t) for t in sorted(parent.subtypes, key=lambda t: t.id)
        ]
        parents.append(item)
    subject = canonical(
        {
            "engine_version": CLASSIFIER_ENGINE_VERSION,
            "rule_schema_version": rules.schema_version,
            "format": rules.format,
            "identity_contract": IDENTITY_CONTRACT_VERSION,
            "aliases": CARD_ALIASES,
            "color_policies": color_policy_subject(),
            "card_facts_sha256": card_facts().digest,
            "semantic_features": asdict(rules.semantic_features)
            if rules.semantic_features
            else None,
            "archetypes": parents,
        }
    )
    encoded = json.dumps(
        subject,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ConditionEvidence:
    card: str
    zone: str
    actual_count: int
    min_count: int | None
    max_count: int | None
    exact_count: int | None
    scope: str = "rule"


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
    color_diagnostics: tuple[tuple[str, DeckColors], ...] = ()


def _condition_evidence(
    condition: CardCondition,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> ConditionEvidence:
    return ConditionEvidence(
        card=(
            "total_count:" + "|".join(condition.cards)
            if condition.cards
            else condition.card
        ),
        zone=condition.zone,
        actual_count=(
            count_card(condition.card, condition.zone, main_counts, side_counts)
            if not condition.cards
            else sum(
                (main_counts.get(name, 0) if condition.zone != "side" else 0)
                + (side_counts.get(name, 0) if condition.zone != "main" else 0)
                for name in dict.fromkeys(
                    alias
                    for n in (condition.cards or (condition.card,))
                    for alias in equivalent_basic_land_names(classifier_card_name(n))
                )
            )
        ),
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


def _conditions_evidence(
    conditions: tuple[CardCondition | AnyCondition, ...],
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    *,
    scope: str = "rule",
) -> tuple[ConditionEvidence, ...] | None:
    evidence: list[ConditionEvidence] = []
    for condition in conditions:
        if isinstance(condition, AnyCondition):
            alternatives = [
                _conditions_evidence(alt, main_counts, side_counts, scope=scope)
                for alt in condition.alternatives
            ]
            successful = [alt for alt in alternatives if alt is not None]
            if not successful:
                return None
            # Retain all successful alternatives in declared order.
            evidence.extend(item for alt in successful for item in alt)
        else:
            item = _condition_evidence(condition, main_counts, side_counts)
            if scope != "rule":
                item = replace(item, scope=scope)
            if not condition_matches(item):
                return None
            evidence.append(item)
    return tuple(evidence)


def _match_sort_key(match: RuleMatch) -> tuple[int, str, str, str]:
    return (-match.priority, match.archetype_id, match.rule_id, match.subtype_id or "")


def _evaluate(
    rule_set: RuleSet,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> tuple[
    tuple[RuleMatch, ...], list[tuple[int, str]], tuple[tuple[str, DeckColors], ...]
]:
    matches = []
    unresolved = []
    diagnostics = []
    colors_by_profile = {}
    for archetype in rule_set.archetypes:
        inherited = _conditions_evidence(
            archetype.conditions, main_counts, side_counts, scope="parent"
        )
        if inherited is None:
            continue
        subtype_names = {s.id: s.name for s in archetype.subtypes}
        structural = []
        for rule in archetype.rules:
            evidence = _conditions_evidence(rule.conditions, main_counts, side_counts)
            if evidence is not None:
                structural.append((rule, inherited + evidence))
        if not structural:
            continue
        colors = None
        if archetype.color_profile is not None:
            profile = archetype.color_profile
            cache_key = (profile, archetype.card_uses)
            if cache_key not in colors_by_profile:
                colors_by_profile[cache_key] = deck_colors(
                    main_counts,
                    side_counts,
                    profile=profile,
                    uses=dict(archetype.card_uses),
                )
            colors = colors_by_profile[cache_key]
            diagnostics.append((archetype.id, colors))
        accepted = False
        for rule, evidence in structural:
            subtype_id = rule.subtype_id
            required_colors = rule.colors
            if subtype_id is None and archetype.color_subtypes:
                if colors is None or colors.missing or colors.unresolved_uses:
                    continue
                subtype_id = next(
                    (
                        key
                        for key, names in archetype.color_subtypes
                        if frozenset(names) == colors.colors
                    ),
                    None,
                )
                if subtype_id is None:
                    continue
                required_colors = tuple(sorted(colors.colors))
            if required_colors is not None:
                if colors is None or colors.missing or colors.unresolved_uses:
                    continue
                observed = colors.colors
                convention = (
                    archetype.color_profile == "modern-creativity"
                    and count_card("Leyline Binding", "any", main_counts, side_counts)
                    > 0
                    and len(colors.basic_land_types) == 5
                )
                if convention:
                    observed = frozenset({"white", "blue", "black", "red", "green"})
                if observed != frozenset(required_colors):
                    continue
                evidence += (
                    ConditionEvidence(
                        "colors:" + ",".join(sorted(observed)),
                        "any",
                        1,
                        1,
                        None,
                        None,
                        "binding-domain-convention" if convention else "color-profile",
                    ),
                )
            accepted = True
            matches.append(
                RuleMatch(
                    archetype.id,
                    archetype.name,
                    subtype_id,
                    subtype_names.get(subtype_id) if subtype_id else None,
                    rule.id,
                    rule.priority,
                    evidence,
                )
            )
        if (
            not accepted
            and colors is not None
            and (colors.missing or colors.unresolved_uses or archetype.require_color_subtype)
        ):
            reason = (
                "missing card facts: " + ", ".join(colors.missing)
                if colors.missing
                else "unresolved card uses: " + ", ".join(colors.unresolved_uses)
                if colors.unresolved_uses
                else "unresolved colors: " + ", ".join(sorted(colors.colors))
            )
            unresolved.append(
                (max(r.priority for r, _ in structural), archetype.id + ": " + reason)
            )
    return (
        tuple(sorted(matches, key=_match_sort_key)),
        sorted(unresolved, key=lambda item: (-item[0], item[1])),
        tuple(sorted(diagnostics, key=lambda item: item[0])),
    )


def evaluate_matches(
    rule_set: RuleSet, main_counts: Mapping[str, int], side_counts: Mapping[str, int]
) -> tuple[RuleMatch, ...]:
    """Return every successful inherited rule in deterministic priority order."""
    return _evaluate(rule_set, main_counts, side_counts)[0]


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

    main_counts = normalize_counts(main_counts)
    side_counts = normalize_counts(side_counts)

    if rule_set.semantic_feature_path is not None:
        if rule_set.semantic_features is None:
            return _invalid_result("rules: semantic feature manifest is not loaded")
        try:
            main_counts, side_counts = augment_semantic_counts(
                main_counts,
                side_counts,
                rule_set.semantic_features,
            )
        except SemanticFeatureError as exc:
            return _invalid_result(f"deck: cannot add semantic features ({exc})")

    matches, unresolved, diagnostics = _evaluate(rule_set, main_counts, side_counts)
    blocking = tuple(
        reason
        for priority, reason in unresolved
        if not matches or priority >= matches[0].priority
    )
    if not matches or blocking:
        if not matches and not blocking:
            blocking = tuple(
                parent + ": unresolved colors: " + ", ".join(sorted(colors.colors))
                for parent, colors in diagnostics
            )
        return ClassificationResult(
            status="unknown",
            archetype_id=None,
            archetype_name=None,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=None,
            matched_rules=matches,
            top_priority_matches=(),
            overridden_matches=(),
            conflict_matches=(),
            conflict_kind=None,
            priority_tie=False,
            errors=blocking,
            color_diagnostics=diagnostics,
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
            color_diagnostics=diagnostics,
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
            color_diagnostics=diagnostics,
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
        color_diagnostics=diagnostics,
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


def color_diagnostics_payload(result: ClassificationResult) -> list[dict[str, Any]]:
    """Serialize review evidence only where needed, without duplicating all decks."""
    return [
        {
            "archetype_id": parent,
            "colors": sorted(colors.colors),
            "missing": list(colors.missing),
            "mana_support": sorted(colors.mana_support),
            "basic_land_types": sorted(colors.basic_land_types),
            "contributions": [
                {**asdict(item), "colors": list(item.colors)}
                for item in colors.contributions
            ],
        }
        for parent, colors in result.color_diagnostics
    ]
