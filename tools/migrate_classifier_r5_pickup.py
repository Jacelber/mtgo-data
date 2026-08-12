"""Migrate parent-keyed Pickup known state for the accepted R4 taxonomy."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

from tools.build_classifier_r5_production_rules import (
    BASELINE_ROOT,
    SHADOW_ROOT,
    accepted_shadow_document,
)


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "CLASSIFIER-R5-PRODUCTION-PROMOTION"
BASELINE_PICKUP_ROOT = ROOT / "docs" / "audits" / "classifier-r4" / "baseline_pickup"
SOURCE_PATHS = {
    "modern": BASELINE_PICKUP_ROOT / "modern_known_archetypes.json",
    "standard": BASELINE_PICKUP_ROOT / "standard_known_archetypes.json",
}
DESTINATION_PATHS = {
    "modern": ROOT / "stats" / "modern" / "mtgo" / "pickup" / "known_archetypes.json",
    "standard": ROOT
    / "stats"
    / "standard"
    / "mtgo"
    / "pickup"
    / "known_archetypes.json",
}
SOURCE_HASHES = {
    "modern": "9bdec0902255774386f7222d52a38d09e84ac194c97bb65db4640fecf87ff5fd",
    "standard": "a77116cdec4173b86b7eb37b50beccd9a440e77d3eecb3e31297a56d20a1244c",
}
KEYS = {"modern": "known_ids", "standard": "known"}


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"{path}: unsupported document type")
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def _parents(path: Path) -> dict[str, str]:
    document = _load_mapping(path)
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError(f"{path}: expected archetypes")
    parents = {item["id"]: item["name"] for item in archetypes}
    if len(parents) != len(archetypes):
        raise ValueError(f"{path}: duplicate parent id")
    return parents


def migration_delta(format_id: str) -> dict[str, list[str]]:
    accepted_shadow_document(format_id)
    baseline = _parents(BASELINE_ROOT / f"{format_id}.yaml")
    accepted = _parents(SHADOW_ROOT / f"{format_id}.yaml")
    added_ids = sorted(accepted.keys() - baseline.keys())
    removed_ids = sorted(baseline.keys() - accepted.keys())
    renamed_ids = sorted(
        parent_id
        for parent_id in accepted.keys() & baseline.keys()
        if accepted[parent_id] != baseline[parent_id]
    )
    return {
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "renamed_ids": renamed_ids,
    }


def build_migrated_document(format_id: str) -> tuple[dict[str, list[str]], dict[str, Any]]:
    if format_id not in SOURCE_PATHS:
        raise ValueError(f"unsupported R5 format: {format_id}")
    source = SOURCE_PATHS[format_id]
    if sha256_path(source) != SOURCE_HASHES[format_id]:
        raise ValueError(f"{format_id} frozen Pickup baseline changed")
    document = _load_mapping(source)
    key = KEYS[format_id]
    if set(document) != {key} or not isinstance(document[key], list):
        raise ValueError(f"{format_id} Pickup known state has unexpected structure")
    if any(not isinstance(item, str) or not item for item in document[key]):
        raise ValueError(f"{format_id} Pickup known state has invalid entries")
    if len(document[key]) != len(set(document[key])):
        raise ValueError(f"{format_id} Pickup known state has duplicate entries")

    baseline = _parents(BASELINE_ROOT / f"{format_id}.yaml")
    accepted = _parents(SHADOW_ROOT / f"{format_id}.yaml")
    delta = migration_delta(format_id)
    current = set(document[key])
    if format_id == "modern":
        removed = set(delta["removed_ids"])
        added = set(delta["added_ids"])
        migrated = sorted(current - removed | added)
        false_new_prevented = sorted(added)
    else:
        removed_names = {
            baseline[parent_id]
            for parent_id in delta["removed_ids"]
            if baseline[parent_id] in current
        }
        renamed_old = {
            baseline[parent_id]
            for parent_id in delta["renamed_ids"]
            if baseline[parent_id] in current
        }
        added_names = {accepted[parent_id] for parent_id in delta["added_ids"]}
        renamed_new = {
            accepted[parent_id]
            for parent_id in delta["renamed_ids"]
            if baseline[parent_id] in current
        }
        migrated = sorted(current - removed_names - renamed_old | added_names | renamed_new)
        false_new_prevented = sorted(added_names | renamed_new)

    result = {key: migrated}
    details = {
        **delta,
        "entry_count_before": len(document[key]),
        "entry_count_after": len(migrated),
        "false_new_prevented": false_new_prevented,
    }
    return result, details


def migrate(*, execute: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_id": TASK_ID,
        "status": "applied" if execute else "dry_run",
        "formats": {},
    }
    for format_id in ("modern", "standard"):
        source = SOURCE_PATHS[format_id]
        destination = DESTINATION_PATHS[format_id]
        if sha256_path(destination) != SOURCE_HASHES[format_id]:
            raise ValueError(f"{format_id} production Pickup state is not the R4 baseline")
        document, details = build_migrated_document(format_id)
        payload = (
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        ).encode("utf-8")
        if execute:
            destination.write_bytes(payload)
        result["formats"][format_id] = {
            "source_path": source.relative_to(ROOT).as_posix(),
            "destination_path": destination.relative_to(ROOT).as_posix(),
            "source_sha256": sha256_path(source),
            "result_sha256": sha256(payload).hexdigest(),
            **details,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the accepted R5 Weekly Pickup known-state migration."
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(migrate(execute=args.execute), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
