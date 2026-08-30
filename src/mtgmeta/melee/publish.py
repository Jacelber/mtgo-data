"""Deterministic public packaging for one Tabletop Major Events event."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

from .config import MeleeConfigError, load_melee_event_registry
from .matchup import MeleeMatchupError, build_event_matchup_from_paths
from .stats import (
    MeleeStatisticsError,
    build_event_statistics_from_paths,
    statistics_document_bytes,
    write_statistics_document,
)


PUBLICATION_SCHEMA_VERSION = "1.0.0"
CATALOG_SCHEMA_VERSION = "1.2.0"
MATCHUP_COMPATIBILITY_SCHEMA_VERSION = "1.0.0"
ACTIVE_TAXONOMY_SCHEMA_VERSION = "1.0.0"
FORMAT_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
OUTPUT_NAMES = ("overview", "decks", "matchup", "quality")


class MeleePublicationError(ValueError):
    """Raised when deterministic event publication cannot be proven."""


def build_matchup_compatibility(
    *,
    format_id: str,
    input_document: Mapping[str, Any],
    quality: Mapping[str, Any],
    matchup_descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the minimum catalog evidence for multi-event admission."""

    taxonomy_version = input_document.get("taxonomy_schema_version")
    taxonomy_digest = input_document.get("taxonomy_sha256")
    matchup_version = matchup_descriptor.get("schema_version")
    matchup_digest = matchup_descriptor.get("sha256")
    if not isinstance(format_id, str) or not FORMAT_PATTERN.fullmatch(format_id):
        raise MeleePublicationError("matchup compatibility has an invalid format")
    if not isinstance(taxonomy_version, str) or not taxonomy_version:
        raise MeleePublicationError("matchup compatibility has no taxonomy version")
    if not isinstance(taxonomy_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", taxonomy_digest
    ):
        raise MeleePublicationError(
            "matchup compatibility has an invalid taxonomy digest"
        )
    if (
        matchup_descriptor.get("path") != "matchup.json"
        or not isinstance(matchup_version, str)
        or not matchup_version
    ):
        raise MeleePublicationError(
            "matchup compatibility has an invalid matchup descriptor"
        )
    if not isinstance(matchup_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", matchup_digest
    ):
        raise MeleePublicationError(
            "matchup compatibility has an invalid matchup digest"
        )
    if (
        quality.get("status") not in {"pass", "warning"}
        or quality.get("blocking") is not False
    ):
        raise MeleePublicationError(
            "matchup compatibility requires non-blocking quality"
        )
    return {
        "schema_version": MATCHUP_COMPATIBILITY_SCHEMA_VERSION,
        "source": "melee",
        "product": "tabletop-major-events",
        "format": format_id,
        "scope": "all_constructed",
        "matchup_schema_version": matchup_version,
        "matchup_sha256": matchup_digest,
        "taxonomy_schema_version": taxonomy_version,
        "taxonomy_sha256": taxonomy_digest,
        "quality_blocking": False,
    }


def build_active_taxonomy(
    *, format_id: str, input_document: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind a future format catalog to the maintained taxonomy used to build it."""

    taxonomy_version = input_document.get("taxonomy_schema_version")
    taxonomy_digest = input_document.get("taxonomy_sha256")
    if not isinstance(format_id, str) or not FORMAT_PATTERN.fullmatch(format_id):
        raise MeleePublicationError("active taxonomy has an invalid format")
    if not isinstance(taxonomy_version, str) or not taxonomy_version:
        raise MeleePublicationError("active taxonomy has no taxonomy version")
    if not isinstance(taxonomy_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", taxonomy_digest
    ):
        raise MeleePublicationError("active taxonomy has an invalid taxonomy digest")
    return {
        "schema_version": ACTIVE_TAXONOMY_SCHEMA_VERSION,
        "taxonomy_schema_version": taxonomy_version,
        "taxonomy_sha256": taxonomy_digest,
    }


def _read_object(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        document = json.loads(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MeleePublicationError(f"{path}: cannot read JSON object") from exc
    if not isinstance(document, dict):
        raise MeleePublicationError(f"{path}: must contain a JSON object")
    return document, payload


def _catalog_events(
    catalog: Mapping[str, Any], *, label: str
) -> tuple[list[Mapping[str, Any]], list[str]]:
    events = catalog.get("events")
    if not isinstance(events, list) or not events:
        raise MeleePublicationError(f"{label} catalog has no events")
    event_ids: list[str] = []
    for event in events:
        event_id = event.get("event_id") if isinstance(event, Mapping) else None
        if not isinstance(event_id, str) or not EVENT_ID_PATTERN.fullmatch(event_id):
            raise MeleePublicationError(f"{label} catalog has an invalid event")
        if event_id in event_ids:
            raise MeleePublicationError(
                f"{label} catalog has duplicate event {event_id}"
            )
        event_ids.append(event_id)
    return events, event_ids


def merge_event_catalog(
    existing_catalog: Mapping[str, Any],
    generated_catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge one generated event without changing the existing cohort selection."""

    identity_fields = ("document_type", "source", "product", "format")
    for field in identity_fields:
        if existing_catalog.get(field) != generated_catalog.get(field):
            raise MeleePublicationError(
                f"existing catalog {field} does not match generated catalog"
            )
    generated_events, generated_ids = _catalog_events(
        generated_catalog, label="generated"
    )
    if len(generated_events) != 1:
        raise MeleePublicationError("generated catalog must contain exactly one event")
    selected_id = generated_ids[0]
    if generated_catalog.get("default_event_id") != selected_id:
        raise MeleePublicationError("generated catalog has an invalid default event")

    existing_events, existing_ids = _catalog_events(existing_catalog, label="existing")
    existing_default = existing_catalog.get("default_event_id")
    if existing_default not in existing_ids:
        raise MeleePublicationError("existing catalog has an invalid default event")

    if existing_catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        if existing_ids == [selected_id] and existing_default == selected_id:
            return dict(generated_catalog)
        raise MeleePublicationError(
            "existing catalog requires a separate active-taxonomy migration "
            "before multi-event growth"
        )
    if existing_catalog.get("active_taxonomy") != generated_catalog.get(
        "active_taxonomy"
    ):
        raise MeleePublicationError(
            "generated event does not match the existing catalog active taxonomy"
        )

    selected_event = generated_events[0]
    merged_events: list[Mapping[str, Any]] = []
    replaced = False
    for event, event_id in zip(existing_events, existing_ids, strict=True):
        if event_id == selected_id:
            merged_events.append(selected_event)
            replaced = True
        else:
            merged_events.append(event)
    if not replaced:
        merged_events.append(selected_event)

    merged = dict(generated_catalog)
    merged["default_event_id"] = existing_default
    merged["events"] = merged_events
    return merged


def _descriptor(name: str, document: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    version = document.get("schema_version")
    if not isinstance(version, str) or not version:
        raise MeleePublicationError(f"{name}.json has no schema version")
    return {
        "path": f"{name}.json",
        "schema_version": version,
        "bytes": len(payload),
        "sha256": sha256(payload).hexdigest(),
    }


def _verified_outputs(
    event_directory: Path,
    rebuilt: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    documents: dict[str, dict[str, Any]] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for name in OUTPUT_NAMES:
        path = event_directory / f"{name}.json"
        document, payload = _read_object(path)
        expected = statistics_document_bytes(rebuilt[name])
        if payload != expected:
            raise MeleePublicationError(
                f"{path}: does not match deterministic rebuild"
            )
        documents[name] = document
        descriptors[name] = _descriptor(name, document, payload)
    return documents, descriptors


def _quality_summary(quality: Mapping[str, Any]) -> dict[str, Any]:
    status = quality.get("status")
    blocking = quality.get("blocking")
    issues = quality.get("issues")
    if status not in {"ready", "warning"} or blocking is not False or not isinstance(
        issues, list
    ):
        raise MeleePublicationError("quality output is not publication-eligible")
    issue_codes: list[str] = []
    for issue in issues:
        code = issue.get("code") if isinstance(issue, Mapping) else None
        if not isinstance(code, str) or not code:
            raise MeleePublicationError("quality output has an invalid issue")
        issue_codes.append(code)
    if len(issue_codes) != len(set(issue_codes)):
        raise MeleePublicationError("quality output has duplicate issue codes")
    return {
        "status": "pass" if status == "ready" else status,
        "blocking": False,
        "issue_codes": issue_codes,
    }


def build_event_publication_from_paths(
    event_path: Path,
    classification_path: Path,
    opportunity_path: Path,
    taxonomy_path: Path,
    registry_path: Path,
    repository_root: Path,
) -> dict[str, dict[str, Any]]:
    """Build deterministic event metadata and its format catalog."""

    root = repository_root.resolve()
    statistics = build_event_statistics_from_paths(
        event_path,
        classification_path,
        opportunity_path,
        taxonomy_path,
        root,
    )
    matchup = build_event_matchup_from_paths(
        event_path,
        classification_path,
        opportunity_path,
        taxonomy_path,
        root,
    )
    overview = statistics["overview"]
    event_id = overview.get("event_id")
    format_id = overview.get("format")
    if not isinstance(event_id, str) or not isinstance(format_id, str):
        raise MeleePublicationError("rebuilt overview has no event identity")
    event_definition = load_melee_event_registry(registry_path).require_fetchable(
        event_id
    )
    if (
        event_definition.format != format_id
        or event_definition.structure != overview.get("event_structure")
    ):
        raise MeleePublicationError("whitelist identity does not match event output")

    event_directory = root / "stats" / format_id / "melee" / "events" / event_id
    rebuilt = {**statistics, "matchup": matchup}
    documents, descriptors = _verified_outputs(event_directory, rebuilt)
    event = overview.get("event")
    input_document = overview.get("input")
    if not isinstance(event, Mapping) or not isinstance(input_document, Mapping):
        raise MeleePublicationError("rebuilt overview metadata is incomplete")
    for name, document in documents.items():
        if (
            document.get("event_id") != event_id
            or document.get("format") != format_id
            or document.get("source") != "melee"
            or document.get("input") != input_document
        ):
            raise MeleePublicationError(f"{name}.json identity is inconsistent")

    quality = _quality_summary(documents["quality"])
    meta = {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "document_type": "meta",
        "source": "melee",
        "product": "tabletop-major-events",
        "event_id": event_id,
        "format": format_id,
        "event_structure": overview["event_structure"],
        "event": dict(event),
        "input": dict(input_document),
        "scope_order": list(overview["scope_order"]),
        "default_scope": overview["default_scope"],
        "quality": quality,
        "outputs": descriptors,
    }
    prefix = f"events/{event_id}"
    catalog_event = {
        "event_id": event_id,
        "name": event["name"],
        "series": event["series"],
        "date": dict(event["date"]),
        "event_structure": overview["event_structure"],
        "source_url": event["source_url"],
        "meta": f"{prefix}/meta.json",
        "overview": f"{prefix}/overview.json",
        "decks": f"{prefix}/decks.json",
        "matchup": f"{prefix}/matchup.json",
        "quality": f"{prefix}/quality.json",
        "scope_order": list(overview["scope_order"]),
        "default_scope": overview["default_scope"],
        "quality_status": quality["status"],
        "matchup_compatibility": build_matchup_compatibility(
            format_id=format_id,
            input_document=input_document,
            quality=quality,
            matchup_descriptor=descriptors["matchup"],
        ),
    }
    catalog = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "document_type": "event_catalog",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": format_id,
        "active_taxonomy": build_active_taxonomy(
            format_id=format_id,
            input_document=input_document,
        ),
        "default_event_id": event_id,
        "events": [catalog_event],
    }
    return {"meta": meta, "catalog": catalog}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package one verified Melee event for public discovery."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", required=True, dest="format_id")
    parser.add_argument("--event-id", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="atomically write meta.json and index.json; default mode is read-only",
    )
    args = parser.parse_args(argv)
    if not FORMAT_PATTERN.fullmatch(args.format_id):
        parser.error("--format must be a lowercase hyphenated identifier")
    if not EVENT_ID_PATTERN.fullmatch(args.event_id):
        parser.error("--event-id must be a positive numeric identifier")

    root = args.root.resolve()
    base = root / "data" / args.format_id / "melee"
    try:
        publication = build_event_publication_from_paths(
            base / "events" / f"{args.event_id}.json",
            base / "classifications" / f"{args.event_id}.json",
            base / "opportunities" / f"{args.event_id}.json",
            root / "my_archetypes" / f"{args.format_id}.yaml",
            root / "configs" / "melee_events.yaml",
            root,
        )
        event_directory = (
            root
            / "stats"
            / args.format_id
            / "melee"
            / "events"
            / args.event_id
        )
        destinations = {
            "meta": event_directory / "meta.json",
            "catalog": root / "stats" / args.format_id / "melee" / "index.json",
        }
        if destinations["catalog"].is_file():
            existing_catalog, _ = _read_object(destinations["catalog"])
            publication["catalog"] = merge_event_catalog(
                existing_catalog,
                publication["catalog"],
            )
        reused = None
        if args.execute:
            reused = {
                name: write_statistics_document(
                    destinations[name],
                    statistics_document_bytes(publication[name]),
                )
                for name in ("meta", "catalog")
            }
        print(
            json.dumps(
                {
                    "event_id": args.event_id,
                    "format": args.format_id,
                    "mode": "execute" if args.execute else "dry-run",
                    "outputs": (
                        {
                            name: destinations[name].relative_to(root).as_posix()
                            for name in ("meta", "catalog")
                        }
                        if args.execute
                        else {}
                    ),
                    "reused": reused,
                },
                sort_keys=True,
            )
        )
    except (
        MeleeConfigError,
        MeleeMatchupError,
        MeleePublicationError,
        MeleeStatisticsError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
