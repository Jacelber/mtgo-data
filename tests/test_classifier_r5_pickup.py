from __future__ import annotations

import json
from pathlib import Path

from tools.migrate_classifier_r5_pickup import (
    DESTINATION_PATHS,
    KEYS,
    SOURCE_HASHES,
    SOURCE_PATHS,
    build_migrated_document,
    migration_delta,
    sha256_path,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_frozen_pickup_baselines_are_exact() -> None:
    for format_id in ("modern", "standard"):
        assert sha256_path(SOURCE_PATHS[format_id]) == SOURCE_HASHES[format_id]


def test_production_pickup_state_is_the_exact_r4_migration() -> None:
    expected_counts = {"modern": (69, 126), "standard": (60, 91)}
    for format_id in ("modern", "standard"):
        migrated, details = build_migrated_document(format_id)
        assert _load(DESTINATION_PATHS[format_id]) == migrated
        identities = migrated[KEYS[format_id]]
        assert (details["entry_count_before"], len(identities)) == expected_counts[
            format_id
        ]
        assert details["entry_count_after"] == len(identities)
        assert details["false_new_prevented"]


def test_pickup_migration_tracks_only_parent_identity_changes() -> None:
    modern = migration_delta("modern")
    standard = migration_delta("standard")
    assert len(modern["added_ids"]) == 57
    assert modern["removed_ids"] == []
    assert modern["renamed_ids"] == []
    assert len(standard["added_ids"]) == 31
    assert standard["removed_ids"] == ["grixis-elementals"]
    assert standard["renamed_ids"] == ["temur-elementals"]

    standard_known = build_migrated_document("standard")[0]["known"]
    assert "Ramp Elementals" in standard_known
    assert "Temur Elementals" not in standard_known
    assert "Grixis Elementals" not in standard_known
