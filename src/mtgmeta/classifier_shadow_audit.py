"""Deterministic, de-identified R2 shadow-classifier audit helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .classifier import ClassificationResult, classify_counts
from .classifier_shadow import ShadowFeatureManifest, classify_shadow_counts
from .rules import ArchetypeDefinition, RuleSet


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deidentified_deck_id(
    format_id: str,
    ordinal: int,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> str:
    payload = canonical_json(
        {
            "format": format_id,
            "ordinal": ordinal,
            "main": sorted(main_counts.items()),
            "side": sorted(side_counts.items()),
        }
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:20]


def selected_identity(result: ClassificationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
        "rule_id": result.selected_rule_id,
        "priority": result.selected_priority,
        "matched_rule_count": len(result.matched_rules),
        "conflict_kind": result.conflict_kind,
    }


def identity_signature(result: ClassificationResult) -> tuple[Any, ...]:
    return (
        result.status,
        result.archetype_id,
        result.subtype_id,
        result.selected_rule_id,
        result.selected_priority,
        result.conflict_kind,
    )


def reordered_rule_set(rule_set: RuleSet) -> RuleSet:
    archetypes: list[ArchetypeDefinition] = []
    for archetype in reversed(rule_set.archetypes):
        archetypes.append(replace(archetype, rules=tuple(reversed(archetype.rules))))
    return replace(rule_set, archetypes=tuple(archetypes))


def diagnostic_flags(result: ClassificationResult, rule_set: RuleSet) -> dict[str, bool]:
    subtype_parents = {
        archetype.id for archetype in rule_set.archetypes if archetype.subtypes
    }
    candidates: dict[str, set[str]] = {}
    for match in result.matched_rules:
        if match.subtype_id is not None:
            candidates.setdefault(match.archetype_id, set()).add(match.subtype_id)
    return {
        "multiple_matches": len(result.matched_rules) > 1,
        "same_parent_multiple_subtype_matches": any(
            len(subtypes) > 1 for subtypes in candidates.values()
        ),
        "residual_subtype": (
            result.status == "classified"
            and result.archetype_id in subtype_parents
            and result.subtype_id is None
        ),
        "conflict": result.status == "conflict",
        "invalid_deck": result.status == "invalid_deck",
    }


def _counter_summary(
    results: Iterable[tuple[ClassificationResult, dict[str, bool]]]
) -> dict[str, Any]:
    statuses: Counter[str] = Counter()
    parents: Counter[str] = Counter()
    subtypes: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    total = 0
    for result, item_flags in results:
        total += 1
        statuses[result.status] += 1
        if result.archetype_id is not None:
            parents[result.archetype_id] += 1
        if result.archetype_id is not None and result.subtype_id is not None:
            subtypes[f"{result.archetype_id}/{result.subtype_id}"] += 1
        flags.update(key for key, enabled in item_flags.items() if enabled)
    diagnostic_names = (
        "multiple_matches",
        "same_parent_multiple_subtype_matches",
        "residual_subtype",
        "conflict",
        "invalid_deck",
    )
    return {
        "total": total,
        "statuses": dict(sorted(statuses.items())),
        "selected_by_parent": dict(sorted(parents.items())),
        "selected_by_subtype": dict(sorted(subtypes.items())),
        **{key: flags[key] for key in diagnostic_names},
    }


def diagnostic_delta(
    baseline: Mapping[str, Any], shadow: Mapping[str, Any]
) -> dict[str, int]:
    """Return the exact R1-requested diagnostic count changes."""

    names = (
        "multiple_matches",
        "same_parent_multiple_subtype_matches",
        "conflict",
        "residual_subtype",
        "invalid_deck",
    )
    result = {
        name: int(shadow[name]) - int(baseline[name])
        for name in names
    }
    for status in ("classified", "unknown", "conflict", "invalid_deck"):
        result[status] = int(shadow["statuses"].get(status, 0)) - int(
            baseline["statuses"].get(status, 0)
        )
    return result


def rule_inventory(rule_set: RuleSet) -> dict[str, Any]:
    """List final rule identities and prove numeric priorities are unique."""

    entries = [
        {
            "parent_id": archetype.id,
            "subtype_id": item.subtype_id,
            "rule_id": item.id,
            "priority": item.priority,
        }
        for archetype in rule_set.archetypes
        for item in archetype.rules
    ]
    priority_counts = Counter(item["priority"] for item in entries)
    return {
        "parent_count": len(rule_set.archetypes),
        "subtype_count": sum(len(item.subtypes) for item in rule_set.archetypes),
        "rule_count": len(entries),
        "rule_ids_unique": len({item["rule_id"] for item in entries}) == len(entries),
        "numeric_priorities_globally_unique": all(
            count == 1 for count in priority_counts.values()
        ),
        "priority_collisions": sorted(
            priority for priority, count in priority_counts.items() if count > 1
        ),
        "rules": sorted(entries, key=lambda item: (item["parent_id"], item["rule_id"])),
    }


def _record_counts(record: Mapping[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    return dict(record["main"]), dict(record["side"])


def audit_frozen_corpus(
    format_id: str,
    records: list[Mapping[str, Any]],
    baseline_rules: RuleSet,
    shadow_rules: RuleSet,
    manifest: ShadowFeatureManifest,
) -> dict[str, Any]:
    """Compare every frozen record without copying source identity fields."""

    reordered = reordered_rule_set(shadow_rules)
    rows: list[dict[str, Any]] = []
    unknown_evidence: list[dict[str, Any]] = []
    baseline_diagnostics = []
    shadow_diagnostics = []
    transitions: Counter[str] = Counter()
    expected_transitions: Counter[str] = Counter()
    order_mismatches = 0

    for ordinal, record in enumerate(records):
        main_counts, side_counts = _record_counts(record)
        baseline = classify_counts(baseline_rules, main_counts, side_counts)
        shadow = classify_shadow_counts(
            shadow_rules, main_counts, side_counts, manifest
        )
        shuffled = classify_shadow_counts(
            reordered, main_counts, side_counts, manifest
        )
        if identity_signature(shadow) != identity_signature(shuffled):
            order_mismatches += 1

        deck_id = deidentified_deck_id(
            format_id, ordinal, main_counts, side_counts
        )
        baseline_flags = diagnostic_flags(baseline, baseline_rules)
        shadow_flags = diagnostic_flags(shadow, shadow_rules)
        baseline_diagnostics.append((baseline, baseline_flags))
        shadow_diagnostics.append((shadow, shadow_flags))
        baseline_label = baseline.archetype_id or baseline.status
        shadow_label = shadow.archetype_id or shadow.status
        transitions[f"{baseline_label} -> {shadow_label}"] += 1
        expected_transitions[
            f"{record.get('expected', 'Unknown')} -> {shadow_label}"
        ] += 1
        rows.append(
            {
                "format": format_id,
                "deck_id": deck_id,
                "baseline": selected_identity(baseline),
                "baseline_diagnostics": baseline_flags,
                "shadow": selected_identity(shadow),
                "shadow_diagnostics": shadow_flags,
            }
        )
        if baseline.status == "unknown" or shadow.status == "unknown":
            unknown_evidence.append(
                {
                    "format": format_id,
                    "deck_id": deck_id,
                    "baseline_status": baseline.status,
                    "shadow_status": shadow.status,
                    "main": [
                        {"name": name, "quantity": quantity}
                        for name, quantity in sorted(main_counts.items())
                    ],
                    "side": [
                        {"name": name, "quantity": quantity}
                        for name, quantity in sorted(side_counts.items())
                    ],
                }
            )

    baseline_summary = _counter_summary(baseline_diagnostics)
    shadow_summary = _counter_summary(shadow_diagnostics)
    return {
        "format": format_id,
        "record_count": len(rows),
        "baseline_summary": baseline_summary,
        "shadow_summary": shadow_summary,
        "diagnostic_delta": diagnostic_delta(baseline_summary, shadow_summary),
        "baseline_to_shadow": dict(sorted(transitions.items())),
        "submitted_expected_to_shadow": dict(sorted(expected_transitions.items())),
        "order_independence_mismatches": order_mismatches,
        "rows": rows,
        "unknown_evidence": unknown_evidence,
    }


def _event_decks(event: Mapping[str, Any]) -> list[tuple[dict[str, int], dict[str, int]]]:
    decklists = event.get("decklists")
    if not isinstance(decklists, list):
        raise ValueError("Melee event decklists must be a list")
    decks = []
    for decklist in decklists:
        if not isinstance(decklist, Mapping):
            raise ValueError("Melee decklists must be objects")
        if decklist.get("status") != "submitted" or decklist.get("game_format") != "modern":
            continue
        cards = decklist.get("cards")
        if not isinstance(cards, list):
            raise ValueError("submitted Melee decklist cards must be a list")
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in cards:
            if not isinstance(card, Mapping):
                raise ValueError("Melee decklist card must be an object")
            name = card.get("name")
            quantity = card.get("quantity")
            section = card.get("section")
            if not isinstance(name, str) or not isinstance(quantity, int):
                raise ValueError("Melee card name and quantity are invalid")
            normalized_name = name.strip().partition(" // ")[0]
            if section == "main":
                main[normalized_name] += quantity
            elif section == "sideboard":
                side[normalized_name] += quantity
            else:
                raise ValueError(f"unsupported Melee card section {section!r}")
        decks.append((dict(main), dict(side)))
    decks.sort(key=lambda item: canonical_json([sorted(item[0].items()), sorted(item[1].items())]))
    return decks


def audit_melee_event(
    event_path: Path,
    baseline_rules: RuleSet,
    shadow_rules: RuleSet,
    manifest: ShadowFeatureManifest,
) -> dict[str, Any]:
    original_hash = sha256_path(event_path)
    event = json.loads(event_path.read_text(encoding="utf-8"))
    decks = _event_decks(event)
    transitions: Counter[str] = Counter()
    baseline_diagnostics = []
    shadow_diagnostics = []
    for main_counts, side_counts in decks:
        baseline = classify_counts(baseline_rules, main_counts, side_counts)
        shadow = classify_shadow_counts(
            shadow_rules, main_counts, side_counts, manifest
        )
        baseline_diagnostics.append(
            (baseline, diagnostic_flags(baseline, baseline_rules))
        )
        shadow_diagnostics.append((shadow, diagnostic_flags(shadow, shadow_rules)))
        transitions[
            f"{baseline.archetype_id or baseline.status} -> "
            f"{shadow.archetype_id or shadow.status}"
        ] += 1
    final_hash = sha256_path(event_path)
    return {
        "schema_version": "1.0.0",
        "event_id": "434455",
        "source": "melee",
        "format": "modern",
        "event_sha256_before": original_hash,
        "event_sha256_after": final_hash,
        "event_bytes_unchanged": original_hash == final_hash,
        "baseline_summary": _counter_summary(baseline_diagnostics),
        "shadow_summary": _counter_summary(shadow_diagnostics),
        "baseline_to_shadow": dict(sorted(transitions.items())),
        "participant_identifiers_retained": False,
    }


def pickup_dry_run(root: Path, transition_path: Path) -> dict[str, Any]:
    transitions = yaml.safe_load(transition_path.read_text(encoding="utf-8"))
    plan = transitions["pickup_target_plan"]
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "status": "dry_run_not_applied",
        "formats": {},
    }
    source_paths = {
        "modern": root / "stats" / "modern" / "mtgo" / "pickup" / "known_archetypes.json",
        "standard": root / "stats" / "standard" / "mtgo" / "pickup" / "known_archetypes.json",
    }
    for format_id, source_path in source_paths.items():
        source_hash = sha256_path(source_path)
        document = json.loads(source_path.read_text(encoding="utf-8"))
        if format_id == "modern":
            current = set(document["known_ids"])
            remove = set(plan[format_id]["known_parent_ids_remove"])
            add = set(plan[format_id]["known_parent_ids_add"])
        else:
            current = set(document["known"])
            remove = set(plan[format_id]["known_display_names_remove"])
            add = set(plan[format_id]["known_display_names_add"])
        migrated = current - remove | add
        result["formats"][format_id] = {
            "source_path": source_path.relative_to(root).as_posix(),
            "source_sha256_before": source_hash,
            "source_sha256_after": sha256_path(source_path),
            "source_bytes_unchanged": source_hash == sha256_path(source_path),
            "retained": sorted(current & migrated),
            "removed": sorted(remove),
            "added": sorted(add),
            "false_new_prevented": sorted(add),
            "entry_count_before": len(current),
            "entry_count_after_dry_run": len(migrated),
        }
    return result


def load_frozen_records(path: Path) -> list[Mapping[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    records = value.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path}: records must be a list")
    return records


def compare_p6_01(
    records: list[Mapping[str, Any]],
    p6_rules: RuleSet,
    shadow_rules: RuleSet,
    manifest: ShadowFeatureManifest,
) -> dict[str, Any]:
    transitions: Counter[str] = Counter()
    for record in records:
        main_counts, side_counts = _record_counts(record)
        previous = classify_counts(p6_rules, main_counts, side_counts)
        shadow = classify_shadow_counts(
            shadow_rules, main_counts, side_counts, manifest
        )
        transitions[
            f"{previous.archetype_id or previous.status} -> "
            f"{shadow.archetype_id or shadow.status}"
        ] += 1
    return {
        "record_count": len(records),
        "p6_01_to_shadow": dict(sorted(transitions.items())),
    }
