from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import mtgmeta.melee.publish as publish
from mtgmeta.melee.multi_event_contract import (
    ERROR_CODES,
    MultiEventContractError,
    build_multi_event_matchup_contract,
)
from mtgmeta.melee.publish import (
    MeleePublicationError,
    build_active_taxonomy,
    build_matchup_compatibility,
    merge_event_catalog,
)
from validate_schemas import load_schemas, validate_instance


ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_SHA256 = "c" * 64
HIERARCHY = {
    "parents": [
        {"id": "alpha", "name": "Alpha", "expandable": False, "subtype_ids": []},
        {"id": "beta", "name": "Beta", "expandable": False, "subtype_ids": []},
    ],
    "leaves": [
        {
            "id": "alpha",
            "kind": "archetype",
            "name": "Alpha",
            "display_name": "Alpha",
            "parent_id": "alpha",
            "subtype_id": None,
        },
        {
            "id": "beta",
            "kind": "archetype",
            "name": "Beta",
            "display_name": "Beta",
            "parent_id": "beta",
            "subtype_id": None,
        },
    ],
}


def _event_input(
    event_id: str, digest_character: str, alpha_wins: int
) -> dict[str, Any]:
    matchup_sha256 = digest_character * 64
    event = {"name": f"Synthetic {event_id}"}
    input_document = {
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
    }
    inverse_wins = 10 - alpha_wins
    matrix = {
        "alpha": {
            "alpha": {"wins": 0, "losses": 0, "draws": 0},
            "beta": {"wins": alpha_wins, "losses": inverse_wins, "draws": 0},
        },
        "beta": {
            "alpha": {"wins": inverse_wins, "losses": alpha_wins, "draws": 0},
            "beta": {"wins": 0, "losses": 0, "draws": 0},
        },
    }
    meta = {
        "schema_version": "1.0.0",
        "document_type": "meta",
        "source": "melee",
        "product": "tabletop-major-events",
        "event_id": event_id,
        "format": "modern",
        "event": event,
        "input": input_document,
        "scope_order": ["all_constructed"],
        "quality": {"status": "pass", "blocking": False},
        "outputs": {
            "matchup": {
                "path": "matchup.json",
                "schema_version": "1.0.0",
                "bytes": 100,
                "sha256": matchup_sha256,
            }
        },
    }
    matchup = {
        "schema_version": "1.0.0",
        "document_type": "matchup",
        "source": "melee",
        "event_id": event_id,
        "format": "modern",
        "input": deepcopy(input_document),
        "event": deepcopy(event),
        "scope_order": ["all_constructed"],
        "hierarchy": deepcopy(HIERARCHY),
        "scopes": {
            "all_constructed": {
                "source_match_count": 10,
                "included_match_count": 10,
                "excluded_match_count": 0,
                "directed_observation_count": 20,
                "excluded_match_counts": {
                    "bye": 0,
                    "intentional_draw": 0,
                    "no_show": 0,
                    "awarded_win_top8_lock": 0,
                    "administrative_result": 0,
                    "disqualified_participant": 0,
                    "unknown": 0,
                },
                "parent_order": ["alpha", "beta"],
                "leaf_order": ["alpha", "beta"],
                "leaf_matrix": matrix,
            }
        },
    }
    return {"meta": meta, "matchup": matchup}


def _catalog_event(event_input: dict[str, Any]) -> dict[str, Any]:
    meta = event_input["meta"]
    event_id = meta["event_id"]
    descriptor = meta["outputs"]["matchup"]
    return {
        "event_id": event_id,
        "name": meta["event"]["name"],
        "series": "synthetic",
        "date": {"start": "2026-08-01", "end": "2026-08-02"},
        "event_structure": "constructed_single_stage",
        "source_url": f"https://melee.gg/Tournament/View/{event_id}",
        "meta": f"events/{event_id}/meta.json",
        "overview": f"events/{event_id}/overview.json",
        "decks": f"events/{event_id}/decks.json",
        "matchup": f"events/{event_id}/matchup.json",
        "quality": f"events/{event_id}/quality.json",
        "scope_order": ["all_constructed"],
        "default_scope": "all_constructed",
        "quality_status": "pass",
        "matchup_compatibility": build_matchup_compatibility(
            format_id="modern",
            input_document=meta["input"],
            quality=meta["quality"],
            matchup_descriptor=descriptor,
        ),
    }


def _catalog(event_inputs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.2.0",
        "document_type": "event_catalog",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": "modern",
        "active_taxonomy": build_active_taxonomy(
            format_id="modern",
            input_document=event_inputs[0]["meta"]["input"],
        ),
        "default_event_id": event_inputs[0]["meta"]["event_id"],
        "events": [_catalog_event(event_input) for event_input in event_inputs],
    }


def _schema_failures(document: dict[str, Any], schema_name: str) -> list[Any]:
    schemas, registry = load_schemas(ROOT / "schemas")
    return validate_instance(document, schemas[schema_name], registry)


def test_contract_error_vocabulary_is_frozen() -> None:
    assert ERROR_CODES == {
        "active_taxonomy_mismatch",
        "catalog_compatibility_mismatch",
        "catalog_event_missing",
        "catalog_identity_mismatch",
        "duplicate_catalog_event",
        "invalid_contract_input",
        "missing_active_taxonomy",
        "missing_catalog_compatibility",
        "provenance_mismatch",
        "unsupported_catalog_schema",
    }


def test_builds_versioned_result_from_catalog_admitted_inputs() -> None:
    event_20 = _event_input("20", "a", 8)
    event_10 = _event_input("10", "b", 1)

    result = build_multi_event_matchup_contract(
        [event_20, event_10],
        canonical_hierarchy=HIERARCHY,
        catalog=_catalog([event_20, event_10]),
    )

    assert result["schema_version"] == "1.0.0"
    assert result["event_ids"] == ["10", "20"]
    assert [item["event_id"] for item in result["inputs"]] == ["10", "20"]
    assert result["compatibility"] == {
        "catalog_schema_version": "1.2.0",
        "catalog_compatibility_schema_version": "1.0.0",
        "active_taxonomy_schema_version": "1.0.0",
        "matchup_schema_version": "1.0.0",
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
    }
    assert result["parent_matrix"]["alpha"]["beta"]["wins"] == 9
    assert not _schema_failures(result, "melee-multi-event-matchup.schema.json")


def test_catalog_schema_preserves_legacy_and_requires_versioned_evidence() -> (
    None
):
    event_10 = _event_input("10", "a", 5)
    legacy = _catalog([event_10])
    legacy["schema_version"] = "1.0.0"
    del legacy["active_taxonomy"]
    del legacy["events"][0]["matchup_compatibility"]
    assert not _schema_failures(legacy, "melee-event-catalog.schema.json")

    historical = _catalog([event_10])
    historical["schema_version"] = "1.1.0"
    del historical["active_taxonomy"]
    assert not _schema_failures(historical, "melee-event-catalog.schema.json")

    incomplete = deepcopy(legacy)
    incomplete["schema_version"] = "1.1.0"
    assert _schema_failures(incomplete, "melee-event-catalog.schema.json")

    active = _catalog([event_10])
    del active["active_taxonomy"]
    assert _schema_failures(active, "melee-event-catalog.schema.json")


def test_legacy_or_incomplete_catalog_is_not_multi_event_eligible() -> None:
    inputs = [_event_input("10", "a", 5), _event_input("20", "b", 5)]
    catalog = _catalog(inputs)
    catalog["schema_version"] = "1.0.0"
    with pytest.raises(MultiEventContractError, match="unsupported_catalog_schema"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=catalog,
        )

    catalog = _catalog(inputs)
    catalog["schema_version"] = "1.1.0"
    with pytest.raises(MultiEventContractError, match="unsupported_catalog_schema"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=catalog,
        )

    catalog = _catalog(inputs)
    del catalog["events"][0]["matchup_compatibility"]
    with pytest.raises(MultiEventContractError, match="missing_catalog_compatibility"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=catalog,
        )


def test_active_taxonomy_is_required_and_must_match_every_event() -> None:
    inputs = [_event_input("10", "a", 5), _event_input("20", "b", 5)]

    missing = _catalog(inputs)
    del missing["active_taxonomy"]
    with pytest.raises(MultiEventContractError, match="missing_active_taxonomy"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=missing,
        )

    stale = _catalog(inputs)
    stale["active_taxonomy"]["taxonomy_sha256"] = "d" * 64
    with pytest.raises(MultiEventContractError, match="active_taxonomy_mismatch"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=stale,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "mtgo"),
        ("product", "environment-trends"),
        ("format", "legacy"),
        ("scope", "day1"),
        ("matchup_schema_version", "2.0.0"),
        ("matchup_sha256", "f" * 64),
        ("taxonomy_schema_version", "2.0.0"),
        ("taxonomy_sha256", "f" * 64),
        ("quality_blocking", True),
    ],
)
def test_catalog_compatibility_evidence_must_reconcile(field: str, value: Any) -> None:
    inputs = [_event_input("10", "a", 5), _event_input("20", "b", 5)]
    catalog = _catalog(inputs)
    catalog["events"][0]["matchup_compatibility"][field] = value

    with pytest.raises(MultiEventContractError, match="catalog_compatibility_mismatch"):
        build_multi_event_matchup_contract(
            inputs,
            canonical_hierarchy=HIERARCHY,
            catalog=catalog,
        )


def test_publication_helper_emits_minimum_fail_closed_compatibility_block() -> None:
    block = build_matchup_compatibility(
        format_id="modern",
        input_document={
            "taxonomy_schema_version": "1.1.0",
            "taxonomy_sha256": TAXONOMY_SHA256,
        },
        quality={"status": "warning", "blocking": False},
        matchup_descriptor={
            "path": "matchup.json",
            "schema_version": "1.0.0",
            "bytes": 100,
            "sha256": "a" * 64,
        },
    )
    assert block == {
        "schema_version": "1.0.0",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": "modern",
        "scope": "all_constructed",
        "matchup_schema_version": "1.0.0",
        "matchup_sha256": "a" * 64,
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
        "quality_blocking": False,
    }

    with pytest.raises(ValueError, match="taxonomy digest"):
        build_matchup_compatibility(
            format_id="modern",
            input_document={
                "taxonomy_schema_version": "1.1.0",
                "taxonomy_sha256": "not-a-digest",
            },
            quality={"status": "pass", "blocking": False},
            matchup_descriptor={
                "path": "matchup.json",
                "schema_version": "1.0.0",
                "bytes": 100,
                "sha256": "a" * 64,
            },
        )

    assert build_active_taxonomy(
        format_id="modern",
        input_document={
            "taxonomy_schema_version": "1.1.0",
            "taxonomy_sha256": TAXONOMY_SHA256,
        },
    ) == {
        "schema_version": "1.0.0",
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
    }


def test_event_publisher_wires_catalog_version_and_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_input = _event_input("10", "a", 5)
    meta = event_input["meta"]
    overview = {
        "event_id": "10",
        "format": "modern",
        "event_structure": "constructed_single_stage",
        "event": {
            "name": "Synthetic 10",
            "series": "synthetic",
            "date": {"start": "2026-08-01", "end": "2026-08-02"},
            "source_url": "https://melee.gg/Tournament/View/10",
        },
        "input": deepcopy(meta["input"]),
        "scope_order": ["all_constructed"],
        "default_scope": "all_constructed",
    }
    documents = {
        name: {
            "event_id": "10",
            "format": "modern",
            "source": "melee",
            "input": deepcopy(meta["input"]),
        }
        for name in ("overview", "decks", "matchup", "quality")
    }
    documents["quality"].update(
        {"status": "ready", "blocking": False, "issues": []}
    )
    descriptors = {
        name: {
            "path": f"{name}.json",
            "schema_version": "1.0.0",
            "bytes": 100,
            "sha256": ("a" if name == "matchup" else "b") * 64,
        }
        for name in documents
    }
    monkeypatch.setattr(
        publish,
        "build_event_statistics_from_paths",
        lambda *args: {"overview": overview},
    )
    monkeypatch.setattr(
        publish,
        "build_event_matchup_from_paths",
        lambda *args: event_input["matchup"],
    )
    monkeypatch.setattr(
        publish,
        "load_melee_event_registry",
        lambda path: SimpleNamespace(
            require_fetchable=lambda event_id: SimpleNamespace(
                format="modern", structure="constructed_single_stage"
            )
        ),
    )
    monkeypatch.setattr(
        publish,
        "_verified_outputs",
        lambda *args: (documents, descriptors),
    )

    publication = publish.build_event_publication_from_paths(
        Path("event.json"),
        Path("classification.json"),
        Path("opportunity.json"),
        Path("taxonomy.yaml"),
        Path("registry.yaml"),
        ROOT,
    )

    assert publication["meta"]["schema_version"] == "1.0.0"
    assert publication["catalog"]["schema_version"] == "1.2.0"
    assert publication["catalog"]["active_taxonomy"] == {
        "schema_version": "1.0.0",
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
    }
    assert publication["catalog"]["events"][0]["matchup_compatibility"] == {
        "schema_version": "1.0.0",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": "modern",
        "scope": "all_constructed",
        "matchup_schema_version": "1.0.0",
        "matchup_sha256": "a" * 64,
        "taxonomy_schema_version": "1.1.0",
        "taxonomy_sha256": TAXONOMY_SHA256,
        "quality_blocking": False,
    }


def test_event_publisher_merges_new_event_without_changing_existing_selection() -> None:
    existing = _catalog([_event_input("434455", "a", 5)])
    generated = _catalog([_event_input("441441", "b", 5)])
    protected_event = deepcopy(existing["events"][0])

    merged = merge_event_catalog(existing, generated)

    assert merged["default_event_id"] == "434455"
    assert [event["event_id"] for event in merged["events"]] == [
        "434455",
        "441441",
    ]
    assert merged["events"][0] == protected_event


def test_event_publisher_main_writes_the_merged_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog([_event_input("434455", "a", 5)])
    generated = _catalog([_event_input("441441", "b", 5)])
    catalog_path = tmp_path / "stats" / "modern" / "melee" / "index.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_bytes(publish.statistics_document_bytes(existing))
    monkeypatch.setattr(
        publish,
        "build_event_publication_from_paths",
        lambda *args: {"meta": {"schema_version": "1.0.0"}, "catalog": generated},
    )

    result = publish.main(
        [
            "--root",
            str(tmp_path),
            "--format",
            "modern",
            "--event-id",
            "441441",
            "--execute",
        ]
    )

    assert result == 0
    merged, _ = publish._read_object(catalog_path)
    assert merged["default_event_id"] == "434455"
    assert [event["event_id"] for event in merged["events"]] == [
        "434455",
        "441441",
    ]


def test_event_publisher_rejects_multi_event_growth_from_legacy_catalog() -> None:
    existing = _catalog([_event_input("434455", "a", 5)])
    existing["schema_version"] = "1.0.0"
    del existing["active_taxonomy"]
    del existing["events"][0]["matchup_compatibility"]
    generated = _catalog([_event_input("441441", "b", 5)])

    with pytest.raises(MeleePublicationError, match="migration"):
        merge_event_catalog(existing, generated)


def test_event_publisher_allows_single_selected_event_legacy_migration() -> None:
    existing = _catalog([_event_input("434455", "a", 5)])
    existing["schema_version"] = "1.0.0"
    del existing["active_taxonomy"]
    del existing["events"][0]["matchup_compatibility"]
    generated = _catalog([_event_input("434455", "b", 5)])

    assert merge_event_catalog(existing, generated) == generated


def test_event_publisher_rejects_active_taxonomy_change_for_existing_cohort() -> None:
    existing = _catalog([_event_input("434455", "a", 5)])
    generated = _catalog([_event_input("441441", "b", 5)])
    generated["active_taxonomy"]["taxonomy_sha256"] = "d" * 64

    with pytest.raises(MeleePublicationError, match="active taxonomy"):
        merge_event_catalog(existing, generated)


def test_multi_event_schema_rejects_missing_provenance() -> None:
    inputs = [_event_input("10", "a", 5), _event_input("20", "b", 5)]
    result = build_multi_event_matchup_contract(
        inputs,
        canonical_hierarchy=HIERARCHY,
        catalog=_catalog(inputs),
    )
    del result["inputs"]
    assert _schema_failures(result, "melee-multi-event-matchup.schema.json")
