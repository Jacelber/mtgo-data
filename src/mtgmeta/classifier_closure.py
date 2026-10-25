"""Inspect and restate classifier-derived artifacts from retained inputs."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from time import perf_counter
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
STAGE_DIRECTORY_ATTEMPTS = 8
STAGE_COPY_IGNORES = (
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "test-results",
    "playwright-report",
)



class ClassifierClosureError(RuntimeError):
    """Raised when classifier closure cannot be proved or materialized safely."""


class SchemaExecutionError(ClassifierClosureError):
    """Validation did not complete; not a business-data rejection."""


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
    construction = None
    if name in {"mtgo_statistics", "mtgo_top8"}:
        from .mtgo.stats import construction_digest
        construction = construction_digest()
    for path in paths:
        if not path.is_file():
            issues.append(f"missing:{_relative(root, path)}")
            continue
        try:
            document = _json_object(path)
            actual = document.get("classifier_digest")
        except ClassifierClosureError as exc:
            issues.append(f"invalid:{_relative(root, path)}:{exc}")
            continue
        if actual != desired:
            issues.append(f"stale:{_relative(root, path)}:{actual!r}")
        if construction is not None and document.get("construction_digest") != construction:
            issues.append(f"stale-construction:{_relative(root, path)}")
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


def _discover_completeness_paths(root: Path, format_id: str) -> list[Path]:
    base = root / "stats" / format_id / "mtgo" / "completeness"
    index_path = base / "index.json"
    paths = [index_path]
    if index_path.is_file():
        index = _json_object(index_path)
        for item in index.get("ranges", []):
            if isinstance(item, Mapping):
                paths.append(
                    _safe_relative(base, item.get("file"), label="completeness range")
                )
    return paths


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


def _retained_landing_is_bound(root: Path, format_id: str, document: Mapping[str, Any],
                               artifacts: Sequence[Path]) -> bool:
    """A data-only advance can retain the exact previously published week."""
    from .mtgo.publication import resolve_scope, week_monday
    try:
        scope = resolve_scope(root, format_id)
        week = document["week"]["id"]
        digest = document["classifier"]["digest"]
        files = document["data_files"]
        if (week_monday(week) >= scope.week
                or not digest
                or document["review_binding"]["classifier_digest"] != digest
                or set(files) != {"range", "environment_decks", "feature_decks", "completeness"}
                or not set(document["source_event_ids"]) <= scope.event_ids):
            return False
        base = root / "stats" / format_id / "mtgo"
        binding = _json_object(base / "meta.json")["publication"]["artifacts"]
        for relative in files.values():
            target = _safe_relative(base / "landing", relative, label="retained Landing")
            if target.parent != base / "landing" / "weeks" / week:
                return False
        return all(path.is_file() and binding.get(_relative(root, path)) == _sha256(path)
                   for path in artifacts)
    except (OSError, ValueError, KeyError, TypeError, ClassifierClosureError):
        return False


def _inspect_landing(root: Path, format_id: str, desired: str) -> dict[str, Any]:
    path = root / "stats" / format_id / "mtgo" / "landing" / "current.json"
    artifacts = [path]
    issues: list[str] = []
    if not path.is_file():
        issues.append("missing current Landing")
    else:
        try:
            document = _json_object(path)
            week = document.get("week", {}).get("id")
            if isinstance(week, str) and re.fullmatch(r"\d{4}-W\d{2}", week):
                artifacts.extend((path.parent / "features" / "index.json",
                                  path.parent / "features" / f"{week}.json"))
            artifacts.extend(
                path.parent / relative
                for relative in document.get("data_files", {}).values()
            )
            classifier = document.get("classifier")
            binding = document.get("review_binding")
            if _retained_landing_is_bound(root, format_id, document, artifacts):
                return _family("mtgo_landing", artifacts, root)
            if not isinstance(classifier, Mapping) or classifier.get("digest") != desired:
                issues.append("current Landing classifier subject is stale")
            if not isinstance(binding, Mapping) or binding.get("classifier_digest") != desired:
                issues.append("current Landing review binding is stale")
        except ClassifierClosureError as exc:
            issues.append(str(exc))
    return _family("mtgo_landing", artifacts, root, issues)


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


def _inspect_protected_melee_compatibility(root, format_id, event_id):
    """Protect retained source facts, independently of current classification."""
    from build_pages_artifact import PublicationError, validate_compatibility
    config = _json_object(root / "configs/pages_publication.json")
    paths = []
    invalid = []
    manifests = config.get("compatibility_manifests")
    if not isinstance(manifests, list):
        raise ClassifierClosureError("Pages publication config has no compatibility manifest list")
    for relative in manifests:
        path = _safe_relative(root, relative, label="compatibility manifest")
        manifest = _json_object(path)
        event = manifest.get("event", {})
        if event.get("format") != format_id or str(event.get("event_id")) != event_id:
            continue
        paths.append(path)
        # Source checks run before expensive generation. Catalog/consumer checks
        # run after generation, when their current derived inputs are complete.
        try:
            validate_compatibility(root, {"compatibility_manifests": [relative]},
                                   None, sources_only=True)
        except (PublicationError, OSError, ValueError) as exc:
            invalid.append(str(exc))
    return paths, [], invalid


def _inspect_melee(
    root: Path,
    format_id: str,
    desired: str,
    catalog_path: Path | None,
    *, event_ids: set[str] | None = None,
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
            if event_ids is not None and isinstance(entry, Mapping) and str(entry.get("event_id")) not in event_ids:
                continue
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
                if field == "overview":
                    from .melee.stats import EVENT_OVERVIEW_SCHEMA_VERSION
                    if document.get("schema_version") != EVENT_OVERVIEW_SCHEMA_VERSION:
                        issues.append(f"Melee event {event_id} overview contract is stale")
                if field == "matchup":
                    from .melee.matchup import MATCHUP_SCHEMA_VERSION
                    if document.get("schema_version") != MATCHUP_SCHEMA_VERSION:
                        issues.append(f"Melee event {event_id} matchup contract is stale")
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


def current_melee_sync(root: Path, format_id: str) -> list[dict[str, Any]]:
    """List stale current consumers; retained but unadmitted events stay private."""
    catalog = root / "stats" / format_id / "melee/index.json"
    if not catalog.is_file():
        return []
    desired = classifier_digest(load_rules_for_format(root, format_id))
    events = _json_object(catalog)["events"]
    ids = [str(item["event_id"]) for item in events]
    if len(ids) != len(set(ids)):
        raise ClassifierClosureError("duplicate current Melee event")
    result = []
    for event_id in ids:
        report = _inspect_melee(root, format_id, desired, catalog, event_ids={event_id})
        if report["state"] == INVALID:
            raise ClassifierClosureError("; ".join(report["issues"]))
        if report["state"] != CURRENT:
            result.append({"format": format_id, "event_id": event_id,
                           "steps": ["classification", "opportunities", "stats", "matchup", "publish"]})
    return result


def validate_current_melee(root: Path, format_id: str) -> dict[str, Any]:
    """Validate the complete current chain and the real combined consumer."""
    from .melee.multi_event_contract import build_multi_event_matchup_contract, _admit_event
    from .mtgo.matchup import build_matchup_hierarchy
    catalog_path = root / "stats" / format_id / "melee/index.json"
    if not catalog_path.is_file():
        return {"event_ids": []}
    desired = classifier_digest(load_rules_for_format(root, format_id))
    report = _inspect_melee(root, format_id, desired, catalog_path)
    if report["state"] != CURRENT:
        raise ClassifierClosureError("; ".join(report["issues"]))
    catalog = _json_object(catalog_path)
    inputs = [{name: _json_object(_safe_relative(catalog_path.parent, entry[name], label=name))
               for name in ("meta", "matchup")} for entry in catalog["events"]]
    if len(inputs) == 1:
        entry = catalog["events"][0]
        _admit_event(event_id=str(entry["event_id"]), event_name=entry["name"],
                     event_input=inputs[0], catalog_event=entry,
                     active_taxonomy=catalog["active_taxonomy"], format_id=format_id)
        return {"event_ids": [str(catalog["events"][0]["event_id"])], "classifier_digest": desired}
    hierarchy = build_matchup_hierarchy(load_rules_for_format(root, format_id))
    hierarchy["parents"].append({"id": "unknown", "name": "Unknown", "expandable": False, "subtype_ids": []})
    hierarchy["leaves"].append({"id": "unknown", "kind": "unknown", "name": "Unknown",
        "display_name": "Unknown", "parent_id": "unknown", "subtype_id": None})
    result = build_multi_event_matchup_contract(inputs, canonical_hierarchy=hierarchy, catalog=catalog)
    return {"event_ids": result["event_ids"], "classifier_digest": desired}


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
        publication_paths = [root / "stats" / format_id / "mtgo/meta.json"]
        publication_paths.extend(_discover_completeness_paths(root, format_id))
        families["mtgo_publication"] = _family(
            "mtgo_publication", publication_paths,
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


def _create_stage_directory(root: Path, prefix: str) -> Path:
    """Create an external stage without tempfile's unbounded permission retry."""

    resolved_root = root.resolve()
    candidates = (resolved_root.parent, Path(tempfile.gettempdir()).resolve())
    failures: list[str] = []
    seen: set[Path] = set()
    for parent in candidates:
        if parent in seen:
            continue
        seen.add(parent)
        if not parent.is_dir():
            failures.append(f"{parent}: not a directory")
            continue
        try:
            parent.relative_to(resolved_root)
        except ValueError:
            pass
        else:
            failures.append(f"{parent}: stage parent is inside the repository")
            continue
        for _attempt in range(STAGE_DIRECTORY_ATTEMPTS):
            stage = parent / f"{prefix}{secrets.token_hex(8)}"
            try:
                stage.mkdir(mode=0o700)
            except FileExistsError:
                continue
            except OSError as exc:
                failures.append(f"{parent}: {exc}")
                break
            return stage
        else:
            failures.append(
                f"{parent}: exhausted {STAGE_DIRECTORY_ATTEMPTS} name attempts"
            )
    raise ClassifierClosureError(
        "cannot create an external staging directory: " + "; ".join(failures)
    )


def _copy_repository_to_stage(root: Path, prefix: str) -> Path:
    stage = _create_stage_directory(root, prefix)
    try:
        shutil.copytree(
            root,
            stage,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*STAGE_COPY_IGNORES),
        )
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return stage


def _create_stage(root: Path, format_id: str) -> Path:
    return _copy_repository_to_stage(root, f"classifier-closure-{format_id}-")


def _report_phase(format_id: str, phase: str, started: float) -> None:
    print(
        json.dumps(
            {
                "format": format_id,
                "operation": "classifier-closure-progress",
                "phase": phase,
                "seconds": round(perf_counter() - started, 3),
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )


def _generate_melee(stage: Path, format_id: str, *, event_ids: set[str] | None = None) -> None:
    from .melee.classification import (
        build_classification_overlay_from_paths,
        classification_overlay_bytes,
        write_classification_overlay,
    )
    from .melee.matchup import build_event_matchup_from_paths, build_event_matchup_from_statistics
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

    from .generation_progress import GenerationProgress, COMMON, files, implementation
    progress = GenerationProgress(stage.with_name(stage.name + f".melee-{format_id}.progress.json"),
                                  {"root": str(stage.resolve()), "format": format_id})
    _entry, catalog_path = _catalog_format(stage, format_id)
    if catalog_path is None:
        return
    existing = _json_object(catalog_path)
    events = existing.get("events")
    if not isinstance(events, list) or not events:
        raise ClassifierClosureError("Melee catalog has no active events")
    current_ids = [str(item["event_id"]) for item in events if isinstance(item, Mapping)]
    rebuild = set(current_ids) if event_ids is None else event_ids
    merged_catalog: dict[str, Any] | None = None
    base = stage / "data" / format_id / "melee"
    taxonomy = stage / "my_archetypes" / f"{format_id}.yaml"
    registry = stage / "configs" / "melee_events.yaml"
    for event_id in current_ids:
        if event_id not in rebuild:
            retained = {**existing, "default_event_id": event_id,
                        "events": [item for item in events if str(item["event_id"]) == event_id]}
            merged_catalog = retained if merged_catalog is None else merge_event_catalog(merged_catalog, retained)
            continue
        event_path = base / "events" / f"{event_id}.json"
        classification_path = base / "classifications" / f"{event_id}.json"
        opportunity_path = base / "opportunities" / f"{event_id}.json"
        event_output = stage / "stats" / format_id / "melee" / "events" / event_id
        def classify():
            write_classification_overlay(classification_path, classification_overlay_bytes(
                build_classification_overlay_from_paths(event_path, taxonomy, stage)))
        def opportunities():
            write_opportunity_ledger(opportunity_path, opportunity_ledger_bytes(
                build_opportunity_ledger_from_paths(event_path, classification_path, stage)))
        generated_statistics = None
        def statistics():
            nonlocal generated_statistics
            generated_statistics = build_event_statistics_from_paths(
                event_path, classification_path, opportunity_path, taxonomy, stage)
            for name, document in generated_statistics.items():
                write_statistics_document(event_output / f"{name}.json", statistics_document_bytes(document))
        def matchups():
            document = (
                build_event_matchup_from_statistics(generated_statistics, opportunity_path)
                if generated_statistics is not None else
                build_event_matchup_from_paths(event_path, classification_path, opportunity_path, taxonomy, stage)
            )
            write_statistics_document(event_output / "matchup.json", statistics_document_bytes(document, compact=True))
        prefix = event_output.relative_to(stage).as_posix()
        shared = implementation(stage, COMMON + ["src/mtgmeta/melee/*.py", "src/mtgmeta/classifier_closure.py"])
        for name, inputs, outputs, producer in (
            ("classification", [event_path, taxonomy, registry], [classification_path.relative_to(stage).as_posix()], classify),
            ("opportunities", [event_path, classification_path], [opportunity_path.relative_to(stage).as_posix()], opportunities),
            ("statistics", [event_path, classification_path, opportunity_path, taxonomy],
             [prefix + "/" + name + ".json" for name in ("overview", "decks", "quality")], statistics),
            ("matchup", [event_path, classification_path, opportunity_path, taxonomy], [prefix + "/matchup.json"], matchups),
        ):
            progress.run(f"{event_id}/{name}", {"code": shared,
                "inputs": files(stage, [p.relative_to(stage).as_posix() for p in inputs]),
                "config": files(stage, ["configs/melee*.yaml"])}, stage, outputs, producer)
        def publish_event():
            publication = build_event_publication_from_paths(event_path, classification_path,
                opportunity_path, taxonomy, registry, stage)
            write_statistics_document(event_output / "meta.json", statistics_document_bytes(publication["meta"]))
            return publication["catalog"]
        catalog_fragment = progress.run(f"{event_id}/publication", {"code": shared,
            "inputs": files(stage, [p.relative_to(stage).as_posix() for p in
                (event_path, classification_path, opportunity_path, taxonomy, registry)]),
            "products": files(stage, [prefix + "/" + name + ".json" for name in ("overview", "decks", "quality", "matchup")])},
            stage, [prefix + "/meta.json"], publish_event, retain_result=True)
        merged_catalog = (
            dict(catalog_fragment)
            if merged_catalog is None
            else merge_event_catalog(merged_catalog, catalog_fragment)
        )
    assert merged_catalog is not None
    progress.run("catalog", {"catalog": merged_catalog,
        "code": implementation(stage, ["src/mtgmeta/melee/publish.py", "src/mtgmeta/melee/stats.py"])},
        stage, [catalog_path.relative_to(stage).as_posix()],
        lambda: write_statistics_document(catalog_path, statistics_document_bytes(merged_catalog)))
    validate_current_melee(stage, format_id)
    progress.validated()


def _build_staged_format(
    stage: Path,
    format_id: str,
    initial: Mapping[str, Any],
) -> None:
    from .classification_reports_cli import generate_reports
    from .mtgo import completeness, landing, landing_editorial, matchup, metadata, stats, top8

    families = initial["families"]
    current_meta = _json_object(stage / "stats" / format_id / "mtgo/meta.json")
    publication_stale = families.get("mtgo_publication", {}).get("state") != CURRENT
    if publication_stale or families["mtgo_statistics"]["state"] != CURRENT:
        stats.build_all_stats(stage, format_id)
    if publication_stale or families["mtgo_matchups"]["state"] != CURRENT:
        matchup.build_all_matchups(stage, format_id)
    if publication_stale or families["mtgo_top8"]["state"] != CURRENT:
        top8.build_all_top8(stage, format_id)
    if families["mtgo_hierarchy"]["state"] != CURRENT:
        metadata.generate_hierarchy_catalog(
            stage,
            format_id,
            rules_updated=current_meta["rules_updated"],
        )
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
                "BLOCKED_OWNER_REVIEW: Landing material or accepted result changed: "
                f"{result['status']}"
            )
    if families["melee"]["state"] != CURRENT:
        _generate_melee(stage, format_id)
    if publication_stale:
        completeness.build_all_completeness(stage, format_id)
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


def _allowed_refreshed_artifacts(
    initial: Mapping[str, Any], staged: Mapping[str, Any]
) -> set[str]:
    initial_families = initial["families"]
    staged_families = staged["families"]
    refreshed_families = {
        name
        for name, family in initial_families.items()
        if family["state"] != CURRENT
    }
    if initial_families.get("mtgo_publication", {}).get("state") != CURRENT:
        refreshed_families.update(
            {"mtgo_statistics", "mtgo_matchups", "mtgo_top8", "classification_reports"}
        )
    if refreshed_families:
        refreshed_families.add("mtgo_publication")
    return {
        path
        for name in refreshed_families
        for path in staged_families[name]["artifacts"]
    }


def _validate_staged_schemas(stage: Path, relative_paths: Sequence[str]) -> None:
    from validate_schemas import schema_timeout_seconds
    deadline = perf_counter() + schema_timeout_seconds()
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
        remaining = deadline - perf_counter()
        if remaining <= 0:
            raise SchemaExecutionError("schema validation operation timed out; stage retained")
        command.extend(("--timeout-seconds", str(remaining)))
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
                stdout=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise SchemaExecutionError(
                f"staged schema validation could not run: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stdout + (completed.stderr or "")).strip()
            error = SchemaExecutionError if completed.returncode == 2 else ClassifierClosureError
            raise error(
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


def _resume_stage(root: Path, resume_stage: str | Path) -> Path:
    stage = Path(resume_stage).resolve()
    if stage == root or stage.is_relative_to(root) or not stage.is_dir():
        raise ClassifierClosureError("resume stage must be an existing external directory")
    # Generator changes invalidate generation; schema-validator changes do not.
    for directory in ("src", "my_archetypes", "configs"):
        def source_bytes(base):
            return {p.relative_to(base).as_posix(): p.read_bytes()
                    for p in (base / directory).rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        if source_bytes(root) != source_bytes(stage):
            raise ClassifierClosureError(f"resume generation inputs changed: {directory}")
    for relative in ("requirements.txt", "pyproject.toml"):
        left, right = root / relative, stage / relative
        if (left.read_bytes() if left.exists() else None) != (right.read_bytes() if right.exists() else None):
            raise ClassifierClosureError(f"resume generation dependencies changed: {relative}")
    # Run the repaired validator from the current checkout on preserved files.
    for name in ("validate_schemas.py", "validate_output_invariants.py"):
        if (root / name).is_file():
            shutil.copy2(root / name, stage / name)
    # Validation dependencies may be repaired independently of generation.
    schema_root, schema_stage = root / "schemas", stage / "schemas"
    if schema_root.is_dir():
        for target in schema_stage.rglob("*"):
            if target.is_file() and not (schema_root / target.relative_to(schema_stage)).is_file():
                target.unlink()
        shutil.copytree(schema_root, schema_stage, dirs_exist_ok=True)
    return stage


def converge_format(
    repository_root: str | Path,
    format_id: str,
    *,
    execute: bool = False,
    resume_stage: str | Path | None = None,
) -> dict[str, Any]:
    """Stage one format completely, then optionally materialize it atomically."""

    root = Path(repository_root).resolve()
    phase_started = perf_counter()
    initial = inspect_format(root, format_id)
    _report_phase(format_id, "inspect", phase_started)
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
    phase_started = perf_counter()
    before_inputs = _protected_input_fingerprints(root, format_id)
    _report_phase(format_id, "fingerprint-inputs", phase_started)
    if resume_stage is not None:
        stage = _resume_stage(root, resume_stage)
    else:
        phase_started = perf_counter()
        try:
            stage = _create_stage(root, format_id)
        except (ClassifierClosureError, OSError) as exc:
            return {
                "format": format_id,
                "state": INVALID,
                "mode": "execute" if execute else "plan",
                "changed_paths": [],
                "stage": None,
                "issues": [str(exc)],
            }
        _report_phase(format_id, "copy-stage", phase_started)
        try:
            phase_started = perf_counter()
            _build_staged_format(stage, format_id, initial)
            _report_phase(format_id, "generate-stage", phase_started)
        except ClassifierClosureError as exc:
            _report_phase(format_id, "generate-stage-blocked", phase_started)
            state = BLOCKED_OWNER_REVIEW if str(exc).startswith("BLOCKED_OWNER_REVIEW:") else INVALID
            return {
                "format": format_id,
                "state": state,
                "mode": "execute" if execute else "plan",
                "changed_paths": [],
                "stage": str(stage),
                "issues": [str(exc)],
            }
        phase_started = perf_counter()
    after_inputs = _protected_input_fingerprints(stage, format_id)
    _report_phase(format_id, "verify-staged-inputs", phase_started)
    if before_inputs != after_inputs:
        return {
            "format": format_id,
            "state": INVALID,
            "mode": "execute" if execute else "plan",
            "changed_paths": [],
            "stage": str(stage),
            "issues": ["retained or Owner-reviewed input changed during staging"],
        }
    phase_started = perf_counter()
    staged = inspect_format(stage, format_id)
    _report_phase(format_id, "inspect-stage", phase_started)
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
    allowed = _allowed_refreshed_artifacts(initial, staged)
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
        phase_started = perf_counter()
        _validate_staged_schemas(stage, changed)
        _report_phase(format_id, "validate-staged-schemas", phase_started)
    except ClassifierClosureError as exc:
        return {
            "format": format_id,
            "state": "EXECUTION_FAILED" if isinstance(exc, SchemaExecutionError) else INVALID,
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
    if "EXECUTION_FAILED" in values:
        return 2
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
            command.add_argument("--resume-stage", type=Path)
            command.add_argument("--schema-timeout-seconds", type=float)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "converge":
        if args.resume_stage and len(args.formats) != 1:
            raise ValueError("resume stage requires exactly one format")
        if args.schema_timeout_seconds is not None:
            os.environ["MTGO_SCHEMA_TIMEOUT_SECONDS"] = str(args.schema_timeout_seconds)
    if args.command == "inspect":
        result = inspect_repository(root, args.formats)
        states = [item["state"] for item in result["formats"]]
    else:
        formats = [
            converge_format(root, format_id, execute=args.execute, resume_stage=args.resume_stage)
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
