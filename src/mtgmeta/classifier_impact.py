"""Compare accepted and candidate classifier rules on one retained corpus."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .classifier import ClassificationResult, classifier_digest, classify_deck
from .config import load_rule_set
from .melee.classification import _adapt_decklist
from .mtgo import load_mtgo_event_collection_context
from .mtgo.classification import load_mtgo_events_for_format


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _sha256_json(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _identity(result: ClassificationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
        "rule_id": result.selected_rule_id,
        "conflict_kind": result.conflict_kind,
        "priority_tie": result.priority_tie,
        "matched_rule_ids": sorted(item.rule_id for item in result.matched_rules),
        "overridden_rule_ids": sorted(item.rule_id for item in result.overridden_matches),
        "errors": list(result.errors),
    }


def _change_kinds(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    kinds = []
    if before.get("status") != after.get("status"):
        kinds.append("status_change")
    if after.get("status") == "unknown" and before.get("status") != "unknown":
        kinds.append("new_unknown")
    if after.get("status") == "conflict" and before.get("status") != "conflict":
        kinds.append("new_conflict")
    if before.get("status") == "classified" and after.get("status") != "classified":
        kinds.append("classification_lost")
    if before.get("parent_id") != after.get("parent_id"):
        kinds.append("identity_migration")
    if (
        before.get("parent_id") == after.get("parent_id")
        and before.get("subtype_id") != after.get("subtype_id")
    ):
        kinds.append("subtype_drift")
    diagnostic_fields = {
        "rule_id",
        "conflict_kind",
        "priority_tie",
        "matched_rule_ids",
        "overridden_rule_ids",
        "errors",
    }
    if any(before.get(field) != after.get(field) for field in diagnostic_fields):
        kinds.append("diagnostic_drift")
    return kinds


def _mtgo_decks(root: Path, format_id: str) -> list[dict[str, Any]]:
    context = load_mtgo_event_collection_context(root, format_id)
    events, _excluded = load_mtgo_events_for_format(
        context.paths["events"].glob("*.json"), root, format_id
    )
    rows = []
    for source_file, event in events:
        event_id = str(event.get("event_id", ""))
        players = event.get("players")
        if not isinstance(players, list):
            raise ValueError(f"{source_file}: players must be a list")
        for index, player in enumerate(players):
            if not isinstance(player, dict):
                raise ValueError(f"{source_file}#players/{index}: must be an object")
            rows.append(
                {
                    "record_id": f"mtgo:{format_id}:{event_id}:{index}",
                    "source": "mtgo",
                    "event_id": event_id,
                    "source_locator": f"{source_file}#players/{index}",
                    "deck": player,
                }
            )
    return rows


def _melee_decks(root: Path, format_id: str) -> list[dict[str, Any]]:
    base = root / "data" / format_id / "melee" / "events"
    rows = []
    if not base.is_dir():
        return rows
    for event_path in sorted(base.glob("*.json")):
        event = _json_object(event_path)
        metadata = event.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("constructed_format") != format_id:
            continue
        event_id = str(metadata.get("event_id", ""))
        decklists = event.get("decklists")
        if not isinstance(decklists, list):
            raise ValueError(f"{event_path}: decklists must be a list")
        for index, decklist in enumerate(decklists):
            if (
                not isinstance(decklist, dict)
                or decklist.get("status") != "submitted"
                or decklist.get("game_format") != format_id
            ):
                continue
            participant_id = decklist.get("participant_id")
            if not isinstance(participant_id, str):
                raise ValueError(f"{event_path}#decklists/{index}: participant_id is missing")
            deck, errors = _adapt_decklist(decklist)
            if deck is None:
                deck = {"main_deck": [], "sideboard": [], "__adapter_errors": list(errors)}
            rows.append(
                {
                    "record_id": f"melee:{format_id}:{event_id}:{participant_id}",
                    "source": "melee",
                    "event_id": event_id,
                    "source_locator": (
                        f"{event_path.relative_to(root).as_posix()}#decklists/{index}"
                    ),
                    "deck": deck,
                }
            )
    return rows


def _classify(rule_set: Any, deck: Mapping[str, Any]) -> dict[str, Any]:
    adapter_errors = deck.get("__adapter_errors")
    if isinstance(adapter_errors, list):
        return {
            "status": "invalid_deck",
            "parent_id": None,
            "subtype_id": None,
            "rule_id": None,
            "conflict_kind": None,
            "priority_tie": False,
            "matched_rule_ids": [],
            "overridden_rule_ids": [],
            "errors": adapter_errors,
        }
    return _identity(classify_deck(rule_set, deck))


def _expected_map(path: Path | None) -> dict[str, dict[str, Any]] | None:
    if path is None:
        return None
    value = _json_object(path)
    rows = value.get("expected_changes")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected_changes must be a list")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("record_id"), str):
            raise ValueError(f"{path}: expected change is invalid")
        candidate = row.get("candidate")
        if not isinstance(candidate, dict):
            raise ValueError(f"{path}: expected candidate identity is invalid")
        required_candidate = {"status", "parent_id", "subtype_id", "rule_id"}
        if set(candidate) != required_candidate:
            raise ValueError(
                f"{path}: expected candidate must bind "
                + ", ".join(sorted(required_candidate))
            )
        change_kinds = row.get("change_kinds")
        if (
            not isinstance(change_kinds, list)
            or not change_kinds
            or any(not isinstance(kind, str) or not kind for kind in change_kinds)
            or len(change_kinds) != len(set(change_kinds))
        ):
            raise ValueError(f"{path}: expected change kinds are invalid")
        record_id = row["record_id"]
        if record_id in result:
            raise ValueError(f"{path}: duplicate expected record {record_id}")
        result[record_id] = {
            "candidate": candidate,
            "change_kinds": sorted(change_kinds),
        }
    return result


def compare_classifier_impact(
    repository_root: str | Path,
    format_id: str,
    accepted_rules_path: str | Path,
    candidate_rules_path: str | Path,
    *,
    expected_changes_path: str | Path | None = None,
) -> dict[str, Any]:
    """Classify one retained corpus twice and explain every changed result."""

    root = Path(repository_root).resolve()
    accepted_path = Path(accepted_rules_path)
    candidate_path = Path(candidate_rules_path)
    if not accepted_path.is_absolute():
        accepted_path = root / accepted_path
    if not candidate_path.is_absolute():
        candidate_path = root / candidate_path
    expected_path = Path(expected_changes_path) if expected_changes_path is not None else None
    if expected_path is not None and not expected_path.is_absolute():
        expected_path = root / expected_path
    accepted = load_rule_set(accepted_path)
    candidate = load_rule_set(candidate_path)
    if accepted.format != format_id or candidate.format != format_id:
        raise ValueError("accepted and candidate rules must match the requested format")

    records = _mtgo_decks(root, format_id) + _melee_decks(root, format_id)
    records.sort(key=lambda item: item["record_id"])
    input_subject = [
        {
            "record_id": item["record_id"],
            "source_locator": item["source_locator"],
            "deck": item["deck"],
        }
        for item in records
    ]
    changes = []
    for item in records:
        before = _classify(accepted, item["deck"])
        after = _classify(candidate, item["deck"])
        if before == after:
            continue
        changes.append(
            {
                "record_id": item["record_id"],
                "source": item["source"],
                "event_id": item["event_id"],
                "source_locator": item["source_locator"],
                "before": before,
                "after": after,
                "change_kinds": _change_kinds(before, after),
            }
        )

    expected = _expected_map(expected_path)
    actual_by_id = {item["record_id"]: item for item in changes}
    missing_expected = []
    unexpected = []
    if expected is not None:
        for record_id, expected_change in expected.items():
            actual = actual_by_id.get(record_id)
            if actual is None or any(
                actual["after"].get(key) != value
                for key, value in expected_change["candidate"].items()
            ) or sorted(actual["change_kinds"]) != expected_change["change_kinds"]:
                missing_expected.append(record_id)
        unexpected = sorted(set(actual_by_id) - set(expected))

    if expected is None:
        status = "REVIEW_REQUIRED" if changes else "NO_RULE_CHANGE"
    elif missing_expected or unexpected:
        status = "UNEXPLAINED_IMPACT"
    else:
        status = "ACCEPTED_CHANGE_SET"
    return {
        "schema_version": "1.0.0",
        "operation": "classifier_impact",
        "status": status,
        "format": format_id,
        "accepted_classifier_subject": classifier_digest(accepted),
        "candidate_classifier_subject": classifier_digest(candidate),
        "retained_corpus": {
            "input_subject_digest": _sha256_json(input_subject),
            "record_count": len(records),
            "source_counts": {
                source: sum(item["source"] == source for item in records)
                for source in ("mtgo", "melee")
            },
            "same_input_used_for_both_rules": True,
        },
        "summary": {
            "change_count": len(changes),
            "new_unknown_count": sum("new_unknown" in item["change_kinds"] for item in changes),
            "new_conflict_count": sum("new_conflict" in item["change_kinds"] for item in changes),
            "identity_migration_count": sum(
                "identity_migration" in item["change_kinds"] for item in changes
            ),
            "subtype_drift_count": sum("subtype_drift" in item["change_kinds"] for item in changes),
            "classification_lost_count": sum(
                "classification_lost" in item["change_kinds"] for item in changes
            ),
            "missing_expected_record_ids": missing_expected,
            "unexpected_record_ids": unexpected,
        },
        "changes": changes,
    }


__all__ = ["compare_classifier_impact"]
