"""Reviewed semantic card features for shared production classification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]


COLORS = ("white", "blue", "black", "red", "green")
FEATURE_PREFIX = "__classifier-semantic-"
FEATURE_SCHEMA_VERSION = "1.0.0"


def mana_source_marker(color: str, *, prefix: str = FEATURE_PREFIX) -> str:
    return f"{prefix}main-{color}-source__"


def spell_marker(color: str, *, prefix: str = FEATURE_PREFIX) -> str:
    return f"{prefix}any-{color}-spell__"


def equipment_marker(*, prefix: str = FEATURE_PREFIX) -> str:
    return f"{prefix}main-equipment__"


EQUIPMENT_MARKER = equipment_marker()


@dataclass(frozen=True)
class CardFeatures:
    mana_sources: frozenset[str]
    spell_colors: frozenset[str]
    equipment: bool
    phyrexian_color_neutral: bool


@dataclass(frozen=True)
class SemanticFeatureManifest:
    schema_version: str
    cards: Mapping[str, CardFeatures]


class SemanticFeatureError(ValueError):
    """Raised when semantic feature configuration is malformed or unsafe."""


def _color_set(value: object, path: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SemanticFeatureError(f"{path} must be a list of color names")
    result = frozenset(value)
    unknown = result - set(COLORS)
    if unknown:
        raise SemanticFeatureError(f"{path} has unknown colors: {sorted(unknown)}")
    return result


def load_semantic_feature_manifest(path: str | Path) -> SemanticFeatureManifest:
    """Load the explicit fail-closed feature set used by production rules."""

    source = Path(path)
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SemanticFeatureError(f"{source}: cannot load feature manifest") from exc
    if not isinstance(value, dict):
        raise SemanticFeatureError("feature manifest root must be a mapping")
    allowed_root = {"schema_version", "task_id", "status", "scope", "cards"}
    unknown_root = set(value) - allowed_root
    if unknown_root:
        raise SemanticFeatureError(
            f"feature manifest has unknown fields: {sorted(unknown_root)}"
        )
    if value.get("schema_version") != FEATURE_SCHEMA_VERSION:
        raise SemanticFeatureError(
            f"feature manifest schema_version must be {FEATURE_SCHEMA_VERSION!r}"
        )
    raw_cards = value.get("cards")
    if not isinstance(raw_cards, dict):
        raise SemanticFeatureError("feature manifest cards must be a mapping")

    cards: dict[str, CardFeatures] = {}
    for name, raw in raw_cards.items():
        if not isinstance(name, str) or not name.strip():
            raise SemanticFeatureError("feature card names must be non-empty strings")
        if not isinstance(raw, dict):
            raise SemanticFeatureError(f"cards.{name} must be a mapping")
        unknown_keys = set(raw) - {
            "mana_sources",
            "spell_colors",
            "equipment",
            "phyrexian_color_neutral",
            "evidence",
        }
        if unknown_keys:
            raise SemanticFeatureError(
                f"cards.{name} has unknown fields: {sorted(unknown_keys)}"
            )
        evidence = raw.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise SemanticFeatureError(f"cards.{name}.evidence must be non-empty")
        neutral = raw.get("phyrexian_color_neutral", False)
        equipment = raw.get("equipment", False)
        if not isinstance(neutral, bool) or not isinstance(equipment, bool):
            raise SemanticFeatureError(
                f"cards.{name} boolean feature fields must be booleans"
            )
        spell_colors = _color_set(raw.get("spell_colors"), f"cards.{name}.spell_colors")
        if neutral and spell_colors:
            raise SemanticFeatureError(
                f"cards.{name} cannot be both Phyrexian-neutral and a spell marker"
            )
        cards[name] = CardFeatures(
            mana_sources=_color_set(
                raw.get("mana_sources"), f"cards.{name}.mana_sources"
            ),
            spell_colors=spell_colors,
            equipment=equipment,
            phyrexian_color_neutral=neutral,
        )
    return SemanticFeatureManifest(
        schema_version=FEATURE_SCHEMA_VERSION,
        cards=cards,
    )


def augment_semantic_counts(
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    manifest: SemanticFeatureManifest,
    *,
    prefix: str = FEATURE_PREFIX,
) -> tuple[dict[str, int], dict[str, int]]:
    """Add deterministic semantic markers without changing input mappings."""

    main = dict(main_counts)
    side = dict(side_counts)
    if any(name.startswith(prefix) for name in main | side):
        raise SemanticFeatureError("deck input contains a reserved feature marker")

    for name, quantity in main_counts.items():
        features = manifest.cards.get(name)
        if features is None:
            continue
        for color in features.mana_sources:
            marker = mana_source_marker(color, prefix=prefix)
            main[marker] = main.get(marker, 0) + quantity
        if features.equipment:
            marker = equipment_marker(prefix=prefix)
            main[marker] = main.get(marker, 0) + quantity
        if not features.phyrexian_color_neutral:
            for color in features.spell_colors:
                marker = spell_marker(color, prefix=prefix)
                main[marker] = main.get(marker, 0) + quantity

    for name, quantity in side_counts.items():
        features = manifest.cards.get(name)
        if features is None or features.phyrexian_color_neutral:
            continue
        for color in features.spell_colors:
            marker = spell_marker(color, prefix=prefix)
            side[marker] = side.get(marker, 0) + quantity
    return main, side


def semantic_feature_names(*, prefix: str = FEATURE_PREFIX) -> frozenset[str]:
    """Return every reserved marker supported by the feature adapter."""

    return frozenset(
        [equipment_marker(prefix=prefix)]
        + [mana_source_marker(color, prefix=prefix) for color in COLORS]
        + [spell_marker(color, prefix=prefix) for color in COLORS]
    )
