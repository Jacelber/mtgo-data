"""Inspect and restate classifier-derived artifacts from retained inputs."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import yaml

from .catalog import complete_public_formats, resolve_complete_public_format
from .classifier import classifier_digest
from .mtgo.normalize import load_rules_for_format


CURRENT = "CURRENT"
STALE = "STALE_REGENERABLE"
BLOCKED_OWNER_REVIEW = "BLOCKED_OWNER_REVIEW"
INVALID = "INVALID"
FORMAT_STATES = {CURRENT, STALE, BLOCKED_OWNER_REVIEW, INVALID}
PROTECTED_MELEE_DERIVED_ROLES = frozenset(
    {
        "classification_overlay",
        "opportunity_ledger",
        "event_overview",
        "event_decks",
        "event_matchup",
        "event_quality",
        "event_meta",
    }
)


class ClassifierClosureError(RuntimeError):
    """Raised when classifier closure cannot be proved or materialized safely."""


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClassifierClosureError(f"{path}: cannot read JSON object") from exc
    if not isinstance(value, dict):
        raise ClassifierClosureError(f"{path}: JSON root must be an object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _safe_relative(root: Path, value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ClassifierClosureError(f"{label}: invalid repository-relative path")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ClassifierClosureError(f"{label}: path escapes repository root") from exc
    return candidate


def _family(
    name: str,
    artifacts: Iterable[Path],
    root: Path,
    issues: Iterable[str] = (),
    *,
    state: str | None = None,
) -> dict[str, Any]:
    issue_list = list(issues)
    resolved_state = state or (STALE if issue_list else CURRENT)
    if resolved_state not in FORMAT_STATES:
        raise AssertionError(f"unsupported closure state: {resolved_state}")
    return {
        "name": name,
        "state": resolved_state,
        "artifacts": sorted({_relative(root, path) for path in artifacts}),
        "issues": issue_list,
    }


def _direct_digest_family(
    root: Path,
    name: str,
    paths: Sequence[Path],
    desired: str,
) -> dict[str, Any]:
    issues: list[str] = []
    for path in paths:
        if not path.is_file():
            issues.append(f"missing:{_relative(root, path)}")
            continue
        try:
            actual = _json_object(path).get("classifier_digest")
        except ClassifierClosureError as exc:
            issues.append(f"invalid:{_relative(root, path)}:{exc}")
            continue
        if actual != desired:
            issues.append(f"stale:{_relative(root, path)}:{actual!r}")
    return _family(name, paths, root, issues)


def _discover_mtgo_paths(root: Path, format_id: str) -> dict[str, list[Path]]:
    base = root / "stats" / format_id / "mtgo"
    result: dict[str, list[Path]] = {
        "mtgo_statistics": [base / "index.json"],
        "mtgo_matchups": [base / "matchup_index.json"],
        "mtgo_top8": [base / "top8" / "index.json"],
        "mtgo_hierarchy": [base / "archetype_hierarchy.json"],
        "mtgo_landing": [base / "landing" / "current.json"],
    }
    if (base / "index.json").is_file():
        index = _json_object(base / "index.json")
        for item in index.get("ranges", []):
            if isinstance(item, Mapping):
                for field in ("file", "decks_file"):
                    result["mtgo_statistics"].append(
                        _safe_relative(base, item.get(field), label=f"statistics {field}")
                    )
    if (base / "matchup_index.json").is_file():
        index = _json_object(base / "matchup_index.json")
        for item in index.get("ranges", []):
            if isinstance(item, Mapping):
                result["mtgo_matchups"].append(
                    _safe_relative(base, item.get("file"), label="matchup range")
                )
    top8_base = base / "top8"
    if (top8_base / "index.json").is_file():
        index = _json_object(top8_base / "index.json")
        for item in index.get("weeks", []):
            if isinstance(item, Mapping):
                for field in ("file", "comparison_bases_file"):
                    result["mtgo_top8"].append(
                        _safe_relative(top8_base, item.get(field), label=f"Top 8 {field}")
                    )
    return result


def _inspect_names(root: Path, format_id: str) -> dict[str, Any]:
    from .mtgo.landing_editorial import (
        MTGOLandingEditorialError,
        build_public_name_contract,
    )

    path = root / "stats" / format_id / "archetype_names.json"
    try:
        expected = build_public_name_contract(root, format_id)
    except MTGOLandingEditorialError as exc:
        return _family(
            "public_archetype_names",
            [path],
            root,
            [str(exc)],
            state=BLOCKED_OWNER_REVIEW,
        )
    if not path.is_file():
        return _family(
            "public_archetype_names", [path], root, ["missing public projection"]
        )
    try:
        actual = _json_object(path)
    except ClassifierClosureError as exc:
        return _family("public_archetype_names", [path], root, [str(exc)])
    issues = [] if actual == expected else ["projection provenance or content is stale"]
    return _family("public_archetype_names", [path], root, issues)


def _inspect_reports(root: Path, format_id: str, desired: str) -> dict[str, Any]:
    base = root / "reports" / format_id / "mtgo"
    index_path = base / "index.json"
    paths = [index_path]
    issues: list[str] = []
    if index_path.is_file():
        try:
            index = _json_object(index_path)
            for value in index.get("files", []):
                paths.append(_safe_relative(base, value, label="classification report"))
        except ClassifierClosureError as exc:
            issues.append(str(exc))
    for path in paths:
        if not path.is_file():
            issues.append(f"missing:{_relative(root, path)}")
            continue
        try:
            actual = _json_object(path).get("classifier_digest")
        except ClassifierClosureError as exc:
            issues.append(str(exc))
            continue
        if actual != desired:
            issues.append(f"stale:{_relative(root, path)}:{actual!r}")
    return _family("classification_reports", paths, root, issues)


def _inspect_landing(root: Path, format_id: str, desired: str) -> dict[str, Any]:
    path = root / "stats" / format_id / "mtgo" / "landing" / "current.json"
    issues: list[str] = []
    if not path.is_file():
        issues.append("missing current Landing")
    else:
        try:
            document = _json_object(path)
            classifier = document.get("classifier")
            binding = document.get("review_binding")
            if not isinstance(classifier, Mapping) or classifier.get("digest") != desired:
                issues.append("current Landing classifier subject is stale")
            if not isinstance(binding, Mapping) or binding.get("classifier_digest") != desired:
                issues.append("current Landing review binding is stale")
        except ClassifierClosureError as exc:
            issues.append(str(exc))
    return _family("mtgo_landing", [path], root, issues)


def _enabled_melee_ids(root: Path, format_id: str) -> set[str]:
    path = root / "configs" / "melee_events.yaml"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ClassifierClosureError(f"{path}: cannot read Melee registry") from exc
    events = document.get("events") if isinstance(document, Mapping) else None
    if not isinstance(events, list):
        raise ClassifierClosureError(f"{path}: events must be an array")
    return {
        str(item["id"])
        for item in events
        if isinstance(item, Mapping)
        and item.get("format") == format_id
        and item.get("enabled") is True
        and item.get("review_status") == "verified"
        and item.get("tabletop") is True
    }


def _protected_record_matches(root: Path, record: Mapping[str, Any]) -> bool:
    path = _safe_relative(root, record.get("path"), label="protected record")
    expected_bytes = record.get("bytes")
    expected_sha = record.get("sha256")
    return (
        path.is_file()
        and isinstance(expected_bytes, int)
        and expected_bytes >= 0
        and isinstance(expected_sha, str)
        and path.stat().st_size == expected_bytes
        and _sha256(path) == expected_sha
    )


def _protected_projection_matches(root: Path, projection: Mapping[str, Any]) -> bool:
    if projection.get("expansion_policy") != (
        "allow_unselected_entries_and_volatile_root_fields"
    ):
        raise ClassifierClosureError("protected catalog projection policy is invalid")
    document = _json_object(
        _safe_relative(root, projection.get("path"), label="protected projection")
    )
    requirements = projection.get("root_requirements")
    selection = projection.get("selection")
    expected = projection.get("expected")
    if (
        not isinstance(requirements, Mapping)
        or not isinstance(selection, list)
        or not isinstance(expected, Mapping)
    ):
        raise ClassifierClosureError("protected catalog projection is malformed")
    if any(document.get(key) != value for key, value in requirements.items()):
        return False
    current: Mapping[str, Any] = document
    for step in selection:
        if not isinstance(step, Mapping):
            raise ClassifierClosureError("protected catalog selection is malformed")
        collection = current.get(step.get("collection"))
        if not isinstance(collection, list):
            return False
        matches = [
            item
            for item in collection
            if isinstance(item, Mapping)
            and item.get(step.get("field")) == step.get("equals")
        ]
        if len(matches) != 1:
            return False
        current = matches[0]
    return current == expected


def _inspect_protected_melee_compatibility(
    root: Path,
    format_id: str,
    event_id: str,
) -> tuple[list[Path], list[str], list[str]]:
    """Return manifest paths, Owner blockers, and invalid immutable inputs."""

    config_path = root / "configs" / "pages_publication.json"
    config = _json_object(config_path)
    manifest_values = config.get("compatibility_manifests")
    if not isinstance(manifest_values, list):
        raise ClassifierClosureError(
            "Pages publication config has no compatibility manifest list"
        )
    artifacts: list[Path] = []
    blockers: list[str] = []
    invalid: list[str] = []
    for value in manifest_values:
        manifest_path = _safe_relative(
            root, value, label="Pages compatibility manifest"
        )
        manifest = _json_object(manifest_path)
        event = manifest.get("event")
        if (
            not isinstance(event, Mapping)
            or event.get("format") != format_id
            or str(event.get("event_id") or "") != event_id
        ):
            continue
        artifacts.append(manifest_path)
        policy = manifest.get("migration_policy")
        if (
            not isinstance(policy, Mapping)
            or policy.get("exact_byte_change")
            != "separate_owner_approved_version_migration"
        ):
            invalid.append(
                f"Melee event {event_id} compatibility migration policy is invalid"
            )
            continue
        immutable = manifest.get("immutable_snapshot")
        immutable_record = (
            immutable.get("manifest") if isinstance(immutable, Mapping) else None
        )
        if not isinstance(immutable_record, Mapping) or not _protected_record_matches(
            root, immutable_record
        ):
            invalid.append(
                f"Melee event {event_id} immutable snapshot authority changed"
            )
        exact_files = manifest.get("exact_files")
        if not isinstance(exact_files, list):
            invalid.append(f"Melee event {event_id} exact-file authority is invalid")
        else:
            for record in exact_files:
                if not isinstance(record, Mapping):
                    invalid.append(
                        f"Melee event {event_id} exact-file authority is malformed"
                    )
                    continue
                if _protected_record_matches(root, record):
                    continue
                role = record.get("role")
                if role in PROTECTED_MELEE_DERIVED_ROLES:
                    blockers.append(
                        f"Melee event {event_id} protected {role} requires Owner-approved migration"
                    )
                else:
                    invalid.append(
                        f"Melee event {event_id} protected immutable {role} changed"
                    )
        projections = manifest.get("catalog_projections")
        if not isinstance(projections, list):
            invalid.append(
                f"Melee event {event_id} catalog projection authority is invalid"
            )
        else:
            for projection in projections:
                if not isinstance(projection, Mapping):
                    invalid.append(
                        f"Melee event {event_id} catalog projection is malformed"
                    )
                elif not _protected_projection_matches(root, projection):
                    blockers.append(
                        f"Melee event {event_id} protected catalog projection requires Owner-approved migration"
                    )
    return artifacts, blockers, invalid


def _inspect_melee(
    root: Path,
    format_id: str,
    desired: str,
    catalog_path: Path | None,
) -> dict[str, Any]:
    if catalog_path is None:
        return _family("melee", [], root)
    artifacts: list[Path] = [catalog_path]
    issues: list[str] = []
    owner_blockers: list[str] = []
    invalid_issues: list[str] = []
    if not catalog_path.is_file():
        return _family("melee", artifacts, root, ["missing Melee format catalog"])
    try:
        catalog = _json_object(catalog_path)
        catalog_events = catalog.get("events")
        if not isinstance(catalog_events, list) or not catalog_events:
            raise ClassifierClosureError("Melee catalog has no active events")
        enabled = _enabled_melee_ids(root, format_id)
        rules_path = root / "my_archetypes" / f"{format_id}.yaml"
        active_taxonomy = catalog.get("active_taxonomy")
        if (
            not isinstance(active_taxonomy, Mapping)
            or active_taxonomy.get("taxonomy_sha256") != _sha256(rules_path)
        ):
            issues.append("Melee active taxonomy does not match the current rule file")
        seen: set[str] = set()
        for entry in catalog_events:
            if not isinstance(entry, Mapping):
                issues.append("Melee catalog contains a non-object event")
                continue
            event_id = str(entry.get("event_id") or "")
            if not event_id or event_id in seen or event_id not in enabled:
                issues.append(f"Melee catalog event is not uniquely enabled:{event_id!r}")
                continue
            seen.add(event_id)
            event_path = root / "data" / format_id / "melee" / "events" / f"{event_id}.json"
            classification_path = (
                root / "data" / format_id / "melee" / "classifications" / f"{event_id}.json"
            )
            opportunity_path = (
                root / "data" / format_id / "melee" / "opportunities" / f"{event_id}.json"
            )
            artifacts.extend([classification_path, opportunity_path])
            if not all(path.is_file() for path in (event_path, classification_path, opportunity_path)):
                issues.append(f"Melee event {event_id} is missing retained or derived input")
                continue
            classification = _json_object(classification_path)
            classifier = classification.get("classifier")
            if not isinstance(classifier, Mapping) or classifier.get("digest") != desired:
                issues.append(f"Melee event {event_id} classifier subject is stale")
            classification_input = classification.get("input")
            if (
                not isinstance(classification_input, Mapping)
                or classification_input.get("event_sha256") != _sha256(event_path)
            ):
                issues.append(f"Melee event {event_id} classification input hash is stale")
            classification_sha = _sha256(classification_path)
            opportunity = _json_object(opportunity_path)
            opportunity_input = opportunity.get("input")
            if (
                not isinstance(opportunity_input, Mapping)
                or opportunity_input.get("classification_sha256") != classification_sha
                or opportunity_input.get("event_sha256") != _sha256(event_path)
            ):
                issues.append(f"Melee event {event_id} opportunity chain is stale")
            opportunity_sha = _sha256(opportunity_path)
            public_documents: dict[str, tuple[Path, dict[str, Any]]] = {}
            for field in ("meta", "overview", "decks", "matchup", "quality"):
                path = _safe_relative(
                    catalog_path.parent,
                    entry.get(field),
                    label=f"Melee event {event_id} {field}",
                )
                artifacts.append(path)
                if not path.is_file():
                    issues.append(f"Melee event {event_id} is missing {field}")
                    continue
                document = _json_object(path)
                public_documents[field] = (path, document)
                input_document = document.get("input")
                if (
                    not isinstance(input_document, Mapping)
                    or input_document.get("classification_sha256") != classification_sha
                    or input_document.get("opportunity_sha256") != opportunity_sha
                    or input_document.get("event_sha256") != _sha256(event_path)
                ):
                    issues.append(f"Melee event {event_id} {field} upstream chain is stale")
            meta_pair = public_documents.get("meta")
            if meta_pair is not None:
                outputs = meta_pair[1].get("outputs")
                if not isinstance(outputs, Mapping):
                    issues.append(f"Melee event {event_id} meta has no output descriptors")
                else:
                    for field in ("overview", "decks", "matchup", "quality"):
                        pair = public_documents.get(field)
                        descriptor = outputs.get(field)
                        if (
                            pair is None
                            or not isinstance(descriptor, Mapping)
                            or descriptor.get("sha256") != _sha256(pair[0])
                        ):
                            issues.append(
                                f"Melee event {event_id} {field} descriptor is stale"
                            )
            compatibility = entry.get("matchup_compatibility")
            matchup_pair = public_documents.get("matchup")
            if (
                matchup_pair is None
                or not isinstance(compatibility, Mapping)
                or compatibility.get("matchup_sha256") != _sha256(matchup_pair[0])
            ):
                issues.append(f"Melee event {event_id} catalog matchup evidence is stale")
            protected, blockers, invalid = _inspect_protected_melee_compatibility(
                root, format_id, event_id
            )
            artifacts.extend(protected)
            owner_blockers.extend(blockers)
            invalid_issues.extend(invalid)
    except ClassifierClosureError as exc:
        return _family("melee", artifacts, root, [str(exc)], state=INVALID)
    if invalid_issues:
        return _family(
            "melee",
            artifacts,
            root,
            [*invalid_issues, *owner_blockers, *issues],
            state=INVALID,
        )
    if owner_blockers:
        return _family(
            "melee",
            artifacts,
            root,
            [*owner_blockers, *issues],
            state=BLOCKED_OWNER_REVIEW,
        )
    return _family("melee", artifacts, root, issues)


def _catalog_format(root: Path, format_id: str) -> tuple[dict[str, Any], Path | None]:
    catalog_path = root / "stats" / "catalog.json"
    catalog = _json_object(catalog_path)
    formats = catalog.get("formats")
    if not isinstance(formats, list):
        raise ClassifierClosureError("stats/catalog.json has no format list")
    selected = next(
        (
            item
            for item in formats
            if isinstance(item, dict) and item.get("id") == format_id
        ),
        None,
    )
    if selected is None or selected.get("state") != "executable":
        raise ClassifierClosureError(f"format {format_id!r} is not a live executable format")
    products = selected.get("products")
    if not isinstance(products, list):
        raise ClassifierClosureError(f"format {format_id!r} has no product catalog")
    tabletop = next(
        (
            item
            for item in products
            if isinstance(item, Mapping)
            and item.get("id") == "tabletop-major-events"
        ),
        None,
    )
    tabletop_path = None
    if isinstance(tabletop, Mapping) and tabletop.get("available") is True:
        tabletop_path = _safe_relative(
            root, tabletop.get("path"), label=f"{format_id} Tabletop catalog"
        )
    return selected, tabletop_path


def inspect_format(repository_root: str | Path, format_id: str) -> dict[str, Any]:
    """Read provenance only; never classify retained inputs or write output."""

    root = Path(repository_root).resolve()
    try:
        resolve_complete_public_format(root, format_id)
        _catalog_format(root, format_id)
        desired = classifier_digest(load_rules_for_format(root, format_id))
        discovered = _discover_mtgo_paths(root, format_id)
        families = {
            name: _direct_digest_family(root, name, paths, desired)
            for name, paths in discovered.items()
            if name != "mtgo_landing"
        }
        families["mtgo_landing"] = _inspect_landing(root, format_id, desired)
        families["public_archetype_names"] = _inspect_names(root, format_id)
        families["classification_reports"] = _inspect_reports(
            root, format_id, desired
        )
        from .mtgo.publication import inspect_publication
        families["mtgo_publication"] = _family(
            "mtgo_publication", [root / "stats" / format_id / "mtgo/meta.json"],
            root, inspect_publication(root, format_id))
        _format_entry, tabletop_path = _catalog_format(root, format_id)
        families["melee"] = _inspect_melee(
            root, format_id, desired, tabletop_path
        )
    except (ClassifierClosureError, OSError, ValueError) as exc:
        return {
            "format": format_id,
            "desired_classifier_digest": None,
            "state": INVALID,
            "families": {},
            "issues": [str(exc)],
        }
    states = {family["state"] for family in families.values()}
    if INVALID in states:
        state = INVALID
    elif BLOCKED_OWNER_REVIEW in states:
        state = BLOCKED_OWNER_REVIEW
    elif STALE in states:
        state = STALE
    else:
        state = CURRENT
    return {
        "format": format_id,
        "desired_classifier_digest": desired,
        "state": state,
        "families": families,
        "issues": [],
    }


def discover_live_formats(repository_root: str | Path) -> list[str]:
    root = Path(repository_root).resolve()
    return sorted(definition.id for definition in complete_public_formats(root))


def inspect_repository(
    repository_root: str | Path,
    formats: Sequence[str] | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    selected = list(formats) if formats is not None else discover_live_formats(root)
    reports = [inspect_format(root, format_id) for format_id in selected]
    return {
        "operation": "inspect",
        "repository_root": str(root),
        "state": CURRENT if all(item["state"] == CURRENT for item in reports) else "NOT_CURRENT",
        "formats": reports,
    }


def _protected_input_fingerprints(root: Path, format_id: str) -> dict[str, str]:
    paths: set[Path] = {
        root / "configs" / "formats.yaml",
        root / "configs" / "melee_events.yaml",
        root / "configs" / "mtgo_archetype_names.yaml",
        root / "configs" / "mtgo_landing_visuals.yaml",
        root / "configs" / "mtgo_intentional_unknowns.yaml",
        root / "configs" / "mtgo_weekly_review_completions.yaml",
        root / "my_archetypes" / f"{format_id}.yaml",
    }
    paths.update((root / "data" / format_id).glob("*.json"))
    paths.update((root / "data" / format_id / "mtgo" / "matches").glob("*.json"))
    paths.update((root / "data" / format_id / "melee" / "events").glob("*.json"))
    review = root / "stats" / format_id / "mtgo" / "landing" / "review"
    if review.is_dir():
        paths.update(path for path in review.rglob("*") if path.is_file())
    return {
        _relative(root, path): _sha256(path)
        for path in sorted(paths)
        if path.is_file()
    }


def _create_stage(root: Path, format_id: str) -> Path:
    stage = Path(
        tempfile.mkdtemp(
            prefix=f"classifier-closure-{format_id}-",
            dir=root.parent,
        )
    )
    shutil.copytree(
        root,
        stage,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
    )
    return stage


def _generate_melee(stage: Path, format_id: str) -> None:
    from .melee.classification import (
        build_classification_overlay_from_paths,
        classification_overlay_bytes,
        write_classification_overlay,
    )
    from .melee.matchup import build_event_matchup_from_paths
    from .melee.opportunities import (
        build_opportunity_ledger_from_paths,
        opportunity_ledger_bytes,
        write_opportunity_ledger,
    )
    from .melee.publish import build_event_publication_from_paths, merge_event_catalog
    from .melee.stats import (
        build_event_statistics_from_paths,
        statistics_document_bytes,
        write_statistics_document,
    )

    _entry, catalog_path = _catalog_format(stage, format_id)
    if catalog_path is None:
        return
    existing = _json_object(catalog_path)
    events = existing.get("events")
    if not isinstance(events, list) or not events:
        raise ClassifierClosureError("Melee catalog has no active events")
    event_ids = [str(item["event_id"]) for item in events if isinstance(item, Mapping)]
    merged_catalog: dict[str, Any] | None = None
    base = stage / "data" / format_id / "melee"
    taxonomy = stage / "my_archetypes" / f"{format_id}.yaml"
    registry = stage / "configs" / "melee_events.yaml"
    for event_id in event_ids:
        event_path = base / "events" / f"{event_id}.json"
        classification_path = base / "classifications" / f"{event_id}.json"
        opportunity_path = base / "opportunities" / f"{event_id}.json"
        classification = build_classification_overlay_from_paths(
            event_path, taxonomy, stage
        )
        write_classification_overlay(
            classification_path, classification_overlay_bytes(classification)
        )
        opportunity = build_opportunity_ledger_from_paths(
            event_path, classification_path, stage
        )
        write_opportunity_ledger(
            opportunity_path, opportunity_ledger_bytes(opportunity)
        )
        statistics = build_event_statistics_from_paths(
            event_path, classification_path, opportunity_path, taxonomy, stage
        )
        event_output = stage / "stats" / format_id / "melee" / "events" / event_id
        for name, document in statistics.items():
            write_statistics_document(
                event_output / f"{name}.json", statistics_document_bytes(document)
            )
        matchup = build_event_matchup_from_paths(
            event_path, classification_path, opportunity_path, taxonomy, stage
        )
        write_statistics_document(
            event_output / "matchup.json", statistics_document_bytes(matchup)
        )
        publication = build_event_publication_from_paths(
            event_path,
            classification_path,
            opportunity_path,
            taxonomy,
            registry,
            stage,
        )
        write_statistics_document(
            event_output / "meta.json",
            statistics_document_bytes(publication["meta"]),
        )
        merged_catalog = (
            dict(publication["catalog"])
            if merged_catalog is None
            else merge_event_catalog(merged_catalog, publication["catalog"])
        )
    assert merged_catalog is not None
    write_statistics_document(
        catalog_path, statistics_document_bytes(merged_catalog)
    )


def _build_staged_format(
    stage: Path,
    format_id: str,
    initial: Mapping[str, Any],
) -> None:
    from .classification_reports_cli import generate_reports
    from .mtgo import completeness, landing, landing_editorial, matchup, metadata, stats, top8

    families = initial["families"]
    publication_stale = families.get("mtgo_publication", {}).get("state") != CURRENT
    if publication_stale or families["mtgo_statistics"]["state"] != CURRENT:
        stats.build_all_stats(stage, format_id)
    if publication_stale or families["mtgo_matchups"]["state"] != CURRENT:
        matchup.build_all_matchups(stage, format_id)
    if publication_stale or families["mtgo_top8"]["state"] != CURRENT:
        top8.build_all_top8(stage, format_id)
    if families["mtgo_hierarchy"]["state"] != CURRENT:
        metadata.generate_hierarchy_catalog(stage, format_id)
    if families["public_archetype_names"]["state"] != CURRENT:
        landing_editorial.generate_public_name_contract(stage, format_id)
    if publication_stale or families["classification_reports"]["state"] != CURRENT:
        generate_reports(stage, format_id)
    if families["mtgo_landing"]["state"] != CURRENT:
        result = landing.generate(
            stage,
            format_id,
            allow_classifier_restatement=True,
        )
        if result["status"] in {"stale_review_required", "summary_review_required"}:
            raise ClassifierClosureError(
                "BLOCKED_OWNER_REVIEW: Landing material or accepted result changed"
            )
    if families["melee"]["state"] != CURRENT:
        _generate_melee(stage, format_id)
    if publication_stale:
        completeness.build_all_completeness(stage, format_id)
    current_meta = _json_object(stage / "stats" / format_id / "mtgo/meta.json")
    metadata.generate_metadata(stage, format_id, rules_updated=current_meta["rules_updated"])


def _candidate_tree_paths(root: Path, format_id: str) -> set[str]:
    bases = (
        root / "stats" / format_id,
        root / "reports" / format_id / "mtgo",
        root / "data" / format_id / "melee" / "classifications",
        root / "data" / format_id / "melee" / "opportunities",
    )
    return {
        _relative(root, path)
        for base in bases
        if base.is_dir()
        for path in base.rglob("*")
        if path.is_file()
    }


def _changed_tree_paths(root: Path, stage: Path, format_id: str) -> list[str]:
    paths = _candidate_tree_paths(root, format_id) | _candidate_tree_paths(
        stage, format_id
    )
    changed = []
    for relative in sorted(paths):
        original = root / relative
        candidate = stage / relative
        if original.is_file() != candidate.is_file():
            changed.append(relative)
        elif original.is_file() and original.read_bytes() != candidate.read_bytes():
            changed.append(relative)
    return changed


def _validate_staged_schemas(stage: Path, relative_paths: Sequence[str]) -> None:
    environment = os.environ.copy()
    source_path = str(stage / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing else os.pathsep.join((source_path, existing))
    )
    internal = [
        path
        for path in relative_paths
        if path.startswith("data/")
        and (
            "/melee/classifications/" in path
            or "/melee/opportunities/" in path
        )
    ]
    public = [path for path in relative_paths if path not in internal]

    def validate(paths: Sequence[str], manifest: str | None = None) -> None:
        if not paths:
            return
        command = [
                sys.executable,
                "-B",
                str(stage / "validate_schemas.py"),
                "--root",
                str(stage),
            ]
        if manifest is not None:
            command.extend(("--manifest", manifest))
        for relative in paths:
            command.extend(("--path", relative))
        try:
            completed = subprocess.run(
                command,
                cwd=stage,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise ClassifierClosureError(
                f"staged schema validation could not run: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip()
            raise ClassifierClosureError(
                f"staged schema validation failed: {detail or completed.returncode}"
            )

    validate(public)
    validate(internal, "schemas/melee-data-manifest.json")


def _prepare_sibling(path: Path, payload: bytes, suffix: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=suffix
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _materialize_with_rollback(
    root: Path,
    stage: Path,
    relative_paths: Sequence[str],
    *,
    replace_file: Callable[[Path, Path], None] = os.replace,
    validate_final: Callable[[], None] | None = None,
) -> None:
    snapshots: dict[str, bytes | None] = {}
    candidates: dict[str, Path] = {}
    rollbacks: dict[str, Path | None] = {}
    exposed: list[str] = []
    try:
        for relative in relative_paths:
            target = root / relative
            candidate = stage / relative
            if not candidate.is_file():
                raise ClassifierClosureError(
                    f"format-atomic materialization does not permit deletion: {relative}"
                )
            original = target.read_bytes() if target.is_file() else None
            snapshots[relative] = original
            candidates[relative] = _prepare_sibling(
                target, candidate.read_bytes(), ".closure-candidate"
            )
            rollbacks[relative] = (
                _prepare_sibling(target, original, ".closure-rollback")
                if original is not None
                else None
            )
        for relative in relative_paths:
            target = root / relative
            replace_file(candidates[relative], target)
            exposed.append(relative)
        if validate_final is not None:
            validate_final()
    except BaseException as original_error:
        rollback_errors: list[str] = []
        for relative in reversed(exposed):
            target = root / relative
            rollback = rollbacks[relative]
            try:
                if rollback is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(rollback, target)
            except OSError as exc:
                rollback_errors.append(f"{relative}:{exc}")
        for relative, expected in snapshots.items():
            target = root / relative
            actual = target.read_bytes() if target.is_file() else None
            if actual != expected:
                rollback_errors.append(f"{relative}:restore verification failed")
        if rollback_errors:
            raise ClassifierClosureError(
                "format rollback failed: " + "; ".join(rollback_errors)
            ) from original_error
        raise ClassifierClosureError(
            f"format materialization failed and was rolled back: {original_error}"
        ) from original_error
    finally:
        for path in (*candidates.values(), *rollbacks.values()):
            if path is not None:
                path.unlink(missing_ok=True)


def converge_format(
    repository_root: str | Path,
    format_id: str,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    """Stage one format completely, then optionally materialize it atomically."""

    root = Path(repository_root).resolve()
    initial = inspect_format(root, format_id)
    if initial["state"] == CURRENT:
        return {
            "format": format_id,
            "state": CURRENT,
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": None,
        }
    if initial["state"] in {INVALID, BLOCKED_OWNER_REVIEW}:
        return {
            "format": format_id,
            "state": initial["state"],
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": None,
            "inspection": initial,
        }
    before_inputs = _protected_input_fingerprints(root, format_id)
    stage = _create_stage(root, format_id)
    try:
        _build_staged_format(stage, format_id, initial)
    except ClassifierClosureError as exc:
        state = BLOCKED_OWNER_REVIEW if str(exc).startswith("BLOCKED_OWNER_REVIEW:") else INVALID
        return {
            "format": format_id,
            "state": state,
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": str(stage),
            "issues": [str(exc)],
        }
    after_inputs = _protected_input_fingerprints(stage, format_id)
    if before_inputs != after_inputs:
        return {
            "format": format_id,
            "state": INVALID,
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": str(stage),
            "issues": ["retained or Owner-reviewed input changed during staging"],
        }
    staged = inspect_format(stage, format_id)
    if staged["state"] != CURRENT:
        return {
            "format": format_id,
            "state": staged["state"],
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": str(stage),
            "inspection": staged,
        }
    changed = _changed_tree_paths(root, stage, format_id)
    refreshed_families = {
        name
        for name, family in initial["families"].items()
        if family["state"] != CURRENT
    }
    allowed = {
        path
        for name in refreshed_families
        for path in staged["families"][name]["artifacts"]
    }
    unexpected = sorted(set(changed) - allowed)
    if unexpected:
        return {
            "format": format_id,
            "state": INVALID,
            "mode": "execute" if execute else "plan",
            "changed_paths": changed,
            "stage": str(stage),
            "issues": ["unexpected staged paths: " + ", ".join(unexpected)],
        }
    try:
        _validate_staged_schemas(stage, changed)
    except ClassifierClosureError as exc:
        return {
            "format": format_id,
            "state": INVALID,
            "mode": "execute" if execute else "plan",
            "changed_paths": changed,
            "stage": str(stage),
            "issues": [str(exc)],
        }
    if not execute:
        return {
            "format": format_id,
            "state": "STAGED_CURRENT",
            "mode": "plan",
            "changed_paths": changed,
            "stage": str(stage),
            "retained_input_count": len(before_inputs),
        }
    def validate_final() -> None:
        final = inspect_format(root, format_id)
        if final["state"] != CURRENT:
            raise ClassifierClosureError(
                f"post-materialization inspection failed for {format_id}: "
                f"{final['state']}"
            )

    _materialize_with_rollback(
        root,
        stage,
        changed,
        validate_final=validate_final,
    )
    return {
        "format": format_id,
        "state": CURRENT,
        "mode": "execute",
        "changed_paths": changed,
        "stage": str(stage),
        "retained_input_count": len(before_inputs),
    }


def _exit_code(states: Iterable[str]) -> int:
    values = set(states)
    if INVALID in values:
        return 1
    if BLOCKED_OWNER_REVIEW in values:
        return 2
    if STALE in values or "NOT_CURRENT" in values:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "converge"):
        command = commands.add_parser(name)
        command.add_argument("--format", dest="formats", action="append", required=True)
        if name == "converge":
            command.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "inspect":
        result = inspect_repository(root, args.formats)
        states = [item["state"] for item in result["formats"]]
    else:
        formats = [
            converge_format(root, format_id, execute=args.execute)
            for format_id in args.formats
        ]
        result = {
            "operation": "converge",
            "mode": "execute" if args.execute else "plan",
            "repository_root": str(root),
            "formats": formats,
        }
        states = [item["state"] for item in formats]
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return _exit_code(states)


if __name__ == "__main__":
    raise SystemExit(main())
