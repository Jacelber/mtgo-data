from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from mtgmeta.mtgo import landing


SYNTHETIC_WEEK = "2099-W02"
SYNTHETIC_TODAY = date.fromisocalendar(2099, 3, 2)
DIGEST = "a" * 64
FACT_DIGEST = "b" * 64
PICKUP_DIGEST = "d" * 64
ROOT = Path(__file__).resolve().parents[1]


def test_classifier_restatement_requires_identical_accepted_material():
    material = {
        field: {"value": field}
        for field in landing.CLASSIFIER_RESTATEMENT_MATERIAL_FIELDS
    }

    assert landing._classifier_restatement_preserves_accepted_material(
        {"classifier_digest", "machine_fact_digest"}, material, dict(material)
    )

    changed = dict(material)
    changed["environment"] = {"value": "changed"}
    assert not landing._classifier_restatement_preserves_accepted_material(
        {"classifier_digest"}, material, changed
    )
    assert not landing._classifier_restatement_preserves_accepted_material(
        {"bilingual_catalog_digest"}, material, material
    )


def test_no_event_document_is_schema_shaped_without_candidates(monkeypatch, tmp_path):
    from mtgmeta.mtgo import publication
    monkeypatch.setattr(publication, "resolve_scope", lambda *args: SimpleNamespace(
        week=date.fromisocalendar(2099, 2, 1)))
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
        today=SYNTHETIC_TODAY,
    )

    assert review_status == "not_applicable"
    assert document["week"] == {
        "id": SYNTHETIC_WEEK,
        "start": date.fromisocalendar(2099, 2, 1).isoformat(),
        "end": date.fromisocalendar(2099, 2, 7).isoformat(),
    }
    assert document["state"] == "no_events"
    assert document["source_event_ids"] == []
    assert document["comparison"] == {
        "available": False,
        "unavailable_reason": "no_current_events",
    }
    assert document["environment"]["rows"] == []
    assert document["schema_version"] == "1.2.0"
    assert document["weekly_summary"] == {"week": SYNTHETIC_WEEK, "items": []}
    assert "observations" not in document
    assert document["features"]["items"] == []
    schema = json.loads(
        (ROOT / "schemas" / "mtgo-landing.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(document)) == []
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
        f"stats/standard/mtgo/landing/features/{SYNTHETIC_WEEK}.json",
        f"stats/standard/mtgo/pickup/{SYNTHETIC_WEEK}.json",
        f"stats/standard/mtgo/pickup/candidates_{SYNTHETIC_WEEK}.yaml",
        f"stats/standard/mtgo/pickup/base_reference_{SYNTHETIC_WEEK}.yaml",
        "stats/standard/mtgo/pickup/known_archetypes.json",
        f"stats/standard/mtgo/landing/review/candidates_{SYNTHETIC_WEEK}.yaml",
        f"stats/standard/mtgo/landing/review/base_reference_{SYNTHETIC_WEEK}.yaml",
        f"stats/standard/mtgo/landing/review/{SYNTHETIC_WEEK}.yaml",
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
    assert f"stats/standard/mtgo/landing/features/{SYNTHETIC_WEEK}.json" in selected
    assert f"stats/standard/mtgo/pickup/{SYNTHETIC_WEEK}.json" in selected
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
        f"stats/standard/mtgo/landing/features/{SYNTHETIC_WEEK}.json", formats, formats
    )
    assert not _allowed_new_path(
        f"stats/standard/mtgo/landing/{SYNTHETIC_WEEK}.json", formats, formats
    )
    assert not _allowed_new_path(
        f"stats/standard/mtgo/landing/candidates_{SYNTHETIC_WEEK}.yaml", formats, formats
    )
    assert _allowed_new_path(
        f"stats/standard/mtgo/landing/review/candidates_{SYNTHETIC_WEEK}.yaml",
        formats,
        formats,
    )
    assert _allowed_new_path(
        f"stats/standard/mtgo/landing/review/base_reference_{SYNTHETIC_WEEK}.yaml",
        formats,
        formats,
    )
    assert not _allowed_new_path(
        f"stats/standard/mtgo/landing/review/{SYNTHETIC_WEEK}.yaml", formats, formats
    )
    assert not _allowed_new_path(
        f"stats/standard/mtgo/landing/features/candidates_{SYNTHETIC_WEEK}.yaml",
        formats,
        formats,
    )


def test_production_candidate_admits_only_public_bilingual_name_contract():
    from validate_production_candidate import _allowed_new_path, _allowed_path

    collection_formats = ("legacy", "standard", "modern")
    product_formats = ("standard", "modern")
    for predicate in (_allowed_path, _allowed_new_path):
        assert predicate(
            "stats/standard/archetype_names.json",
            collection_formats,
            product_formats,
        )
        assert predicate(
            "stats/modern/archetype_names.json",
            collection_formats,
            product_formats,
        )
        for rejected_path in (
            "stats/legacy/archetype_names.json",
            "stats/standard/archetype_name.json",
            "stats/standard/archetype_names.yaml",
            "stats/standard/archetype_names/extra.json",
            "reports/standard/archetype_names.json",
        ):
            assert not predicate(
                rejected_path,
                collection_formats,
                product_formats,
            )
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
            "week": SYNTHETIC_WEEK,
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
