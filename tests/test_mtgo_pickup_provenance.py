from datetime import date
from types import SimpleNamespace

import pytest
import yaml

from mtgmeta.mtgo import pickup


WEEK_START = date(2026, 8, 10)
EVENTS = [(WEEK_START, {"event_id": "100"})]


POLICY = {
    "schema_version": "1.0",
    "thresholds": {
        "share_increase_pp": 5,
        "return_share": 0.03,
        "build_shift": 20,
        "build_reference_minimum": 8,
        "new_card_review_weeks": 2,
    },
    "identity_continuity": {"standard": {}, "modern": {}},
    "release_sets": [],
}


def _candidate_document(*, approved: bool = False) -> dict:
    return {
        "week": "2026-W33",
        "start": "2026-08-10",
        "end": "2026-08-16",
        "existing_changes": [
            {
                "archetype": "Current Identity",
                "approved": approved,
                "comment_zh": "",
                "comment_en": "",
            }
        ],
        "new_archetypes": [],
    }


def _prepare_candidate_generation(monkeypatch, tmp_path, *, digest: str) -> None:
    rules = object()
    monkeypatch.setattr(
        pickup,
        "_pickup_directories",
        lambda *args, **kwargs: (tmp_path, tmp_path),
    )
    monkeypatch.setattr(pickup, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(pickup, "load_pickup_policy", lambda *args, **kwargs: POLICY)
    monkeypatch.setattr(pickup.stats, "load_all_events", lambda *args, **kwargs: EVENTS)
    monkeypatch.setattr(
        pickup.stats,
        "latest_complete_week",
        lambda *args, **kwargs: WEEK_START,
    )
    monkeypatch.setattr(pickup, "load_known", lambda *args, **kwargs: {"known"})
    monkeypatch.setattr(pickup, "classifier_digest", lambda value: digest)
    monkeypatch.setattr(
        pickup,
        "_candidate_documents",
        lambda *args, **kwargs: (_candidate_document(), {"week": "2026-W33"}, 1, 1),
    )


def test_week_records_add_stable_source_identity(monkeypatch):
    record = {
        "main_deck": [{"name": "Example Card", "qty": 4}],
        "side_deck": [{"name": "Sideboard Card", "qty": 2}],
    }
    monkeypatch.setattr(
        pickup.stats,
        "process_event",
        lambda *args: {"records": [record]},
    )

    first = pickup.week_records(EVENTS, object(), WEEK_START)[0]
    second = pickup.week_records(EVENTS, object(), WEEK_START)[0]

    assert first["event_id"] == "100"
    assert len(first["deck_id"]) == 20
    assert first["deck_id"] == second["deck_id"]


def test_standard_candidate_rows_include_exact_source_and_classifier_identity(
    monkeypatch,
):
    record = {
        "event_id": "100",
        "deck_id": "deck-100",
        "archetype": "Current Identity",
        "archetype_id": "current-identity",
        "subtype": None,
        "subtype_id": None,
        "player": "Example",
        "final_rank": 1,
        "swiss_score": 15,
        "player_count": 32,
        "starttime": "2026-08-10 00:00:00.0",
        "is_top8": True,
        "is_high_score": True,
        "main_deck": [{"name": "Example Card", "qty": 4}],
        "side_deck": [{"name": "Sideboard Card", "qty": 2}],
    }
    monkeypatch.setattr(
        pickup.stats,
        "build_base_pack",
        lambda *args, **kwargs: ({}, 0.0),
    )
    monkeypatch.setattr(
        pickup.stats,
        "build_subtype_base_pack",
        lambda *args, **kwargs: ({}, 0.0),
    )
    monkeypatch.setattr(pickup, "week_records", lambda *args, **kwargs: [record])
    monkeypatch.setattr(
        pickup,
        "_record_identity",
        lambda *args: {
            "identity_id": "current-identity",
            "archetype_id": "current-identity",
            "subtype_id": None,
            "subtype": None,
        },
    )

    candidates, _base, _top8_count, _deduplicated_count = pickup._candidate_documents(
        [],
        SimpleNamespace(archetypes=()),
        WEEK_START,
        set(),
        POLICY,
        "standard",
    )

    entry = candidates["new_archetypes"][0]
    assert entry["event_id"] == "100"
    assert entry["deck_id"] == "deck-100"
    assert entry["identity_id"] == "current-identity"
    assert len(entry["deck_fingerprint_sha256"]) == 64


def test_unreviewed_candidate_regenerates_when_classifier_digest_changes(
    monkeypatch, tmp_path
):
    _prepare_candidate_generation(monkeypatch, tmp_path, digest="b" * 64)
    candidate_path = tmp_path / "candidates_2026-W33.yaml"
    stale = _candidate_document()
    stale.update({"source_event_ids": ["100"], "classifier_digest": "a" * 64})
    candidate_path.write_text(yaml.safe_dump(stale), encoding="utf-8")

    result = pickup.generate_candidates(
        tmp_path,
        "standard",
        today=date(2026, 8, 18),
        preserve_existing=True,
    )

    refreshed = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    assert result is not None
    assert result["skipped_existing"] is False
    assert result["review_required"] is False
    assert refreshed["classifier_digest"] == "b" * 64


def test_unreviewed_candidate_regenerates_when_selection_policy_changes(
    monkeypatch, tmp_path
):
    _prepare_candidate_generation(monkeypatch, tmp_path, digest="a" * 64)
    candidate_path = tmp_path / "candidates_2026-W33.yaml"
    stale = _candidate_document()
    stale.update(
        {
            "source_event_ids": ["100"],
            "classifier_digest": "a" * 64,
            "selection_policy_digest": "f" * 64,
        }
    )
    candidate_path.write_text(yaml.safe_dump(stale), encoding="utf-8")

    result = pickup.generate_candidates(
        tmp_path,
        "standard",
        today=date(2026, 8, 18),
        preserve_existing=True,
    )

    refreshed = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    assert result is not None
    assert result["skipped_existing"] is False
    assert refreshed["selection_policy_digest"] == pickup.document_digest(POLICY)


def test_reviewed_candidate_is_preserved_but_requires_review_when_classifier_changes(
    monkeypatch, tmp_path
):
    _prepare_candidate_generation(monkeypatch, tmp_path, digest="b" * 64)
    candidate_path = tmp_path / "candidates_2026-W33.yaml"
    stale = _candidate_document(approved=True)
    stale.update({"source_event_ids": ["100"], "classifier_digest": "a" * 64})
    candidate_path.write_text(yaml.safe_dump(stale), encoding="utf-8")

    result = pickup.generate_candidates(
        tmp_path,
        "standard",
        today=date(2026, 8, 18),
        preserve_existing=True,
    )

    preserved = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    assert result is not None
    assert result["skipped_existing"] is True
    assert result["review_required"] is True
    assert preserved["classifier_digest"] == "a" * 64
    assert preserved["existing_changes"][0]["approved"] is True


def test_publish_rejects_candidate_from_an_old_classifier(monkeypatch, tmp_path):
    rules = object()
    monkeypatch.setattr(
        pickup,
        "_pickup_directories",
        lambda *args, **kwargs: (tmp_path, tmp_path / "published"),
    )
    monkeypatch.setattr(pickup, "load_mtgo_context", lambda *args, **kwargs: object())
    monkeypatch.setattr(pickup, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(pickup.stats, "load_all_events", lambda *args, **kwargs: EVENTS)
    monkeypatch.setattr(
        pickup.stats,
        "latest_complete_week",
        lambda *args, **kwargs: WEEK_START,
    )
    monkeypatch.setattr(pickup, "classifier_digest", lambda value: "b" * 64)
    stale = _candidate_document(approved=True)
    stale.update({"source_event_ids": ["100"], "classifier_digest": "a" * 64})
    (tmp_path / "candidates_2026-W33.yaml").write_text(
        yaml.safe_dump(stale),
        encoding="utf-8",
    )

    with pytest.raises(pickup.MTGOPickupError, match="classifier changed"):
        pickup.publish(
            tmp_path,
            "standard",
            today=date(2026, 8, 18),
            candidate_directory=tmp_path,
        )
