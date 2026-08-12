from __future__ import annotations

import json
from pathlib import Path

from tools.migrate_classifier_r3_pickup import (
    KEYS,
    build_migrated_document,
    migration_plan,
    sha256_path,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINES = {
    "modern": ROOT
    / "docs"
    / "audits"
    / "classifier-r2"
    / "baseline_pickup"
    / "modern_known_archetypes.json",
    "standard": ROOT
    / "docs"
    / "audits"
    / "classifier-r2"
    / "baseline_pickup"
    / "standard_known_archetypes.json",
}
R3_PRODUCTION_BASELINES = {
    "modern": ROOT
    / "docs"
    / "audits"
    / "classifier-r4"
    / "baseline_pickup"
    / "modern_known_archetypes.json",
    "standard": ROOT
    / "docs"
    / "audits"
    / "classifier-r4"
    / "baseline_pickup"
    / "standard_known_archetypes.json",
}


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_production_known_state_is_the_exact_accepted_migration() -> None:
    plan = migration_plan()
    for format_id in ("modern", "standard"):
        accepted = plan["formats"][format_id]
        assert sha256_path(BASELINES[format_id]) == accepted["source_sha256_before"]
        migrated = build_migrated_document(format_id, _load(BASELINES[format_id]), plan)
        production = _load(R3_PRODUCTION_BASELINES[format_id])
        assert production == migrated
        identities = production[KEYS[format_id]]
        assert isinstance(identities, list)
        assert len(identities) == accepted["entry_count_after_dry_run"]
        assert set(accepted["removed"]).isdisjoint(identities)
        assert set(accepted["added"]) <= set(identities)
        assert accepted["false_new_prevented"] == accepted["added"]
