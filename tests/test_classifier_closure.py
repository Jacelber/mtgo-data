from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier_closure import (
    CURRENT,
    STALE,
    ClassifierClosureError,
    _allowed_refreshed_artifacts,
    _create_stage,
    _inspect_landing,
    _inspect_melee,
    _materialize_with_rollback,
    converge_format,
    discover_live_formats,
    inspect_repository,
)
from mtgmeta.catalog import write_catalog
from mtgmeta.mtgo import landing_editorial


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_allowed_refresh_includes_dependent_publication_metadata() -> None:
    initial = {
        "families": {
            "mtgo_statistics": {"state": STALE},
            "mtgo_publication": {"state": CURRENT},
            "melee": {"state": CURRENT},
        }
    }
    staged = {
        "families": {
            "mtgo_statistics": {"artifacts": ["stats/modern/mtgo/stats.json"]},
            "mtgo_publication": {"artifacts": [
                "stats/modern/mtgo/meta.json",
                "stats/modern/mtgo/completeness/index.json",
            ]},
            "melee": {"artifacts": ["stats/modern/melee/index.json"]},
        }
    }

    assert _allowed_refreshed_artifacts(initial, staged) == {
        "stats/modern/mtgo/stats.json",
        "stats/modern/mtgo/meta.json",
        "stats/modern/mtgo/completeness/index.json",
    }


def test_allowed_refresh_includes_data_generated_for_new_admission() -> None:
    families = {
        "mtgo_statistics": "stats/modern/mtgo/decks_1w.json",
        "mtgo_matchups": "stats/modern/mtgo/matchup_1w.json",
        "mtgo_top8": "stats/modern/mtgo/top8/2026-W39.json",
        "classification_reports": "reports/modern/mtgo/index.json",
        "mtgo_publication": "stats/modern/mtgo/meta.json",
        "melee": "stats/modern/melee/index.json",
    }
    initial = {
        "families": {
            name: {"state": STALE if name == "mtgo_publication" else CURRENT}
            for name in families
        }
    }
    staged = {"families": {name: {"artifacts": [path]} for name, path in families.items()}}

    assert _allowed_refreshed_artifacts(initial, staged) == set(families.values()) - {
        families["melee"]
    }


def test_landing_refresh_declares_pinned_week_files(tmp_path: Path) -> None:
    path = tmp_path / "stats/modern/mtgo/landing/current.json"
    document = {"week": {"id": "2026-W36"}, "classifier": {"digest": "current"},
                "review_binding": {"classifier_digest": "current"}}
    _write_json(path, document)
    original = _inspect_landing(tmp_path, "modern", "current")
    assert original["state"] == CURRENT
    assert {"stats/modern/mtgo/landing/features/index.json",
            "stats/modern/mtgo/landing/features/2026-W36.json"} <= set(original["artifacts"])
    assert "stats/modern/mtgo/landing/features/2026-W35.json" not in original["artifacts"]
    document["data_files"] = {
        name: f"weeks/2026-W36/{name}.json"
        for name in ("range", "environment_decks", "feature_decks", "completeness")
    }
    _write_json(path, document)
    refreshed = _inspect_landing(tmp_path, "modern", "current")
    assert refreshed["state"] == CURRENT
    assert set(refreshed["artifacts"]) == set(original["artifacts"]) | {
        f"stats/modern/mtgo/landing/{relative}"
        for relative in document["data_files"].values()
    }
    assert _inspect_landing(tmp_path, "modern", "new")["state"] == STALE


def test_stage_creation_falls_back_after_preferred_parent_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    root = tmp_path / "managed-parent" / "repository"
    root.mkdir(parents=True)
    (root / "kept.txt").write_text("kept\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    fallback = tmp_path / "system-temp"
    fallback.mkdir()
    original_mkdir = Path.mkdir

    def guarded_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        if path.parent == root.parent and path.name.startswith(
            "classifier-closure-modern-"
        ):
            raise PermissionError("synthetic managed-parent denial")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fallback))
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)

    stage = _create_stage(root, "modern")

    assert stage.parent == fallback
    assert (stage / "kept.txt").read_text(encoding="utf-8") == "kept\n"
    assert not (stage / "node_modules").exists()


@pytest.mark.parametrize("damage", [None, "dependency", "binding", "same_week"])
def test_data_advance_retains_only_bound_older_landing(tmp_path, monkeypatch, damage):
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta.mtgo import publication

    base = tmp_path / "stats/modern/mtgo"
    files = {name: f"weeks/2026-W36/{name}.json" for name in
             ("range", "environment_decks", "feature_decks", "completeness")}
    document = {"week": {"id": "2026-W36"}, "classifier": {"digest": "old"},
                "review_binding": {"classifier_digest": "old"},
                "source_event_ids": ["123"], "data_files": files}
    current = base / "landing/current.json"
    _write_json(current, document)
    paths = [current]
    for relative in [*files.values(), "features/index.json", "features/2026-W36.json"]:
        path = base / "landing" / relative
        _write_json(path, {"retained": True})
        paths.append(path)
    _write_json(base / "meta.json", {"publication": {"artifacts": {
        p.relative_to(tmp_path).as_posix(): _digest(p) for p in paths}}})
    monkeypatch.setattr(publication, "resolve_scope", lambda *args: SimpleNamespace(
        week=date(2026, 8, 31) if damage == "same_week" else date(2026, 9, 7),
        event_ids=frozenset({"123", "456"})))
    if damage == "dependency":
        _write_json(paths[1], {"retained": False})
    elif damage == "binding":
        document["review_binding"]["classifier_digest"] = "different"
        _write_json(current, document)
    result = _inspect_landing(tmp_path, "modern", "new")
    assert result["state"] == (CURRENT if damage is None else STALE)


def test_stage_creation_permission_failures_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile
    from mtgmeta import classifier_closure

    root = tmp_path / "repository"
    root.mkdir()
    fallback = tmp_path / "system-temp"
    fallback.mkdir()
    attempts = 0

    def denied_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise PermissionError("synthetic denial")

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fallback))
    monkeypatch.setattr(Path, "mkdir", denied_mkdir)

    with pytest.raises(ClassifierClosureError, match="cannot create"):
        classifier_closure._create_stage_directory(root, "bounded-")
    assert attempts == 2


def test_public_name_projection_binds_classifier_identity_and_owner_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = tmp_path / "names.yaml"
    rows = [
        {
            "format": "modern",
            "parent_id": "alpha",
            "subtype_id": None,
            "english": "Alpha",
            "chinese": "阿尔法",
            "review_status": "approved",
            "identity_key": "modern|alpha|none",
        }
    ]
    catalog.write_text(
        yaml.safe_dump({"schema_version": "1.0.0", "names": rows}, sort_keys=False),
        encoding="utf-8",
    )
    taxonomy = [
        {
            "format": "modern",
            "parent_id": "alpha",
            "subtype_id": None,
            "english": "Alpha",
            "identity_key": "modern|alpha|none",
        }
    ]
    monkeypatch.setattr(
        landing_editorial,
        "validate_name_catalog",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(landing_editorial, "_taxonomy_rows", lambda *_args: taxonomy)

    original = landing_editorial.build_public_name_contract(
        tmp_path, "modern", catalog_path=catalog
    )
    identity_changed = [
        *taxonomy,
        {
            "format": "modern",
            "parent_id": "beta",
            "subtype_id": None,
            "english": "Beta",
            "identity_key": "modern|beta|none",
        },
    ]
    monkeypatch.setattr(
        landing_editorial, "_taxonomy_rows", lambda *_args: identity_changed
    )
    changed_identity = landing_editorial.build_public_name_contract(
        tmp_path, "modern", catalog_path=catalog
    )
    assert (
        changed_identity["provenance"]["classifier_identity_digest"]
        != original["provenance"]["classifier_identity_digest"]
    )

    monkeypatch.setattr(landing_editorial, "_taxonomy_rows", lambda *_args: taxonomy)
    rows[0]["chinese"] = "阿尔法牌组"
    catalog.write_text(
        yaml.safe_dump({"schema_version": "1.0.0", "names": rows}, sort_keys=False),
        encoding="utf-8",
    )
    changed_name = landing_editorial.build_public_name_contract(
        tmp_path, "modern", catalog_path=catalog
    )
    assert (
        changed_name["provenance"]["name_catalog_digest"]
        != original["provenance"]["name_catalog_digest"]
    )
    assert (
        changed_name["provenance"]["projection_subject_digest"]
        != original["provenance"]["projection_subject_digest"]
    )


def test_melee_closure_follows_public_catalog_and_exact_sha_chain(tmp_path):
    from dataclasses import replace
    from melee_synthetic import source_fixture, registry_file, public_products, RULES

    definition, document, event, snapshot = source_fixture(tmp_path)
    registry_file(tmp_path, [definition])
    desired, catalog = public_products(tmp_path, definition, document, event)
    public = catalog.parent / "events" / definition.id
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == CURRENT
    immutable = {p: p.read_bytes() for p in [event, *snapshot.iterdir()]}
    # Legitimate registry growth does not add an unadmitted event to consumers.
    registry_file(tmp_path, [definition, replace(definition, id="900002", url="https://melee.gg/Tournament/View/900002")])
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == CURRENT
    # A real changed taxonomy and coherent downstream regeneration is accepted.
    desired, catalog = public_products(tmp_path, definition, document, event,
        rule_text=RULES.replace("name: Alpha", "name: Updated Alpha"))
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == CURRENT
    for name, old_version in (("overview", "1.1.0"), ("matchup", "1.0.0")):
        path = public / f"{name}.json"
        original = path.read_bytes()
        value = json.loads(original)
        value["schema_version"] = old_version
        _write_json(path, value)
        result = _inspect_melee(tmp_path, "modern", desired, catalog)
        assert result["state"] == STALE
        assert any(f"{name} contract is stale" in issue for issue in result["issues"])
        path.write_bytes(original)
    assert all(p.read_bytes() == value for p, value in immutable.items())
    # Corruption is INVALID, not a request to regenerate historical inputs.
    raw = snapshot / "deck-1.json"
    raw.write_bytes(raw.read_bytes() + b" ")
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == "INVALID"


@pytest.mark.parametrize("damage", ["classification_event", "classification_participant", "classifier",
    "ledger_hash", "ledger_match", "upstream_path", "public_event", "descriptor_size", "catalog_route", "missing_public",
    "unreadable_classification", "unreadable_public"])
def test_melee_closure_rejects_broken_derived_chains(tmp_path, damage):
    from melee_synthetic import source_fixture, registry_file, public_products
    definition, document, event, _ = source_fixture(tmp_path)
    registry_file(tmp_path, [definition])
    desired, catalog = public_products(tmp_path, definition, document, event)
    base = tmp_path / "data/modern/melee"
    public = catalog.parent / "events" / definition.id
    if damage.startswith("classification") or damage == "classifier":
        path = base / f"classifications/{definition.id}.json"
        value = json.loads(path.read_bytes())
        if damage == "classification_event": value["event_id"] = "900002"
        elif damage == "classification_participant": value["records"].pop()
        else: value["classifier"]["digest"] = "f" * 64
    elif damage.startswith("ledger"):
        path = base / f"opportunities/{definition.id}.json"
        value = json.loads(path.read_bytes())
        if damage == "ledger_hash": value["input"]["classification_sha256"] = "f" * 64
        else: value["opportunities"][0]["match_id"] = "unknown-match"
    elif damage == "catalog_route":
        path = catalog; value = json.loads(path.read_bytes())
        value["events"][0]["decks"] = "events/900002/decks.json"
    else:
        path = public / "meta.json"; value = json.loads(path.read_bytes())
        if damage == "upstream_path": value["input"]["event_path"] = "data/modern/melee/events/900002.json"
        elif damage == "public_event": value["event_id"] = "900002"
        elif damage == "descriptor_size": value["outputs"]["decks"]["bytes"] += 1
        elif damage == "missing_public": (public / "decks.json").unlink()
    _write_json(path, value)
    if damage == "unreadable_classification":
        (base / f"classifications/{definition.id}.json").write_text('{')
    elif damage == "unreadable_public":
        (public / "decks.json").write_text('{')
    result = _inspect_melee(tmp_path, "modern", desired, catalog)
    assert result["state"] == STALE
    assert result["issues"]


def test_melee_closure_accepts_a_new_catalog_event(tmp_path):
    from melee_synthetic import source_fixture, registry_file, public_products
    from mtgmeta.melee.publish import merge_event_catalog
    first, doc1, path1, _ = source_fixture(tmp_path)
    second, doc2, path2, _ = source_fixture(tmp_path, event_id="900002", day1_rounds=3)
    registry_file(tmp_path, [first, second])
    desired, catalog = public_products(tmp_path, first, doc1, path1)
    original = json.loads(catalog.read_bytes())
    _, catalog = public_products(tmp_path, second, doc2, path2)
    merged = merge_event_catalog(original, json.loads(catalog.read_bytes()))
    _write_json(catalog, merged)
    assert {e["event_id"] for e in merged["events"]} == {first.id, second.id}
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == CURRENT


def test_format_materialization_rolls_back_after_partial_failure(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    stage = tmp_path / "stage"
    for base, left, right in (
        (root, b"old-a", b"old-b"),
        (stage, b"new-a", b"new-b"),
    ):
        (base / "stats" / "modern").mkdir(parents=True)
        (base / "stats" / "modern" / "a.json").write_bytes(left)
        (base / "stats" / "modern" / "b.json").write_bytes(right)
    calls = 0

    def fail_second(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic write failure")
        os.replace(source, destination)

    with pytest.raises(ClassifierClosureError, match="was rolled back"):
        _materialize_with_rollback(
            root,
            stage,
            ["stats/modern/a.json", "stats/modern/b.json"],
            replace_file=fail_second,
        )

    assert (root / "stats" / "modern" / "a.json").read_bytes() == b"old-a"
    assert (root / "stats" / "modern" / "b.json").read_bytes() == b"old-b"


def test_format_materialization_rolls_back_after_final_validation_failure(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    stage = tmp_path / "stage"
    for base, payload in ((root, b"old"), (stage, b"new")):
        (base / "stats" / "modern").mkdir(parents=True)
        (base / "stats" / "modern" / "a.json").write_bytes(payload)

    def reject_final_tree() -> None:
        raise ClassifierClosureError("synthetic final validation failure")

    with pytest.raises(ClassifierClosureError, match="was rolled back"):
        _materialize_with_rollback(
            root,
            stage,
            ["stats/modern/a.json"],
            validate_final=reject_final_tree,
        )

    assert (root / "stats" / "modern" / "a.json").read_bytes() == b"old"


def test_public_format_selection_excludes_and_rejects_private_executable(
    tmp_path: Path,
) -> None:
    capabilities = [
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
        "weekly_top8",
        "completeness_reporting",
        "landing_generation",
        "metadata_generation",
        "catalog_generation",
    ]
    formats = []
    for format_id, public in (("standard", True), ("pauper", False)):
        formats.append(
            {
                "id": format_id,
                "display_name": format_id.title(),
                "state": "executable",
                "public": public,
                "mtgo": {
                    "enabled": True,
                    "event_collection_enabled": True,
                    "capabilities": capabilities,
                    "paths": {
                        "events": f"data/{format_id}",
                        "matches": f"data/{format_id}/mtgo/matches",
                        "rules": f"my_archetypes/{format_id}.yaml",
                        "statistics": f"stats/{format_id}/mtgo",
                        "reports": f"reports/{format_id}/mtgo",
                    },
                },
            }
        )
        for suffix in (
            "meta.json",
            "matchup_index.json",
            "top8/index.json",
            "landing/current.json",
            "archetype_hierarchy.json",
        ):
            _write_json(tmp_path / "stats" / format_id / "mtgo" / suffix, {})
    config = tmp_path / "configs" / "formats.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        yaml.safe_dump({"schema_version": "1.3.0", "formats": formats}),
        encoding="utf-8",
    )
    (tmp_path / "configs" / "archetype_mana_identities.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "formats": {"standard": {"approved": {}, "candidates": {}}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    rendered = tmp_path / "assets/js/phase8/archetype-visuals.js"
    rendered.parent.mkdir(parents=True)
    rendered.write_text(
        "const manaIdentities = Object.freeze({\n"
        "  standard: Object.freeze({\n"
        "  }),\n"
        "});\n",
        encoding="utf-8",
    )
    write_catalog(tmp_path, generated_at="2026-09-05T00:00:00+00:00")

    assert discover_live_formats(tmp_path) == ["standard"]
    stored_catalog = json.loads(
        (tmp_path / "stats" / "catalog.json").read_text(encoding="utf-8")
    )
    stored_catalog["formats"] = []
    _write_json(tmp_path / "stats" / "catalog.json", stored_catalog)
    assert discover_live_formats(tmp_path) == ["standard"]

    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    inspection = inspect_repository(tmp_path, ["pauper"])
    assert inspection["state"] == "NOT_CURRENT"
    assert inspection["formats"][0]["state"] == "INVALID"
    assert inspection["formats"][0]["issues"] == [
        "format 'pauper' is not a complete public MTGO format: "
        "registry public is false"
    ]
    convergence = converge_format(tmp_path, "pauper", execute=True)
    assert convergence["state"] == "INVALID"
    assert convergence["changed_paths"] == []
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == before
