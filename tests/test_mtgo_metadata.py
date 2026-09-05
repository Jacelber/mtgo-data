import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator

from mtgmeta.mtgo import metadata
from validate_schemas import load_schemas


def test_metadata_scope_binding_schema_preserves_legacy_and_rejects_missing_binding():
    schemas, registry = load_schemas(Path(__file__).resolve().parents[1] / "schemas")
    validator = Draft202012Validator(schemas["mtgo-meta.schema.json"], registry=registry)
    document = {"schema_version": "1.0.0", "format": "standard", "source": "mtgo",
        "rules_updated": "synthetic", "data_updated": "synthetic", "statistics_catalog": "index.json",
        "matchup_catalog": "matchup_index.json", "hierarchy_catalog": "archetype_hierarchy.json",
        "top8_catalog": None, "completeness_catalog": None, "pickup_catalog": None,
        "landing_document": None, "landing_feature_catalog": None, "matchup_source": "Videre",
        "matchup_coverage": {key: 0 for key in ("official_events", "events_with_archives",
            "events_without_archives", "stored_archives", "archives_outside_official_events")}}
    validator.validate(document)
    document["schema_version"] = "1.1.0"
    assert list(validator.iter_errors(document))
    document["publication"] = {"scope_digest": "a" * 64, "week": "2025-W02",
        "artifacts": {"stats/standard/mtgo/index.json": "b" * 64}}
    validator.validate(document)
    document["schema_version"] = "1.2.0"
    assert list(validator.iter_errors(document))


def _context(tmp_path):
    statistics = tmp_path / "stats/standard/mtgo"
    statistics.mkdir(parents=True)
    rules = tmp_path / "my_archetypes/standard.yaml"
    rules.parent.mkdir(parents=True)
    rules.write_text("archetypes: []\n", encoding="utf-8")
    return SimpleNamespace(
        repository_root=tmp_path,
        definition=SimpleNamespace(id="standard", public=True),
        paths={
            "rules": rules,
            "statistics": statistics,
            "matches": tmp_path / "matches",
        },
    )


def test_metadata_does_not_publish_the_frozen_pickup_catalog(monkeypatch, tmp_path):
    from mtgmeta.mtgo import publication
    monkeypatch.setattr(publication, "publication_binding", lambda *args: {
        "scope_digest": "a" * 64, "week": "2025-W02", "artifacts": {}})
    context = _context(tmp_path)
    frozen = context.paths["statistics"] / "pickup/index.json"
    frozen.parent.mkdir(parents=True)
    frozen.write_text('{"weeks": []}\n', encoding="utf-8")
    landing = context.paths["statistics"] / "landing"
    (landing / "features").mkdir(parents=True)
    (landing / "current.json").write_text("{}\n", encoding="utf-8")
    (landing / "features/index.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(metadata, "load_mtgo_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(
        metadata,
        "_matchup_coverage",
        lambda *args, **kwargs: {"official_events": 0},
    )

    destination = metadata.generate_metadata(
        tmp_path,
        "standard",
        data_updated="2026-08-24T00:00:00+00:00",
        rules_updated="2026-08-23T00:00:00+00:00",
    )
    document = json.loads(destination.read_text(encoding="utf-8"))

    assert document["pickup_catalog"] is None
    assert document["landing_document"] == "landing/current.json"
    assert document["landing_feature_catalog"] == "landing/features/index.json"


def test_hierarchy_generation_remains_owned_by_metadata(monkeypatch, tmp_path):
    context = _context(tmp_path)
    rules = object()
    hierarchy = {
        "parents": [{"id": "parent", "expandable": True}],
        "leaves": [{"id": "parent/subtype"}],
    }
    monkeypatch.setattr(metadata, "load_mtgo_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(metadata, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(metadata, "classifier_digest", lambda value: "a" * 64)
    monkeypatch.setattr(
        metadata.matchup,
        "build_matchup_hierarchy",
        lambda value: hierarchy if value is rules else None,
    )

    destination = metadata.generate_hierarchy_catalog(
        tmp_path,
        "standard",
        rules_updated="2026-08-23T00:00:00+00:00",
    )
    document = json.loads(destination.read_text(encoding="utf-8"))

    assert document["classifier_digest"] == "a" * 64
    assert document["summary"] == {
        "parents": 1,
        "leaves": 1,
        "expandable_parents": 1,
    }
    assert document["parents"] == hierarchy["parents"]
    assert document["leaves"] == hierarchy["leaves"]
