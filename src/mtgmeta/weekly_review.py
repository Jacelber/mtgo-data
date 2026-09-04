"""Build complete weekly classification review evidence from retained inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .classifier import ClassificationResult, classifier_digest, classify_deck
from .config import load_rule_set
from .mtgo import load_mtgo_event_collection_context
from .mtgo.classification import load_mtgo_events_for_format
from .mtgo.stats import high_score_threshold, rounds_from_player_count
from .melee.classification import build_classification_overlay_from_paths


MAX_OFFICIAL_PLACEMENT = 32
NAME_CATALOG = Path("configs/mtgo_archetype_names.yaml")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _sha256_json(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _positive_integer(value: Any, *, label: str) -> int:
    try:
        result = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if result < 1:
        raise ValueError(f"{label} must be positive")
    return result


def _name_authority(root: Path, format_id: str) -> dict[tuple[str, str | None], dict[str, str]]:
    path = root / NAME_CATALOG
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("names"), list):
        raise ValueError(f"{path}: names must be a list")
    result: dict[tuple[str, str | None], dict[str, str]] = {}
    for item in value["names"]:
        if not isinstance(item, dict) or item.get("format") != format_id:
            continue
        parent_id = item.get("parent_id")
        subtype_id = item.get("subtype_id")
        english = item.get("english")
        chinese = item.get("chinese")
        if (
            not isinstance(parent_id, str)
            or (subtype_id is not None and not isinstance(subtype_id, str))
            or not isinstance(english, str)
            or not isinstance(chinese, str)
            or item.get("review_status") != "approved"
        ):
            continue
        result[(parent_id, subtype_id)] = {"english": english, "chinese": chinese}
    return result


def _classification(result: ClassificationResult) -> dict[str, Any]:
    selected = None
    if result.status == "classified":
        selected = {
            "parent_id": result.archetype_id,
            "subtype_id": result.subtype_id,
            "rule_id": result.selected_rule_id,
        }
    return {
        "status": result.status,
        "selected": selected,
        "multiple_matches": len(result.matched_rules) > 1,
        "overridden_matches": len(result.overridden_matches),
        "conflict_kind": result.conflict_kind,
        "errors": list(result.errors),
    }


def _localized_identity(
    result: ClassificationResult,
    names: Mapping[tuple[str, str | None], Mapping[str, str]],
) -> dict[str, Any]:
    if result.status != "classified":
        return {
            "parent_id": None,
            "subtype_id": None,
            "parent_english": "Unknown",
            "parent_chinese": "未知",
            "subtype_english": None,
            "subtype_chinese": None,
        }
    assert result.archetype_id is not None
    parent = names.get((result.archetype_id, None))
    exact = names.get((result.archetype_id, result.subtype_id))
    if parent is None:
        raise ValueError(f"missing approved parent name for {result.archetype_id}")
    if result.subtype_id is not None and exact is None:
        raise ValueError(
            "missing approved subtype name for "
            f"{result.archetype_id}/{result.subtype_id}"
        )
    return {
        "parent_id": result.archetype_id,
        "subtype_id": result.subtype_id,
        "parent_english": parent["english"],
        "parent_chinese": parent["chinese"],
        "subtype_english": exact["english"] if exact is not None else None,
        "subtype_chinese": exact["chinese"] if exact is not None else None,
    }


def _priority_reasons(result: ClassificationResult) -> list[str]:
    reasons = []
    if result.status == "unknown":
        reasons.append("unknown")
    elif result.status == "conflict":
        reasons.append("classification_conflict")
    elif result.status == "invalid_deck":
        reasons.append("invalid_deck")
    if len(result.matched_rules) > 1:
        reasons.append("multiple_matches")
    if result.overridden_matches:
        reasons.append("overridden_matches")
    if result.conflict_kind == "subtype":
        reasons.append("subtype_conflict")
    return reasons


def _event_map(root: Path, format_id: str) -> dict[str, tuple[str, Mapping[str, Any]]]:
    context = load_mtgo_event_collection_context(root, format_id)
    events, _excluded = load_mtgo_events_for_format(
        context.paths["events"].glob("*.json"), root, format_id
    )
    result: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for source_file, event in events:
        event_id = str(event.get("event_id", ""))
        if not event_id:
            raise ValueError(f"{source_file}: missing event_id")
        if event_id in result:
            raise ValueError(f"duplicate retained MTGO event_id {event_id}")
        result[event_id] = (source_file, event)
    return result


def build_mtgo_weekly_review(
    repository_root: str | Path,
    format_id: str,
    week_id: str,
) -> dict[str, Any]:
    """Return every officially published weekly record, capped at rank 32."""

    root = Path(repository_root).resolve()
    from datetime import timedelta
    from .mtgo.publication import week_monday
    monday = week_monday(week_id)

    rule_path = root / "my_archetypes" / f"{format_id}.yaml"
    rules = load_rule_set(rule_path)
    names = _name_authority(root, format_id)
    retained = _event_map(root, format_id)
    events = [event for _, event in retained.values()
              if monday.isoformat() <= str(event["starttime"])[:10]
              <= (monday + timedelta(days=6)).isoformat()]
    events.sort(key=lambda event: (str(event["starttime"]), str(event["event_id"])))
    if not events:
        raise ValueError(f"{format_id} {week_id}: no retained official events")
    rows: list[dict[str, Any]] = []
    event_summaries: list[dict[str, Any]] = []

    for week_event in events:
        event_id = str(week_event.get("event_id", ""))
        if event_id not in retained:
            raise ValueError(f"retained MTGO event {event_id} is unavailable")
        source_file, event = retained[event_id]
        players = event.get("players")
        if not isinstance(players, list):
            raise ValueError(f"{source_file}: players must be a list")
        player_count = _positive_integer(event.get("player_count"), label="player_count")
        threshold = high_score_threshold(rounds_from_player_count(player_count))
        event_rows = []
        for index, player in enumerate(players):
            if not isinstance(player, dict):
                raise ValueError(f"{source_file}#players/{index}: must be an object")
            rank = _positive_integer(
                player.get("final_rank"), label=f"{source_file}#players/{index}/final_rank"
            )
            if rank > MAX_OFFICIAL_PLACEMENT:
                continue
            result = classify_deck(rules, player)
            score = int(str(player.get("swiss_score", "0")).strip())
            row = {
                "source": "mtgo",
                "format": format_id,
                "event_id": event_id,
                "event_name": str(event.get("description", "")),
                "date": str(event.get("starttime", ""))[:10],
                "player_count": player_count,
                "high_score_count": None,
                "rank": rank,
                "player": str(player.get("player") or player.get("name") or ""),
                "identity": _localized_identity(result, names),
                "classification": _classification(result),
                "priority_reasons": _priority_reasons(result),
                "source_locator": f"{source_file}#players/{index}",
            }
            event_rows.append((row, score >= threshold))
        event_rows.sort(key=lambda item: (item[0]["rank"], item[0]["source_locator"]))
        high_score_count = sum(is_high for _row, is_high in event_rows)
        for row, _is_high in event_rows:
            row["high_score_count"] = high_score_count
            rows.append(row)
        event_summaries.append(
            {
                "event_id": event_id,
                "event_name": str(event.get("description", "")),
                "date": str(event.get("starttime", ""))[:10],
                "player_count": player_count,
                "review_record_count": len(event_rows),
                "high_score_count": high_score_count,
                "source_file": source_file,
            }
        )

    subject = {
        "week": week_id,
        "format": format_id,
        "source": "mtgo",
        "event_ids": [item["event_id"] for item in event_summaries],
        "classifier_subject": classifier_digest(rules),
        "events": event_summaries,
        "records": [
            {key: value for key, value in row.items() if key != "priority_reasons"}
            for row in rows
        ],
    }
    return {
        "schema_version": "1.0.0",
        "document_type": "weekly_full_classification_review",
        "week": week_id,
        "format": format_id,
        "source": "mtgo",
        "classifier": {
            "rules_path": rule_path.relative_to(root).as_posix(),
            "subject_digest": classifier_digest(rules),
        },
        "event_ids": subject["event_ids"],
        "events": event_summaries,
        "records": rows,
        "machine_priority_records": [
            row for row in rows if row["priority_reasons"]
        ],
        "classification_review_digest": _sha256_json(subject),
        "decklists_embedded": False,
    }


def mtgo_record_detail(
    repository_root: str | Path,
    format_id: str,
    event_id: str,
    rank: int,
) -> dict[str, Any]:
    """Return one Owner-selected MTGO deck with its current rule result."""

    root = Path(repository_root).resolve()
    retained = _event_map(root, format_id)
    if event_id not in retained:
        raise ValueError(f"retained MTGO event {event_id} is unavailable")
    source_file, event = retained[event_id]
    rules_path = root / "my_archetypes" / f"{format_id}.yaml"
    rules = load_rule_set(rules_path)
    matches = [
        (index, player)
        for index, player in enumerate(event.get("players", []))
        if isinstance(player, dict) and int(str(player.get("final_rank", "0"))) == rank
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {event_id} rank {rank} record, found {len(matches)}")
    index, player = matches[0]
    result = classify_deck(rules, player)
    return {
        "source": "mtgo",
        "format": format_id,
        "event_id": event_id,
        "rank": rank,
        "player": player.get("player") or player.get("name"),
        "main_deck": player.get("main_deck", []),
        "sideboard": player.get("sideboard", []),
        "classification": _classification(result),
        "matched_rules": [item.rule_id for item in result.matched_rules],
        "rules_path": rules_path.relative_to(root).as_posix(),
        "classifier_subject": classifier_digest(rules),
        "source_locator": f"{source_file}#players/{index}",
    }


def build_melee_review(
    repository_root: str | Path,
    format_id: str,
    event_id: str,
) -> dict[str, Any]:
    """Build full available-deck review evidence for one review-ready Melee event."""

    root = Path(repository_root).resolve()
    event_path = root / "data" / format_id / "melee" / "events" / f"{event_id}.json"
    classification_path = (
        root / "data" / format_id / "melee" / "classifications" / f"{event_id}.json"
    )
    event = _json_object(event_path)
    overlay = _json_object(classification_path)
    rule_path = root / "my_archetypes" / f"{format_id}.yaml"
    rules = load_rule_set(rule_path)
    desired = classifier_digest(rules)
    classifier = overlay.get("classifier")
    if not isinstance(classifier, dict) or classifier.get("digest") != desired:
        raise ValueError(f"Melee {event_id} classification is not review-ready")
    reproduced = build_classification_overlay_from_paths(event_path, rule_path, root)
    if overlay != reproduced:
        raise ValueError(
            f"Melee {event_id} classification cannot be reproduced from retained source"
        )
    participants = {
        item.get("id"): item.get("display_name")
        for item in event.get("participants", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    standings = {
        item.get("participant_id"): item.get("rank")
        for item in event.get("standings", [])
        if isinstance(item, dict) and isinstance(item.get("participant_id"), str)
    }
    decklists = {
        item.get("participant_id"): item
        for item in event.get("decklists", [])
        if isinstance(item, dict)
        and item.get("status") == "submitted"
        and item.get("game_format") == format_id
        and isinstance(item.get("participant_id"), str)
    }
    names = _name_authority(root, format_id)
    rows = []
    classified_ids = set()
    for record in overlay.get("records", []):
        if not isinstance(record, dict):
            raise ValueError(f"{classification_path}: record must be an object")
        participant_id = record.get("participant_id")
        if not isinstance(participant_id, str) or participant_id not in decklists:
            raise ValueError(f"{classification_path}: classification has no submitted deck")
        classified_ids.add(participant_id)
        selected = record.get("selected") if isinstance(record.get("selected"), dict) else None
        status = record.get("classification_status")
        parent_id = selected.get("archetype_id") if selected else None
        subtype_id = selected.get("subtype_id") if selected else None
        if status == "classified":
            parent = names.get((parent_id, None))
            exact = names.get((parent_id, subtype_id))
            if parent is None or (subtype_id is not None and exact is None):
                raise ValueError(f"missing approved name for Melee identity {parent_id}/{subtype_id}")
            identity = {
                "parent_id": parent_id,
                "subtype_id": subtype_id,
                "parent_english": parent["english"],
                "parent_chinese": parent["chinese"],
                "subtype_english": exact["english"] if subtype_id is not None else None,
                "subtype_chinese": exact["chinese"] if subtype_id is not None else None,
            }
        else:
            identity = {
                "parent_id": None,
                "subtype_id": None,
                "parent_english": "Unknown",
                "parent_chinese": "未知",
                "subtype_english": None,
                "subtype_chinese": None,
            }
        reasons = []
        if status == "unknown":
            reasons.append("unknown")
        elif status == "conflict":
            reasons.append("classification_conflict")
        elif status == "invalid_deck":
            reasons.append("invalid_deck")
        if len(record.get("matched_rules", [])) > 1:
            reasons.append("multiple_matches")
        if record.get("overridden_matches"):
            reasons.append("overridden_matches")
        rows.append(
            {
                "source": "melee",
                "format": format_id,
                "event_id": event_id,
                "rank": standings.get(participant_id),
                "player": participants.get(participant_id),
                "participant_id": participant_id,
                "identity": identity,
                "classification_status": status,
                "priority_reasons": reasons,
                "source_locator": (
                    f"{classification_path.relative_to(root).as_posix()}"
                    f"#participant/{participant_id}"
                ),
            }
        )
    rows.sort(key=lambda item: (item["rank"] is None, item["rank"] or 0, item["participant_id"]))
    unavailable = [
        {
            "participant_id": participant_id,
            "player": participants.get(participant_id),
            "rank": standings.get(participant_id),
            "reason": "missing_or_unavailable_decklist",
        }
        for participant_id in sorted(set(participants) - classified_ids)
    ]
    return {
        "schema_version": "1.0.0",
        "document_type": "weekly_melee_classification_review",
        "format": format_id,
        "source": "melee",
        "event_id": event_id,
        "classifier": {
            "rules_path": rule_path.relative_to(root).as_posix(),
            "subject_digest": desired,
        },
        "available_records": rows,
        "unavailable_records": unavailable,
        "machine_priority_records": [row for row in rows if row["priority_reasons"]],
        "decklists_embedded": False,
    }


def melee_record_detail(
    repository_root: str | Path,
    format_id: str,
    event_id: str,
    participant_id: str,
) -> dict[str, Any]:
    """Return one Owner-selected Melee deck with its current rule result."""

    root = Path(repository_root).resolve()
    build_melee_review(root, format_id, event_id)
    event_path = root / "data" / format_id / "melee" / "events" / f"{event_id}.json"
    classification_path = (
        root / "data" / format_id / "melee" / "classifications" / f"{event_id}.json"
    )
    event = _json_object(event_path)
    overlay = _json_object(classification_path)
    decklists = [
        item
        for item in event.get("decklists", [])
        if isinstance(item, dict)
        and item.get("participant_id") == participant_id
        and item.get("status") == "submitted"
        and item.get("game_format") == format_id
    ]
    records = [
        item
        for item in overlay.get("records", [])
        if isinstance(item, dict) and item.get("participant_id") == participant_id
    ]
    if len(decklists) != 1 or len(records) != 1:
        raise ValueError(
            f"expected one Melee {event_id} participant {participant_id} record"
        )
    cards = decklists[0].get("cards")
    assert isinstance(cards, list)
    rule_path = root / "my_archetypes" / f"{format_id}.yaml"
    rules = load_rule_set(rule_path)
    standings = [
        item.get("rank")
        for item in event.get("standings", [])
        if isinstance(item, dict) and item.get("participant_id") == participant_id
    ]
    participants = [
        item.get("display_name")
        for item in event.get("participants", [])
        if isinstance(item, dict) and item.get("id") == participant_id
    ]
    return {
        "source": "melee",
        "format": format_id,
        "event_id": event_id,
        "participant_id": participant_id,
        "rank": standings[0] if len(standings) == 1 else None,
        "player": participants[0] if len(participants) == 1 else None,
        "main_deck": [item for item in cards if item.get("section") == "main"],
        "sideboard": [item for item in cards if item.get("section") == "sideboard"],
        "classification": records[0],
        "rules_path": rule_path.relative_to(root).as_posix(),
        "classifier_subject": classifier_digest(rules),
        "source_locator": (
            f"{event_path.relative_to(root).as_posix()}#participant/{participant_id}"
        ),
    }


def build_v2_completion_record(
    reviews: Sequence[Mapping[str, Any]],
    *,
    week_id: str,
    completed_on: str,
    evidence: str,
    landing_content_digests: Mapping[str, str],
    independent_format: bool = False,
) -> dict[str, Any]:
    """Build a minimal full-review completion record without writing a registry."""

    by_format = {str(review.get("format")): review for review in reviews}
    valid = bool(by_format) and set(by_format) <= {"standard", "modern"}
    if not valid or (not independent_format and set(by_format) != {"standard", "modern"}):
        raise ValueError("Weekly V2 completion must bind Standard and Modern")
    formats = {}
    for format_id in (item for item in ("standard", "modern") if item in by_format):
        review = by_format[format_id]
        classifier = review.get("classifier")
        if not isinstance(classifier, Mapping):
            raise ValueError(f"{format_id} review classifier is missing")
        event_ids = review.get("event_ids")
        classifier_subject = classifier.get("subject_digest")
        review_digest = review.get("classification_review_digest")
        landing_digest = landing_content_digests.get(format_id)
        if (
            not isinstance(event_ids, list)
            or not event_ids
            or any(
                not isinstance(event_id, str) or not event_id.isdigit()
                for event_id in event_ids
            )
        ):
            raise ValueError(f"{format_id} accepted event IDs are invalid")
        for label, digest in (
            ("classifier subject", classifier_subject),
            ("classification review", review_digest),
            ("Landing content", landing_digest),
        ):
            if not _is_sha256(digest):
                raise ValueError(f"{format_id} {label} digest is invalid")
        formats[format_id] = {
            "accepted_event_ids": list(event_ids),
            "accepted_classifier_subject": classifier_subject,
            "classification_review_digest": review_digest,
            "landing_content_digest": landing_digest,
        }
    return {
        "week": week_id,
        "review_scope": "full_official_classification_v2",
        "completed_on": completed_on,
        "evidence": evidence,
        "formats": formats,
    }


__all__ = [
    "MAX_OFFICIAL_PLACEMENT",
    "build_melee_review",
    "build_mtgo_weekly_review",
    "build_v2_completion_record",
    "melee_record_detail",
    "mtgo_record_detail",
]
