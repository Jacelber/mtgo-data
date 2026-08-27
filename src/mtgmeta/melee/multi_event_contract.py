"""Versioned catalog-admitted contract for multi-event Melee matchups."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .multi_event_matchup import aggregate_multi_event_matchups


MULTI_EVENT_SCHEMA_VERSION = "1.0.0"
SUPPORTED_CATALOG_SCHEMA_VERSIONS = frozenset({"1.1.0"})
SUPPORTED_COMPATIBILITY_SCHEMA_VERSIONS = frozenset({"1.0.0"})
ERROR_CODES = frozenset(
    {
        "catalog_compatibility_mismatch",
        "catalog_event_missing",
        "catalog_identity_mismatch",
        "duplicate_catalog_event",
        "invalid_contract_input",
        "missing_catalog_compatibility",
        "provenance_mismatch",
        "unsupported_catalog_schema",
    }
)


class MultiEventContractError(ValueError):
    """A stable fail-closed catalog or provenance contract error."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    if code not in ERROR_CODES:
        raise AssertionError(f"unregistered multi-event contract error: {code}")
    raise MultiEventContractError(code, detail)


def _mapping(value: Any, code: str, detail: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(code, detail)
    return value


def _catalog_events(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw_events = catalog.get("events")
    if not isinstance(raw_events, list):
        _fail("invalid_contract_input", "catalog events must be an array")
    events: dict[str, Mapping[str, Any]] = {}
    for position, raw_event in enumerate(raw_events):
        event = _mapping(
            raw_event,
            "invalid_contract_input",
            f"catalog event {position} must be an object",
        )
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.isdigit() or event_id == "0":
            _fail("invalid_contract_input", f"catalog event {position} has no valid ID")
        if event_id in events:
            _fail("duplicate_catalog_event", f"catalog repeats event {event_id}")
        events[event_id] = event
    return events


def _input_index(
    event_inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for position, event_input in enumerate(event_inputs):
        event = _mapping(
            event_input,
            "invalid_contract_input",
            f"event input {position} must be an object",
        )
        meta = _mapping(
            event.get("meta"),
            "invalid_contract_input",
            f"event input {position} has no meta",
        )
        event_id = meta.get("event_id")
        if isinstance(event_id, str):
            indexed.setdefault(event_id, event)
    return indexed


def _admit_event(
    *,
    event_id: str,
    event_name: str,
    event_input: Mapping[str, Any],
    catalog_event: Mapping[str, Any],
    format_id: str,
) -> dict[str, Any]:
    meta = _mapping(
        event_input.get("meta"),
        "invalid_contract_input",
        f"event {event_id} has no meta",
    )
    matchup = _mapping(
        event_input.get("matchup"),
        "invalid_contract_input",
        f"event {event_id} has no matchup",
    )
    meta_event = _mapping(
        meta.get("event"),
        "provenance_mismatch",
        f"event {event_id} has no event metadata",
    )
    quality = _mapping(
        meta.get("quality"),
        "provenance_mismatch",
        f"event {event_id} has no quality metadata",
    )
    input_document = _mapping(
        meta.get("input"),
        "provenance_mismatch",
        f"event {event_id} has no taxonomy input",
    )
    outputs = _mapping(
        meta.get("outputs"),
        "provenance_mismatch",
        f"event {event_id} has no output descriptors",
    )
    descriptor = _mapping(
        outputs.get("matchup"),
        "provenance_mismatch",
        f"event {event_id} has no matchup descriptor",
    )
    compatibility = catalog_event.get("matchup_compatibility")
    if not isinstance(compatibility, Mapping):
        _fail(
            "missing_catalog_compatibility",
            f"catalog event {event_id} has no matchup compatibility evidence",
        )
    compatibility_version = compatibility.get("schema_version")
    if compatibility_version not in SUPPORTED_COMPATIBILITY_SCHEMA_VERSIONS:
        _fail(
            "catalog_compatibility_mismatch",
            f"catalog event {event_id} uses unsupported compatibility Schema",
        )
    expected = {
        "schema_version": "1.0.0",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": format_id,
        "scope": "all_constructed",
        "matchup_schema_version": matchup.get("schema_version"),
        "matchup_sha256": descriptor.get("sha256"),
        "taxonomy_schema_version": input_document.get("taxonomy_schema_version"),
        "taxonomy_sha256": input_document.get("taxonomy_sha256"),
        "quality_blocking": False,
    }
    if dict(compatibility) != expected:
        _fail(
            "catalog_compatibility_mismatch",
            f"catalog event {event_id} evidence does not match validated inputs",
        )
    expected_meta_path = f"events/{event_id}/meta.json"
    expected_matchup_path = f"events/{event_id}/matchup.json"
    if (
        catalog_event.get("name") != event_name
        or meta_event.get("name") != event_name
        or catalog_event.get("meta") != expected_meta_path
        or catalog_event.get("matchup") != expected_matchup_path
        or descriptor.get("path") != "matchup.json"
        or catalog_event.get("scope_order")
        not in (
            ["all_constructed"],
            ["day1", "day2", "all_constructed"],
        )
        or catalog_event.get("default_scope") != "all_constructed"
        or catalog_event.get("quality_status") != quality.get("status")
    ):
        _fail(
            "provenance_mismatch",
            f"catalog event {event_id} paths or identity do not reconcile",
        )
    return {
        "event_id": event_id,
        "event_name": event_name,
        "meta_path": expected_meta_path,
        "matchup_path": expected_matchup_path,
        "matchup_schema_version": compatibility["matchup_schema_version"],
        "matchup_sha256": compatibility["matchup_sha256"],
        "taxonomy_schema_version": compatibility["taxonomy_schema_version"],
        "taxonomy_sha256": compatibility["taxonomy_sha256"],
    }


def build_multi_event_matchup_contract(
    event_inputs: Sequence[Mapping[str, Any]],
    *,
    canonical_hierarchy: Mapping[str, Any],
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Aggregate prevalidated inputs admitted by a compatible active catalog.

    The caller owns active JSON Schema validation of the loaded catalog, meta,
    and matchup documents. This wrapper reconciles their cross-document
    identity, paths, digests, supported versions, scope, and quality evidence.
    """

    if isinstance(event_inputs, (str, bytes)) or not isinstance(event_inputs, Sequence):
        _fail("invalid_contract_input", "event inputs must be a sequence")
    if not isinstance(catalog, Mapping):
        _fail("invalid_contract_input", "catalog must be an object")
    catalog_version = catalog.get("schema_version")
    if catalog_version not in SUPPORTED_CATALOG_SCHEMA_VERSIONS:
        _fail(
            "unsupported_catalog_schema",
            f"catalog Schema {catalog_version!r} is not multi-event eligible",
        )
    result = aggregate_multi_event_matchups(
        event_inputs,
        canonical_hierarchy=canonical_hierarchy,
    )
    format_id = result["format"]
    if (
        catalog.get("document_type") != "event_catalog"
        or catalog.get("source") != result["source"]
        or catalog.get("product") != result["product"]
        or catalog.get("format") != format_id
    ):
        _fail(
            "catalog_identity_mismatch",
            "catalog source, product, or format does not match selected inputs",
        )
    catalog_events = _catalog_events(catalog)
    inputs_by_id = _input_index(event_inputs)
    admitted_inputs: list[dict[str, Any]] = []
    for event_id, event_name in zip(
        result["event_ids"], result["event_names"], strict=True
    ):
        if event_id not in catalog_events:
            _fail("catalog_event_missing", f"event {event_id} is not in the catalog")
        event_input = inputs_by_id.get(event_id)
        if event_input is None:
            _fail("invalid_contract_input", f"event {event_id} input is unavailable")
        admitted_inputs.append(
            _admit_event(
                event_id=event_id,
                event_name=event_name,
                event_input=event_input,
                catalog_event=catalog_events[event_id],
                format_id=format_id,
            )
        )
    compatibility_versions = {
        item["matchup_schema_version"] for item in admitted_inputs
    }
    if len(compatibility_versions) != 1:
        _fail(
            "catalog_compatibility_mismatch",
            "catalog-admitted matchup Schema versions differ",
        )
    return {
        "schema_version": MULTI_EVENT_SCHEMA_VERSION,
        **result,
        "inputs": admitted_inputs,
        "compatibility": {
            "catalog_schema_version": catalog_version,
            "catalog_compatibility_schema_version": "1.0.0",
            **result["compatibility"],
        },
    }
