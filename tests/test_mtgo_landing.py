from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from mtgmeta.mtgo import landing


WEEK = "2026-W33"
DIGEST = "a" * 64
FACT_DIGEST = "b" * 64
PICKUP_DIGEST = "d" * 64
ROOT = Path(__file__).resolve().parents[1]


def test_no_event_document_is_schema_shaped_without_candidates(monkeypatch, tmp_path):
    context = SimpleNamespace(paths={"statistics": tmp_path / "stats"})
    rules = SimpleNamespace(archetypes=())
    monkeypatch.setattr(landing, "load_mtgo_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(landing, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(landing.stats, "load_all_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(landing, "classifier_digest", lambda value: DIGEST)
    monkeypatch.setattr(
        landing.screening,
        "load_screening_policy",
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
    assert document["schema_version"] == "1.2.0"
    assert document["weekly_summary"] == {"week": WEEK, "items": []}
    assert "observations" not in document
    assert document["features"]["items"] == []
    schema = json.loads(
        (ROOT / "schemas" / "mtgo-landing.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(document)) == []


def test_current_landing_uses_one_private_review_without_standalone_pickup_reader():
    assert not hasattr(landing, "_load_published_pickup")
    review_status, document = landing.build_document(
        ROOT,
        "standard",
        today=date(2026, 8, 18),
    )

    assert review_status == "current"
    assert len(document["weekly_summary"]["items"]) == 9
    assert len(document["features"]["items"]) == 14
    assert all(item["headline"]["zh"] for item in document["features"]["items"])
    assert all(item["headline"]["en"] for item in document["features"]["items"])


def test_cross_field_population_mismatch_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["environment"]["other_classified"]["current"]["count"] += 1

    with pytest.raises(landing.MTGOLandingError, match="decomposition"):
        landing.validate_document(document)


def test_weekly_summary_duplicate_order_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["schema_version"] = "1.1.0"
    document.pop("observations", None)
    document["weekly_summary"] = {
        "week": document["week"]["id"],
        "items": [
            {"order": 1, "text": {"zh": "甲", "en": ""}, "deck_links": []},
            {"order": 1, "text": {"zh": "乙", "en": ""}, "deck_links": []},
        ],
    }
    document["review_binding"]["pickup_document_digest"] = PICKUP_DIGEST
    document["review_binding"]["summary_fact_digest"] = FACT_DIGEST

    with pytest.raises(landing.MTGOLandingError, match="summary order"):
        landing.validate_document(document)


def test_weekly_summary_link_without_exact_feature_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    linked = document["weekly_summary"]["items"][2]["deck_links"][0]["token"]
    document["features"]["items"] = [
        item
        for item in document["features"]["items"]
        if item["destination_id"] != linked
    ]

    with pytest.raises(landing.MTGOLandingError, match="no exact reviewed feature"):
        landing.validate_document(document)


def test_legacy_1_1_landing_remains_valid_without_feature_destinations():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["schema_version"] = "1.1.0"
    for item in document["features"]["items"]:
        item.pop("destination_id")

    landing.validate_document(document)


def test_deck_link_catalog_keeps_every_top8_deck_independent_of_review_inputs():
    records = []
    for rank in range(1, 9):
        records.append(
            {
                "is_top8": True,
                "event_id": "100",
                "deck_id": f"deck-{rank}",
                "archetype_id": "example-parent",
                "archetype": "Example Parent",
                "player": f"Player {rank}",
                "final_rank": rank,
                "starttime": "2026-08-10 00:00:00.0",
                "main_deck": [{"name": f"Card {rank}", "qty": 60}],
                "side_deck": [],
            }
        )

    catalog = landing._deck_link_catalog(records)

    assert len(catalog) == 8
    assert [item["final_rank"] for item in catalog] == list(range(1, 9))
    assert catalog[0]["link_id"] == "deck:deck-1"


def test_pages_selection_excludes_all_private_landing_review_files(tmp_path):
    from build_pages_artifact import publication_paths

    for relative in (
        "stats/standard/mtgo/landing/current.json",
        "stats/standard/mtgo/landing/features/index.json",
        "stats/standard/mtgo/landing/features/2026-W33.json",
        "stats/standard/mtgo/pickup/2026-W33.json",
        "stats/standard/mtgo/pickup/candidates_2026-W33.yaml",
        "stats/standard/mtgo/pickup/base_reference_2026-W33.yaml",
        "stats/standard/mtgo/pickup/known_archetypes.json",
        "stats/standard/mtgo/landing/review/candidates_2026-W33.yaml",
        "stats/standard/mtgo/landing/review/base_reference_2026-W33.yaml",
        "stats/standard/mtgo/landing/review/2026-W33.yaml",
        "stats/standard/mtgo/landing/review/known_archetypes.json",
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
                "stats/*/mtgo/landing/review/*",
            ],
    }

    selected = publication_paths(tmp_path, config)

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/landing/features/index.json" in selected
    assert "stats/standard/mtgo/landing/features/2026-W33.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W33.json" in selected
    assert not any("candidates_" in path for path in selected)
    assert not any("base_reference_" in path for path in selected)
    assert not any(path.endswith("known_archetypes.json") for path in selected)
    assert not any("/landing/review/" in path for path in selected)


def test_production_candidate_admits_latest_and_bounded_feature_archive_only():
    from validate_production_candidate import _allowed_new_path

    formats = ("standard", "modern")
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/current.json", formats, formats
    )
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/features/index.json", formats, formats
    )
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/features/2026-W33.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/2026-W33.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/candidates_2026-W33.yaml", formats, formats
    )
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/review/candidates_2026-W33.yaml",
        formats,
        formats,
    )
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/review/base_reference_2026-W33.yaml",
        formats,
        formats,
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/review/2026-W33.yaml", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/features/candidates_2026-W33.yaml",
        formats,
        formats,
    )


def test_repository_pages_policy_admits_landing_and_excludes_private_review_state():
    from build_pages_artifact import load_config, publication_paths

    config_path = ROOT / "configs" / "pages_publication.json"
    selected = publication_paths(ROOT, load_config(ROOT, config_path))

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/modern/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/landing/features/2026-W27.json" in selected
    assert "stats/standard/mtgo/landing/features/2026-W33.json" in selected
    assert "stats/modern/mtgo/landing/features/2026-W33.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W27.json" in selected
    assert not any("/pickup/candidates_" in path for path in selected)
    assert not any("/pickup/base_reference_" in path for path in selected)
    assert not any(path.endswith("/pickup/known_archetypes.json") for path in selected)
    assert not any("/landing/review/" in path for path in selected)


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


def test_landing_cli_reports_pending_summary_review_without_count_lookup(
    monkeypatch, tmp_path, capsys
):
    from mtgmeta.mtgo import __main__ as mtgo_cli

    monkeypatch.setattr(
        mtgo_cli.landing,
        "generate",
        lambda *args, **kwargs: {
            "status": "summary_review_required",
            "path": tmp_path / "current.json",
            "week": WEEK,
            "feature_count": 0,
            "summary_count": 0,
        },
    )

    result = mtgo_cli._run_landing(
        SimpleNamespace(format_id="standard"), tmp_path, tmp_path / "formats.yaml"
    )

    assert result == 0
    assert "preserved for explicit summary review" in capsys.readouterr().out


def test_existing_frontend_keeps_landing_in_the_accepted_product_order():
    source = (ROOT / "assets" / "js" / "phase8" / "app-core.js").read_text(
        encoding="utf-8"
    )

    assert "item.available && PRODUCT_ORDER.includes(item.id)" in source
    product_order = source.split("const PRODUCT_ORDER = [", 1)[1].split("];", 1)[0]
    assert '"mtgo-landing"' in product_order
