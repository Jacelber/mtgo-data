"""Promote the owner-accepted R2 rules into R3 production rule files."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SHADOW_ROOT = ROOT / "docs" / "audits" / "classifier-r2" / "shadow_rules"
MANIFEST_PATH = ROOT / "configs" / "classifier_semantic_features.yaml"
PRODUCTION_ROOT = ROOT / "my_archetypes"
R2_PREFIX = "__classifier-r2-"
R3_PREFIX = "__classifier-semantic-"
ACCEPTED_SHADOW_HASHES = {
    "modern": "687E309E0EA06880E75F9C5C71C7EA7C65C20F4BDFF48CD9F8C2A444F7B4324D",
    "standard": "0FF089445475C4C1EFF283D01F266695CAE8C8D9D81756B5F4A7380F9BE3590C",
}


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def build_production_rules(format_id: str) -> dict[str, Any]:
    source = SHADOW_ROOT / f"{format_id}.yaml"
    expected_hash = ACCEPTED_SHADOW_HASHES.get(format_id)
    if expected_hash is None:
        raise ValueError(f"unsupported R3 format: {format_id}")
    if _sha256(source) != expected_hash:
        raise ValueError(f"accepted R2 {format_id} shadow rules changed")
    value = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{source}: expected a mapping")
    if value.get("schema_version") != "1.0.0" or value.get("format") != format_id:
        raise ValueError(f"{source}: unexpected R2 identity")

    marker_replacements = 0
    for archetype in value["archetypes"]:
        for rule in archetype["rules"]:
            for condition in rule["conditions"]["all"]:
                card = condition["card"]
                if isinstance(card, str) and card.startswith(R2_PREFIX):
                    condition["card"] = R3_PREFIX + card.removeprefix(R2_PREFIX)
                    marker_replacements += 1
    if marker_replacements == 0:
        raise ValueError(f"{source}: no R2 semantic markers found")

    return {
        "schema_version": "1.1.0",
        "format": format_id,
        "semantic_features": {
            "manifest_path": "configs/classifier_semantic_features.yaml",
            "manifest_sha256": sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
        },
        "archetypes": value["archetypes"],
    }


def render_production_rules(format_id: str) -> str:
    document = yaml.safe_dump(
        build_production_rules(format_id),
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )
    if format_id == "modern":
        return (
            "# Adapted from Joan G.E., j6e/mtg-meta-analyzer, "
            "data/archetypes/modern.yaml\n"
            "# at commit 0ecd26bd734cedc6c40e7c753115f796613a32ba "
            "(CC BY 4.0).\n"
            "# Changes: shared schema, stable IDs, explicit priorities and main "
            "zones, explicit Unknown,\n"
            "# reviewed R1/R2 taxonomy, and omission of the upstream "
            "corpus-dependent centroid fallback.\n"
            + document
        )
    return document


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
