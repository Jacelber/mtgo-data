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


def _unknown_record(format_name: str, label: str, event_id: str) -> dict:
    return {
        "deck_id": f"{format_name}-{label}",
        "event_id": event_id,
        "event_name": f"{label.title()} event",
        "event_start": "2026-08-16 20:00:00.0",
        "source_file": f"data/{format_name}/{label}.json",
        "main_deck": [{"name": f"{label.title()} Card", "quantity": 4}],
        "sideboard": [{"name": "Sideboard Card", "quantity": 2}],
    }


def _write_intentional_unknowns(root: Path, *, reason_code: str = "random_card_pile") -> None:
    path = root / "configs" / "mtgo_intentional_unknowns.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "records": [
                    {
                        "format": "standard",
                        "event_id": "98",
                        "deck_id": "standard-random",
                        "source_file": "data/standard/random.json",
                        "disposition": "intentional_unknown",
                        "reason_code": reason_code,
                        "owner_accepted_on": "2026-08-12",
                        "evidence": "docs/audits/example.md#random",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


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
    unknown_records = [
        _unknown_record(format_name, "current", "101"),
        _unknown_record(format_name, "old", "99"),
    ]
    if format_name == "standard":
        unknown_records.append(_unknown_record(format_name, "random", "98"))
    _write_json(
        reports / "index.json",
        {
            "scope": "all_available_events",
            "summary": {
                "unknown": len(unknown_records),
                "conflicts": 0,
                "invalid_decks": 0,
                "strict_validation": "pass",
            },
        },
    )
    _write_json(
        reports / "unknown_decks.json",
        {"records": unknown_records},
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
                    "classifier_digest": digest,
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


def test_readiness_is_schema_valid_and_includes_every_unresolved_unknown(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)

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
        classification = item["classification"]
        assert classification["unresolved_unknown_count"] == 2
        assert {record["event_id"] for record in classification["unresolved_unknown_records"]} == {
            "99",
            "101",
        }
        assert classification["unresolved_unknown_records"][0]["main_deck"]
        assert item["pickup"]["total_candidate_count"] == 3
        assert item["visual_metadata"]["deck_colors"]["exception_count"] is None
    standard = document["formats"][0]["classification"]
    assert standard["accepted_intentional_unknown_count"] == 1
    assert standard["accepted_intentional_unknown_records"][0]["reason_code"] == "random_card_pile"
    assert document["formats"][1]["classification"]["accepted_intentional_unknown_count"] == 0


def test_readiness_digest_ignores_run_time_but_binds_review_inputs(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)

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
    _write_intentional_unknowns(tmp_path)

    document = _build(tmp_path)

    assert document["status"] == "blocked"
    assert document["workflow"]["next_action"] == "resolve_blocker"
    assert document["formats"][1]["pickup"]["status"] == "unavailable"


def test_stale_pickup_classifier_digest_is_reported_as_a_blocker(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    candidate_path = (
        tmp_path / "stats" / "standard" / "mtgo" / "pickup" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["classifier_digest"] = "c" * 64
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    document = _build(tmp_path)

    pickup = document["formats"][0]["pickup"]
    assert document["status"] == "blocked"
    assert pickup["status"] == "stale_review_required"
    assert pickup["candidate_classifier_digest"] == "c" * 64
    assert pickup["expected_classifier_digest"] == "a" * 64
    assert "classifier_digest" in pickup["reason"]


def test_mismatched_format_week_fails_closed(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
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


def test_only_random_card_piles_may_be_registered_as_intentional_unknown(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path, reason_code="singleton")

    with pytest.raises(ValueError, match="Only Owner-accepted random card piles"):
        _build(tmp_path)
