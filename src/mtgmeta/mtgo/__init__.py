"""Format-aware MTGO pipeline primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import DisabledFormatError, FormatDefinition, load_format_registry


DEFAULT_REGISTRY_PATH = Path("configs/formats.yaml")


@dataclass(frozen=True)
class MTGOFormatContext:
    repository_root: Path
    definition: FormatDefinition
    paths: dict[str, Path]


def load_mtgo_context(
    repository_root: str | Path,
    format_id: str,
    capability: str,
    *,
    registry_path: str | Path | None = None,
) -> MTGOFormatContext:
    """Resolve one explicitly selected, executable MTGO format and capability."""

    root = Path(repository_root).resolve()
    source = Path(registry_path) if registry_path is not None else root / DEFAULT_REGISTRY_PATH
    definition = load_format_registry(source).require_mtgo(format_id)
    if capability not in definition.mtgo.capabilities:
        raise DisabledFormatError(f"MTGO format {format_id!r} does not support {capability!r}")
    return MTGOFormatContext(
        repository_root=root,
        definition=definition,
        paths=definition.mtgo.paths.resolve(root),
    )


def load_mtgo_event_collection_context(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
) -> MTGOFormatContext:
    """Resolve a format authorized only for raw MTGO event collection."""

    root = Path(repository_root).resolve()
    source = Path(registry_path) if registry_path is not None else root / DEFAULT_REGISTRY_PATH
    definition = load_format_registry(source).require_mtgo_event_collection(format_id)
    return MTGOFormatContext(
        repository_root=root,
        definition=definition,
        paths=definition.mtgo.paths.resolve(root),
    )


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "MTGOFormatContext",
    "load_mtgo_context",
    "load_mtgo_event_collection_context",
]


from .classification import (  # noqa: E402  (context functions must exist first)
    ExcludedMTGOEvent,
    MTGOClassificationAudit,
    MTGOClassificationAuditError,
    audit_mtgo_classification,
    load_mtgo_events_for_format,
    mtgo_event_format,
)

__all__ += [
    "ExcludedMTGOEvent",
    "MTGOClassificationAudit",
    "MTGOClassificationAuditError",
    "audit_mtgo_classification",
    "load_mtgo_events_for_format",
    "mtgo_event_format",
]
