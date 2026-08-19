import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tools.generate_weekly_maintenance_readiness import build_readiness


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_format(root: Path, format_name: str, *, candidate: bool = True) -> None:
    digest = "a" * 64 if format_name == "standard" else "b" * 64
    top8 = root / "stats" / format_name / "mtgo" / "top8"
    entry = {
        "file": "2026-W33.json",
        "start": "2026-08-10",
        "end": "2026-08-16",
        "status": "provisional",
        "provisional_through": "2026-08-23",
        "seal_on": "2026-08-24",
    }
    _write_json(
        top8 / "index.json",
        {
            "classifier_digest": digest,
            "latest_complete_week": "2026-08-10",
            "weeks": [entry],
        },
    )
    _write_json(
        top8 / "2026-W33.json",
        {
            "classifier_digest": digest,
            "week": {"start": "2026-08-10", "end": "2026-08-16"},
            "events": [{"event_id": "100"}, {"event_id": "101"}],
        },
    )
    reports = root / "reports" / format_name / "mtgo"
    _write_json(
        reports / "index.json",
        {
            "scope": "all_available_events",
            "summary": {
                "unknown": 2,
                "conflicts": 0,
                "invalid_decks": 0,
                "strict_validation": "pass",
            },
        },
    )
    _write_json(
        reports / "unknown_decks.json",
        {
            "records": [
                {
                    "deck_id": f"{format_name}-current",
                    "event_id": "101",
                    "event_name": "Current event",
                    "event_start": "2026-08-16 20:00:00.0",
                    "source_file": f"data/{format_name}/current.json",
                },
                {
                    "deck_id": f"{format_name}-old",
                    "event_id": "99",
                    "event_name": "Old event",
                    "event_start": "2026-08-09 20:00:00.0",
                    "source_file": f"data/{format_name}/old.json",
                },
            ]
        },
    )
    if candidate:
        pickup = root / "stats" / format_name / "mtgo" / "pickup"
        pickup.mkdir(parents=True, exist_ok=True)
        (pickup / "candidates_2026-W33.yaml").write_text(
            yaml.safe_dump(
                {
                    "week": "2026-W33",
                    "start": "2026-08-10",
                    "end": "2026-08-16",
                    "week_status": "provisional",
                    "provisional_through": "2026-08-23",
                    "seal_on": "2026-08-24",
                    "source_event_ids": ["101", "100"],
                    "existing_changes": [{"candidate": 1}],
                    "new_archetypes": [{"candidate": 2}, {"candidate": 3}],
                }
            ),
            encoding="utf-8",
        )


def _build(root: Path, generated_at: str = "2026-08-19T09:00:00Z") -> dict:
    return build_readiness(
        root,
        publication_sha="1" * 40,
        production_run_id="123",
        production_run_attempt="1",
        source_sha="2" * 40,
        generated_at=generated_at,
    )


def test_readiness_is_schema_valid_and_filters_unknowns_to_the_review_week(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)

    document = _build(tmp_path)

    schema = json.loads(
        (ROOT / "schemas" / "weekly-maintenance-readiness.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        document
    )
    assert document["status"] == "awaiting_owner_start"
    assert document["workflow"]["codex_automation_required"] is False
    for item in document["formats"]:
        assert item["classification"]["review_week_unknown_count"] == 1
        assert item["classification"]["review_week_unknown_records"][0]["event_id"] == "101"
        assert item["pickup"]["total_candidate_count"] == 3
        assert item["visual_metadata"]["deck_colors"]["exception_count"] is None


def test_readiness_digest_ignores_run_time_but_binds_review_inputs(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)

    first = _build(tmp_path, "2026-08-19T09:00:00Z")
    second = _build(tmp_path, "2026-08-20T09:00:00Z")
    assert first["readiness_digest"] == second["readiness_digest"]

    candidate_path = (
        tmp_path / "stats" / "modern" / "mtgo" / "pickup" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["new_archetypes"].append({"candidate": 4})
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")
    changed = _build(tmp_path, "2026-08-20T09:00:00Z")
    assert changed["readiness_digest"] != first["readiness_digest"]


def test_missing_pickup_candidate_is_reported_as_a_blocker(tmp_path):
    _write_format(tmp_path, "standard")
    _write_format(tmp_path, "modern", candidate=False)

    document = _build(tmp_path)

    assert document["status"] == "blocked"
    assert document["workflow"]["next_action"] == "resolve_blocker"
    assert document["formats"][1]["pickup"]["status"] == "unavailable"


def test_mismatched_format_week_fails_closed(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    modern_index = tmp_path / "stats" / "modern" / "mtgo" / "top8" / "index.json"
    value = json.loads(modern_index.read_text(encoding="utf-8"))
    value["weeks"][0]["seal_on"] = "2026-08-25"
    _write_json(modern_index, value)
    candidate_path = (
        tmp_path / "stats" / "modern" / "mtgo" / "pickup" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["seal_on"] = "2026-08-25"
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    with pytest.raises(ValueError, match="same weekly review window"):
        _build(tmp_path)
