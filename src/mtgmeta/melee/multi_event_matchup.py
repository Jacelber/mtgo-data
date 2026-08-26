"""Pure raw-count aggregation for compatible Melee matchup documents."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import re
from typing import Any

from ..consumer import literal_match_record


SUPPORTED_MATCHUP_SCHEMA_VERSIONS = frozenset({"1.0.0"})
LOW_SAMPLE_THRESHOLD = 20
ERROR_CODES = frozenset(
    {
        "blocking_quality",
        "duplicate_event_conflict",
        "event_identity_mismatch",
        "format_mismatch",
        "identity_metadata_mismatch",
        "invalid_event_input",
        "matrix_invariant_failed",
        "missing_all_constructed_scope",
        "product_mismatch",
        "source_mismatch",
        "taxonomy_digest_mismatch",
        "taxonomy_version_mismatch",
        "too_few_events",
        "unsupported_matchup_schema",
    }
)
COUNT_FIELDS = ("wins", "losses", "draws")
PARENT_MEANING_FIELDS = ("id", "name", "expandable")
LEAF_MEANING_FIELDS = (
    "id",
    "kind",
    "name",
    "display_name",
    "parent_id",
    "subtype_id",
)
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MultiEventMatchupError(ValueError):
    """A stable fail-closed compatibility or aggregation error."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    if code not in ERROR_CODES:
        raise AssertionError(f"unregistered multi-event error code: {code}")
    raise MultiEventMatchupError(code, detail)


def _mapping(value: Any, detail: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid_event_input", detail)
    return value


def _object_list(value: Any, detail: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(
        isinstance(item, Mapping) for item in value
    ):
        _fail("identity_metadata_mismatch", detail)
    return value


def _identity_index(
    rows: Sequence[Mapping[str, Any]],
    *,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for position, row in enumerate(rows):
        identity_id = row.get("id")
        if not isinstance(identity_id, str) or not identity_id:
            _fail(
                "identity_metadata_mismatch",
                f"{label} identity {position} has no stable ID",
            )
        if identity_id in indexed:
            _fail(
                "identity_metadata_mismatch",
                f"{label} contains duplicate identity {identity_id}",
            )
        indexed[identity_id] = row
    return indexed


def _canonical_hierarchy(
    hierarchy: Mapping[str, Any],
) -> tuple[
    list[str],
    list[str],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    parents = _object_list(hierarchy.get("parents"), "canonical parents are invalid")
    leaves = _object_list(hierarchy.get("leaves"), "canonical leaves are invalid")
    if not parents or not leaves:
        _fail("identity_metadata_mismatch", "canonical hierarchy must not be empty")
    parent_index = _identity_index(parents, label="canonical parent")
    leaf_index = _identity_index(leaves, label="canonical leaf")
    parent_order = list(parent_index)
    leaf_order = list(leaf_index)

    for leaf_id, leaf in leaf_index.items():
        parent_id = leaf.get("parent_id")
        if parent_id not in parent_index:
            _fail(
                "identity_metadata_mismatch",
                f"canonical leaf {leaf_id} has unknown parent {parent_id}",
            )
    for parent_id, parent in parent_index.items():
        subtype_ids = parent.get("subtype_ids")
        expected_subtypes = [
            leaf_id
            for leaf_id in leaf_order
            if leaf_index[leaf_id].get("parent_id") == parent_id
            and leaf_index[leaf_id].get("kind") == "subtype"
        ]
        if subtype_ids != expected_subtypes:
            _fail(
                "identity_metadata_mismatch",
                f"canonical parent {parent_id} has inconsistent subtype order",
            )
    return parent_order, leaf_order, parent_index, leaf_index


def _event_id(meta: Mapping[str, Any], matchup: Mapping[str, Any]) -> str:
    meta_id = meta.get("event_id")
    matchup_id = matchup.get("event_id")
    if (
        not isinstance(meta_id, str)
        or not EVENT_ID_PATTERN.fullmatch(meta_id)
        or matchup_id != meta_id
    ):
        _fail(
            "event_identity_mismatch",
            "event metadata and matchup document IDs must be the same positive integer",
        )
    return meta_id


def _deduplicate_inputs(
    event_inputs: Sequence[Mapping[str, Any]],
) -> list[tuple[str, Mapping[str, Any], Mapping[str, Any]]]:
    unique: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for position, event_input in enumerate(event_inputs):
        if not isinstance(event_input, Mapping):
            _fail("invalid_event_input", f"event input {position} must be an object")
        meta = _mapping(event_input.get("meta"), f"event input {position} has no meta")
        matchup = _mapping(
            event_input.get("matchup"),
            f"event input {position} has no matchup",
        )
        event_id = _event_id(meta, matchup)
        existing = unique.get(event_id)
        if existing is not None:
            if existing != (meta, matchup):
                _fail(
                    "duplicate_event_conflict",
                    f"event {event_id} was supplied with conflicting documents",
                )
            continue
        unique[event_id] = (meta, matchup)
    if len(unique) < 2:
        _fail("too_few_events", "at least two distinct event IDs are required")
    return [
        (event_id, *unique[event_id])
        for event_id in sorted(unique, key=int)
    ]


def _taxonomy_identity(
    meta: Mapping[str, Any],
    matchup: Mapping[str, Any],
    event_id: str,
) -> tuple[str, str]:
    meta_input = _mapping(meta.get("input"), f"event {event_id} meta.input is invalid")
    matchup_input = _mapping(
        matchup.get("input"),
        f"event {event_id} matchup.input is invalid",
    )
    meta_version = meta_input.get("taxonomy_schema_version")
    matchup_version = matchup_input.get("taxonomy_schema_version")
    if (
        not isinstance(meta_version, str)
        or not meta_version
        or matchup_version != meta_version
    ):
        _fail(
            "taxonomy_version_mismatch",
            f"event {event_id} has inconsistent taxonomy Schema versions",
        )
    meta_digest = meta_input.get("taxonomy_sha256")
    matchup_digest = matchup_input.get("taxonomy_sha256")
    if (
        not isinstance(meta_digest, str)
        or not SHA256_PATTERN.fullmatch(meta_digest)
        or matchup_digest != meta_digest
    ):
        _fail(
            "taxonomy_digest_mismatch",
            f"event {event_id} has inconsistent taxonomy digests",
        )
    return meta_version, meta_digest


def _validate_identity_subset(
    hierarchy: Mapping[str, Any],
    *,
    event_id: str,
    canonical_parent_order: Sequence[str],
    canonical_leaf_order: Sequence[str],
    canonical_parents: Mapping[str, Mapping[str, Any]],
    canonical_leaves: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str], dict[str, str]]:
    parents = _object_list(
        hierarchy.get("parents"),
        f"event {event_id} parents are invalid",
    )
    leaves = _object_list(
        hierarchy.get("leaves"),
        f"event {event_id} leaves are invalid",
    )
    if not parents or not leaves:
        _fail(
            "identity_metadata_mismatch",
            f"event {event_id} hierarchy must not be empty",
        )
    parent_index = _identity_index(parents, label=f"event {event_id} parent")
    leaf_index = _identity_index(leaves, label=f"event {event_id} leaf")
    event_parent_order = list(parent_index)
    event_leaf_order = list(leaf_index)
    if set(event_parent_order) - set(canonical_parent_order) or set(
        event_leaf_order
    ) - set(canonical_leaf_order):
        _fail(
            "identity_metadata_mismatch",
            f"event {event_id} contains an identity outside the canonical hierarchy",
        )

    leaf_to_parent: dict[str, str] = {}
    for leaf_id, leaf in leaf_index.items():
        canonical = canonical_leaves.get(leaf_id)
        if canonical is None or any(
            leaf.get(field) != canonical.get(field) for field in LEAF_MEANING_FIELDS
        ):
            _fail(
                "identity_metadata_mismatch",
                f"event {event_id} leaf {leaf_id} changed stable meaning",
            )
        parent_id = leaf.get("parent_id")
        if not isinstance(parent_id, str) or parent_id not in parent_index:
            _fail(
                "identity_metadata_mismatch",
                f"event {event_id} leaf {leaf_id} has no observed parent",
            )
        leaf_to_parent[leaf_id] = parent_id

    for parent_id, parent in parent_index.items():
        canonical = canonical_parents.get(parent_id)
        if canonical is None or any(
            parent.get(field) != canonical.get(field)
            for field in PARENT_MEANING_FIELDS
        ):
            _fail(
                "identity_metadata_mismatch",
                f"event {event_id} parent {parent_id} changed stable meaning",
            )
        expected_subtypes = [
            leaf_id
            for leaf_id in event_leaf_order
            if leaf_to_parent[leaf_id] == parent_id
            and leaf_index[leaf_id].get("kind") == "subtype"
        ]
        if parent.get("subtype_ids") != expected_subtypes:
            _fail(
                "identity_metadata_mismatch",
                f"event {event_id} parent {parent_id} has inconsistent subtypes",
            )
    return event_parent_order, event_leaf_order, leaf_to_parent


def _nonnegative_integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def _validate_scope_matrix(
    scope: Mapping[str, Any],
    *,
    event_id: str,
    parent_order: Sequence[str],
    leaf_order: Sequence[str],
) -> tuple[
    dict[str, dict[str, dict[str, int]]],
    int,
    int,
    int,
    dict[str, int],
]:
    if scope.get("parent_order") != list(parent_order) or scope.get(
        "leaf_order"
    ) != list(leaf_order):
        _fail(
            "identity_metadata_mismatch",
            f"event {event_id} scope order does not match its hierarchy",
        )
    raw_matrix = _mapping(
        scope.get("leaf_matrix"),
        f"event {event_id} all_constructed leaf matrix is invalid",
    )
    if set(raw_matrix) != set(leaf_order):
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} leaf matrix rows do not match leaf order",
        )
    matrix: dict[str, dict[str, dict[str, int]]] = {}
    observations = 0
    for row_id in leaf_order:
        raw_columns = _mapping(
            raw_matrix[row_id],
            f"event {event_id} matrix row {row_id} is invalid",
        )
        if set(raw_columns) != set(leaf_order):
            _fail(
                "matrix_invariant_failed",
                f"event {event_id} matrix row {row_id} has incomplete columns",
            )
        matrix[row_id] = {}
        for column_id in leaf_order:
            raw_cell = _mapping(
                raw_columns[column_id],
                f"event {event_id} matrix cell {row_id}/{column_id} is invalid",
            )
            if any(not _nonnegative_integer(raw_cell.get(field)) for field in COUNT_FIELDS):
                _fail(
                    "matrix_invariant_failed",
                    f"event {event_id} matrix cell {row_id}/{column_id} has invalid counts",
                )
            cell = {field: int(raw_cell[field]) for field in COUNT_FIELDS}
            matrix[row_id][column_id] = cell
            observations += sum(cell.values())

    for row_id in leaf_order:
        for column_id in leaf_order:
            cell = matrix[row_id][column_id]
            inverse = matrix[column_id][row_id]
            if (
                cell["wins"] != inverse["losses"]
                or cell["losses"] != inverse["wins"]
                or cell["draws"] != inverse["draws"]
            ):
                _fail(
                    "matrix_invariant_failed",
                    f"event {event_id} matrix cell {row_id}/{column_id} is not inverse",
                )
            if row_id == column_id and cell["draws"] % 2:
                _fail(
                    "matrix_invariant_failed",
                    f"event {event_id} mirror draws are not paired observations",
                )

    included = scope.get("included_match_count")
    directed = scope.get("directed_observation_count")
    source = scope.get("source_match_count")
    excluded = scope.get("excluded_match_count")
    if not all(_nonnegative_integer(value) for value in (included, directed, source, excluded)):
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} scope counts are invalid",
        )
    if directed != observations or observations != 2 * included:
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} directed observations do not conserve physical matches",
        )
    if source != included + excluded:
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} source matches do not reconcile",
        )
    raw_exclusions = _mapping(
        scope.get("excluded_match_counts"),
        f"event {event_id} exclusion counts are invalid",
    )
    if not raw_exclusions or any(
        not isinstance(key, str) or not _nonnegative_integer(value)
        for key, value in raw_exclusions.items()
    ):
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} exclusion counts are invalid",
        )
    exclusions = {key: int(value) for key, value in raw_exclusions.items()}
    if sum(exclusions.values()) != excluded:
        _fail(
            "matrix_invariant_failed",
            f"event {event_id} exclusions do not reconcile",
        )
    return matrix, int(source), int(included), int(excluded), exclusions


def _blank_matrix(order: Sequence[str]) -> dict[str, dict[str, dict[str, int]]]:
    return {
        row_id: {
            column_id: {field: 0 for field in COUNT_FIELDS}
            for column_id in order
        }
        for row_id in order
    }


def _blank_contributors(order: Sequence[str]) -> dict[str, dict[str, set[str]]]:
    return {
        row_id: {column_id: set() for column_id in order} for row_id in order
    }


def _roll_up(
    leaf_matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    leaf_contributors: Mapping[str, Mapping[str, set[str]]],
    *,
    parent_order: Sequence[str],
    leaf_order: Sequence[str],
    leaf_to_parent: Mapping[str, str],
) -> tuple[
    dict[str, dict[str, dict[str, int]]],
    dict[str, dict[str, set[str]]],
]:
    parent_matrix = _blank_matrix(parent_order)
    parent_contributors = _blank_contributors(parent_order)
    for row_id in leaf_order:
        parent_row = leaf_to_parent[row_id]
        for column_id in leaf_order:
            parent_column = leaf_to_parent[column_id]
            target = parent_matrix[parent_row][parent_column]
            for field in COUNT_FIELDS:
                target[field] += leaf_matrix[row_id][column_id][field]
            parent_contributors[parent_row][parent_column].update(
                leaf_contributors[row_id][column_id]
            )
    return parent_matrix, parent_contributors


def _record(
    counts: Mapping[str, int],
    contributors: set[str],
    *,
    mirror: bool,
) -> dict[str, Any]:
    record = literal_match_record(
        int(counts["wins"]),
        int(counts["losses"]),
        int(counts["draws"]),
    )
    matches = int(record["matches"])
    return {
        **record,
        "mirror": mirror,
        "low_sample": 0 < matches < LOW_SAMPLE_THRESHOLD,
        "contributing_event_ids": sorted(contributors, key=int),
    }


def _emit_matrix(
    matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    contributors: Mapping[str, Mapping[str, set[str]]],
    order: Sequence[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        row_id: {
            column_id: _record(
                matrix[row_id][column_id],
                contributors[row_id][column_id],
                mirror=row_id == column_id,
            )
            for column_id in order
        }
        for row_id in order
    }


def _emit_overall(
    matrix: Mapping[str, Mapping[str, Mapping[str, int]]],
    contributors: Mapping[str, Mapping[str, set[str]]],
    order: Sequence[str],
) -> dict[str, dict[str, Any]]:
    emitted: dict[str, dict[str, Any]] = {}
    for row_id in order:
        counts = {field: 0 for field in COUNT_FIELDS}
        event_ids: set[str] = set()
        for column_id in order:
            if row_id == column_id:
                continue
            for field in COUNT_FIELDS:
                counts[field] += matrix[row_id][column_id][field]
            event_ids.update(contributors[row_id][column_id])
        emitted[row_id] = _record(counts, event_ids, mirror=False)
    return emitted


def _result_hierarchy(
    parent_order: Sequence[str],
    leaf_order: Sequence[str],
    canonical_parents: Mapping[str, Mapping[str, Any]],
    canonical_leaves: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    leaves = [dict(canonical_leaves[leaf_id]) for leaf_id in leaf_order]
    parents: list[dict[str, Any]] = []
    for parent_id in parent_order:
        parent = dict(canonical_parents[parent_id])
        parent["subtype_ids"] = [
            leaf_id
            for leaf_id in leaf_order
            if canonical_leaves[leaf_id].get("parent_id") == parent_id
            and canonical_leaves[leaf_id].get("kind") == "subtype"
        ]
        parents.append(parent)
    return {"parents": parents, "leaves": leaves}


def aggregate_multi_event_matchups(
    event_inputs: Sequence[Mapping[str, Any]],
    *,
    canonical_hierarchy: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine compatible event leaf matrices by summing raw W-L-D counts.

    Each input pairs a validated current ``meta`` document with its validated
    ``matchup`` document. ``canonical_hierarchy`` supplies the maintained
    taxonomy identity metadata and order. The function performs no I/O and
    emits no public artifact.
    """

    if isinstance(event_inputs, (str, bytes)) or not isinstance(
        event_inputs, Sequence
    ):
        _fail("invalid_event_input", "event inputs must be a sequence")
    if not isinstance(canonical_hierarchy, Mapping):
        _fail("identity_metadata_mismatch", "canonical hierarchy must be an object")
    (
        canonical_parent_order,
        canonical_leaf_order,
        canonical_parents,
        canonical_leaves,
    ) = _canonical_hierarchy(canonical_hierarchy)
    inputs = _deduplicate_inputs(event_inputs)

    validated: list[dict[str, Any]] = []
    observed_parent_ids: set[str] = set()
    observed_leaf_ids: set[str] = set()
    format_id: str | None = None
    taxonomy_version: str | None = None
    taxonomy_digest: str | None = None

    for event_id, meta, matchup in inputs:
        if meta.get("document_type") != "meta" or matchup.get(
            "document_type"
        ) != "matchup":
            _fail(
                "invalid_event_input",
                f"event {event_id} requires meta and matchup documents",
            )
        if meta.get("source") != "melee" or matchup.get("source") != "melee":
            _fail("source_mismatch", f"event {event_id} is not from Melee")
        if meta.get("product") != "tabletop-major-events":
            _fail(
                "product_mismatch",
                f"event {event_id} is not a Tabletop Major Events input",
            )
        event_format = meta.get("format")
        if not isinstance(event_format, str) or matchup.get("format") != event_format:
            _fail(
                "format_mismatch",
                f"event {event_id} metadata and matchup format differ",
            )
        if format_id is None:
            format_id = event_format
        elif event_format != format_id:
            _fail("format_mismatch", "selected events use different formats")
        schema_version = matchup.get("schema_version")
        if schema_version not in SUPPORTED_MATCHUP_SCHEMA_VERSIONS:
            _fail(
                "unsupported_matchup_schema",
                f"event {event_id} matchup Schema {schema_version!r} is unsupported",
            )
        quality = _mapping(
            meta.get("quality"),
            f"event {event_id} quality metadata is invalid",
        )
        if quality.get("blocking") is not False or quality.get("status") not in {
            "pass",
            "warning",
        }:
            _fail("blocking_quality", f"event {event_id} has blocking quality")
        meta_scopes = meta.get("scope_order")
        matchup_scopes = matchup.get("scope_order")
        scopes = _mapping(
            matchup.get("scopes"),
            f"event {event_id} matchup scopes are invalid",
        )
        if (
            not isinstance(meta_scopes, list)
            or "all_constructed" not in meta_scopes
            or not isinstance(matchup_scopes, list)
            or "all_constructed" not in matchup_scopes
            or matchup_scopes != meta_scopes
            or "all_constructed" not in scopes
        ):
            _fail(
                "missing_all_constructed_scope",
                f"event {event_id} does not expose all_constructed",
            )
        current_version, current_digest = _taxonomy_identity(meta, matchup, event_id)
        if taxonomy_version is None:
            taxonomy_version = current_version
        elif current_version != taxonomy_version:
            _fail(
                "taxonomy_version_mismatch",
                "selected events use different taxonomy Schema versions",
            )
        if taxonomy_digest is None:
            taxonomy_digest = current_digest
        elif current_digest != taxonomy_digest:
            _fail(
                "taxonomy_digest_mismatch",
                "selected events use different taxonomy digests",
            )
        meta_event = _mapping(meta.get("event"), f"event {event_id} name is missing")
        matchup_event = _mapping(
            matchup.get("event"),
            f"event {event_id} matchup name is missing",
        )
        event_name = meta_event.get("name")
        if (
            not isinstance(event_name, str)
            or not event_name
            or matchup_event.get("name") != event_name
        ):
            _fail(
                "event_identity_mismatch",
                f"event {event_id} name does not reconcile",
            )
        hierarchy = _mapping(
            matchup.get("hierarchy"),
            f"event {event_id} hierarchy is invalid",
        )
        parent_order, leaf_order, _ = _validate_identity_subset(
            hierarchy,
            event_id=event_id,
            canonical_parent_order=canonical_parent_order,
            canonical_leaf_order=canonical_leaf_order,
            canonical_parents=canonical_parents,
            canonical_leaves=canonical_leaves,
        )
        scope = _mapping(
            scopes["all_constructed"],
            f"event {event_id} all_constructed scope is invalid",
        )
        matrix, source, included, excluded, exclusions = _validate_scope_matrix(
            scope,
            event_id=event_id,
            parent_order=parent_order,
            leaf_order=leaf_order,
        )
        observed_parent_ids.update(parent_order)
        observed_leaf_ids.update(leaf_order)
        validated.append(
            {
                "event_id": event_id,
                "event_name": event_name,
                "parent_order": parent_order,
                "leaf_order": leaf_order,
                "matrix": matrix,
                "source": source,
                "included": included,
                "excluded": excluded,
                "exclusions": exclusions,
                "schema_version": schema_version,
            }
        )

    parent_order = [
        identity_id
        for identity_id in canonical_parent_order
        if identity_id in observed_parent_ids
    ]
    leaf_order = [
        identity_id for identity_id in canonical_leaf_order if identity_id in observed_leaf_ids
    ]
    leaf_to_parent = {
        leaf_id: str(canonical_leaves[leaf_id]["parent_id"]) for leaf_id in leaf_order
    }
    leaf_matrix = _blank_matrix(leaf_order)
    leaf_contributors = _blank_contributors(leaf_order)
    source_match_count = 0
    included_match_count = 0
    excluded_match_count = 0
    excluded_match_counts: defaultdict[str, int] = defaultdict(int)

    for event in validated:
        event_id = str(event["event_id"])
        source_match_count += int(event["source"])
        included_match_count += int(event["included"])
        excluded_match_count += int(event["excluded"])
        for key, value in event["exclusions"].items():
            excluded_match_counts[key] += int(value)
        for row_id in event["leaf_order"]:
            for column_id in event["leaf_order"]:
                cell = event["matrix"][row_id][column_id]
                target = leaf_matrix[row_id][column_id]
                for field in COUNT_FIELDS:
                    target[field] += cell[field]
                if any(cell[field] for field in COUNT_FIELDS):
                    leaf_contributors[row_id][column_id].add(event_id)

    observations = sum(
        sum(cell.values())
        for columns in leaf_matrix.values()
        for cell in columns.values()
    )
    if observations != 2 * included_match_count:
        _fail(
            "matrix_invariant_failed",
            "combined leaf observations do not conserve physical matches",
        )
    parent_matrix, parent_contributors = _roll_up(
        leaf_matrix,
        leaf_contributors,
        parent_order=parent_order,
        leaf_order=leaf_order,
        leaf_to_parent=leaf_to_parent,
    )
    parent_observations = sum(
        sum(cell.values())
        for columns in parent_matrix.values()
        for cell in columns.values()
    )
    if parent_observations != observations:
        _fail(
            "matrix_invariant_failed",
            "combined parent roll-up does not reconcile with leaf counts",
        )

    event_ids = [str(event["event_id"]) for event in validated]
    return {
        "document_type": "multi_event_matchup",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": format_id,
        "scope": "all_constructed",
        "event_ids": event_ids,
        "event_names": [str(event["event_name"]) for event in validated],
        "compatibility": {
            "matchup_schema_version": validated[0]["schema_version"],
            "taxonomy_schema_version": taxonomy_version,
            "taxonomy_sha256": taxonomy_digest,
        },
        "rate_method": {
            "literal_win_rate_method": "wins_over_valid_matches",
            "confidence_interval": "wilson_95",
            "low_sample_threshold": LOW_SAMPLE_THRESHOLD,
        },
        "hierarchy": _result_hierarchy(
            parent_order,
            leaf_order,
            canonical_parents,
            canonical_leaves,
        ),
        "source_match_count": source_match_count,
        "included_match_count": included_match_count,
        "excluded_match_count": excluded_match_count,
        "directed_observation_count": observations,
        "excluded_match_counts": {
            key: excluded_match_counts[key] for key in sorted(excluded_match_counts)
        },
        "parent_order": parent_order,
        "parent_overall": _emit_overall(
            parent_matrix,
            parent_contributors,
            parent_order,
        ),
        "parent_matrix": _emit_matrix(
            parent_matrix,
            parent_contributors,
            parent_order,
        ),
        "leaf_order": leaf_order,
        "leaf_overall": _emit_overall(
            leaf_matrix,
            leaf_contributors,
            leaf_order,
        ),
        "leaf_matrix": _emit_matrix(
            leaf_matrix,
            leaf_contributors,
            leaf_order,
        ),
    }
