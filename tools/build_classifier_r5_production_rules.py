"""Promote the exact owner-accepted R4 shadows into production rule files."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "CLASSIFIER-R5-PRODUCTION-PROMOTION"
SHADOW_ROOT = ROOT / "docs" / "audits" / "classifier-r4" / "shadow_rules"
BASELINE_ROOT = ROOT / "docs" / "audits" / "classifier-r4" / "baseline_rules"
PRODUCTION_ROOT = ROOT / "my_archetypes"
MANIFEST_PATH = ROOT / "configs" / "classifier_semantic_features.yaml"
ACCEPTED_SHADOW_HASHES = {
    "modern": "5bff0207af7e43d3b59807c102ab323a0e51109e7543e27e59f293bade632b31",
    "standard": "b72aa3fcb0202eb9bc5d9c1f6f88abbe76d8d8ca29923662e3a75f8e54d3da74",
}
BASELINE_HASHES = {
    "modern": "df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045",
    "standard": "d88c3342826343f07442c37d4652b4caac5be7f690d21122fc31884b63eb37f5",
}
EXPECTED_INVENTORIES = {
    "modern": (127, 70, 205),
    "standard": (102, 11, 126),
}
MANIFEST_SHA256 = "0cd94ee3a4d6974f88446a660e661943d1cc2c4d8a25891dd6d214931a6aa999"


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a mapping")
    return value


def _inventory(document: dict[str, Any]) -> tuple[int, int, int]:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("accepted R4 shadow has no archetype list")
    return (
        len(archetypes),
        sum(len(item.get("subtypes", [])) for item in archetypes),
        sum(len(item.get("rules", [])) for item in archetypes),
    )


def accepted_shadow_document(format_id: str) -> dict[str, Any]:
    if format_id not in ACCEPTED_SHADOW_HASHES:
        raise ValueError(f"unsupported R5 format: {format_id}")
    baseline_path = BASELINE_ROOT / f"{format_id}.yaml"
    shadow_path = SHADOW_ROOT / f"{format_id}.yaml"
    if sha256_path(baseline_path) != BASELINE_HASHES[format_id]:
        raise ValueError(f"frozen R3 {format_id} production baseline changed")
    if sha256_path(shadow_path) != ACCEPTED_SHADOW_HASHES[format_id]:
        raise ValueError(f"accepted R4 {format_id} shadow changed")
    if sha256_path(MANIFEST_PATH) != MANIFEST_SHA256:
        raise ValueError("classifier semantic manifest changed")

    document = _load_mapping(shadow_path)
    if document.get("schema_version") != "1.1.0":
        raise ValueError(f"{format_id}: unexpected rule schema")
    if document.get("format") != format_id:
        raise ValueError(f"{format_id}: shadow format mismatch")
    if document.get("semantic_features") != {
        "manifest_path": "configs/classifier_semantic_features.yaml",
        "manifest_sha256": MANIFEST_SHA256,
    }:
        raise ValueError(f"{format_id}: unexpected semantic manifest binding")
    if _inventory(document) != EXPECTED_INVENTORIES[format_id]:
        raise ValueError(f"{format_id}: accepted R4 inventory changed")
    return document


def render_production_rules(format_id: str) -> str:
    accepted_shadow_document(format_id)
    return (SHADOW_ROOT / f"{format_id}.yaml").read_text(encoding="utf-8")


def main() -> int:
    for format_id in ("modern", "standard"):
        destination = PRODUCTION_ROOT / f"{format_id}.yaml"
        destination.write_text(
            render_production_rules(format_id),
            encoding="utf-8",
            newline="\n",
        )
        print(destination.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
