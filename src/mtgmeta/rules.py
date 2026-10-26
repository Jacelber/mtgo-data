"""Versioned shared classification-rule models and semantic validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeGuard

if TYPE_CHECKING:
    from .classifier_cards import CardFacts
    from .classifier_features import SemanticFeatureManifest


RULE_SCHEMA_VERSION = "1.2.0"
SUPPORTED_RULE_SCHEMA_VERSIONS = frozenset({"1.0.0", "1.1.0", RULE_SCHEMA_VERSION})
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
    cards: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnyCondition:
    alternatives: tuple[tuple[CardCondition | AnyCondition, ...], ...]


@dataclass(frozen=True)
class ClassificationRule:
    id: str
    priority: int
    subtype_id: str | None
    conditions: tuple[CardCondition | AnyCondition, ...]
    colors: tuple[str, ...] | None = None


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
    conditions: tuple[CardCondition | AnyCondition, ...] = ()
    color_profile: str | None = None
    require_color_subtype: bool = False
    color_subtypes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    card_uses: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RuleSet:
    schema_version: str
    format: str
    archetypes: tuple[ArchetypeDefinition, ...]
    semantic_feature_path: str | None = None
    semantic_feature_sha256: str | None = None
    semantic_features: SemanticFeatureManifest | None = None
    card_facts_sha256: str | None = None
    facts: CardFacts | None = field(default=None, compare=False, repr=False)


def _is_nonempty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _is_priority(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _unexpected_keys(
    value: dict[str, Any], allowed: set[str], path: str
) -> list[RuleValidationFailure]:
    return [
        RuleValidationFailure(f"{path}.{key}", "is not an allowed field")
        for key in sorted(set(value) - allowed)
    ]


def validate_rule_data(data: Any) -> list[RuleValidationFailure]:
    failures: list[RuleValidationFailure] = []
    if not isinstance(data, dict):
        return [RuleValidationFailure("root", "must be a mapping")]
    schema_version = str(data.get("schema_version", ""))
    allowed_root = {"schema_version", "format", "archetypes"}
    if schema_version in {"1.1.0", RULE_SCHEMA_VERSION}:
        allowed_root.add("semantic_features")
    if schema_version == RULE_SCHEMA_VERSION:
        allowed_root.add("card_facts_sha256")
        if not isinstance(data.get("card_facts_sha256"), str) or not re.fullmatch(
            r"[a-f0-9]{64}", data["card_facts_sha256"]
        ):
            failures.append(
                RuleValidationFailure(
                    "card_facts_sha256", "requires the pinned card facts SHA-256"
                )
            )
    failures.extend(_unexpected_keys(data, allowed_root, "root"))
    if schema_version not in SUPPORTED_RULE_SCHEMA_VERSIONS:
        failures.append(
            RuleValidationFailure(
                "schema_version",
                f"must be one of {sorted(SUPPORTED_RULE_SCHEMA_VERSIONS)!r}",
            )
        )
    semantic_features = data.get("semantic_features")
    if schema_version in {"1.1.0", RULE_SCHEMA_VERSION}:
        if not isinstance(semantic_features, dict):
            failures.append(
                RuleValidationFailure(
                    "semantic_features",
                    f"is required for schema {RULE_SCHEMA_VERSION}",
                )
            )
        else:
            failures.extend(
                _unexpected_keys(
                    semantic_features,
                    {"manifest_path", "manifest_sha256"},
                    "semantic_features",
                )
            )
            manifest_path = semantic_features.get("manifest_path")
            if (
                not _is_nonempty_string(manifest_path)
                or not re.fullmatch(
                    r"configs/[a-z0-9][a-z0-9_./-]*\.ya?ml",
                    manifest_path,
                )
                or ".." in manifest_path.split("/")
            ):
                failures.append(
                    RuleValidationFailure(
                        "semantic_features.manifest_path",
                        "must be a safe repository-relative YAML path under configs/",
                    )
                )
            digest = semantic_features.get("manifest_sha256")
            if not _is_nonempty_string(digest) or not re.fullmatch(
                r"[a-fA-F0-9]{64}", digest
            ):
                failures.append(
                    RuleValidationFailure(
                        "semantic_features.manifest_sha256",
                        "must be a 64-character SHA-256 digest",
                    )
                )
    if not _is_nonempty_string(data.get("format")) or not ID_PATTERN.fullmatch(
        str(data.get("format", ""))
    ):
        failures.append(
            RuleValidationFailure("format", "must be a lowercase hyphenated identifier")
        )
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, list) or not archetypes:
        failures.append(RuleValidationFailure("archetypes", "must be a non-empty list"))
        return failures

    archetype_ids: set[str] = set()
    rule_ids: set[str] = set()
    for i, archetype in enumerate(archetypes):
        ap = f"archetypes[{i}]"
        if not isinstance(archetype, dict):
            failures.append(RuleValidationFailure(ap, "must be a mapping"))
            continue
        allowed_parent = {"id", "name", "priority", "subtypes", "rules"}
        if schema_version == RULE_SCHEMA_VERSION:
            allowed_parent |= {
                "conditions",
                "color_profile",
                "require_color_subtype",
                "color_subtypes",
                "card_uses",
            }
        failures.extend(_unexpected_keys(archetype, allowed_parent, ap))
        if "conditions" in archetype:
            failures.extend(
                _validate_conditions(
                    archetype["conditions"], f"{ap}.conditions", schema_version
                )
            )
        if "card_uses" in archetype:
            from .classifier_cards import (
                CARD_USES, FLING_SECONDARY_FACES, card_facts, classifier_card_name,
            )

            uses = archetype["card_uses"]
            if (
                not isinstance(uses, dict)
                or not archetype.get("color_profile")
                or any(
                    not _is_nonempty_string(k)
                    or not isinstance(v, str) or v not in CARD_USES
                    for k, v in uses.items()
                )
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.card_uses",
                        "requires a color_profile and valid named card-use policies",
                    )
                )
            elif isinstance(uses, dict):
                for name, use in uses.items():
                    if use == "fling_secondary" and (
                        classifier_card_name(name) not in FLING_SECONDARY_FACES
                        or data.get("format") not in {"standard", "pioneer"}
                    ):
                        failures.append(RuleValidationFailure(
                            f"{ap}.card_uses.{name}",
                            "fling_secondary is limited to Sell-Sword/Otter in Standard/Pioneer",
                        ))
                    if use in {"front_only", "adventure_only"}:
                        card = card_facts().cards.get(classifier_card_name(name))
                        if card is None or card.layout != "adventure":
                            failures.append(RuleValidationFailure(
                                f"{ap}.card_uses.{name}",
                                "face selection requires a known adventure card",
                            ))
        if "require_color_subtype" in archetype:
            if (
                not isinstance(archetype["require_color_subtype"], bool)
                or not archetype.get("conditions")
                or not archetype.get("subtypes")
                or not archetype.get("color_profile")
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.require_color_subtype",
                        "requires an independent shared core, color profile and subtypes",
                    )
                )
        if "color_profile" in archetype:
            from .classifier_cards import COLOR_PROFILES

            if archetype["color_profile"] not in COLOR_PROFILES:
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.color_profile", "unknown color profile"
                    )
                )
            elif (
                archetype["color_profile"].startswith("modern-")
                and data.get("format") != "modern"
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.color_profile", "profile is Modern-only"
                    )
                )
            elif (
                archetype["color_profile"].startswith("standard-")
                and data.get("format") != "standard"
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.color_profile", "profile is Standard-only"
                    )
                )
            elif (
                archetype["color_profile"].startswith("pauper-")
                and data.get("format") != "pauper"
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.color_profile", "profile is Pauper-only"
                    )
                )
        archetype_id = archetype.get("id")
        if not _is_nonempty_string(archetype_id) or not ID_PATTERN.fullmatch(
            str(archetype_id or "")
        ):
            failures.append(
                RuleValidationFailure(
                    f"{ap}.id", "must be a lowercase hyphenated identifier"
                )
            )
        elif archetype_id in archetype_ids:
            failures.append(
                RuleValidationFailure(
                    f"{ap}.id", f"duplicates archetype id {archetype_id!r}"
                )
            )
        else:
            archetype_ids.add(archetype_id)
        if not _is_nonempty_string(archetype.get("name")):
            failures.append(
                RuleValidationFailure(f"{ap}.name", "must be a non-empty string")
            )
        if not _is_priority(archetype.get("priority")):
            failures.append(
                RuleValidationFailure(
                    f"{ap}.priority", "must be a non-negative integer"
                )
            )

        subtypes = archetype.get("subtypes", [])
        subtype_ids: set[str] = set()
        subtype_paths: dict[str, str] = {}
        if not isinstance(subtypes, list):
            failures.append(RuleValidationFailure(f"{ap}.subtypes", "must be a list"))
            subtypes = []
        for j, subtype in enumerate(subtypes):
            sp = f"{ap}.subtypes[{j}]"
            if not isinstance(subtype, dict):
                failures.append(RuleValidationFailure(sp, "must be a mapping"))
                continue
            failures.extend(_unexpected_keys(subtype, {"id", "name"}, sp))
            subtype_id = subtype.get("id")
            if not _is_nonempty_string(subtype_id) or not ID_PATTERN.fullmatch(
                str(subtype_id or "")
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{sp}.id", "must be a lowercase hyphenated identifier"
                    )
                )
            elif subtype_id in subtype_ids:
                failures.append(
                    RuleValidationFailure(
                        f"{sp}.id",
                        f"duplicates subtype id {subtype_id!r} within archetype",
                    )
                )
            else:
                subtype_ids.add(subtype_id)
                subtype_paths[subtype_id] = sp
            if not _is_nonempty_string(subtype.get("name")):
                failures.append(
                    RuleValidationFailure(f"{sp}.name", "must be a non-empty string")
                )

        color_subtypes = archetype.get("color_subtypes", {})
        if not isinstance(color_subtypes, dict):
            failures.append(
                RuleValidationFailure(
                    f"{ap}.color_subtypes", "must map subtype ids to color lists"
                )
            )
            color_subtypes = {}
        elif color_subtypes:
            from .classifier_features import COLORS

            seen_colors: set[tuple[str, ...]] = set()
            for subtype, colors in color_subtypes.items():
                if (
                    subtype not in subtype_ids
                    or not isinstance(colors, list)
                    or any(not isinstance(c, str) or c not in COLORS for c in colors)
                ):
                    failures.append(
                        RuleValidationFailure(
                            f"{ap}.color_subtypes",
                            "must map declared subtype ids to colors",
                        )
                    )
                    continue
                key = tuple(sorted(colors))
                if len(colors) != len(set(colors)) or key in seen_colors:
                    failures.append(
                        RuleValidationFailure(
                            f"{ap}.color_subtypes", "must have distinct color sets"
                        )
                    )
                seen_colors.add(key)
            if not archetype.get("color_profile"):
                failures.append(
                    RuleValidationFailure(
                        f"{ap}.color_subtypes", "requires a color_profile"
                    )
                )
        rules = archetype.get("rules")
        if not isinstance(rules, list) or not rules:
            failures.append(
                RuleValidationFailure(f"{ap}.rules", "must be a non-empty list")
            )
            continue
        referenced_subtype_ids: set[str] = set()
        for j, rule in enumerate(rules):
            rp = f"{ap}.rules[{j}]"
            if not isinstance(rule, dict):
                failures.append(RuleValidationFailure(rp, "must be a mapping"))
                continue
            allowed_rule = {"id", "priority", "subtype_id", "conditions"}
            if schema_version == RULE_SCHEMA_VERSION:
                allowed_rule.add("colors")
            failures.extend(_unexpected_keys(rule, allowed_rule, rp))
            if "colors" in rule:
                colors = rule["colors"]
                if (
                    not isinstance(colors, list)
                    or any(
                        c not in {"white", "blue", "black", "red", "green"}
                        for c in colors
                    )
                    or len(colors) != len(set(colors))
                ):
                    failures.append(
                        RuleValidationFailure(
                            f"{rp}.colors", "must be distinct color names"
                        )
                    )
                if "color_profile" not in archetype:
                    failures.append(
                        RuleValidationFailure(
                            f"{rp}.colors", "requires a parent color_profile"
                        )
                    )
            rule_id = rule.get("id")
            if not _is_nonempty_string(rule_id) or not ID_PATTERN.fullmatch(
                str(rule_id or "")
            ):
                failures.append(
                    RuleValidationFailure(
                        f"{rp}.id", "must be a lowercase hyphenated identifier"
                    )
                )
            elif rule_id in rule_ids:
                failures.append(
                    RuleValidationFailure(f"{rp}.id", f"duplicates rule id {rule_id!r}")
                )
            else:
                rule_ids.add(rule_id)
            if not _is_priority(rule.get("priority")):
                failures.append(
                    RuleValidationFailure(
                        f"{rp}.priority", "must be a non-negative integer"
                    )
                )
            subtype_id = rule.get("subtype_id")
            if subtype_id is None and subtype_ids and not color_subtypes:
                failures.append(
                    RuleValidationFailure(
                        f"{rp}.subtype_id",
                        "must select a subtype when the parent defines subtypes",
                    )
                )
            elif subtype_id is not None:
                if not _is_nonempty_string(subtype_id) or not ID_PATTERN.fullmatch(
                    str(subtype_id or "")
                ):
                    failures.append(
                        RuleValidationFailure(
                            f"{rp}.subtype_id",
                            "must be null or a lowercase hyphenated identifier",
                        )
                    )
                elif subtype_id not in subtype_ids:
                    failures.append(
                        RuleValidationFailure(
                            f"{rp}.subtype_id",
                            f"references unknown subtype {subtype_id!r}",
                        )
                    )
                else:
                    referenced_subtype_ids.add(subtype_id)
            failures.extend(
                _validate_conditions(
                    rule.get("conditions"),
                    f"{rp}.conditions",
                    schema_version,
                    allow_empty=bool(archetype.get("conditions")) or "colors" in rule,
                )
            )
        if any(isinstance(r, dict) and r.get("subtype_id") is None for r in rules):
            referenced_subtype_ids.update(color_subtypes)
        for subtype_id in sorted(subtype_ids - referenced_subtype_ids):
            failures.append(
                RuleValidationFailure(
                    f"{subtype_paths[subtype_id]}.id",
                    f"subtype {subtype_id!r} is not referenced by any rule",
                )
            )
    return failures


def _validate_conditions(
    value: Any, path: str, version: str, *, allow_empty: bool = False
) -> list[RuleValidationFailure]:
    failures: list[RuleValidationFailure] = []
    if not isinstance(value, dict):
        return [RuleValidationFailure(path, "must be a mapping")]
    failures.extend(_unexpected_keys(value, {"all"}, path))
    items = value.get("all")
    if not isinstance(items, list) or (not items and not allow_empty):
        return failures + [
            RuleValidationFailure(path + ".all", "must be a non-empty list")
        ]
    for i, item in enumerate(items):
        cp = f"{path}.all[{i}]"
        if not isinstance(item, dict):
            failures.append(RuleValidationFailure(cp, "must be a mapping"))
            continue
        if "any" in item and version == RULE_SCHEMA_VERSION:
            failures.extend(_unexpected_keys(item, {"any"}, cp))
            if not isinstance(item["any"], list) or not item["any"]:
                failures.append(
                    RuleValidationFailure(cp + ".any", "must be a non-empty list")
                )
            else:
                for j, alternative in enumerate(item["any"]):
                    failures.extend(
                        _validate_conditions(alternative, f"{cp}.any[{j}]", version)
                    )
            continue
        allowed = {"card", "zone", "min_count", "max_count", "exact_count"}
        if version == RULE_SCHEMA_VERSION:
            allowed.add("total_count")
        failures.extend(_unexpected_keys(item, allowed, cp))
        if "total_count" in item:
            names = item["total_count"]
            if (
                "card" in item
                or not isinstance(names, list)
                or not names
                or any(not _is_nonempty_string(n) for n in names)
                or len(names) != len(set(names))
            ):
                failures.append(
                    RuleValidationFailure(
                        cp + ".total_count",
                        "requires distinct card names instead of card",
                    )
                )
        elif not _is_nonempty_string(item.get("card")):
            failures.append(
                RuleValidationFailure(cp + ".card", "must be a non-empty string")
            )
        if item.get("zone", "any") not in ZONES:
            failures.append(
                RuleValidationFailure(cp + ".zone", "must be one of any, main, side")
            )
        keys = [k for k in ("min_count", "max_count", "exact_count") if k in item]
        for key in keys:
            if not _is_priority(item[key]):
                failures.append(
                    RuleValidationFailure(
                        cp + "." + key, "must be a non-negative integer"
                    )
                )
        if "exact_count" in item and len(keys) > 1:
            failures.append(
                RuleValidationFailure(
                    cp, "exact_count cannot be combined with min_count or max_count"
                )
            )
        if (
            _is_priority(item.get("min_count"))
            and _is_priority(item.get("max_count"))
            and item["min_count"] > item["max_count"]
        ):
            failures.append(
                RuleValidationFailure(cp, "min_count must not exceed max_count")
            )
    return failures


def build_conditions(value: dict[str, Any]) -> tuple[CardCondition | AnyCondition, ...]:
    conditions: list[CardCondition | AnyCondition] = []
    for item in value["all"]:
        if "any" in item:
            conditions.append(
                AnyCondition(tuple(build_conditions(alt) for alt in item["any"]))
            )
        else:
            specified = any(
                k in item for k in ("min_count", "max_count", "exact_count")
            )
            names = tuple(item.get("total_count", ()))
            conditions.append(
                CardCondition(
                    item.get("card", "total_count"),
                    item.get("zone", "any"),
                    item.get("min_count", None if specified else 1),
                    item.get("max_count"),
                    item.get("exact_count"),
                    names,
                )
            )
    return tuple(conditions)


def leaf_conditions(
    conditions: tuple[CardCondition | AnyCondition, ...],
) -> tuple[CardCondition, ...]:
    return tuple(
        leaf
        for condition in conditions
        for leaf in (
            leaf_conditions(tuple(c for alt in condition.alternatives for c in alt))
            if isinstance(condition, AnyCondition)
            else (condition,)
        )
    )


def build_rule_set(data: dict[str, Any]) -> RuleSet:
    """Build immutable models from validated data, retaining parent inheritance."""
    archetypes = []
    for parent in data["archetypes"]:
        subtypes = tuple(
            SubtypeDefinition(s["id"], s["name"], parent["id"])
            for s in parent.get("subtypes", [])
        )
        rules = tuple(
            ClassificationRule(
                r["id"],
                r["priority"],
                r.get("subtype_id"),
                build_conditions(r["conditions"]),
                tuple(sorted(r["colors"])) if "colors" in r else None,
            )
            for r in parent["rules"]
        )
        archetypes.append(
            ArchetypeDefinition(
                parent["id"],
                parent["name"],
                parent["priority"],
                subtypes,
                rules,
                build_conditions(parent.get("conditions", {"all": []})),
                parent.get("color_profile"),
                parent.get("require_color_subtype", False),
                tuple(
                    (k, tuple(sorted(v)))
                    for k, v in sorted(parent.get("color_subtypes", {}).items())
                ),
                tuple(sorted(parent.get("card_uses", {}).items())),
            )
        )
    semantic = data.get("semantic_features", {})
    return RuleSet(
        data["schema_version"],
        data["format"],
        tuple(archetypes),
        semantic.get("manifest_path"),
        semantic.get("manifest_sha256", "").lower() or None,
        card_facts_sha256=data.get("card_facts_sha256"),
    )
