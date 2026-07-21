"""Read-only MTGO classification audits for executable or planned formats."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..config import FormatConfigError, load_rule_set
from ..reports import build_classification_reports, find_identity_fields
from . import load_mtgo_event_collection_context


class MTGOClassificationAuditError(ValueError):
    """Raised when a read-only classification audit cannot run safely."""


@dataclass(frozen=True)
class ExcludedMTGOEvent:
    source_file: str
    actual_format: str
    expected_format: str
    reason: str = "embedded_format_mismatch"


@dataclass(frozen=True)
class MTGOClassificationAudit:
    format_id: str
    expected_event_format: str
    event_directory: Path
    rule_path: Path
    included_event_count: int
    excluded_events: tuple[ExcludedMTGOEvent, ...]
    reports: Mapping[str, Mapping[str, Any]]


def mtgo_event_format(format_id: str) -> str:
    """Return the normalized MTGO event-format marker for a project format ID."""

    return f"C{format_id.upper()}"


def load_mtgo_events_for_format(
    paths: Iterable[Path],
    repository_root: str | Path,
    format_id: str,
) -> tuple[list[tuple[str, Mapping[str, Any]]], tuple[ExcludedMTGOEvent, ...]]:
    """Load only events whose embedded MTGO format matches the requested format."""

    root = Path(repository_root).resolve()
    expected = mtgo_event_format(format_id)
    included: list[tuple[str, Mapping[str, Any]]] = []
    excluded: list[ExcludedMTGOEvent] = []
    for path in sorted(paths):
        resolved = path.resolve()
        try:
            source_file = resolved.relative_to(root).as_posix()
        except ValueError as exc:
            raise MTGOClassificationAuditError(
                f"event path escapes repository root: {path}"
            ) from exc
        try:
            value = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MTGOClassificationAuditError(
                f"{source_file}: cannot read a valid event object ({type(exc).__name__})"
            ) from exc
        if not isinstance(value, Mapping):
            raise MTGOClassificationAuditError(f"{source_file}: event root must be an object")
        actual = value.get("format")
        if not isinstance(actual, str) or not actual:
            raise MTGOClassificationAuditError(
                f"{source_file}: embedded event format must be a non-empty string"
            )
        if actual != expected:
            excluded.append(
                ExcludedMTGOEvent(
                    source_file=source_file,
                    actual_format=actual,
                    expected_format=expected,
                )
            )
            continue
        included.append((source_file, value))
    return included, tuple(excluded)


def audit_mtgo_classification(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
) -> MTGOClassificationAudit:
    """Build de-identified diagnostics in memory without enabling product output."""

    context = load_mtgo_event_collection_context(
        repository_root,
        format_id,
        registry_path=registry_path,
    )
    rule_path = context.paths["rules"]
    rule_set = load_rule_set(rule_path)
    if rule_set.format != format_id:
        raise FormatConfigError(
            f"classification rules declare {rule_set.format!r}, expected {format_id!r}"
        )
    event_directory = context.paths["events"]
    paths = sorted(event_directory.glob("*.json"))
    if not paths:
        raise MTGOClassificationAuditError(
            f"no event files found for classification audit in {event_directory}"
        )
    events, excluded = load_mtgo_events_for_format(paths, context.repository_root, format_id)
    if not events:
        raise MTGOClassificationAuditError(
            f"no {mtgo_event_format(format_id)} event files found in {event_directory}"
        )
    reports = build_classification_reports(
        events,
        rule_set,
        format_id=format_id,
        source="mtgo",
    )
    identity_fields = find_identity_fields(reports)
    if identity_fields:
        raise MTGOClassificationAuditError(
            "forbidden identity fields found: " + ", ".join(identity_fields)
        )
    return MTGOClassificationAudit(
        format_id=format_id,
        expected_event_format=mtgo_event_format(format_id),
        event_directory=event_directory,
        rule_path=rule_path,
        included_event_count=len(events),
        excluded_events=excluded,
        reports=reports,
    )


__all__ = [
    "ExcludedMTGOEvent",
    "MTGOClassificationAudit",
    "MTGOClassificationAuditError",
    "audit_mtgo_classification",
    "load_mtgo_events_for_format",
    "mtgo_event_format",
]
