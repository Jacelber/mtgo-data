"""Build the private handoff for the weekly MTGO maintenance review."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from mtgmeta.classifier import classifier_digest
from mtgmeta.mtgo.normalize import load_rules_for_format


FORMATS = ("standard", "modern")
SCHEMA_VERSION = "1.6.0"
INTENTIONAL_UNKNOWN_CONFIG = Path("configs/mtgo_intentional_unknowns.yaml")
WEEKLY_REVIEW_COMPLETIONS_CONFIG = Path(
    "configs/mtgo_weekly_review_completions.yaml"
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return value


def _sorted_event_ids(values: list[Any]) -> list[str]:
    event_ids = {str(value) for value in values}
    if any(not value.isdigit() for value in event_ids):
        raise ValueError("Weekly source event IDs must contain digits only")
    return sorted(event_ids, key=int)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _top8_review_digest(root: Path, format_name: str, week_id: str) -> str:
    document = _read_json(
        root / "stats" / format_name / "mtgo" / "top8" / f"{week_id}.json"
    )
    events = []
    for event in document.get("events", []):
        if not isinstance(event, dict):
            raise ValueError(f"{format_name} Top 8 event is not an object")
        placements = []
        for placement in event.get("placements", []):
            if not isinstance(placement, dict):
                raise ValueError(f"{format_name} Top 8 placement is not an object")
            placements.append(
                {
                    field: placement.get(field)
                    for field in ("rank", "deck_status", "identity", "exact_deck")
                }
            )
        events.append(
            {
                field: event.get(field)
                for field in ("event_id", "name", "display_name", "date", "player_count")
            }
            | {"placements": placements}
        )
    subject = {
        "format": document.get("format"),
        "week": document.get("week"),
        "events": events,
    }
    return _sha256_json(subject)


def _landing_content_digest(root: Path, format_name: str, week_id: str) -> str | None:
    path = (
        root
        / "stats"
        / format_name
        / "mtgo"
        / "landing"
        / "features"
        / f"{week_id}.json"
    )
    if not path.exists():
        return None
    digest = _read_json(path).get("content_digest")
    return digest if _is_sha256(digest) else None


def _completion_state(root: Path, week_id: str) -> dict[str, Any]:
    path = root / WEEKLY_REVIEW_COMPLETIONS_CONFIG
    if not path.exists():
        return {
            "state": "unrecorded",
            "completed_on": None,
            "evidence": None,
            "mismatches": [],
        }
    registry = _read_yaml(path)
    if registry.get("schema_version") != "1.0.0":
        raise ValueError("Weekly review completion registry schema_version must be 1.0.0")
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("Weekly review completion registry records must be a list")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("Weekly review completion registry records must be mappings")
    matches = [record for record in records if record.get("week") == week_id]
    if len(matches) > 1:
        raise ValueError(f"Weekly review completion registry duplicates {week_id}")
    if not matches:
        return {
            "state": "unrecorded",
            "completed_on": None,
            "evidence": None,
            "mismatches": [],
        }
    record = matches[0]
    completed_on = record.get("completed_on")
    evidence = record.get("evidence")
    subjects = record.get("formats")
    if not isinstance(completed_on, str) or not isinstance(evidence, str):
        raise ValueError(f"Weekly review completion record for {week_id} is incomplete")
    if not isinstance(subjects, dict) or set(subjects) != set(FORMATS):
        raise ValueError(
            f"Weekly review completion record for {week_id} must bind Standard and Modern"
        )
    mismatches = []
    for format_name in FORMATS:
        expected = subjects.get(format_name)
        if not isinstance(expected, dict):
            raise ValueError(f"{week_id} {format_name} completion subject is invalid")
        expected_top8 = expected.get("top8_review_digest")
        expected_landing = expected.get("landing_content_digest")
        if not _is_sha256(expected_top8) or not _is_sha256(expected_landing):
            raise ValueError(f"{week_id} {format_name} completion digests are invalid")
        if _top8_review_digest(root, format_name, week_id) != expected_top8:
            mismatches.append(f"{format_name} Top 8 review subject")
        if _landing_content_digest(root, format_name, week_id) != expected_landing:
            mismatches.append(f"{format_name} Landing content")
    return {
        "state": "stale" if mismatches else "verified",
        "completed_on": completed_on,
        "evidence": evidence,
        "mismatches": mismatches,
    }


def _default_landing_subject_builder(
    root: str | Path,
    format_name: str,
    week_id: str,
) -> dict[str, Any]:
    from mtgmeta.mtgo.landing_editorial import build_top8_subject

    return build_top8_subject(root, format_name, week_id)


def _landing_binding(
    subject: Any,
    *,
    format_name: str,
    week_id: str,
    week_entry: dict[str, Any],
    source_event_ids: list[str],
    classifier_digest: str,
) -> dict[str, Any]:
    if not isinstance(subject, dict):
        raise ValueError(f"{format_name} Landing machine-fact subject is not an object")
    subject_week = subject.get("week")
    if not isinstance(subject_week, dict):
        raise ValueError(f"{format_name} Landing machine-fact subject has no week")
    subject_event_ids = _sorted_event_ids(subject.get("source_event_ids", []))
    digests = {
        field: subject.get(field)
        for field in (
            "classifier_digest",
            "selection_policy_digest",
            "machine_fact_digest",
            "link_catalog_digest",
        )
    }
    invalid_digests = [field for field, value in digests.items() if not _is_sha256(value)]
    if invalid_digests:
        raise ValueError(
            f"{format_name} Landing machine-fact subject has invalid digests: "
            + ", ".join(invalid_digests)
        )
    expected_week = {
        "id": week_id,
        "start": week_entry.get("start"),
        "end": week_entry.get("end"),
    }
    mismatches = []
    if subject.get("format") != format_name:
        mismatches.append("format")
    if any(subject_week.get(key) != value for key, value in expected_week.items()):
        mismatches.append("week")
    if subject_event_ids != source_event_ids:
        mismatches.append("source_event_ids")
    if digests["classifier_digest"] != classifier_digest:
        mismatches.append("classifier_digest")
    return {
        "format": format_name,
        "status": "stale" if mismatches else "available",
        "source_event_ids": subject_event_ids,
        **digests,
        "reason": (
            "Landing machine-fact provenance does not match current Top 8: "
            + ", ".join(mismatches)
            if mismatches
            else None
        ),
    }


def _card_list(value: Any, *, field: str, format_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{format_name} Unknown record has no {field} list")
    cards = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{format_name} Unknown {field} contains a non-object")
        name = item.get("name")
        quantity = item.get("quantity")
        if not isinstance(name, str) or not name or not isinstance(quantity, int) or quantity < 1:
            raise ValueError(f"{format_name} Unknown {field} contains an invalid card")
        cards.append({"name": name, "quantity": quantity})
    return cards


def _unknown_record(record: Any, *, format_name: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"{format_name} Unknown report contains a non-object")
    normalized = {
        "deck_id": str(record.get("deck_id", "")),
        "event_id": str(record.get("event_id", "")),
        "event_name": str(record.get("event_name", "")),
        "event_start": str(record.get("event_start", "")),
        "source_file": str(record.get("source_file", "")),
        "main_deck": _card_list(record.get("main_deck"), field="main_deck", format_name=format_name),
        "sideboard": _card_list(record.get("sideboard"), field="sideboard", format_name=format_name),
    }
    if not normalized["deck_id"] or not normalized["event_id"].isdigit() or not normalized["source_file"]:
        raise ValueError(f"{format_name} Unknown record identity is invalid")
    return normalized


def _intentional_unknowns(root: Path) -> dict[str, dict[tuple[str, str, str], dict[str, str]]]:
    config = _read_yaml(root / INTENTIONAL_UNKNOWN_CONFIG)
    if config.get("schema_version") != "1.0.0":
        raise ValueError("Intentional Unknown registry has an unsupported schema version")
    records = config.get("records")
    if not isinstance(records, list):
        raise ValueError("Intentional Unknown registry has no records list")
    result: dict[str, dict[tuple[str, str, str], dict[str, str]]] = {
        format_name: {} for format_name in FORMATS
    }
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Intentional Unknown registry contains a non-object")
        format_name = item.get("format")
        event_id = str(item.get("event_id", ""))
        deck_id = str(item.get("deck_id", ""))
        source_file = str(item.get("source_file", ""))
        disposition = item.get("disposition")
        reason_code = item.get("reason_code")
        owner_accepted_on = str(item.get("owner_accepted_on", ""))
        evidence = str(item.get("evidence", ""))
        if format_name not in FORMATS or not event_id.isdigit() or not deck_id or not source_file:
            raise ValueError("Intentional Unknown registry contains an invalid identity")
        if disposition != "intentional_unknown" or reason_code != "random_card_pile":
            raise ValueError("Only Owner-accepted random card piles may remain intentional Unknown")
        if not owner_accepted_on or not evidence:
            raise ValueError("Intentional Unknown registry entry lacks acceptance evidence")
        key = (event_id, deck_id, source_file)
        if key in result[format_name]:
            raise ValueError("Intentional Unknown registry contains a duplicate identity")
        result[format_name][key] = {
            "disposition": disposition,
            "reason_code": reason_code,
            "owner_accepted_on": owner_accepted_on,
            "evidence": evidence,
        }
    return result


def _latest_week(root: Path, format_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = root / "stats" / format_name / "mtgo" / "top8"
    index = _read_json(directory / "index.json")
    weeks = index.get("weeks")
    if not isinstance(weeks, list) or not weeks or not isinstance(weeks[0], dict):
        raise ValueError(f"{format_name} Top 8 index has no reviewable week")
    week_entry = weeks[0]
    week_file = week_entry.get("file")
    if not isinstance(week_file, str):
        raise ValueError(f"{format_name} Top 8 week file is missing")
    week = _read_json(directory / week_file)
    expected_start = index.get("latest_complete_week")
    if week_entry.get("start") != expected_start:
        raise ValueError(f"{format_name} latest complete week does not match its index")
    if week.get("week") != {"start": week_entry.get("start"), "end": week_entry.get("end")}:
        raise ValueError(f"{format_name} Top 8 week dates do not match its index")
    if week.get("classifier_digest") != index.get("classifier_digest"):
        raise ValueError(f"{format_name} classifier digests do not match")
    return index, week


def _current_classifier_digest(root: Path, format_name: str) -> str:
    return classifier_digest(load_rules_for_format(root, format_name))


def _public_classifier_binding(
    root: Path,
    format_name: str,
    *,
    top8_index: dict[str, Any],
    top8_week: dict[str, Any],
    expected_digest: str,
) -> dict[str, Any]:
    statistics_root = root / "stats" / format_name / "mtgo"
    latest_complete_week = top8_index.get("latest_complete_week")
    week_id = Path(top8_index["weeks"][0]["file"]).stem
    subjects = [
        ("top8_index", statistics_root / "top8" / "index.json", top8_index),
        ("top8_week", statistics_root / "top8" / f"{week_id}.json", top8_week),
    ]

    statistics_index_path = statistics_root / "index.json"
    statistics_index = _read_json(statistics_index_path)
    if statistics_index.get("latest_complete_week") != latest_complete_week:
        raise ValueError(f"{format_name} statistics use a different complete week")
    subjects.append(("statistics_index", statistics_index_path, statistics_index))
    ranges = statistics_index.get("ranges")
    if not isinstance(ranges, list) or not ranges:
        raise ValueError(f"{format_name} statistics index has no ranges")
    for entry in ranges:
        if not isinstance(entry, dict):
            raise ValueError(f"{format_name} statistics range entry is invalid")
        for family, field in (("statistics_range", "file"), ("representative_decks", "decks_file")):
            filename = entry.get(field)
            if not isinstance(filename, str):
                raise ValueError(f"{format_name} statistics range is missing {field}")
            path = statistics_root / filename
            subjects.append((family, path, _read_json(path)))

    matchup_index_path = statistics_root / "matchup_index.json"
    matchup_index = _read_json(matchup_index_path)
    if matchup_index.get("latest_complete_week") != latest_complete_week:
        raise ValueError(f"{format_name} matchups use a different complete week")
    subjects.append(("matchup_index", matchup_index_path, matchup_index))
    matchup_ranges = matchup_index.get("ranges")
    if not isinstance(matchup_ranges, list) or not matchup_ranges:
        raise ValueError(f"{format_name} matchup index has no ranges")
    for entry in matchup_ranges:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise ValueError(f"{format_name} matchup range entry is invalid")
        path = statistics_root / entry["file"]
        subjects.append(("matchup_range", path, _read_json(path)))

    hierarchy_path = statistics_root / "archetype_hierarchy.json"
    subjects.append(("archetype_hierarchy", hierarchy_path, _read_json(hierarchy_path)))

    products = []
    for family, path, document in subjects:
        actual_digest = document.get("classifier_digest")
        if actual_digest != expected_digest:
            relative = path.relative_to(root).as_posix()
            raise ValueError(
                f"{format_name} public classifier binding mismatch: {relative}"
            )
        products.append({"family": family, "path": path.relative_to(root).as_posix()})
    return {
        "status": "current",
        "classifier_digest": expected_digest,
        "latest_complete_week": latest_complete_week,
        "products": products,
    }


def _format_readiness(
    root: Path,
    format_name: str,
    intentional_unknowns: dict[tuple[str, str, str], dict[str, str]],
    landing_subject: dict[str, Any],
    current_classifier_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    index, week = _latest_week(root, format_name)
    week_entry = index["weeks"][0]
    week_id = Path(week_entry["file"]).stem
    events = week.get("events")
    if not isinstance(events, list):
        raise ValueError(f"{format_name} Top 8 week has no event list")
    top8_event_ids = _sorted_event_ids(
        [event.get("event_id") for event in events if isinstance(event, dict)]
    )
    if len(top8_event_ids) != len(events):
        raise ValueError(f"{format_name} Top 8 events have duplicate or missing IDs")
    classifier_digest = str(index.get("classifier_digest", ""))
    public_classifier_binding = _public_classifier_binding(
        root,
        format_name,
        top8_index=index,
        top8_week=week,
        expected_digest=current_classifier_digest,
    )
    landing_binding = _landing_binding(
        landing_subject,
        format_name=format_name,
        week_id=week_id,
        week_entry=week_entry,
        source_event_ids=top8_event_ids,
        classifier_digest=classifier_digest,
    )

    report_index = _read_json(root / "reports" / format_name / "mtgo" / "index.json")
    report_summary = report_index.get("summary")
    if not isinstance(report_summary, dict):
        raise ValueError(f"{format_name} classification summary is missing")
    unknown_report = _read_json(
        root / "reports" / format_name / "mtgo" / "unknown_decks.json"
    )
    unknown_records = unknown_report.get("records")
    if not isinstance(unknown_records, list):
        raise ValueError(f"{format_name} Unknown report records are missing")
    normalized_unknowns = [
        _unknown_record(record, format_name=format_name) for record in unknown_records
    ]
    total_unknown_count = int(report_summary.get("unknown", -1))
    if total_unknown_count != len(normalized_unknowns):
        raise ValueError(f"{format_name} Unknown report count does not match its summary")
    unresolved_unknowns = []
    accepted_intentional_unknowns = []
    for record in normalized_unknowns:
        key = (record["event_id"], record["deck_id"], record["source_file"])
        accepted = intentional_unknowns.get(key)
        if accepted is None:
            unresolved_unknowns.append(record)
        else:
            accepted_intentional_unknowns.append({**record, **accepted})
    record_sort = lambda item: (int(item["event_id"]), item["deck_id"])
    unresolved_unknowns.sort(key=record_sort)
    accepted_intentional_unknowns.sort(key=record_sort)
    review_event_ids = set(top8_event_ids)
    review_week_unresolved_unknowns = [
        record for record in unresolved_unknowns if record["event_id"] in review_event_ids
    ]
    review_week_intentional_unknowns = [
        record
        for record in accepted_intentional_unknowns
        if record["event_id"] in review_event_ids
    ]
    outside_review_week_unresolved_unknowns = [
        record for record in unresolved_unknowns if record["event_id"] not in review_event_ids
    ]

    candidate_path = (
        root
        / "stats"
        / format_name
        / "mtgo"
        / "landing"
        / "review"
        / f"candidates_{week_id}.yaml"
    )
    if candidate_path.exists():
        candidate = _read_yaml(candidate_path)
        expected_classifier_digest = classifier_digest
        candidate_classifier_digest = candidate.get("classifier_digest")
        if not isinstance(candidate_classifier_digest, str):
            candidate_classifier_digest = None
        expected_selection_policy_digest = landing_binding["selection_policy_digest"]
        candidate_selection_policy_digest = candidate.get("selection_policy_digest")
        if not isinstance(candidate_selection_policy_digest, str):
            candidate_selection_policy_digest = None
        expected = {
            "week": week_id,
            "start": week_entry.get("start"),
            "end": week_entry.get("end"),
            "week_status": week_entry.get("status"),
            "provisional_through": week_entry.get("provisional_through"),
            "seal_on": week_entry.get("seal_on"),
        }
        mismatches = [key for key, value in expected.items() if candidate.get(key) != value]
        stale_reasons = []
        if mismatches:
            stale_reasons.append(f"lifecycle fields: {', '.join(mismatches)}")
        candidate_event_ids = _sorted_event_ids(candidate.get("source_event_ids", []))
        if candidate_event_ids != top8_event_ids:
            stale_reasons.append("source_event_ids")
        if candidate_classifier_digest != expected_classifier_digest:
            stale_reasons.append("classifier_digest")
        if candidate_selection_policy_digest != expected_selection_policy_digest:
            stale_reasons.append("selection_policy_digest")
        existing_changes = candidate.get("existing_changes")
        new_archetypes = candidate.get("new_archetypes")
        if not isinstance(existing_changes, list) or not isinstance(new_archetypes, list):
            raise ValueError(f"{format_name} Landing screening candidate lists are missing")
        landing_screening = {
            "status": (
                "stale_review_required"
                if stale_reasons
                else "candidate_review_required"
            ),
            "candidate_file": candidate_path.relative_to(root).as_posix(),
            "candidate_classifier_digest": candidate_classifier_digest,
            "expected_classifier_digest": expected_classifier_digest,
            "candidate_selection_policy_digest": candidate_selection_policy_digest,
            "expected_selection_policy_digest": expected_selection_policy_digest,
            "reason": (
                "Landing screening candidate provenance does not match current Top 8: "
                + ", ".join(stale_reasons)
                if stale_reasons
                else None
            ),
            "existing_change_count": len(existing_changes),
            "new_archetype_count": len(new_archetypes),
            "total_candidate_count": len(existing_changes) + len(new_archetypes),
        }
    else:
        landing_screening = {
            "status": "unavailable",
            "candidate_file": candidate_path.relative_to(root).as_posix(),
            "candidate_classifier_digest": None,
            "expected_classifier_digest": classifier_digest,
            "candidate_selection_policy_digest": None,
            "expected_selection_policy_digest": landing_binding["selection_policy_digest"],
            "reason": "Landing screening candidate file is missing.",
            "existing_change_count": None,
            "new_archetype_count": None,
            "total_candidate_count": None,
        }

    strict_validation = str(report_summary.get("strict_validation", "missing"))
    conflicts = int(report_summary.get("conflicts", -1))
    invalid_decks = int(report_summary.get("invalid_decks", -1))
    classification_status = (
        "review_required"
        if strict_validation == "pass" and conflicts == 0 and invalid_decks == 0
        else "blocked"
    )
    return {
        "format": format_name,
        "classifier_digest": classifier_digest,
        "public_classifier_binding": public_classifier_binding,
        "source_event_ids": top8_event_ids,
        "source_event_count": len(top8_event_ids),
        "classification": {
            "status": classification_status,
            "scope": "review_week_source_events",
            "validation_scope": str(report_index.get("scope", "")),
            "total_unknown_count": len(review_week_unresolved_unknowns)
            + len(review_week_intentional_unknowns),
            "unresolved_unknown_count": len(review_week_unresolved_unknowns),
            "unresolved_unknown_records": review_week_unresolved_unknowns,
            "accepted_intentional_unknown_count": len(review_week_intentional_unknowns),
            "accepted_intentional_unknown_records": review_week_intentional_unknowns,
            "conflict_count": conflicts,
            "invalid_deck_count": invalid_decks,
            "strict_validation": strict_validation,
        },
        "retained_corpus_unknown_queue": {
            "scope": str(report_index.get("scope", "")),
            "total_unknown_count": total_unknown_count,
            "unresolved_unknown_count": len(unresolved_unknowns),
            "unresolved_unknown_records": unresolved_unknowns,
            "accepted_intentional_unknown_count": len(accepted_intentional_unknowns),
            "accepted_intentional_unknown_records": accepted_intentional_unknowns,
            "outside_review_week_unresolved_unknown_count": len(
                outside_review_week_unresolved_unknowns
            ),
            "outside_review_week_unresolved_unknown_records": (
                outside_review_week_unresolved_unknowns
            ),
        },
        "visual_metadata": {
            "representative_cards": {
                "status": "manual_review_required",
                "exception_count": None,
                "reason": "No deterministic representative-card exception report exists; the maintained configuration remains a manual review input.",
            },
            "deck_colors": {
                "status": "manual_review_required",
                "exception_count": None,
                "reason": "No deterministic deck-color exception report exists.",
            },
        },
        "landing_screening": landing_screening,
    }, landing_binding


def build_readiness(
    root: Path,
    *,
    publication_sha: str,
    production_run_id: str,
    production_run_attempt: str,
    source_sha: str,
    generated_at: str,
    landing_subject_builder: Callable[[str | Path, str, str], dict[str, Any]] | None = None,
    classifier_digest_builder: Callable[[Path, str], str] | None = None,
) -> dict[str, Any]:
    intentional_unknowns = _intentional_unknowns(root)
    standard_entry = _read_json(root / "stats" / "standard" / "mtgo" / "top8" / "index.json")["weeks"][0]
    modern_entry = _read_json(root / "stats" / "modern" / "mtgo" / "top8" / "index.json")["weeks"][0]
    lifecycle_fields = ("file", "start", "end", "status", "provisional_through", "seal_on")
    if any(standard_entry.get(key) != modern_entry.get(key) for key in lifecycle_fields):
        raise ValueError("Standard and Modern do not expose the same weekly review window")
    week_id = Path(standard_entry["file"]).stem
    subject_builder = landing_subject_builder or _default_landing_subject_builder
    digest_builder = classifier_digest_builder or _current_classifier_digest
    results = [
        _format_readiness(
            root,
            format_name,
            intentional_unknowns[format_name],
            subject_builder(root, format_name, week_id),
            digest_builder(root, format_name),
        )
        for format_name in FORMATS
    ]
    formats = [item for item, _binding in results]
    bindings = [binding for _item, binding in results]
    blockers = []
    for item, binding in zip(formats, bindings, strict=True):
        format_name = item["format"]
        if item["classification"]["status"] == "blocked":
            blockers.append(f"{format_name} classification")
        if item["landing_screening"]["status"] != "candidate_review_required":
            blockers.append(f"{format_name} Landing screening")
        if binding["status"] != "available":
            blockers.append(f"{format_name} Landing machine-fact binding")
    blocked = bool(blockers)
    landing = {
        "status": "blocked" if blocked else "ready_for_human_review",
        "optional_draft_status": "not_requested",
        "bindings": bindings,
        "reason": (
            "; ".join(blockers) + " must be resolved before Landing human review."
            if blockers
            else None
        ),
    }
    completion = _completion_state(root, week_id)
    if blocked:
        status = "blocked"
        next_action = "resolve_blocker"
    elif completion["state"] == "verified":
        status = "completed"
        next_action = "none"
    elif completion["state"] == "stale":
        status = "revalidation_required"
        next_action = "owner_revalidation_required"
    else:
        status = "awaiting_owner_start"
        next_action = "owner_start_required"
    digest_subject = {
        "schema_version": SCHEMA_VERSION,
        "week": {
            "id": week_id,
            "start": standard_entry["start"],
            "end": standard_entry["end"],
            "status": standard_entry["status"],
            "provisional_through": standard_entry["provisional_through"],
            "seal_on": standard_entry["seal_on"],
        },
        "formats": formats,
        "landing": landing,
        "completion": completion,
    }
    digest = _sha256_json(digest_subject)
    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "weekly_maintenance_readiness",
        "review_id": f"{week_id}@{publication_sha[:12]}",
        "readiness_digest": digest,
        "generated_at": generated_at,
        "status": status,
        "production": {
            "publication_sha": publication_sha,
            "source_sha": source_sha,
            "run_id": production_run_id,
            "run_attempt": production_run_attempt,
        },
        "week": digest_subject["week"],
        "formats": formats,
        "landing": landing,
        "completion": completion,
        "workflow": {
            "next_action": next_action,
            "codex_automation_required": False,
            "repository_mutation_authorized": False,
        },
    }


def _write_github_output(path: Path, document: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"week={document['week']['id']}\n")
        handle.write(f"review-id={document['review_id']}\n")
        handle.write(f"readiness-digest={document['readiness_digest']}\n")
        handle.write(f"status={document['status']}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publication-sha", required=True)
    parser.add_argument("--production-run-id", required=True)
    parser.add_argument("--production-run-attempt", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    generated_at = args.generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    document = build_readiness(
        args.repository_root.resolve(),
        publication_sha=args.publication_sha,
        production_run_id=args.production_run_id,
        production_run_attempt=args.production_run_attempt,
        source_sha=args.source_sha,
        generated_at=generated_at,
    )
    schema = _read_json(
        args.repository_root.resolve()
        / "schemas"
        / "weekly-maintenance-readiness.schema.json"
    )
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if args.github_output:
        _write_github_output(args.github_output, document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
