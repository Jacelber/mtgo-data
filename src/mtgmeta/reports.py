"""Deterministic, de-identified classification diagnostic reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .classifier import ClassificationResult, ConditionEvidence, RuleMatch, classify_deck
from .deck import deck_to_counts
from .rules import RuleSet


REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_FILENAMES = {
    "unknown_decks": "unknown_decks.json",
    "multiple_matches": "multiple_matches.json",
    "classification_conflicts": "classification_conflicts.json",
    "overridden_matches": "overridden_matches.json",
    "subtype_diagnostics": "subtype_diagnostics.json",
}
IDENTITY_FIELDS = frozenset({"player", "loginid", "player_id", "player_name", "username"})


def _card_list(counts: Mapping[str, int]) -> list[dict[str, Any]]:
    return [{"name": name, "quantity": quantity} for name, quantity in sorted(counts.items())]


def _deck_id(event_id: str, player_index: int, deck: Mapping[str, Any]) -> str:
    """Build a stable pseudonymous identifier without using a player identity."""

    try:
        main_counts, side_counts = deck_to_counts(deck)
        fingerprint: Any = {
            "main": sorted(main_counts.items()),
            "side": sorted(side_counts.items()),
        }
    except (KeyError, TypeError, ValueError):
        fingerprint = {"record_index": player_index}
    material = json.dumps(
        {"event_id": event_id, "record_index": player_index, "deck": fingerprint},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(material.encode("utf-8")).hexdigest()[:20]


def _evidence(item: ConditionEvidence) -> dict[str, Any]:
    return {
        "card": item.card,
        "zone": item.zone,
        "actual_count": item.actual_count,
        "min_count": item.min_count,
        "max_count": item.max_count,
        "exact_count": item.exact_count,
    }


def _match(item: RuleMatch) -> dict[str, Any]:
    return {
        "archetype_id": item.archetype_id,
        "archetype_name": item.archetype_name,
        "subtype_id": item.subtype_id,
        "subtype_name": item.subtype_name,
        "rule_id": item.rule_id,
        "priority": item.priority,
        "evidence": [_evidence(evidence) for evidence in item.evidence],
    }


def _selected(result: ClassificationResult) -> dict[str, Any] | None:
    if result.status != "classified":
        return None
    return {
        "archetype_id": result.archetype_id,
        "archetype_name": result.archetype_name,
        "subtype_id": result.subtype_id,
        "subtype_name": result.subtype_name,
        "rule_id": result.selected_rule_id,
        "priority": result.selected_priority,
    }


def _record_identity(event: Mapping[str, Any], source_file: str, player_index: int, player: Mapping[str, Any]) -> dict[str, Any]:
    event_id = str(event.get("event_id", "unknown"))
    return {
        "deck_id": _deck_id(event_id, player_index, player),
        "event_id": event_id,
        "event_name": str(event.get("description", "Unknown event")),
        "event_start": str(event.get("starttime", "")),
        "source_file": source_file,
    }


def _base(
    report_type: str,
    event_count: int,
    data_through: str,
    format_id: str,
    source: str,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": report_type,
        "format": format_id,
        "source": source,
        "scope": "all_available_events",
        "event_count": event_count,
        "data_through": data_through,
    }


def build_classification_reports(
    events: Sequence[tuple[str, Mapping[str, Any]]],
    rule_set: RuleSet,
    *,
    format_id: str | None = None,
    source: str = "mtgo",
) -> dict[str, dict[str, Any]]:
    """Classify every event deck and return deterministic diagnostic documents."""

    resolved_format = rule_set.format if format_id is None else format_id
    if resolved_format != rule_set.format:
        raise ValueError(
            f"classification report format {resolved_format!r} does not match "
            f"rule format {rule_set.format!r}"
        )

    unknown: list[dict[str, Any]] = []
    multiple: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    overridden: list[dict[str, Any]] = []
    subtype: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    subtype_counts: Counter[str] = Counter()
    data_through = max((str(event.get("starttime", "")) for _, event in events), default="")

    for source_file, event in sorted(events, key=lambda item: item[0]):
        players = event.get("players", [])
        if not isinstance(players, list):
            raise ValueError(f"{source_file}: players must be a list")
        for player_index, player in enumerate(players):
            if not isinstance(player, Mapping):
                player = {}
            identity = _record_identity(event, source_file, player_index, player)
            result = classify_deck(rule_set, player)
            statuses[result.status] += 1

            if result.status == "invalid_deck":
                invalid.append({**identity, "errors": list(result.errors)})
                continue
            if result.status == "unknown":
                main_counts, side_counts = deck_to_counts(player)
                unknown.append({
                    **identity,
                    "main_deck": _card_list(main_counts),
                    "sideboard": _card_list(side_counts),
                })
                continue

            selected = _selected(result)
            if len(result.matched_rules) > 1:
                multiple.append({
                    **identity,
                    "classification_status": result.status,
                    "selected": selected,
                    "matches": [_match(match) for match in result.matched_rules],
                })
            if result.overridden_matches:
                overridden.append({
                    **identity,
                    "classification_status": result.status,
                    "selected": selected,
                    "overridden_matches": [_match(match) for match in result.overridden_matches],
                })
            if result.status == "conflict":
                conflicts.append({
                    **identity,
                    "conflict_kind": result.conflict_kind,
                    "selected": selected,
                    "selected_priority": result.selected_priority,
                    "blocking": True,
                    "matches": [_match(match) for match in result.conflict_matches],
                })
                continue
            subtype_candidates = sorted({
                (match.archetype_id, match.subtype_id)
                for match in result.matched_rules
                if match.subtype_id is not None
            })
            if result.subtype_id is not None:
                subtype_counts[f"{result.archetype_id}/{result.subtype_id}"] += 1
            if subtype_candidates:
                candidates_by_parent: dict[str, set[str]] = {}
                for archetype_id, subtype_id in subtype_candidates:
                    candidates_by_parent.setdefault(archetype_id, set()).add(subtype_id)
                subtype.append({
                    **identity,
                    "selected": selected,
                    "matched_subtypes": [
                        {"archetype_id": archetype_id, "subtype_id": subtype_id}
                        for archetype_id, subtype_id in subtype_candidates
                    ],
                    "same_parent_multiple_subtype_matches": any(
                        len(values) > 1 for values in candidates_by_parent.values()
                    ),
                })

    record_sort = lambda item: (item["source_file"], item["deck_id"])
    for records in (unknown, multiple, conflicts, overridden, subtype, invalid):
        records.sort(key=record_sort)

    total = sum(statuses.values())
    common = {
        "event_count": len(events),
        "data_through": data_through,
        "format_id": resolved_format,
        "source": source,
    }
    reports = {
        "unknown_decks": {
            **_base("unknown_decks", **common),
            "summary": {"record_count": len(unknown), "blocking": False},
            "records": unknown,
        },
        "multiple_matches": {
            **_base("multiple_matches", **common),
            "summary": {"record_count": len(multiple), "blocking": False},
            "records": multiple,
        },
        "classification_conflicts": {
            **_base("classification_conflicts", **common),
            "summary": {"record_count": len(conflicts), "blocking": bool(conflicts)},
            "records": conflicts,
        },
        "overridden_matches": {
            **_base("overridden_matches", **common),
            "summary": {"record_count": len(overridden), "blocking": False},
            "records": overridden,
        },
        "subtype_diagnostics": {
            **_base("subtype_diagnostics", **common),
            "summary": {
                "record_count": len(subtype),
                "blocking": False,
                "selected_record_count": sum(subtype_counts.values()),
                "selected_by_subtype": dict(sorted(subtype_counts.items())),
                "same_parent_multiple_subtype_matches": sum(
                    bool(item["same_parent_multiple_subtype_matches"]) for item in subtype
                ),
            },
            "records": subtype,
        },
    }
    reports["index"] = {
        **_base("classification_report_index", **common),
        "summary": {
            "total_decks": total,
            "classified": statuses["classified"],
            "unknown": statuses["unknown"],
            "conflicts": statuses["conflict"],
            "invalid_decks": statuses["invalid_deck"],
            "multiple_matches": len(multiple),
            "overridden_matches": len(overridden),
            "selected_subtypes": sum(subtype_counts.values()),
            "same_parent_multiple_subtype_matches": reports["subtype_diagnostics"]["summary"]["same_parent_multiple_subtype_matches"],
            "strict_validation": "fail" if conflicts or invalid else "pass",
        },
        "files": [REPORT_FILENAMES[name] for name in REPORT_FILENAMES],
        "invalid_records": invalid,
    }
    return reports


def load_events(paths: Iterable[Path], repository_root: Path) -> list[tuple[str, Mapping[str, Any]]]:
    events = []
    for path in sorted(paths):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError(f"{path}: event root must be an object")
        events.append((path.resolve().relative_to(repository_root.resolve()).as_posix(), value))
    return events


def write_classification_reports(reports: Mapping[str, Mapping[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = {**REPORT_FILENAMES, "index": "index.json"}
    for name, filename in filenames.items():
        content = json.dumps(reports[name], ensure_ascii=False, indent=2, sort_keys=False) + "\n"
        (output_dir / filename).write_text(content, encoding="utf-8", newline="\n")


def has_blocking_diagnostics(reports: Mapping[str, Mapping[str, Any]]) -> bool:
    summary = reports["index"]["summary"]
    return bool(summary["conflicts"] or summary["invalid_decks"])


def find_identity_fields(value: Any, path: str = "$") -> list[str]:
    """Return forbidden identity-field paths for tests and safety validation."""

    found = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in IDENTITY_FIELDS:
                found.append(child_path)
            found.extend(find_identity_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_identity_fields(child, f"{path}[{index}]"))
    return found
