from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from mtgmeta.weekly_review import build_v2_completion_record
from mtgmeta.mtgo.review_scope import MTGOReviewScopeError, parse_review_scopes
from validate_schemas import validate_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _registry(root: Path) -> Path:
    formats = []
    for format_id, public in (("standard", True), ("modern", True), ("pauper", False)):
        formats.append({
            "id": format_id,
            "display_name": format_id.title(),
            "state": "executable",
            "public": public,
            "mtgo": {
                "enabled": True,
                "event_collection_enabled": False,
                "capabilities": ["classification", "landing_generation"],
                "paths": {
                    "events": f"data/{format_id}",
                    "matches": f"data/{format_id}/mtgo/matches",
                    "rules": f"my_archetypes/{format_id}.yaml",
                    "statistics": f"stats/{format_id}/mtgo",
                    "reports": f"reports/{format_id}/mtgo",
                },
            },
        })
    path = root / "configs/formats.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema_version": "1.3.0", "formats": formats}), encoding="utf-8")
    return path


def test_private_review_scope_preserves_order_and_independent_weeks(tmp_path):
    registry = _registry(tmp_path)

    scopes = parse_review_scopes(
        tmp_path,
        ["pauper=2026-W32"],
        capability="landing_generation",
        registry_path=registry,
        private=True,
        today=date(2026, 9, 5),
    )

    assert [(scope.format_id, scope.week) for scope in scopes] == [("pauper", "2026-W32")]

    public = parse_review_scopes(
        tmp_path,
        ["modern=2026-W31", "standard=2026-W32"],
        capability="landing_generation",
        registry_path=registry,
        private=False,
        today=date(2026, 9, 5),
    )
    assert [(scope.format_id, scope.week) for scope in public] == [
        ("modern", "2026-W31"),
        ("standard", "2026-W32"),
    ]


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ([], "must not be empty"),
        (["pauper=2026-W32", "pauper=2026-W31"], "duplicates format"),
        (["pauper=2026-W54"], "invalid ISO"),
        (["pauper=2026-W36"], "has not ended"),
        (["missing=2026-W32"], "unknown format"),
    ],
)
def test_private_review_scope_rejects_invalid_subjects(tmp_path, values, message):
    registry = _registry(tmp_path)
    with pytest.raises(MTGOReviewScopeError, match=message):
        parse_review_scopes(
            tmp_path,
            values,
            capability="landing_generation",
            registry_path=registry,
            private=True,
            today=date(2026, 9, 5),
        )


def test_public_and_private_boundaries_are_explicit(tmp_path):
    registry = _registry(tmp_path)
    with pytest.raises(MTGOReviewScopeError, match="public: false"):
        parse_review_scopes(
            tmp_path, ["standard=2026-W32"], capability="landing_generation",
            registry_path=registry, private=True, today=date(2026, 9, 5)
        )
    with pytest.raises(MTGOReviewScopeError, match="cannot include private"):
        parse_review_scopes(
            tmp_path, ["pauper=2026-W32"], capability="landing_generation",
            registry_path=registry, private=False, today=date(2026, 9, 5)
        )


def test_single_format_completion_binds_exact_week_and_rejects_duplicates():
    digest = "a" * 64
    review = {
        "format": "pauper",
        "week": "2026-W32",
        "event_ids": ["1"],
        "classifier": {"subject_digest": digest},
        "classification_review_digest": digest,
    }
    record = build_v2_completion_record(
        [review],
        week_id="2026-W32",
        completed_on="2026-09-01",
        evidence="owner acceptance",
        landing_content_digests={"pauper": digest},
        independent_format=True,
    )
    assert list(record["formats"]) == ["pauper"]
    with pytest.raises(ValueError, match="duplicate format"):
        build_v2_completion_record(
            [review, review], week_id="2026-W32", completed_on="2026-09-01",
            evidence="owner acceptance", landing_content_digests={"pauper": digest},
            independent_format=True,
        )
    with pytest.raises(ValueError, match="week does not match"):
        build_v2_completion_record(
            [review], week_id="2026-W31", completed_on="2026-09-01",
            evidence="owner acceptance", landing_content_digests={"pauper": digest},
            independent_format=True,
        )


def test_generic_name_mapping_keeps_registry_and_path_identity(tmp_path):
    registry = _registry(tmp_path)
    assert registry.is_file()
    output = tmp_path / "stats/pauper/archetype_names.json"
    output.parent.mkdir(parents=True)
    digest = "b" * 64
    output.write_text(json.dumps({
        "schema_version": "1.1.0",
        "format": "pauper",
        "provenance": {
            "classifier_identity_digest": digest,
            "name_catalog_digest": digest,
            "projection_subject_digest": digest,
        },
        "names": [{
            "identity_id": "test-deck",
            "parent_id": "test-deck",
            "subtype_id": None,
            "display": {"en": "Test Deck", "zh": "Test Deck ZH"},
        }],
    }), encoding="utf-8")
    checked, failures = validate_manifest(
        tmp_path,
        REPOSITORY_ROOT / "schemas/manifest.json",
        {"stats/pauper/archetype_names.json"},
    )
    assert checked == 1
    assert failures == []

    document = json.loads(output.read_text(encoding="utf-8"))
    document["format"] = "modern"
    output.write_text(json.dumps(document), encoding="utf-8")
    _checked, failures = validate_manifest(
        tmp_path,
        REPOSITORY_ROOT / "schemas/manifest.json",
        {"stats/pauper/archetype_names.json"},
    )
    assert any("registered output path" in failure.message for failure in failures)
