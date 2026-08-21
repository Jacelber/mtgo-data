from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import yaml
import pytest

from mtgmeta.mtgo import landing


WEEK = "2026-W33"
DIGEST = "a" * 64
FACT_DIGEST = "b" * 64
POLICY_DIGEST = "e" * 64
VISUAL_DIGEST = "f" * 64
ROOT = Path(__file__).resolve().parents[1]


def _candidate(*, approved: bool = False) -> dict:
    entry = {
        "archetype_id": "example-parent",
        "subtype_id": None,
        "archetype": "Example Parent",
        "event_id": "100",
        "deck_id": "deck-100",
        "deck_fingerprint_sha256": "c" * 64,
        "player": "Example",
        "final_rank": 1,
        "player_count": 32,
        "starttime": "2026-08-10 00:00:00.0",
        "approved": approved,
        "comment_zh": "",
        "comment_en": "",
        "candidate_reasons": [
            {
                "type": "new_archetype",
                "prior_record_count_under_current_classifier": 0,
            }
        ],
        "main_deck": [
            {"name": "Card One", "qty": 4},
            {"name": "Card Two", "qty": 4},
            {"name": "Card Three", "qty": 4},
            {"name": "Card Four", "qty": 4},
        ],
        "side_deck": [],
    }
    if approved:
        entry["landing"] = {
            "category": "new_deck",
            "order": 1,
            "headline_zh": "人工标题",
            "headline_en": "Human headline",
            "positioning_zh": "人工可独立改写。",
            "positioning_en": "Human copy may be independent.",
            "featured_cards": ["Card One", "Card Two", "Card Three", "Card Four"],
        }
    return {
        "week": WEEK,
        "source_event_ids": ["100"],
        "classifier_digest": DIGEST,
        "selection_policy_digest": POLICY_DIGEST,
        "visual_metadata_digest": VISUAL_DIGEST if approved else None,
        "landing_visual_diagnostics": [],
        "machine_fact_digest": FACT_DIGEST if approved else None,
        "existing_changes": [],
        "new_archetypes": [entry],
    }


def test_no_event_document_is_schema_shaped_without_candidates(monkeypatch, tmp_path):
    context = SimpleNamespace(paths={"statistics": tmp_path / "stats"})
    rules = SimpleNamespace(archetypes=())
    monkeypatch.setattr(landing, "load_mtgo_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(landing, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(landing.stats, "load_all_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(landing, "classifier_digest", lambda value: DIGEST)
    monkeypatch.setattr(
        landing.pickup,
        "load_pickup_policy",
        lambda *args, **kwargs: {"schema_version": "1.0"},
    )
    monkeypatch.setattr(
        landing,
        "load_visual_metadata",
        lambda *args, **kwargs: {
            "schema_version": "1.0",
            "formats": {"standard": {"parents": {}, "subtypes": {}}},
        },
    )

    review_status, document = landing.build_document(
        tmp_path,
        "standard",
        today=date(2026, 8, 18),
    )

    assert review_status == "not_applicable"
    assert document["week"] == {
        "id": WEEK,
        "start": "2026-08-10",
        "end": "2026-08-16",
    }
    assert document["state"] == "no_events"
    assert document["source_event_ids"] == []
    assert document["comparison"] == {
        "available": False,
        "unavailable_reason": "no_current_events",
    }
    assert document["environment"]["rows"] == []
    assert document["observations"] == []
    assert document["features"]["items"] == []


def test_cross_field_population_mismatch_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["environment"]["other_classified"]["current"]["count"] += 1

    with pytest.raises(landing.MTGOLandingError, match="decomposition"):
        landing.validate_document(document)


def test_unreviewed_candidate_receives_fact_binding_and_default_landing_fields(
    tmp_path,
):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(_candidate()), encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    updated = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert status == "current"
    assert features == []
    assert updated["machine_fact_digest"] == FACT_DIGEST
    assert updated["new_archetypes"][0]["landing"] == {
        "category": "new_deck",
        "order": None,
        "headline_zh": "",
        "headline_en": "",
        "positioning_zh": "",
        "positioning_en": "",
        "featured_cards": [],
    }


def test_reviewed_feature_is_public_without_internal_approval_or_comments(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(_candidate(approved=True)), encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    assert status == "current"
    assert len(features) == 1
    feature = features[0]
    assert feature["category"] == "new_deck"
    assert feature["headline"]["zh"] == "人工标题"
    assert [card["name"] for card in feature["featured_cards"]] == [
        "Card One",
        "Card Two",
        "Card Three",
        "Card Four",
    ]
    serialized = json.dumps(feature, ensure_ascii=False)
    assert "approved" not in serialized
    assert "comment_zh" not in serialized
    assert "machine_fact_digest" not in serialized


def test_reviewed_candidate_is_preserved_when_machine_facts_change(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    original = yaml.safe_dump(_candidate(approved=True))
    path.write_text(original, encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        "d" * 64,
    )

    assert status == "stale_review_required"
    assert features == []
    assert path.read_text(encoding="utf-8") == original


def test_reviewed_candidate_is_preserved_when_selection_policy_changes(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    original = yaml.safe_dump(_candidate(approved=True))
    path.write_text(original, encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        "0" * 64,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    assert status == "stale_review_required"
    assert features == []
    assert path.read_text(encoding="utf-8") == original


def test_pages_selection_excludes_private_pickup_review_files(tmp_path):
    from build_pages_artifact import publication_paths

    for relative in (
        "stats/standard/mtgo/landing/current.json",
        "stats/standard/mtgo/pickup/2026-W33.json",
        "stats/standard/mtgo/pickup/candidates_2026-W33.yaml",
        "stats/standard/mtgo/pickup/base_reference_2026-W33.yaml",
        "stats/standard/mtgo/pickup/known_archetypes.json",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    config = {
        "site_files": ["index.html"],
        "site_directories": ["stats"],
        "excluded_patterns": [
            "stats/*/mtgo/pickup/base_reference_*.yaml",
            "stats/*/mtgo/pickup/candidates_*.yaml",
            "stats/*/mtgo/pickup/known_archetypes.json",
        ],
    }

    selected = publication_paths(tmp_path, config)

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W33.json" in selected
    assert not any("candidates_" in path for path in selected)
    assert not any("base_reference_" in path for path in selected)
    assert not any(path.endswith("known_archetypes.json") for path in selected)


def test_production_candidate_admits_only_latest_landing_document():
    from validate_production_candidate import _allowed_new_path

    formats = ("standard", "modern")
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/current.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/2026-W33.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/candidates_2026-W33.yaml", formats, formats
    )


def test_repository_pages_policy_admits_landing_but_excludes_private_pickup():
    from build_pages_artifact import load_config, publication_paths

    config_path = ROOT / "configs" / "pages_publication.json"
    selected = publication_paths(ROOT, load_config(ROOT, config_path))

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/modern/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W27.json" in selected
    assert not any("/pickup/candidates_" in path for path in selected)
    assert not any("/pickup/base_reference_" in path for path in selected)
    assert not any(path.endswith("/pickup/known_archetypes.json") for path in selected)


def test_landing_cli_requires_the_explicit_format_capability(monkeypatch, tmp_path):
    from mtgmeta.mtgo import __main__ as mtgo_cli

    calls = []

    def run(args, root, registry):
        calls.append((args.format_id, root, registry))
        return 0

    monkeypatch.setitem(mtgo_cli.RUNNERS, "build-landing", run)

    result = mtgo_cli.main(
        [
            "--root",
            str(tmp_path),
            "--registry",
            str(ROOT / "configs" / "formats.yaml"),
            "--format",
            "modern",
            "build-landing",
        ]
    )

    assert result == 0
    assert calls == [
        (
            "modern",
            tmp_path.resolve(),
            (ROOT / "configs" / "formats.yaml").resolve(),
        )
    ]


def test_existing_frontend_ignores_landing_until_its_view_is_implemented():
    source = (ROOT / "assets" / "js" / "phase8" / "app-core.js").read_text(
        encoding="utf-8"
    )

    assert "item.available && PRODUCT_ORDER.includes(item.id)" in source
    product_order = source.split("const PRODUCT_ORDER = [", 1)[1].split("];", 1)[0]
    assert '"mtgo-landing"' not in product_order
