"""MTGO hierarchy and format-metadata generators."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from mtgmeta.classifier import classifier_digest
from mtgmeta.public_contract import versioned

from . import load_mtgo_context, matchup, stats
from .normalize import load_rules_for_format


SOURCE_ID = "mtgo"
MTGO_HIERARCHY_SCHEMA_VERSION = "1.1.0"


def rules_last_commit_iso(
    repository_root: str | Path,
    rules_file: str | Path,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> str | None:
    root = Path(repository_root).resolve()
    rules = Path(rules_file).resolve()
    try:
        relative = rules.relative_to(root).as_posix()
        result = runner(
            ["git", "log", "-1", "--format=%cI", "--", relative],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip()
        return value or None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def generate_hierarchy_catalog(
    repository_root: str | Path,
    format_id: str,
    *,
    rules_updated: str | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path:
    """Generate the complete maintained parent/subtype catalog for one format."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "catalog_generation",
        registry_path=registry_path,
    )
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
    if rules_updated is None:
        rules_updated = rules_last_commit_iso(
            context.repository_root,
            context.paths["rules"],
        )
    hierarchy = matchup.build_matchup_hierarchy(rules)
    parents = hierarchy["parents"]
    leaves = hierarchy["leaves"]
    document = versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "classifier_digest": classifier_digest(rules),
            "rules_updated": rules_updated,
            "summary": {
                "parents": len(parents),
                "leaves": len(leaves),
                "expandable_parents": sum(item["expandable"] for item in parents),
            },
            **hierarchy,
        },
        schema_version=MTGO_HIERARCHY_SCHEMA_VERSION,
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"]
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "archetype_hierarchy.json"
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def _matchup_coverage(
    context,
    *,
    registry_path: str | Path | None = None,
) -> dict[str, int]:
    events = stats.load_all_events(
        context.repository_root,
        context.definition.id,
        registry_path=registry_path,
    )
    official_ids = {
        str(event.get("event_id"))
        for _event_date, event in events
        if event.get("event_id") is not None
    }
    archive_ids: set[str] = set()
    for path in sorted(context.paths["matches"].glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        event_id = document.get("event_id")
        if event_id is not None:
            archive_ids.add(str(event_id))
    overlap = official_ids & archive_ids
    return {
        "official_events": len(official_ids),
        "events_with_archives": len(overlap),
        "events_without_archives": len(official_ids - archive_ids),
        "stored_archives": len(archive_ids),
        "archives_outside_official_events": len(archive_ids - official_ids),
    }


def generate_metadata(
    repository_root: str | Path,
    format_id: str,
    *,
    data_updated: datetime | str | None = None,
    rules_updated: str | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path:
    """Generate format-specific MTGO metadata after capability authorization."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "metadata_generation",
        registry_path=registry_path,
    )
    if rules_updated is None:
        rules_updated = rules_last_commit_iso(
            context.repository_root,
            context.paths["rules"],
        )
    if data_updated is None:
        data_updated_value = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elif isinstance(data_updated, datetime):
        data_updated_value = data_updated.isoformat(timespec="seconds")
    else:
        data_updated_value = data_updated
    document = versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "rules_updated": rules_updated,
            "data_updated": data_updated_value,
        }
    )
    document.update(
        {
            "statistics_catalog": "index.json",
            "matchup_catalog": "matchup_index.json",
            "hierarchy_catalog": "archetype_hierarchy.json",
            "top8_catalog": (
                "top8/index.json"
                if (context.paths["statistics"] / "top8" / "index.json").is_file()
                else None
            ),
            "completeness_catalog": (
                "completeness/index.json"
                if (
                    context.paths["statistics"] / "completeness" / "index.json"
                ).is_file()
                else None
            ),
            "pickup_catalog": None,
            "landing_document": (
                "landing/current.json"
                if (
                    context.paths["statistics"] / "landing" / "current.json"
                ).is_file()
                else None
            ),
            "landing_feature_catalog": (
                "landing/features/index.json"
                if (
                    context.paths["statistics"] / "landing" / "features" / "index.json"
                ).is_file()
                else None
            ),
            "matchup_source": "Videre",
            "matchup_coverage": _matchup_coverage(
                context,
                registry_path=registry_path,
            ),
        }
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"]
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "meta.json"
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


__all__ = [
    "generate_hierarchy_catalog",
    "generate_metadata",
    "rules_last_commit_iso",
]
