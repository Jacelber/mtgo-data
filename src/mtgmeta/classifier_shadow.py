"""Compatibility adapter that reproduces the accepted R2 shadow evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .classifier import ClassificationResult, classify_counts
from .classifier_features import (
    CardFeatures,
    SemanticFeatureError,
    SemanticFeatureManifest,
    augment_semantic_counts,
    equipment_marker,
    load_semantic_feature_manifest,
    mana_source_marker as _mana_source_marker,
    semantic_feature_names,
    spell_marker as _spell_marker,
)
from .rules import RuleSet


FEATURE_PREFIX = "__classifier-r2-"


def mana_source_marker(color: str) -> str:
    return _mana_source_marker(color, prefix=FEATURE_PREFIX)


def spell_marker(color: str) -> str:
    return _spell_marker(color, prefix=FEATURE_PREFIX)


EQUIPMENT_MARKER = equipment_marker(prefix=FEATURE_PREFIX)
ShadowFeatureManifest = SemanticFeatureManifest
ShadowFeatureError = SemanticFeatureError


def load_shadow_feature_manifest(path: str | Path) -> SemanticFeatureManifest:
    """Load the exact manifest used to reproduce the R2 shadow."""

    return load_semantic_feature_manifest(path)


def augment_shadow_counts(
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    manifest: SemanticFeatureManifest,
) -> tuple[dict[str, int], dict[str, int]]:
    """Add deterministic semantic markers without changing the input mappings."""

    return augment_semantic_counts(
        main_counts,
        side_counts,
        manifest,
        prefix=FEATURE_PREFIX,
    )


def classify_shadow_counts(
    rule_set: RuleSet,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
    manifest: SemanticFeatureManifest,
) -> ClassificationResult:
    """Classify counts through the R2 feature adapter and shared classifier."""

    augmented_main, augmented_side = augment_shadow_counts(
        main_counts, side_counts, manifest
    )
    return classify_counts(rule_set, augmented_main, augmented_side)


def shadow_feature_names() -> frozenset[str]:
    """Return every reserved marker allowed in checked-in R2 shadow rules."""

    return semantic_feature_names(prefix=FEATURE_PREFIX)


__all__ = [
    "CardFeatures",
    "EQUIPMENT_MARKER",
    "ShadowFeatureError",
    "ShadowFeatureManifest",
    "augment_shadow_counts",
    "classify_shadow_counts",
    "load_shadow_feature_manifest",
    "mana_source_marker",
    "shadow_feature_names",
    "spell_marker",
]
