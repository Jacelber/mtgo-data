"""Build the deterministic R4 residual-Unknown owner-review queue."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
from statistics import median
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtgmeta.classifier_features import augment_semantic_counts  # noqa: E402
from mtgmeta.config import load_rule_set  # noqa: E402
from mtgmeta.rules import CardCondition, RuleSet  # noqa: E402


TASK_ID = "CLASSIFIER-R4-RESIDUAL-UNKNOWN-REVIEW"
R3_BASE_COMMIT = "7bf804684ac22dcf71560bacae4d3bc49c56f08f"
SIMILARITY_THRESHOLD = 0.55
ALLOWED_DISPOSITIONS = (
    "map_existing",
    "new_identity",
    "intentional_unknown",
    "defer_insufficient_evidence",
)


@dataclass(frozen=True)
class UnknownRecord:
    format_id: str
    source: str
    event_id: str
    event_name: str | None
    event_start: str | None
    record_id: str
    main: tuple[tuple[str, int], ...]
    side: tuple[tuple[str, int], ...]

    def main_counts(self) -> dict[str, int]:
        return dict(self.main)

    def side_counts(self) -> dict[str, int]:
        return dict(self.side)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _cards(value: object, path: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path}: must be a list")
    result: list[tuple[str, int]] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("quantity"), int)
            or item["quantity"] <= 0
        ):
            raise ValueError(f"{path}[{index}]: invalid card entry")
        result.append((item["name"], item["quantity"]))
    return tuple(sorted(result))


def _record_id(
    format_id: str,
    source: str,
    event_id: str,
    private_key: str,
) -> str:
    material = "\0".join((TASK_ID, format_id, source, event_id, private_key))
    return sha256(material.encode("utf-8")).hexdigest()[:20]


def load_unknown_records(root: Path = ROOT) -> list[UnknownRecord]:
    records: list[UnknownRecord] = []
    for format_id in ("modern", "standard"):
        path = root / "reports" / format_id / "mtgo" / "unknown_decks.json"
        document = _read_json(path)
        raw_records = document.get("records")
        if (
            document.get("format") != format_id
            or document.get("source") != "mtgo"
            or not isinstance(raw_records, list)
            or document.get("summary", {}).get("record_count") != len(raw_records)
        ):
            raise ValueError(f"{path}: unexpected Unknown report contract")
        for index, item in enumerate(raw_records):
            if not isinstance(item, dict):
                raise ValueError(f"{path}: records[{index}] must be an object")
            event_id = str(item.get("event_id", ""))
            deck_id = item.get("deck_id")
            if not event_id or not isinstance(deck_id, str) or not deck_id:
                raise ValueError(f"{path}: records[{index}] has no stable evidence key")
            records.append(
                UnknownRecord(
                    format_id=format_id,
                    source="mtgo",
                    event_id=event_id,
                    event_name=(
                        item.get("event_name")
                        if isinstance(item.get("event_name"), str)
                        else None
                    ),
                    event_start=(
                        item.get("event_start")
                        if isinstance(item.get("event_start"), str)
                        else None
                    ),
                    record_id=_record_id(format_id, "mtgo", event_id, deck_id),
                    main=_cards(item.get("main_deck"), f"{path}: records[{index}].main_deck"),
                    side=_cards(item.get("sideboard"), f"{path}: records[{index}].sideboard"),
                )
            )

    path = root / "data" / "modern" / "melee" / "classifications" / "434455.json"
    document = _read_json(path)
    raw_records = document.get("records")
    if document.get("event_id") != "434455" or not isinstance(raw_records, list):
        raise ValueError(f"{path}: unexpected classification overlay contract")
    unknown_count = 0
    for index, item in enumerate(raw_records):
        if not isinstance(item, dict) or item.get("classification_status") != "unknown":
            continue
        unknown_count += 1
        private_key = item.get("participant_id")
        deck = item.get("unknown_deck")
        if not isinstance(private_key, str) or not isinstance(deck, dict):
            raise ValueError(f"{path}: records[{index}] has invalid Unknown evidence")
        records.append(
            UnknownRecord(
                format_id="modern",
                source="melee",
                event_id="434455",
                event_name=None,
                event_start=None,
                record_id=_record_id("modern", "melee", "434455", private_key),
                main=_cards(deck.get("main_deck"), f"{path}: records[{index}].main_deck"),
                side=_cards(deck.get("sideboard"), f"{path}: records[{index}].sideboard"),
            )
        )
    if document.get("summary", {}).get("unknown") != unknown_count:
        raise ValueError(f"{path}: Unknown summary does not match records")
    return sorted(records, key=lambda item: (item.format_id, item.source, item.record_id))


def weighted_jaccard(left: UnknownRecord, right: UnknownRecord) -> float:
    left_counts = left.main_counts()
    right_counts = right.main_counts()
    names = left_counts.keys() | right_counts.keys()
    intersection = sum(min(left_counts.get(name, 0), right_counts.get(name, 0)) for name in names)
    union = sum(max(left_counts.get(name, 0), right_counts.get(name, 0)) for name in names)
    return intersection / union if union else 1.0


def cluster_records(
    records: list[UnknownRecord],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[list[UnknownRecord]]:
    if not 0 < threshold <= 1:
        raise ValueError("similarity threshold must be in (0, 1]")
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for left in range(len(records)):
        for right in range(left):
            if weighted_jaccard(records[left], records[right]) >= threshold:
                union(left, right)

    groups: dict[int, list[UnknownRecord]] = {}
    for index, record in enumerate(records):
        groups.setdefault(find(index), []).append(record)
    return [
        sorted(group, key=lambda item: item.record_id)
        for group in sorted(
            groups.values(),
            key=lambda group: tuple(item.record_id for item in sorted(group, key=lambda item: item.record_id)),
        )
    ]


def _condition_count(
    condition: CardCondition,
    main: dict[str, int],
    side: dict[str, int],
) -> int:
    if condition.zone == "main":
        return main.get(condition.card, 0)
    if condition.zone == "side":
        return side.get(condition.card, 0)
    return main.get(condition.card, 0) + side.get(condition.card, 0)


def _condition_matches(condition: CardCondition, count: int) -> bool:
    if condition.exact_count is not None:
        return count == condition.exact_count
    if condition.min_count is not None and count < condition.min_count:
        return False
    return condition.max_count is None or count <= condition.max_count


def _is_positive(condition: CardCondition) -> bool:
    if condition.exact_count is not None:
        return condition.exact_count > 0
    return condition.min_count is not None and condition.min_count > 0


def _condition_text(condition: CardCondition) -> str:
    zone = condition.zone
    if condition.exact_count is not None:
        constraint = f"={condition.exact_count}"
    elif condition.max_count is None:
        constraint = f">={condition.min_count}"
    elif condition.min_count is None:
        constraint = f"<={condition.max_count}"
    else:
        constraint = f"{condition.min_count}..{condition.max_count}"
    return f"{condition.card} [{zone}] {constraint}"


def _nearest_rules(
    family: list[UnknownRecord],
    rule_set: RuleSet,
    representative: UnknownRecord,
) -> list[dict[str, Any]]:
    if rule_set.semantic_features is None:
        raise ValueError("production semantic features are not loaded")
    augmented: dict[str, tuple[dict[str, int], dict[str, int]]] = {}
    for record in family:
        augmented[record.record_id] = augment_semantic_counts(
            record.main_counts(), record.side_counts(), rule_set.semantic_features
        )
    subtype_names = {
        (archetype.id, subtype.id): subtype.name
        for archetype in rule_set.archetypes
        for subtype in archetype.subtypes
    }
    candidates: list[dict[str, Any]] = []
    for archetype in rule_set.archetypes:
        for rule in archetype.rules:
            positive = [item for item in rule.conditions if _is_positive(item)]
            coverages: list[float] = []
            exclusion_failure_records = 0
            complete_matches = 0
            for record in family:
                main, side = augmented[record.record_id]
                matches = [
                    _condition_matches(item, _condition_count(item, main, side))
                    for item in rule.conditions
                ]
                positive_matches = [
                    matched
                    for item, matched in zip(rule.conditions, matches, strict=True)
                    if _is_positive(item)
                ]
                coverages.append(
                    sum(positive_matches) / len(positive_matches)
                    if positive_matches
                    else 1.0
                )
                if any(
                    not matched
                    for item, matched in zip(rule.conditions, matches, strict=True)
                    if not _is_positive(item)
                ):
                    exclusion_failure_records += 1
                if all(matches):
                    complete_matches += 1
            rep_main, rep_side = augmented[representative.record_id]
            unmet = []
            failed_exclusions = []
            for condition in rule.conditions:
                matched = _condition_matches(
                    condition,
                    _condition_count(condition, rep_main, rep_side),
                )
                if not matched:
                    target = unmet if _is_positive(condition) else failed_exclusions
                    target.append(_condition_text(condition))
            candidates.append(
                {
                    "archetype_id": archetype.id,
                    "archetype_name": archetype.name,
                    "subtype_id": rule.subtype_id,
                    "subtype_name": subtype_names.get((archetype.id, rule.subtype_id)),
                    "rule_id": rule.id,
                    "positive_coverage": round(sum(coverages) / len(coverages), 4),
                    "positive_conditions": len(positive),
                    "exclusion_failure_records": exclusion_failure_records,
                    "complete_matches": complete_matches,
                    "representative_unmet_positive": unmet,
                    "representative_failed_exclusions": failed_exclusions,
                    "priority": rule.priority,
                }
            )
    candidates.sort(
        key=lambda item: (
            -item["positive_coverage"],
            item["exclusion_failure_records"],
            -item["positive_conditions"],
            -item["priority"],
            item["rule_id"],
        )
    )
    return candidates[:3]


def _card_rows(family: list[UnknownRecord]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    counts: dict[str, list[int]] = {}
    for record in family:
        main = record.main_counts()
        for name in set(counts) | set(main):
            counts.setdefault(name, []).append(main.get(name, 0))
        for name in set(main) - set(counts):
            counts[name] = [0] * (len(family) - 1) + [main[name]]
    rows = [
        {
            "name": name,
            "present_in": sum(quantity > 0 for quantity in quantities),
            "presence_share": round(sum(quantity > 0 for quantity in quantities) / len(family), 4),
            "min_count": min(quantities),
            "median_count": median(quantities),
            "max_count": max(quantities),
        }
        for name, quantities in counts.items()
    ]
    rows.sort(key=lambda item: (-item["present_in"], -item["median_count"], item["name"]))
    common = [item for item in rows if item["present_in"] == len(family)][:20]
    prevalent = [item for item in rows if item["present_in"] >= ceil(0.75 * len(family))][:20]
    return common, prevalent


def _representative(family: list[UnknownRecord]) -> UnknownRecord:
    return max(
        family,
        key=lambda candidate: (
            sum(weighted_jaccard(candidate, other) for other in family),
            candidate.record_id,
        ),
    )


def _family_document(
    family: list[UnknownRecord],
    rule_set: RuleSet,
) -> dict[str, Any]:
    member_ids = sorted(record.record_id for record in family)
    fingerprint = sha256("\n".join(member_ids).encode("utf-8")).hexdigest()
    format_id = family[0].format_id
    representative = _representative(family)
    pairwise = [
        weighted_jaccard(family[left], family[right])
        for left in range(len(family))
        for right in range(left)
    ]
    common, prevalent = _card_rows(family)
    event_count = len({(item.source, item.event_id) for item in family})
    if len(family) >= 2 and event_count >= 2:
        priority_tier = "recurring_across_events"
    elif len(family) >= 2:
        priority_tier = "multiple_lists_one_event"
    else:
        priority_tier = "singleton"
    return {
        "family_id": f"{format_id}-unknown-{fingerprint[:12]}",
        "family_fingerprint": fingerprint,
        "format": format_id,
        "review_status": "pending_owner_review",
        "disposition": None,
        "allowed_dispositions": list(ALLOWED_DISPOSITIONS),
        "priority_tier": priority_tier,
        "record_count": len(family),
        "event_count": event_count,
        "source_counts": dict(sorted(Counter(item.source for item in family).items())),
        "similarity": {
            "method": "main-deck quantity-weighted Jaccard connected component",
            "edge_threshold": SIMILARITY_THRESHOLD,
            "minimum_pairwise": round(min(pairwise), 4) if pairwise else 1.0,
            "median_pairwise": round(median(pairwise), 4) if pairwise else 1.0,
            "maximum_pairwise": round(max(pairwise), 4) if pairwise else 1.0,
            "transitive_below_threshold": bool(pairwise and min(pairwise) < SIMILARITY_THRESHOLD),
        },
        "common_core": common,
        "prevalent_cards": prevalent,
        "nearest_production_rules": _nearest_rules(family, rule_set, representative),
        "representative": {
            "record_id": representative.record_id,
            "source": representative.source,
            "event_id": representative.event_id,
            "event_name": representative.event_name,
            "event_start": representative.event_start,
            "main_deck": [
                {"name": name, "quantity": quantity}
                for name, quantity in representative.main
            ],
            "sideboard": [
                {"name": name, "quantity": quantity}
                for name, quantity in representative.side
            ],
        },
        "members": [
            {
                "record_id": record.record_id,
                "source": record.source,
                "event_id": record.event_id,
                "event_name": record.event_name,
                "event_start": record.event_start,
            }
            for record in family
        ],
    }


def build_review(root: Path = ROOT) -> dict[str, Any]:
    records = load_unknown_records(root)
    input_paths = {
        "modern_mtgo": root / "reports" / "modern" / "mtgo" / "unknown_decks.json",
        "standard_mtgo": root / "reports" / "standard" / "mtgo" / "unknown_decks.json",
        "modern_melee_434455": root / "data" / "modern" / "melee" / "classifications" / "434455.json",
        "modern_rules": root / "my_archetypes" / "modern.yaml",
        "standard_rules": root / "my_archetypes" / "standard.yaml",
    }
    families: list[dict[str, Any]] = []
    for format_id in ("modern", "standard"):
        format_records = [item for item in records if item.format_id == format_id]
        rule_set = load_rule_set(input_paths[f"{format_id}_rules"])
        families.extend(
            _family_document(family, rule_set)
            for family in cluster_records(format_records)
        )
    format_order = {"modern": 0, "standard": 1}
    tier_order = {
        "recurring_across_events": 0,
        "multiple_lists_one_event": 1,
        "singleton": 2,
    }
    families.sort(
        key=lambda item: (
            format_order[item["format"]],
            tier_order[item["priority_tier"]],
            -item["record_count"],
            -item["event_count"],
            item["family_id"],
        )
    )
    for rank, family in enumerate(families, start=1):
        family["review_rank"] = rank

    format_summary = {}
    for format_id in ("modern", "standard"):
        selected_records = [item for item in records if item.format_id == format_id]
        selected_families = [item for item in families if item["format"] == format_id]
        format_summary[format_id] = {
            "records": len(selected_records),
            "families": len(selected_families),
            "recurring_families": sum(
                item["priority_tier"] == "recurring_across_events"
                for item in selected_families
            ),
            "multi_record_single_event_families": sum(
                item["priority_tier"] == "multiple_lists_one_event"
                for item in selected_families
            ),
            "singleton_families": sum(
                item["priority_tier"] == "singleton"
                for item in selected_families
            ),
            "source_records": dict(
                sorted(Counter(item.source for item in selected_records).items())
            ),
        }
    return {
        "schema_version": "1.0.0",
        "task_id": TASK_ID,
        "status": "pending_owner_review",
        "base_commit": R3_BASE_COMMIT,
        "parameters": {
            "similarity_method": "main-deck quantity-weighted Jaccard",
            "cluster_method": "connected components",
            "edge_threshold": SIMILARITY_THRESHOLD,
            "review_order": "Modern then Standard; recurring, same-event multiples, singletons",
        },
        "input_sha256": {
            name: sha256(path.read_bytes()).hexdigest()
            for name, path in sorted(input_paths.items())
        },
        "disposition_contract": {
            "review_status_before_decision": "pending_owner_review",
            "allowed_dispositions": list(ALLOWED_DISPOSITIONS),
            "unknown_is_valid": True,
            "automatic_assignment_allowed": False,
        },
        "summary": {
            "records": len(records),
            "families": len(families),
            "formats": format_summary,
        },
        "privacy": {
            "participant_identifiers_retained": False,
            "source_deck_identifiers_retained": False,
            "record_ids": "task-scoped SHA-256 prefixes",
        },
        "limitations": [
            "Similarity proposes review families; it does not assign archetypes.",
            "Connected components can create transitive families; each family reports whether its minimum pairwise similarity falls below the edge threshold.",
            "The committed Unknown reports do not provide a common cross-source performance field, so review priority uses recurrence rather than inferred competitive value.",
        ],
        "families": families,
    }


def _render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Classifier R4 residual Unknown family queue",
        "",
        f"Base commit: `{review['base_commit']}`.",
        "",
        "This is a deterministic owner-review queue, not a production classification.",
        "Every family remains `pending_owner_review` until the Owner selects one of the",
        "four allowed dispositions. Unknown is an accepted fail-closed result.",
        "",
        "## Summary",
        "",
        "| Format | Records | Families | Recurring | Same-event multiples | Singletons |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for format_id in ("modern", "standard"):
        item = review["summary"]["formats"][format_id]
        lines.append(
            f"| {format_id.title()} | {item['records']} | {item['families']} | "
            f"{item['recurring_families']} | {item['multi_record_single_event_families']} | "
            f"{item['singleton_families']} |"
        )
    lines.extend(
        [
            "",
            "## Review queue",
            "",
            "| Rank | Family | Format | Records | Events | Sources | Common core | Nearest production rule | Status |",
            "| ---: | --- | --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for family in review["families"]:
        core = ", ".join(item["name"] for item in family["common_core"][:5]) or "-"
        nearest = family["nearest_production_rules"][0]
        sources = ", ".join(
            f"{name}:{count}" for name, count in family["source_counts"].items()
        )
        lines.append(
            f"| {family['review_rank']} | `{family['family_id']}` | {family['format']} | "
            f"{family['record_count']} | {family['event_count']} | {sources} | "
            f"{core.replace('|', '\\|')} | `{nearest['rule_id']}` "
            f"({nearest['positive_coverage']:.0%}) | pending |"
        )
    lines.extend(
        [
            "",
            "## Stop boundary",
            "",
            "This queue changes no production rule, statistic, Pickup state, source event,",
            "workflow, front end, Schema, or public path. Family decisions and any later",
            "production promotion require their applicable Owner gates.",
            "",
        ]
    )
    return "\n".join(lines)


def _disposition_template(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "task_id": TASK_ID,
        "base_commit": R3_BASE_COMMIT,
        "status": "pending_owner_review",
        "allowed_dispositions": list(ALLOWED_DISPOSITIONS),
        "families": [
            {
                "family_id": family["family_id"],
                "review_status": "pending_owner_review",
                "disposition": None,
                "target_identity": None,
                "rationale": None,
                "owner_accepted": False,
            }
            for family in review["families"]
        ],
    }


def write_review(review: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queue_path = output_dir / "unknown_family_queue.json"
    markdown_path = output_dir / "unknown_family_queue.md"
    dispositions_path = output_dir / "dispositions.yaml"
    queue_path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown_path.write_text(
        _render_markdown(review), encoding="utf-8", newline="\n"
    )
    if dispositions_path.exists():
        existing = yaml.safe_load(dispositions_path.read_text(encoding="utf-8"))
        expected_ids = [item["family_id"] for item in review["families"]]
        actual_ids = (
            [item.get("family_id") for item in existing.get("families", [])]
            if isinstance(existing, dict)
            else []
        )
        if existing.get("base_commit") != R3_BASE_COMMIT or actual_ids != expected_ids:
            raise ValueError("existing R4 dispositions do not match this frozen queue")
    else:
        dispositions_path.write_text(
            yaml.safe_dump(
                _disposition_template(review),
                allow_unicode=True,
                sort_keys=False,
                width=1000,
            ),
            encoding="utf-8",
            newline="\n",
        )
    return {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in (queue_path, markdown_path, dispositions_path)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs" / "audits" / "classifier-r4",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    review = build_review(ROOT)
    if args.write:
        print(json.dumps(write_review(review, args.output_dir), indent=2, sort_keys=True))
    else:
        print(json.dumps(review["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
