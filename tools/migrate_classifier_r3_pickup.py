"""Apply the owner-accepted R3 Weekly Pickup known-state migration."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "audits" / "classifier-r2" / "results" / "pickup_dry_run.json"
SOURCE_PATHS = {
    "modern": ROOT / "stats" / "modern" / "mtgo" / "pickup" / "known_archetypes.json",
    "standard": ROOT / "stats" / "standard" / "mtgo" / "pickup" / "known_archetypes.json",
}
KEYS = {"modern": "known_ids", "standard": "known"}


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def migration_plan() -> dict[str, Any]:
    plan = _load_json(PLAN_PATH)
    if plan.get("status") != "dry_run_not_applied":
        raise ValueError("accepted R2 Pickup plan has unexpected status")
    return plan


def build_migrated_document(
    format_id: str,
    document: dict[str, Any],
    plan: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    if format_id not in SOURCE_PATHS:
        raise ValueError(f"unsupported R3 format: {format_id}")
    key = KEYS[format_id]
    if set(document) != {key} or not isinstance(document[key], list):
        raise ValueError(f"{format_id} known state has unexpected structure")
    current = document[key]
    if any(not isinstance(item, str) or not item for item in current):
        raise ValueError(f"{format_id} known state contains an invalid identity")
    if len(current) != len(set(current)):
        raise ValueError(f"{format_id} known state contains duplicate identities")

    accepted = (plan or migration_plan())["formats"][format_id]
    if len(current) != accepted["entry_count_before"]:
        raise ValueError(f"{format_id} known-state count does not match R2")
    remove = set(accepted["removed"])
    add = set(accepted["added"])
    current_set = set(current)
    if not remove <= current_set or add & current_set:
        raise ValueError(f"{format_id} known-state identities do not match R2")
    migrated = sorted(current_set - remove | add)
    if len(migrated) != accepted["entry_count_after_dry_run"]:
        raise ValueError(f"{format_id} migrated count does not match R2")
    return {key: migrated}


def migrate(*, execute: bool) -> dict[str, Any]:
    plan = migration_plan()
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_id": "CLASSIFIER-R3-PRODUCTION-MIGRATION",
        "status": "applied" if execute else "dry_run",
        "formats": {},
    }
    for format_id, path in SOURCE_PATHS.items():
        accepted = plan["formats"][format_id]
        before_hash = sha256_path(path)
        if before_hash != accepted["source_sha256_before"]:
            raise ValueError(f"{format_id} known-state source hash does not match R2")
        migrated = build_migrated_document(format_id, _load_json(path), plan)
        payload = (
            json.dumps(migrated, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        ).encode("utf-8")
        if execute:
            path.write_bytes(payload)
        result["formats"][format_id] = {
            "path": path.relative_to(ROOT).as_posix(),
            "source_sha256": before_hash,
            "result_sha256": sha256(payload).hexdigest().upper(),
            "removed": accepted["removed"],
            "added": accepted["added"],
            "false_new_prevented": accepted["false_new_prevented"],
            "entry_count_before": accepted["entry_count_before"],
            "entry_count_after": len(migrated[KEYS[format_id]]),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the accepted R3 Weekly Pickup known-state migration."
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(migrate(execute=args.execute), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
