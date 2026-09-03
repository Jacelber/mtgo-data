from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier_closure import (
    BLOCKED_OWNER_REVIEW,
    CURRENT,
    STALE,
    ClassifierClosureError,
    _inspect_melee,
    _materialize_with_rollback,
)
from mtgmeta.mtgo import landing_editorial


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


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
    monkeypatch.setattr(landing_editorial, "validate_name_catalog", lambda *_args: {})
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


def test_melee_closure_follows_public_catalog_and_exact_sha_chain(
    tmp_path: Path,
) -> None:
    desired = "a" * 64
    rules = tmp_path / "my_archetypes" / "modern.yaml"
    rules.parent.mkdir(parents=True)
    rules.write_text("synthetic-rules\n", encoding="utf-8")
    registry = tmp_path / "configs" / "melee_events.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        yaml.safe_dump(
            {
                "events": [
                    {
                        "id": "123",
                        "format": "modern",
                        "enabled": True,
                        "review_status": "verified",
                        "tabletop": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    event = tmp_path / "data" / "modern" / "melee" / "events" / "123.json"
    _write_json(event, {"event": "synthetic"})
    classification = (
        tmp_path / "data" / "modern" / "melee" / "classifications" / "123.json"
    )
    _write_json(
        classification,
        {
            "classifier": {"digest": desired},
            "input": {"event_sha256": _digest(event)},
        },
    )
    opportunity = (
        tmp_path / "data" / "modern" / "melee" / "opportunities" / "123.json"
    )
    _write_json(
        opportunity,
        {
            "input": {
                "event_sha256": _digest(event),
                "classification_sha256": _digest(classification),
            }
        },
    )
    public = tmp_path / "stats" / "modern" / "melee" / "events" / "123"
    shared_input = {
        "event_sha256": _digest(event),
        "classification_sha256": _digest(classification),
        "opportunity_sha256": _digest(opportunity),
    }
    for name in ("overview", "decks", "matchup", "quality"):
        _write_json(public / f"{name}.json", {"input": shared_input})
    descriptors = {
        name: {"sha256": _digest(public / f"{name}.json")}
        for name in ("overview", "decks", "matchup", "quality")
    }
    _write_json(public / "meta.json", {"input": shared_input, "outputs": descriptors})
    catalog = tmp_path / "stats" / "modern" / "melee" / "index.json"
    catalog_document = {
        "active_taxonomy": {"taxonomy_sha256": _digest(rules)},
        "events": [
            {
                "event_id": "123",
                **{
                    name: f"events/123/{name}.json"
                    for name in ("meta", "overview", "decks", "matchup", "quality")
                },
                "matchup_compatibility": {
                    "matchup_sha256": _digest(public / "matchup.json")
                },
            }
        ],
    }
    _write_json(catalog, catalog_document)
    raw_manifest = (
        tmp_path / "data_raw" / "melee" / "123" / "snapshot" / "manifest.json"
    )
    _write_json(raw_manifest, {"responses": []})
    compatibility = (
        tmp_path / "tests" / "fixtures" / "melee" / "123_compatibility.json"
    )
    compatibility_document = {
        "contract_version": "1.0.0",
        "event": {"event_id": "123", "format": "modern"},
        "migration_policy": {
            "exact_byte_change": "separate_owner_approved_version_migration"
        },
        "immutable_snapshot": {
            "manifest": {
                "role": "raw_snapshot_manifest",
                "path": raw_manifest.relative_to(tmp_path).as_posix(),
                "bytes": raw_manifest.stat().st_size,
                "sha256": _digest(raw_manifest),
            }
        },
        "exact_files": [
            {
                "role": "normalized_event",
                "path": event.relative_to(tmp_path).as_posix(),
                "bytes": event.stat().st_size,
                "sha256": _digest(event),
            },
            {
                "role": "classification_overlay",
                "path": classification.relative_to(tmp_path).as_posix(),
                "bytes": classification.stat().st_size,
                "sha256": _digest(classification),
            },
        ],
        "catalog_projections": [
            {
                "path": catalog.relative_to(tmp_path).as_posix(),
                "root_requirements": {
                    "active_taxonomy": catalog_document["active_taxonomy"]
                },
                "selection": [
                    {
                        "collection": "events",
                        "field": "event_id",
                        "equals": "123",
                    }
                ],
                "expected": catalog_document["events"][0],
                "expansion_policy": (
                    "allow_unselected_entries_and_volatile_root_fields"
                ),
            }
        ],
    }
    _write_json(compatibility, compatibility_document)
    _write_json(
        tmp_path / "configs" / "pages_publication.json",
        {
            "compatibility_manifests": [
                compatibility.relative_to(tmp_path).as_posix()
            ]
        },
    )
    immutable_source_sha = _digest(raw_manifest)
    normalized_event_sha = _digest(event)

    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == CURRENT

    opportunity_document = json.loads(opportunity.read_text(encoding="utf-8"))
    opportunity_document["input"]["classification_sha256"] = "b" * 64
    _write_json(opportunity, opportunity_document)
    assert _inspect_melee(tmp_path, "modern", desired, catalog)["state"] == STALE

    opportunity_document["input"]["classification_sha256"] = _digest(classification)
    _write_json(opportunity, opportunity_document)
    registry_document = yaml.safe_load(registry.read_text(encoding="utf-8"))
    registry_document["events"].append(
        {
            "id": "456",
            "format": "modern",
            "enabled": True,
            "review_status": "verified",
            "tabletop": True,
        }
    )
    registry.write_text(yaml.safe_dump(registry_document), encoding="utf-8")
    result = _inspect_melee(tmp_path, "modern", desired, catalog)
    assert result["state"] == CURRENT
    assert result["issues"] == []

    compatibility_document["exact_files"][1]["sha256"] = "b" * 64
    _write_json(compatibility, compatibility_document)
    result = _inspect_melee(tmp_path, "modern", desired, catalog)
    assert result["state"] == BLOCKED_OWNER_REVIEW
    assert "Owner-approved migration" in result["issues"][0]

    compatibility_document["contract_version"] = "1.1.0"
    compatibility_document["exact_files"][1]["sha256"] = _digest(classification)
    _write_json(compatibility, compatibility_document)
    result = _inspect_melee(tmp_path, "modern", desired, catalog)
    assert result["state"] == CURRENT
    assert _digest(raw_manifest) == immutable_source_sha
    assert _digest(event) == normalized_event_sha

    registry_document["events"] = [registry_document["events"][1]]
    registry.write_text(yaml.safe_dump(registry_document), encoding="utf-8")
    result = _inspect_melee(tmp_path, "modern", desired, catalog)
    assert result["state"] == STALE
    assert result["issues"] == [
        "Melee catalog event is not uniquely enabled:'123'"
    ]


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
