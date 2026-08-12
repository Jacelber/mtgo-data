"""Validate the frozen legacy Standard classification-quality baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARED_SRC = ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.classifier import evaluate_matches
from mtgmeta.config import load_rule_set
from mtgmeta.rules import RuleSet


CORPUS = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
BASELINE = ROOT / "tests" / "fixtures" / "standard" / "quality_baseline.json"
RULES = ROOT / "docs" / "audits" / "classifier-r2" / "baseline_rules" / "standard.yaml"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def matching_names(record: dict[str, Any], rule_set: RuleSet) -> list[str]:
    main = dict(record["main"])
    side = dict(record["side"])
    return [match.archetype_name for match in evaluate_matches(rule_set, main, side)]


def analyze(records: list[dict[str, Any]], rule_set: RuleSet) -> dict[str, Any]:
    unknown = 0
    multiple = []
    maximum = 0
    for record in records:
        matches = matching_names(record, rule_set)
        maximum = max(maximum, len(matches))
        if not matches:
            unknown += 1
        if len(matches) > 1:
            multiple.append({"id": record["id"], "matches": matches})

    canonical = json.dumps(multiple, ensure_ascii=False, separators=(",", ":"))
    rule_names = [
        archetype.name
        for archetype in rule_set.archetypes
        for _rule in archetype.rules
    ]
    duplicate_names = {
        name: count
        for name, count in sorted(Counter(rule_names).items())
        if count > 1
    }
    return {
        "records": len(records),
        "rules": len(rule_names),
        "unknown": unknown,
        "multiple_matches": len(multiple),
        "maximum_matches_per_deck": maximum,
        "multiple_match_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "duplicate_display_names": duplicate_names,
    }


def validate() -> list[str]:
    baseline = load_json(BASELINE)
    records = load_json(CORPUS)["records"]
    actual = analyze(records, load_rule_set(RULES))
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
