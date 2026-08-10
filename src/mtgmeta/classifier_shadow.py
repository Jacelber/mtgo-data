"""R2-only semantic features for read-only shadow classification.

Production callers continue to pass ordinary card counts directly to
``classify_counts``.  The shadow path adds reserved synthetic counters derived
from an explicit, reviewed feature manifest, then reuses the shared classifier.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import yaml  # type: ignore[import-untyped]

from .classifier import ClassificationResult, classify_counts
from .rules import RuleSet


COLORS = ("white", "blue", "black", "red", "green")
FEATURE_PREFIX = "__classifier-r2-"


def mana_source_marker(color: str) -> str:
    return f"{FEATURE_PREFIX}main-{color}-source__"


def spell_marker(color: str) -> str:
    return f"{FEATURE_PREFIX}any-{color}-spell__"


EQUIPMENT_MARKER = f"{FEATURE_PREFIX}main-equipment__"


@dataclass(frozen=True)
class CardFeatures:
    mana_sources: frozenset[str]
    spell_colors: frozenset[str]
    equipment: bool
    phyrexian_color_neutral: bool


@dataclass(frozen=True)
class ShadowFeatureManifest:
    schema_version: str
    cards: Mapping[str, CardFeatures]


class ShadowFeatureError(ValueError):
    """Raised when the checked-in R2 feature manifest is malformed."""


def _color_set(value: object, path: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ShadowFeatureError(f"{path} must be a list of color names")
    result = frozenset(value)
    unknown = result - set(COLORS)
    if unknown:
        raise ShadowFeatureError(f"{path} has unknown colors: {sorted(unknown)}")
    return result


def load_shadow_feature_manifest(path: str | Path) -> ShadowFeatureManifest:
    """Load the small explicit feature set used by the R2 shadow only."""

    source = Path(path)
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ShadowFeatureError(f"{source}: cannot load feature manifest") from exc
    if not isinstance(value, dict):
        raise ShadowFeatureError("feature manifest root must be a mapping")
    if value.get("schema_version") != "1.0.0":
        raise ShadowFeatureError("feature manifest schema_version must be '1.0.0'")
    raw_cards = value.get("cards")
    if not isinstance(raw_cards, dict):
        raise ShadowFeatureError("feature manifest cards must be a mapping")

    cards: dict[str, CardFeatures] = {}
    for name, raw in raw_cards.items():
        if not isinstance(name, str) or not name.strip():
            raise ShadowFeatureError("feature card names must be non-empty strings")
        if not isinstance(raw, dict):
            raise ShadowFeatureError(f"cards.{name} must be a mapping")
        unknown_keys = set(raw) - {
            "mana_sources",
            "spell_colors",
            "equipment",
            "phyrexian_color_neutral",
            "evidence",
        }
        if unknown_keys:
            raise ShadowFeatureError(
                f"cards.{name} has unknown fields: {sorted(unknown_keys)}"
            )
        neutral = raw.get("phyrexian_color_neutral", False)
        equipment = raw.get("equipment", False)
        if not isinstance(neutral, bool) or not isinstance(equipment, bool):
            raise ShadowFeatureError(
                f"cards.{name} boolean feature fields must be booleans"
            )
        spell_colors = _color_set(raw.get("spell_colors"), f"cards.{name}.spell_colors")
        if neutral and spell_colors:
            raise ShadowFeatureError(
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
    return ShadowFeatureManifest(schema_version="1.0.0", cards=cards)


def augment_shadow_counts(
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    manifest: ShadowFeatureManifest,
) -> tuple[dict[str, int], dict[str, int]]:
    """Add deterministic semantic markers without changing the input mappings."""

    main = dict(main_counts)
    side = dict(side_counts)
    if any(name.startswith(FEATURE_PREFIX) for name in main | side):
        raise ShadowFeatureError("deck input contains a reserved R2 feature marker")

    for name, quantity in main_counts.items():
        features = manifest.cards.get(name)
        if features is None:
            continue
        for color in features.mana_sources:
            marker = mana_source_marker(color)
            main[marker] = main.get(marker, 0) + quantity
        if features.equipment:
            main[EQUIPMENT_MARKER] = main.get(EQUIPMENT_MARKER, 0) + quantity
        if not features.phyrexian_color_neutral:
            for color in features.spell_colors:
                marker = spell_marker(color)
                main[marker] = main.get(marker, 0) + quantity

    for name, quantity in side_counts.items():
        features = manifest.cards.get(name)
        if features is None or features.phyrexian_color_neutral:
            continue
        for color in features.spell_colors:
            marker = spell_marker(color)
            side[marker] = side.get(marker, 0) + quantity
    return main, side


def classify_shadow_counts(
    rule_set: RuleSet,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    manifest: ShadowFeatureManifest,
) -> ClassificationResult:
    """Classify counts through the R2 feature adapter and shared classifier."""

    augmented_main, augmented_side = augment_shadow_counts(
        main_counts, side_counts, manifest
    )
    return classify_counts(rule_set, augmented_main, augmented_side)


def shadow_feature_names() -> frozenset[str]:
    """Return every reserved marker allowed in checked-in R2 shadow rules."""

    return frozenset(
        [EQUIPMENT_MARKER]
        + [mana_source_marker(color) for color in COLORS]
        + [spell_marker(color) for color in COLORS]
    )
