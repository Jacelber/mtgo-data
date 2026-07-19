"""Validate the frozen legacy Standard classification-quality baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from classify_standard import signature_card_met


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
BASELINE = ROOT / "tests" / "fixtures" / "standard" / "quality_baseline.json"
RULES = ROOT / "my_archetypes" / "standard.yaml"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def matching_names(record: dict[str, Any], rules: list[dict[str, Any]]) -> list[str]:
    main = dict(record["main"])
    side = dict(record["side"])
    return [
        rule["name"]
        for rule in rules
        if rule.get("signatureCards")
        and all(signature_card_met(signature, main, side) for signature in rule["signatureCards"])
    ]


def analyze(records: list[dict[str, Any]], rules: list[dict[str, Any]]) -> dict[str, Any]:
    unknown = 0
    multiple = []
    maximum = 0
    for record in records:
        matches = matching_names(record, rules)
        maximum = max(maximum, len(matches))
        if not matches:
            unknown += 1
        if len(matches) > 1:
            multiple.append({"id": record["id"], "matches": matches})

    canonical = json.dumps(multiple, ensure_ascii=False, separators=(",", ":"))
    duplicate_names = {
        name: count for name, count in sorted(Counter(rule["name"] for rule in rules).items())
        if count > 1
    }
    return {
        "records": len(records),
        "rules": len(rules),
        "unknown": unknown,
        "multiple_matches": len(multiple),
        "maximum_matches_per_deck": maximum,
        "multiple_match_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "duplicate_display_names": duplicate_names,
    }


def validate() -> list[str]:
    baseline = load_json(BASELINE)
    records = load_json(CORPUS)["records"]
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))["archetypes"]
    actual = analyze(records, rules)
    failures = []
    for key in actual:
        if actual[key] != baseline.get(key):
            failures.append(f"{key}: expected {baseline.get(key)!r}, got {actual[key]!r}")
    forbidden = {"player", "login", "loginid", "player_name"}
    if forbidden.intersection(baseline):
        failures.append("baseline contains a player-identifying field")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    failures = validate()
    if failures:
        print("Standard quality baseline FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    baseline = load_json(BASELINE)
    print(
        "Standard quality baseline PASS: "
        f"records={baseline['records']} unknown={baseline['unknown']} "
        f"multiple_matches={baseline['multiple_matches']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
