"""Versioned shared classification-rule models and semantic validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


RULE_SCHEMA_VERSION = "1.0.0"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ZONES = frozenset({"any", "main", "side"})


@dataclass(frozen=True)
class RuleValidationFailure:
    path: str
    message: str


@dataclass(frozen=True)
class CardCondition:
    card: str
    zone: str = "any"
    min_count: int | None = 1
    max_count: int | None = None
    exact_count: int | None = None


@dataclass(frozen=True)
class ClassificationRule:
    id: str
    priority: int
    subtype_id: str | None
    conditions: tuple[CardCondition, ...]


@dataclass(frozen=True)
class SubtypeDefinition:
    id: str
    name: str
    parent_archetype_id: str


@dataclass(frozen=True)
class ArchetypeDefinition:
    id: str
    name: str
    priority: int
    subtypes: tuple[SubtypeDefinition, ...]
    rules: tuple[ClassificationRule, ...]


@dataclass(frozen=True)
class RuleSet:
    schema_version: str
    format: str
    archetypes: tuple[ArchetypeDefinition, ...]


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_priority(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _unexpected_keys(value: dict[str, Any], allowed: set[str], path: str) -> list[RuleValidationFailure]:
    return [RuleValidationFailure(f"{path}.{key}", "is not an allowed field") for key in sorted(set(value) - allowed)]


def validate_rule_data(data: Any) -> list[RuleValidationFailure]:
    failures: list[RuleValidationFailure] = []
    if not isinstance(data, dict):
        return [RuleValidationFailure("root", "must be a mapping")]
    failures.extend(_unexpected_keys(data, {"schema_version", "format", "archetypes"}, "root"))
    if data.get("schema_version") != RULE_SCHEMA_VERSION:
        failures.append(RuleValidationFailure("schema_version", f"must equal {RULE_SCHEMA_VERSION!r}"))
    if not _is_nonempty_string(data.get("format")) or not ID_PATTERN.fullmatch(str(data.get("format", ""))):
        failures.append(RuleValidationFailure("format", "must be a lowercase hyphenated identifier"))
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, list) or not archetypes:
        failures.append(RuleValidationFailure("archetypes", "must be a non-empty list"))
        return failures

    archetype_ids: set[str] = set()
    rule_ids: set[str] = set()
    for i, archetype in enumerate(archetypes):
        ap = f"archetypes[{i}]"
        if not isinstance(archetype, dict):
            failures.append(RuleValidationFailure(ap, "must be a mapping")); continue
        failures.extend(_unexpected_keys(archetype, {"id", "name", "priority", "subtypes", "rules"}, ap))
        archetype_id = archetype.get("id")
        if not _is_nonempty_string(archetype_id) or not ID_PATTERN.fullmatch(str(archetype_id or "")):
            failures.append(RuleValidationFailure(f"{ap}.id", "must be a lowercase hyphenated identifier"))
        elif archetype_id in archetype_ids:
            failures.append(RuleValidationFailure(f"{ap}.id", f"duplicates archetype id {archetype_id!r}"))
        else:
            archetype_ids.add(archetype_id)
        if not _is_nonempty_string(archetype.get("name")):
            failures.append(RuleValidationFailure(f"{ap}.name", "must be a non-empty string"))
        if not _is_priority(archetype.get("priority")):
            failures.append(RuleValidationFailure(f"{ap}.priority", "must be a non-negative integer"))

        subtypes = archetype.get("subtypes", [])
        subtype_ids: set[str] = set()
        subtype_paths: dict[str, str] = {}
        if not isinstance(subtypes, list):
            failures.append(RuleValidationFailure(f"{ap}.subtypes", "must be a list")); subtypes = []
        for j, subtype in enumerate(subtypes):
            sp = f"{ap}.subtypes[{j}]"
            if not isinstance(subtype, dict):
                failures.append(RuleValidationFailure(sp, "must be a mapping")); continue
            failures.extend(_unexpected_keys(subtype, {"id", "name"}, sp))
            subtype_id = subtype.get("id")
            if not _is_nonempty_string(subtype_id) or not ID_PATTERN.fullmatch(str(subtype_id or "")):
                failures.append(RuleValidationFailure(f"{sp}.id", "must be a lowercase hyphenated identifier"))
            elif subtype_id in subtype_ids:
                failures.append(RuleValidationFailure(f"{sp}.id", f"duplicates subtype id {subtype_id!r} within archetype"))
            else:
                subtype_ids.add(subtype_id)
                subtype_paths[subtype_id] = sp
            if not _is_nonempty_string(subtype.get("name")):
                failures.append(RuleValidationFailure(f"{sp}.name", "must be a non-empty string"))

        rules = archetype.get("rules")
        if not isinstance(rules, list) or not rules:
            failures.append(RuleValidationFailure(f"{ap}.rules", "must be a non-empty list")); continue
        referenced_subtype_ids: set[str] = set()
        for j, rule in enumerate(rules):
            rp = f"{ap}.rules[{j}]"
            if not isinstance(rule, dict):
                failures.append(RuleValidationFailure(rp, "must be a mapping")); continue
            failures.extend(_unexpected_keys(rule, {"id", "priority", "subtype_id", "conditions"}, rp))
            rule_id = rule.get("id")
            if not _is_nonempty_string(rule_id) or not ID_PATTERN.fullmatch(str(rule_id or "")):
                failures.append(RuleValidationFailure(f"{rp}.id", "must be a lowercase hyphenated identifier"))
            elif rule_id in rule_ids:
                failures.append(RuleValidationFailure(f"{rp}.id", f"duplicates rule id {rule_id!r}"))
            else:
                rule_ids.add(rule_id)
            if not _is_priority(rule.get("priority")):
                failures.append(RuleValidationFailure(f"{rp}.priority", "must be a non-negative integer"))
            subtype_id = rule.get("subtype_id")
            if subtype_id is not None:
                if not _is_nonempty_string(subtype_id) or not ID_PATTERN.fullmatch(str(subtype_id or "")):
                    failures.append(RuleValidationFailure(f"{rp}.subtype_id", "must be null or a lowercase hyphenated identifier"))
                elif subtype_id not in subtype_ids:
                    failures.append(RuleValidationFailure(f"{rp}.subtype_id", f"references unknown subtype {subtype_id!r}"))
                else:
                    referenced_subtype_ids.add(subtype_id)
            conditions = rule.get("conditions")
            if not isinstance(conditions, dict):
                failures.append(RuleValidationFailure(f"{rp}.conditions", "must be a mapping")); continue
            failures.extend(_unexpected_keys(conditions, {"all"}, f"{rp}.conditions"))
            all_conditions = conditions.get("all")
            if not isinstance(all_conditions, list) or not all_conditions:
                failures.append(RuleValidationFailure(f"{rp}.conditions.all", "must be a non-empty list")); continue
            for k, condition in enumerate(all_conditions):
                cp = f"{rp}.conditions.all[{k}]"
                if not isinstance(condition, dict):
                    failures.append(RuleValidationFailure(cp, "must be a mapping")); continue
                failures.extend(_unexpected_keys(condition, {"card", "zone", "min_count", "max_count", "exact_count"}, cp))
                if not _is_nonempty_string(condition.get("card")):
                    failures.append(RuleValidationFailure(f"{cp}.card", "must be a non-empty string"))
                if condition.get("zone", "any") not in ZONES:
                    failures.append(RuleValidationFailure(f"{cp}.zone", "must be one of any, main, side"))
                count_keys = [key for key in ("min_count", "max_count", "exact_count") if key in condition]
                for key in count_keys:
                    if not _is_priority(condition[key]):
                        failures.append(RuleValidationFailure(f"{cp}.{key}", "must be a non-negative integer"))
                if "exact_count" in condition and len(count_keys) > 1:
                    failures.append(RuleValidationFailure(cp, "exact_count cannot be combined with min_count or max_count"))
                if _is_priority(condition.get("min_count")) and _is_priority(condition.get("max_count")) and condition["min_count"] > condition["max_count"]:
                    failures.append(RuleValidationFailure(cp, "min_count must not exceed max_count"))
        for subtype_id in sorted(subtype_ids - referenced_subtype_ids):
            failures.append(RuleValidationFailure(f"{subtype_paths[subtype_id]}.id", f"subtype {subtype_id!r} is not referenced by any rule"))
    return failures


def build_rule_set(data: dict[str, Any]) -> RuleSet:
    """Build immutable models from data that has passed ``validate_rule_data``."""

    archetypes = []
    for archetype in data["archetypes"]:
        subtypes = tuple(SubtypeDefinition(item["id"], item["name"], archetype["id"]) for item in archetype.get("subtypes", []))
        rules = []
        for rule in archetype["rules"]:
            conditions = []
            for item in rule["conditions"]["all"]:
                specified = any(key in item for key in ("min_count", "max_count", "exact_count"))
                conditions.append(CardCondition(
                    card=item["card"], zone=item.get("zone", "any"),
                    min_count=item.get("min_count", None if specified else 1),
                    max_count=item.get("max_count"), exact_count=item.get("exact_count"),
                ))
            rules.append(ClassificationRule(rule["id"], rule["priority"], rule.get("subtype_id"), tuple(conditions)))
        archetypes.append(ArchetypeDefinition(archetype["id"], archetype["name"], archetype["priority"], subtypes, tuple(rules)))
    return RuleSet(data["schema_version"], data["format"], tuple(archetypes))
