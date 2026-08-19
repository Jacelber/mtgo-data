"""Build the private handoff for the weekly MTGO maintenance review."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import yaml


FORMATS = ("standard", "modern")
SCHEMA_VERSION = "1.0.0"


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


def _format_readiness(root: Path, format_name: str) -> dict[str, Any]:
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
    event_id_set = set(top8_event_ids)
    weekly_unknown = []
    for record in unknown_records:
        if not isinstance(record, dict) or str(record.get("event_id")) not in event_id_set:
            continue
        weekly_unknown.append(
            {
                "deck_id": str(record.get("deck_id", "")),
                "event_id": str(record.get("event_id", "")),
                "event_name": str(record.get("event_name", "")),
                "event_start": str(record.get("event_start", "")),
                "source_file": str(record.get("source_file", "")),
            }
        )
    weekly_unknown.sort(key=lambda item: (int(item["event_id"]), item["deck_id"]))

    candidate_path = (
        root
        / "stats"
        / format_name
        / "mtgo"
        / "pickup"
        / f"candidates_{week_id}.yaml"
    )
    if candidate_path.exists():
        candidate = _read_yaml(candidate_path)
        expected = {
            "week": week_id,
            "start": week_entry.get("start"),
            "end": week_entry.get("end"),
            "week_status": week_entry.get("status"),
            "provisional_through": week_entry.get("provisional_through"),
            "seal_on": week_entry.get("seal_on"),
        }
        mismatches = [key for key, value in expected.items() if candidate.get(key) != value]
        if mismatches:
            raise ValueError(
                f"{format_name} Pickup candidate mismatches: {', '.join(mismatches)}"
            )
        candidate_event_ids = _sorted_event_ids(candidate.get("source_event_ids", []))
        if candidate_event_ids != top8_event_ids:
            raise ValueError(f"{format_name} Pickup candidate event IDs do not match Top 8")
        existing_changes = candidate.get("existing_changes")
        new_archetypes = candidate.get("new_archetypes")
        if not isinstance(existing_changes, list) or not isinstance(new_archetypes, list):
            raise ValueError(f"{format_name} Pickup candidate lists are missing")
        pickup = {
            "status": "candidate_review_required",
            "candidate_file": candidate_path.relative_to(root).as_posix(),
            "existing_change_count": len(existing_changes),
            "new_archetype_count": len(new_archetypes),
            "total_candidate_count": len(existing_changes) + len(new_archetypes),
        }
    else:
        pickup = {
            "status": "unavailable",
            "candidate_file": candidate_path.relative_to(root).as_posix(),
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
        "classifier_digest": str(index.get("classifier_digest", "")),
        "source_event_ids": top8_event_ids,
        "source_event_count": len(top8_event_ids),
        "classification": {
            "status": classification_status,
            "scope": str(report_index.get("scope", "")),
            "total_unknown_count": int(report_summary.get("unknown", -1)),
            "review_week_unknown_count": len(weekly_unknown),
            "review_week_unknown_records": weekly_unknown,
            "conflict_count": conflicts,
            "invalid_deck_count": invalid_decks,
            "strict_validation": strict_validation,
            "since_last_review": {
                "status": "not_available",
                "reason": "No accepted prior weekly review manifest exists yet.",
            },
        },
        "visual_metadata": {
            "representative_cards": {
                "status": "manual_review_required",
                "exception_count": None,
                "reason": "The approved representative-card configuration is not implemented.",
            },
            "deck_colors": {
                "status": "manual_review_required",
                "exception_count": None,
                "reason": "No deterministic deck-color exception report exists.",
            },
        },
        "pickup": pickup,
    }


def build_readiness(
    root: Path,
    *,
    publication_sha: str,
    production_run_id: str,
    production_run_attempt: str,
    source_sha: str,
    generated_at: str,
) -> dict[str, Any]:
    formats = [_format_readiness(root, format_name) for format_name in FORMATS]
    standard_entry = _read_json(root / "stats" / "standard" / "mtgo" / "top8" / "index.json")["weeks"][0]
    modern_entry = _read_json(root / "stats" / "modern" / "mtgo" / "top8" / "index.json")["weeks"][0]
    lifecycle_fields = ("file", "start", "end", "status", "provisional_through", "seal_on")
    if any(standard_entry.get(key) != modern_entry.get(key) for key in lifecycle_fields):
        raise ValueError("Standard and Modern do not expose the same weekly review window")
    week_id = Path(standard_entry["file"]).stem
    blocked = any(
        item["classification"]["status"] == "blocked"
        or item["pickup"]["status"] == "unavailable"
        for item in formats
    )
    digest_subject = {
        "schema_version": SCHEMA_VERSION,
        "publication_sha": publication_sha,
        "week": {
            "id": week_id,
            "start": standard_entry["start"],
            "end": standard_entry["end"],
            "status": standard_entry["status"],
            "provisional_through": standard_entry["provisional_through"],
            "seal_on": standard_entry["seal_on"],
        },
        "formats": formats,
    }
    digest = hashlib.sha256(
        json.dumps(digest_subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "weekly_maintenance_readiness",
        "review_id": f"{week_id}@{publication_sha[:12]}",
        "readiness_digest": digest,
        "generated_at": generated_at,
        "status": "blocked" if blocked else "awaiting_owner_start",
        "production": {
            "publication_sha": publication_sha,
            "source_sha": source_sha,
            "run_id": production_run_id,
            "run_attempt": production_run_attempt,
        },
        "week": digest_subject["week"],
        "formats": formats,
        "landing": {
            "machine_draft_status": "not_available",
            "human_final_status": "not_started",
            "development_gate": "evaluate_after_maintenance_rehearsal",
            "reason": "P12-10 Landing production is not implemented or authorized by this workflow.",
        },
        "workflow": {
            "next_action": "resolve_blocker" if blocked else "owner_start_required",
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
