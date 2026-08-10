"""Run the deterministic, read-only R2 classifier shadow audit."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtgmeta.classifier_shadow import load_shadow_feature_manifest  # noqa: E402
from mtgmeta.classifier_shadow_audit import (  # noqa: E402
    audit_frozen_corpus,
    audit_melee_event,
    canonical_json,
    compare_p6_01,
    load_frozen_records,
    pickup_dry_run,
    rule_inventory,
    sha256_path,
)
from mtgmeta.config import load_rule_set  # noqa: E402


AUDIT_ROOT = ROOT / "docs" / "audits" / "classifier-r2"
RESULTS_ROOT = AUDIT_ROOT / "results"


def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest().upper()


def _write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(canonical_json(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_audit() -> dict[str, Any]:
    manifest_path = AUDIT_ROOT / "semantic_card_features.yaml"
    manifest = load_shadow_feature_manifest(manifest_path)
    transition_path = ROOT / "docs" / "audits" / "classifier-r1" / "transition_map.yaml"

    formats = {
        "modern": {
            "baseline": AUDIT_ROOT / "baseline_rules" / "modern.yaml",
            "shadow": AUDIT_ROOT / "shadow_rules" / "modern.yaml",
            "corpus": ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json",
        },
        "standard": {
            "baseline": AUDIT_ROOT / "baseline_rules" / "standard.yaml",
            "shadow": AUDIT_ROOT / "shadow_rules" / "standard.yaml",
            "corpus": ROOT
            / "tests"
            / "fixtures"
            / "standard"
            / "frozen_legacy_corpus.json",
        },
    }
    audits: dict[str, dict[str, Any]] = {}
    for format_id, paths in formats.items():
        records = load_frozen_records(paths["corpus"])
        audits[format_id] = audit_frozen_corpus(
            format_id,
            records,
            load_rule_set(paths["baseline"]),
            load_rule_set(paths["shadow"]),
            manifest,
        )

    modern_paths = formats["modern"]
    modern_records = load_frozen_records(modern_paths["corpus"])
    modern_shadow = load_rule_set(modern_paths["shadow"])
    event_path = ROOT / "data" / "modern" / "melee" / "events" / "434455.json"
    event = audit_melee_event(
        event_path,
        load_rule_set(modern_paths["baseline"]),
        modern_shadow,
        manifest,
    )
    p6_01 = compare_p6_01(
        modern_records,
        load_rule_set(ROOT / "tests" / "fixtures" / "modern" / "p6_01_rules.yaml"),
        modern_shadow,
        manifest,
    )
    pickup = pickup_dry_run(
        ROOT,
        transition_path,
        source_overrides={
            "modern": AUDIT_ROOT / "baseline_pickup" / "modern_known_archetypes.json",
            "standard": AUDIT_ROOT / "baseline_pickup" / "standard_known_archetypes.json",
        },
    )

    inputs = {
        "feature_manifest": sha256_path(manifest_path),
        "r1_transition_map": sha256_path(transition_path),
        "modern_production_rules": sha256_path(formats["modern"]["baseline"]),
        "standard_production_rules": sha256_path(formats["standard"]["baseline"]),
        "modern_shadow_rules": sha256_path(formats["modern"]["shadow"]),
        "standard_shadow_rules": sha256_path(formats["standard"]["shadow"]),
        "modern_frozen_corpus": sha256_path(formats["modern"]["corpus"]),
        "standard_frozen_corpus": sha256_path(formats["standard"]["corpus"]),
        "modern_p6_01_rules": sha256_path(
            ROOT / "tests" / "fixtures" / "modern" / "p6_01_rules.yaml"
        ),
        "event_434455": sha256_path(event_path),
    }
    summary = {
        "schema_version": "1.0.0",
        "task_id": "CLASSIFIER-R2-SHADOW-CLASSIFIER-AUDIT",
        "status": "local_shadow_not_applied",
        "input_sha256": inputs,
        "formats": {
            format_id: {
                "record_count": audit["record_count"],
                "baseline_summary": audit["baseline_summary"],
                "shadow_summary": audit["shadow_summary"],
                "diagnostic_delta": audit["diagnostic_delta"],
                "baseline_to_shadow": audit["baseline_to_shadow"],
                "submitted_expected_to_shadow": audit["submitted_expected_to_shadow"],
                "order_independence_mismatches": audit[
                    "order_independence_mismatches"
                ],
                "rule_inventory": rule_inventory(
                    load_rule_set(formats[format_id]["shadow"])
                ),
            }
            for format_id, audit in audits.items()
        },
        "p6_01_comparison": p6_01,
        "pickup_dry_run": pickup,
        "event_434455": event,
        "privacy": {
            "deck_ids": "deterministic hashes of format, ordinal, and card counts",
            "participant_identifiers_retained": False,
        },
    }
    rows = audits["modern"]["rows"] + audits["standard"]["rows"]
    unknown = {
        "schema_version": "1.0.0",
        "records": audits["modern"]["unknown_evidence"]
        + audits["standard"]["unknown_evidence"],
    }
    return {
        "summary": summary,
        "rows": rows,
        "unknown": unknown,
        "pickup": pickup,
        "event": event,
    }


def write_audit(audit: dict[str, Any]) -> dict[str, str]:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": RESULTS_ROOT / "summary.json",
        "rows": RESULTS_ROOT / "deck_transitions.jsonl",
        "unknown": RESULTS_ROOT / "unknown_evidence.json",
        "pickup": RESULTS_ROOT / "pickup_dry_run.json",
        "event": RESULTS_ROOT / "event_434455_comparison.json",
    }
    _write_json(paths["summary"], audit["summary"])
    _write_jsonl(paths["rows"], audit["rows"])
    _write_json(paths["unknown"], audit["unknown"])
    _write_json(paths["pickup"], audit["pickup"])
    _write_json(paths["event"], audit["event"])
    return {
        path.relative_to(ROOT).as_posix(): _hash_text(path.read_text(encoding="utf-8"))
        for path in paths.values()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write deterministic local audit artifacts under docs/audits/classifier-r2/results",
    )
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        print(json.dumps(write_audit(audit), indent=2, sort_keys=True))
    else:
        print(json.dumps(audit["summary"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
