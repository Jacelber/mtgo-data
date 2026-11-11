"""Losslessly encode existing public products and rebind their byte descriptors.

This preparation-only pass never recalculates statistics, alters raw inputs,
advances a week, records acceptance, or writes remotely. Normal producers also
emit/accept these compact representations for subsequent regeneration.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from mtgmeta.config import load_format_registry
from mtgmeta.melee import publish
from mtgmeta.melee.stats import statistics_document_bytes
from mtgmeta.mtgo.metadata import generate_metadata
from mtgmeta.mtgo.publication import inspect_publication, require_private_output
from mtgmeta.classifier_closure import validate_current_melee


def read(path):
    return json.loads(path.read_bytes())


def without_byte_descriptors(value):
    if isinstance(value, dict):
        return {
            k: without_byte_descriptors(v)
            for k, v in value.items()
            if k not in {"sha256", "bytes"}
        }
    if isinstance(value, list):
        return [without_byte_descriptors(v) for v in value]
    return value


def compact_public_products(root: Path, *, execute: bool):
    root = root.resolve()
    require_private_output(ROOT, root / "index.html")
    formats = [
        f.id
        for f in load_format_registry(root / "configs/formats.yaml").formats
        if f.public
    ]
    selected, events, meta_before, catalog_before = set(), [], {}, {}
    for fmt in formats:
        problems = inspect_publication(root, fmt)
        if problems:
            raise ValueError(f"Unbound existing MTGO product: {fmt}: {problems}")
        meta_before[fmt] = read(root / f"stats/{fmt}/mtgo/meta.json")
        selected.update((root / f"reports/{fmt}/mtgo").glob("*.json"))
        selected.update((root / f"stats/{fmt}/mtgo").glob("matchup_*.json"))
        catalog = root / f"stats/{fmt}/melee/index.json"
        if not catalog.is_file():
            continue
        catalog_before[fmt] = read(catalog)
        for item in catalog_before[fmt]["events"]:
            event_id = str(item["event_id"])
            events.append((fmt, event_id))
            for name in publish.OUTPUT_NAMES:
                selected.add(root / f"stats/{fmt}/melee/events/{event_id}/{name}.json")
    if execute:
        for fmt in catalog_before:
            validate_current_melee(root, fmt)
    changed, saved = [], 0
    changed_events = set()
    for path in sorted(selected):
        old = path.read_bytes()
        value = json.loads(old)
        compact = statistics_document_bytes(value, compact=True)
        if json.loads(compact) != value:
            raise ValueError(f"JSON value changed: {path}")
        if len(compact) >= len(old):
            continue
        relative = path.relative_to(root).as_posix()
        saved += len(old) - len(compact)
        changed.append(
            {
                "path": relative,
                "before_bytes": len(old),
                "after_bytes": len(compact),
                "semantic_sha256": sha256(
                    json.dumps(
                        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest(),
            }
        )
        if execute:
            path.write_bytes(compact)
        parts = path.relative_to(root).parts
        if parts[:1] == ("stats",) and parts[2:4] == ("melee", "events"):
            changed_events.add((parts[1], parts[4]))
    if execute:
        for fmt, event_id in events:
            if (fmt, event_id) not in changed_events:
                continue
            path = root / f"stats/{fmt}/melee/events/{event_id}/meta.json"
            old = read(path)
            if publish.main(
                [
                    "--root",
                    str(root),
                    "--format",
                    fmt,
                    "--event-id",
                    event_id,
                    "--execute",
                ]
            ):
                raise ValueError(
                    f"Cannot rebind compact Melee product: {fmt}/{event_id}"
                )
            if without_byte_descriptors(old) != without_byte_descriptors(read(path)):
                raise ValueError(
                    f"Non-encoding Melee metadata change: {fmt}/{event_id}"
                )
        for fmt in formats:
            old = meta_before[fmt]
            generate_metadata(
                root,
                fmt,
                data_updated=old["data_updated"],
                rules_updated=old["rules_updated"],
            )
            new = read(root / f"stats/{fmt}/mtgo/meta.json")
            old["publication"].pop("artifacts")
            new["publication"].pop("artifacts")
            if old != new:
                raise ValueError(f"Non-encoding MTGO metadata change: {fmt}")
            problems = inspect_publication(root, fmt)
            if problems:
                raise ValueError(f"Compact product is unbound: {fmt}: {problems}")
            if fmt in catalog_before:
                after = read(root / f"stats/{fmt}/melee/index.json")
                if without_byte_descriptors(
                    catalog_before[fmt]
                ) != without_byte_descriptors(after):
                    raise ValueError(f"Non-encoding Melee catalog change: {fmt}")
                validate_current_melee(root, fmt)
    return {
        "operation": "compact_public_products",
        "executed": execute,
        "formats": formats,
        "files": changed,
        "file_count": len(changed),
        "saved_bytes": saved,
        "json_values_unchanged": True,
        "source_inputs_changed": 0,
        "remote_writes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require_private_output(ROOT, args.output)
    result = compact_public_products(args.root, execute=args.execute)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "files"}))


if __name__ == "__main__":
    main()
