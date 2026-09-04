import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tools.generate_weekly_maintenance_readiness import (
    _completion_state,
    _top8_review_digest,
    build_readiness,
)


ROOT = Path(__file__).resolve().parents[1]


def test_independent_private_review_and_public_weeks(tmp_path, monkeypatch):
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta.mtgo import publication, classification
    from mtgmeta import weekly_review
    from tools import generate_weekly_maintenance_readiness as readiness

    monkeypatch.setattr(readiness, "_intentional_unknowns", lambda root: {"standard": {}, "modern": {}})
    monkeypatch.setattr(publication, "resolve_scope", lambda root, fmt: SimpleNamespace(
        week=date(2025, 1, 6) if fmt == "standard" else date(2024, 12, 30),
        pending_event_ids=frozenset({"200"}), event_ids=frozenset({"100"})))
    monkeypatch.setattr(publication, "retained_events", lambda root, fmt: [("synthetic.json", {
        "event_id": "200", "starttime": "2025-01-13" if fmt == "standard" else "2025-01-20"})])
    monkeypatch.setattr(weekly_review, "build_mtgo_weekly_review", lambda root, fmt, week: {
        "event_ids": ["200"], "format": fmt, "week": week, "records": []})
    monkeypatch.setattr(classification, "audit_mtgo_classification", lambda root, fmt: SimpleNamespace(
        reports={"unknown_decks": {"records": []}, "index": {"summary": {"strict_validation": "pass"}}}))
    for fmt in ("standard", "modern"):
        _write_json(tmp_path / "stats" / fmt / "mtgo/landing/current.json", {"week": {"id": "2025-W01"}})
    registry = {"data_admissions": {"formats": {
        fmt: {"weekly_acceptances": []} for fmt in ("standard", "modern")}}}
    document = readiness._independent_readiness(tmp_path, registry,
        publication_sha="a" * 40, production_run_id="1", production_run_attempt="1",
        source_sha="b" * 40, generated_at="2025-02-03T00:00:00Z")
    assert document["schema_version"] == "1.7.0"
    assert [(row["review_week"], row["public_week"]) for row in document["formats"]] == [
        ("2025-W03", "2025-W02"), ("2025-W04", "2025-W01")]
    assert all(row["completion"]["state"] == "unrecorded" for row in document["formats"])
    assert all(row["data_admission"] == "not_accepted" for row in document["formats"])
    schema = json.loads((ROOT / "schemas/weekly-maintenance-readiness.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(document)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_data_publication_landing_blocker_and_late_delta_are_independent(tmp_path, monkeypatch):
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta.mtgo import publication, classification
    from mtgmeta import weekly_review
    from tools import generate_weekly_maintenance_readiness as readiness
    monkeypatch.setattr(readiness, "_intentional_unknowns", lambda root: {"standard": {}, "modern": {}})
    monkeypatch.setattr(readiness, "_completion_state", lambda *args, **kwargs: {
        "state": "unrecorded", "completed_on": None, "evidence": None, "mismatches": []})
    monkeypatch.setattr(publication, "resolve_scope", lambda root, fmt: SimpleNamespace(
        week=date(2025, 1, 13) if fmt == "standard" else date(2025, 1, 6),
        pending_event_ids=set() if fmt == "standard" else {"200"},
        event_ids={"100", "200"} if fmt == "standard" else {"100"}))
    monkeypatch.setattr(publication, "retained_events", lambda *args: [("synthetic.json", {
        "event_id": "200", "starttime": "2025-01-13"})])
    monkeypatch.setattr(publication, "inspect_publication", lambda *args: [])
    review = {"event_ids": ["200"], "classification_review_digest": "a" * 64}
    def build(root, fmt, week):
        if fmt == "modern":
            raise ValueError("synthetic missing approved bilingual name")
        return review
    monkeypatch.setattr(weekly_review, "build_mtgo_weekly_review", build)
    monkeypatch.setattr(classification, "audit_mtgo_classification", lambda *args: SimpleNamespace(
        reports={"unknown_decks": {"records": []}, "index": {"summary": {"strict_validation": "pass"}}}))
    for fmt in ("standard", "modern"):
        _write_json(tmp_path / "stats" / fmt / "mtgo/landing/current.json", {"week": {"id": "2025-W02"}})
    row = {"week": "2025-W03", "event_ids": ["200"], "classification_review_digest": "a" * 64}
    registry = {"data_admissions": {"formats": {"standard": {"weekly_acceptances": [row]},
                                                  "modern": {"weekly_acceptances": []}}}}
    def result():
        return readiness._independent_readiness(tmp_path, registry, publication_sha="a" * 40,
            production_run_id="1", production_run_attempt="1", source_sha="b" * 40,
            generated_at="2025-02-03T00:00:00Z")["formats"]
    standard, modern = result()
    assert standard["data_admission"] == "published"
    assert standard["status"] == "continue_landing_review"
    assert standard["completion"]["state"] == "unrecorded"
    assert modern["status"] == "blocked_owner_review"
    review["event_ids"] = ["200", "201"]
    standard, modern = result()
    assert standard["data_admission"] == "review_delta_required"
    assert standard["status"] == "awaiting_owner_review"
    assert row["event_ids"] == ["200"]


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
    statistics = root / "stats" / format_name / "mtgo"
    _write_json(
        statistics / "index.json",
        {
            "classifier_digest": digest,
            "latest_complete_week": "2026-08-10",
            "ranges": [{"file": "range_1w.json", "decks_file": "decks_1w.json"}],
        },
    )
    _write_json(statistics / "range_1w.json", {"classifier_digest": digest})
    _write_json(statistics / "decks_1w.json", {"classifier_digest": digest})
    _write_json(
        statistics / "matchup_index.json",
        {
            "classifier_digest": digest,
            "latest_complete_week": "2026-08-10",
            "ranges": [{"file": "matchup_1w.json"}],
        },
    )
    _write_json(statistics / "matchup_1w.json", {"classifier_digest": digest})
    _write_json(
        statistics / "archetype_hierarchy.json",
        {"classifier_digest": digest},
    )
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
            "format": format_name,
            "week": {"start": "2026-08-10", "end": "2026-08-16"},
            "events": [
                {
                    "event_id": "100",
                    "name": "First event",
                    "display_name": "First event",
                    "date": "2026-08-15",
                    "player_count": 64,
                    "placements": [
                        {
                            "rank": 1,
                            "deck_status": "available",
                            "identity": {
                                "identity_id": "deck-a",
                                "parent_id": "deck-a",
                                "subtype_id": None,
                            },
                            "exact_deck": {
                                "player": "Player A",
                                "main_deck": [],
                                "sideboard": [],
                            },
                            "comparison": {"non_review_fact": 1},
                        }
                    ],
                },
                {
                    "event_id": "101",
                    "name": "Second event",
                    "display_name": "Second event",
                    "date": "2026-08-16",
                    "player_count": 80,
                    "placements": [],
                },
            ],
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
        landing_screening = root / "stats" / format_name / "mtgo" / "landing" / "review"
        landing_screening.mkdir(parents=True, exist_ok=True)
        (landing_screening / "candidates_2026-W33.yaml").write_text(
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
                    "selection_policy_digest": "c" * 64,
                    "existing_changes": [{"candidate": 1}],
                    "new_archetypes": [{"candidate": 2}, {"candidate": 3}],
                }
            ),
            encoding="utf-8",
        )


def _landing_subject(root: Path, format_name: str, week: str) -> dict:
    del root
    classifier_digest = "a" * 64 if format_name == "standard" else "b" * 64
    machine_fact_digest = "d" * 64 if format_name == "standard" else "e" * 64
    link_catalog_digest = "f" * 64 if format_name == "standard" else "0" * 64
    return {
        "format": format_name,
        "week": {
            "id": week,
            "start": "2026-08-10",
            "end": "2026-08-16",
        },
        "source_event_ids": ["100", "101"],
        "classifier_digest": classifier_digest,
        "selection_policy_digest": "c" * 64,
        "machine_fact_digest": machine_fact_digest,
        "link_catalog_digest": link_catalog_digest,
    }


def _write_completion(root: Path) -> None:
    landing_digests = {
        "standard": "3" * 64,
        "modern": "4" * 64,
    }
    formats = {}
    for format_name in ("standard", "modern"):
        _write_json(
            root
            / "stats"
            / format_name
            / "mtgo"
            / "landing"
            / "features"
            / "2026-W33.json",
            {"content_digest": landing_digests[format_name]},
        )
        formats[format_name] = {
            "top8_review_digest": _top8_review_digest(
                root, format_name, "2026-W33"
            ),
            "landing_content_digest": landing_digests[format_name],
        }
    path = root / "configs" / "mtgo_weekly_review_completions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "records": [
                    {
                        "week": "2026-W33",
                        "completed_on": "2026-08-18",
                        "evidence": "https://example.test/issues/1",
                        "formats": formats,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _build(
    root: Path,
    generated_at: str = "2026-08-19T09:00:00Z",
    *,
    landing_subject_builder=_landing_subject,
    classifier_digests: dict[str, str] | None = None,
) -> dict:
    expected_digests = classifier_digests or {
        "standard": "a" * 64,
        "modern": "b" * 64,
    }
    return build_readiness(
        root,
        publication_sha="1" * 40,
        production_run_id="123",
        production_run_attempt="1",
        source_sha="2" * 40,
        generated_at=generated_at,
        landing_subject_builder=landing_subject_builder,
        classifier_digest_builder=lambda _root, format_name: expected_digests[
            format_name
        ],
    )


def test_readiness_separates_review_week_unknowns_from_retained_queue(tmp_path):
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
    assert document["completion"] == {
        "state": "unrecorded",
        "completed_on": None,
        "evidence": None,
        "mismatches": [],
    }
    assert document["workflow"]["codex_automation_required"] is False
    assert document["landing"] == {
        "status": "ready_for_human_review",
        "optional_draft_status": "not_requested",
        "bindings": [
            {
                "format": "standard",
                "status": "available",
                "source_event_ids": ["100", "101"],
                "classifier_digest": "a" * 64,
                "selection_policy_digest": "c" * 64,
                "machine_fact_digest": "d" * 64,
                "link_catalog_digest": "f" * 64,
                "reason": None,
            },
            {
                "format": "modern",
                "status": "available",
                "source_event_ids": ["100", "101"],
                "classifier_digest": "b" * 64,
                "selection_policy_digest": "c" * 64,
                "machine_fact_digest": "e" * 64,
                "link_catalog_digest": "0" * 64,
                "reason": None,
            },
        ],
        "reason": None,
    }
    for item in document["formats"]:
        classification = item["classification"]
        assert classification["scope"] == "review_week_source_events"
        assert classification["validation_scope"] == "all_available_events"
        assert classification["unresolved_unknown_count"] == 1
        assert [
            record["event_id"] for record in classification["unresolved_unknown_records"]
        ] == ["101"]
        assert classification["unresolved_unknown_records"][0]["main_deck"]
        queue = item["retained_corpus_unknown_queue"]
        assert queue["scope"] == "all_available_events"
        assert queue["unresolved_unknown_count"] == 2
        assert {record["event_id"] for record in queue["unresolved_unknown_records"]} == {
            "99",
            "101",
        }
        assert queue["outside_review_week_unresolved_unknown_count"] == 1
        assert [
            record["event_id"]
            for record in queue["outside_review_week_unresolved_unknown_records"]
        ] == ["99"]
        assert item["landing_screening"]["total_candidate_count"] == 3
        assert item["visual_metadata"]["deck_colors"]["exception_count"] is None
        binding = item["public_classifier_binding"]
        assert binding["status"] == "current"
        assert binding["classifier_digest"] == item["classifier_digest"]
        assert {product["family"] for product in binding["products"]} == {
            "top8_index",
            "top8_week",
            "statistics_index",
            "statistics_range",
            "representative_decks",
            "matchup_index",
            "matchup_range",
            "archetype_hierarchy",
        }
    standard = document["formats"][0]
    assert standard["classification"]["accepted_intentional_unknown_count"] == 0
    assert standard["retained_corpus_unknown_queue"]["accepted_intentional_unknown_count"] == 1
    assert (
        standard["retained_corpus_unknown_queue"]["accepted_intentional_unknown_records"][0][
            "reason_code"
        ]
        == "random_card_pile"
    )
    assert (
        document["formats"][1]["retained_corpus_unknown_queue"][
            "accepted_intentional_unknown_count"
        ]
        == 0
    )


def test_readiness_digest_ignores_run_time_but_binds_review_inputs(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)

    first = _build(tmp_path, "2026-08-19T09:00:00Z")
    second = _build(tmp_path, "2026-08-20T09:00:00Z")
    assert first["readiness_digest"] == second["readiness_digest"]

    candidate_path = (
        tmp_path / "stats" / "modern" / "mtgo" / "landing" / "review" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["new_archetypes"].append({"candidate": 4})
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")
    changed = _build(tmp_path, "2026-08-20T09:00:00Z")
    assert changed["readiness_digest"] != first["readiness_digest"]

    def changed_machine_facts(root: Path, format_name: str, week: str) -> dict:
        subject = _landing_subject(root, format_name, week)
        if format_name == "modern":
            subject["machine_fact_digest"] = "9" * 64
        return subject

    fact_changed = _build(
        tmp_path,
        "2026-08-20T09:00:00Z",
        landing_subject_builder=changed_machine_facts,
    )
    assert fact_changed["readiness_digest"] != changed["readiness_digest"]


def test_completed_week_survives_non_material_classifier_digest_refresh(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    _write_completion(tmp_path)

    refreshed_digests = {"standard": "5" * 64, "modern": "6" * 64}
    for format_name, digest in refreshed_digests.items():
        statistics_dir = tmp_path / "stats" / format_name / "mtgo"
        for path in (
            statistics_dir / "index.json",
            statistics_dir / "range_1w.json",
            statistics_dir / "decks_1w.json",
            statistics_dir / "matchup_index.json",
            statistics_dir / "matchup_1w.json",
            statistics_dir / "archetype_hierarchy.json",
        ):
            document = json.loads(path.read_text(encoding="utf-8"))
            document["classifier_digest"] = digest
            _write_json(path, document)
        top8_dir = tmp_path / "stats" / format_name / "mtgo" / "top8"
        index = json.loads((top8_dir / "index.json").read_text(encoding="utf-8"))
        index["classifier_digest"] = digest
        _write_json(top8_dir / "index.json", index)
        week = json.loads((top8_dir / "2026-W33.json").read_text(encoding="utf-8"))
        week["classifier_digest"] = digest
        _write_json(top8_dir / "2026-W33.json", week)
        candidate_path = (
            tmp_path
            / "stats"
            / format_name
            / "mtgo"
            / "landing"
            / "review"
            / "candidates_2026-W33.yaml"
        )
        candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
        candidate["classifier_digest"] = digest
        candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    def refreshed_subject(root: Path, format_name: str, week: str) -> dict:
        subject = _landing_subject(root, format_name, week)
        subject["classifier_digest"] = refreshed_digests[format_name]
        return subject

    document = _build(
        tmp_path,
        landing_subject_builder=refreshed_subject,
        classifier_digests=refreshed_digests,
    )

    assert document["status"] == "completed"
    assert document["completion"]["state"] == "verified"
    assert document["workflow"]["next_action"] == "none"


def test_completed_week_requires_revalidation_after_top8_subject_change(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    _write_completion(tmp_path)

    path = tmp_path / "stats" / "modern" / "mtgo" / "top8" / "2026-W33.json"
    week = json.loads(path.read_text(encoding="utf-8"))
    week["events"][0]["placements"][0]["identity"]["parent_id"] = "deck-b"
    _write_json(path, week)

    document = _build(tmp_path)

    assert document["status"] == "revalidation_required"
    assert document["completion"]["state"] == "stale"
    assert document["completion"]["mismatches"] == ["modern Top 8 review subject"]
    assert document["workflow"]["next_action"] == "owner_revalidation_required"


def test_v2_completion_binds_full_review_events_classifier_and_digest(
    tmp_path, monkeypatch
):
    landing_digests = {"standard": "3" * 64, "modern": "4" * 64}
    review_digests = {"standard": "5" * 64, "modern": "6" * 64}
    classifier_digests = {"standard": "a" * 64, "modern": "b" * 64}
    event_ids = {"standard": ["100"], "modern": ["200", "201"]}
    for format_name in ("standard", "modern"):
        _write_json(
            tmp_path
            / "stats"
            / format_name
            / "mtgo"
            / "landing"
            / "features"
            / "2026-W35.json",
            {"content_digest": landing_digests[format_name]},
        )
    completion_path = tmp_path / "configs/mtgo_weekly_review_completions.yaml"
    completion_path.parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.1.0",
                "records": [
                    {
                        "week": "2026-W35",
                        "review_scope": "full_official_classification_v2",
                        "completed_on": "2026-09-03",
                        "evidence": "https://example.test/review",
                        "formats": {
                            format_name: {
                                "accepted_event_ids": event_ids[format_name],
                                "accepted_classifier_subject": classifier_digests[
                                    format_name
                                ],
                                "classification_review_digest": review_digests[
                                    format_name
                                ],
                                "landing_content_digest": landing_digests[format_name],
                            }
                            for format_name in ("standard", "modern")
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def current_review(_root, format_name, week_id):
        assert week_id == "2026-W35"
        return {
            "event_ids": event_ids[format_name],
            "classifier": {"subject_digest": classifier_digests[format_name]},
            "classification_review_digest": review_digests[format_name],
        }

    monkeypatch.setattr(
        "mtgmeta.weekly_review.build_mtgo_weekly_review", current_review
    )
    assert _completion_state(tmp_path, "2026-W35")["state"] == "verified"

    review_digests["modern"] = "7" * 64
    result = _completion_state(tmp_path, "2026-W35")
    assert result["state"] == "stale"
    assert result["mismatches"] == ["modern full classification review subject"]


def test_missing_landing_screening_candidate_is_reported_as_a_blocker(tmp_path):
    _write_format(tmp_path, "standard")
    _write_format(tmp_path, "modern", candidate=False)
    _write_intentional_unknowns(tmp_path)

    document = _build(tmp_path)

    assert document["status"] == "blocked"
    assert document["workflow"]["next_action"] == "resolve_blocker"
    assert document["formats"][1]["landing_screening"]["status"] == "unavailable"
    assert document["landing"]["status"] == "blocked"
    assert "modern Landing screening" in document["landing"]["reason"]


def test_stale_landing_screening_classifier_digest_is_reported_as_a_blocker(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    candidate_path = (
        tmp_path / "stats" / "standard" / "mtgo" / "landing" / "review" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["classifier_digest"] = "c" * 64
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    document = _build(tmp_path)

    landing_screening = document["formats"][0]["landing_screening"]
    assert document["status"] == "blocked"
    assert landing_screening["status"] == "stale_review_required"
    assert landing_screening["candidate_classifier_digest"] == "c" * 64
    assert landing_screening["expected_classifier_digest"] == "a" * 64
    assert "classifier_digest" in landing_screening["reason"]


def test_stale_landing_screening_policy_digest_is_reported_as_a_blocker(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    candidate_path = (
        tmp_path / "stats" / "modern" / "mtgo" / "landing" / "review" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["selection_policy_digest"] = "8" * 64
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    document = _build(tmp_path)

    landing_screening = document["formats"][1]["landing_screening"]
    assert document["status"] == "blocked"
    assert landing_screening["status"] == "stale_review_required"
    assert "selection_policy_digest" in landing_screening["reason"]


def test_landing_machine_fact_binding_mismatch_fails_closed(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)

    def stale_subject(root: Path, format_name: str, week: str) -> dict:
        subject = _landing_subject(root, format_name, week)
        if format_name == "standard":
            subject["source_event_ids"] = ["100"]
        return subject

    document = _build(tmp_path, landing_subject_builder=stale_subject)

    binding = document["landing"]["bindings"][0]
    assert document["status"] == "blocked"
    assert binding["status"] == "stale"
    assert "source_event_ids" in binding["reason"]


def test_mismatched_format_week_fails_closed(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    modern_index = tmp_path / "stats" / "modern" / "mtgo" / "top8" / "index.json"
    value = json.loads(modern_index.read_text(encoding="utf-8"))
    value["weeks"][0]["seal_on"] = "2026-08-25"
    _write_json(modern_index, value)
    candidate_path = (
        tmp_path / "stats" / "modern" / "mtgo" / "landing" / "review" / "candidates_2026-W33.yaml"
    )
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["seal_on"] = "2026-08-25"
    candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    with pytest.raises(ValueError, match="same weekly review window"):
        _build(tmp_path)


def test_stale_public_classifier_binding_fails_closed(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path)
    _write_json(
        tmp_path / "stats" / "standard" / "mtgo" / "range_1w.json",
        {"classifier_digest": "c" * 64},
    )

    with pytest.raises(ValueError, match="public classifier binding mismatch"):
        _build(tmp_path)


def test_only_random_card_piles_may_be_registered_as_intentional_unknown(tmp_path):
    for format_name in ("standard", "modern"):
        _write_format(tmp_path, format_name)
    _write_intentional_unknowns(tmp_path, reason_code="singleton")

    with pytest.raises(ValueError, match="Only Owner-accepted random card piles"):
        _build(tmp_path)
