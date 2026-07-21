"""Contracts for the separately authorized Melee ingestion pipeline.

Phase 5 starts with schemas and stored fixtures. Importing this package performs
no network access and does not authorize fetching or publication.
"""

WHITELIST_SCHEMA_VERSION = "3.0.0"
NORMALIZED_EVENT_SCHEMA_VERSION = "2.1.0"

from .config import (
    DisabledMeleeEventError,
    MeleeConfigError,
    MeleeEventDefinition,
    MeleeEventRegistry,
    MeleeRawRequestDefinition,
    MeleeMatchOverride,
    MeleeOverrideCompetitor,
    UnknownMeleeEventError,
    load_melee_event_registry,
)
from .parser import (
    MeleeSourceParseError,
    ParsedMeleeSnapshot,
    ParsedSourcePage,
    parse_raw_snapshot,
    parse_source_response,
)
from .assembler import (
    MeleeAssemblyError,
    assemble_parsed_snapshot,
    assemble_raw_snapshot,
)
from .normalize import (
    MeleeNormalizationError,
    normalize_parsed_snapshot,
    normalize_raw_snapshot,
)
from .quality import (
    MeleePublicationBlocked,
    MeleeQualityError,
    build_publication_payload,
    finalize_event_quality,
)

__all__ = [
    "WHITELIST_SCHEMA_VERSION",
    "NORMALIZED_EVENT_SCHEMA_VERSION",
    "DisabledMeleeEventError",
    "MeleeConfigError",
    "MeleeEventDefinition",
    "MeleeEventRegistry",
    "MeleeRawRequestDefinition",
    "MeleeMatchOverride",
    "MeleeOverrideCompetitor",
    "UnknownMeleeEventError",
    "load_melee_event_registry",
    "MeleeSourceParseError",
    "ParsedMeleeSnapshot",
    "ParsedSourcePage",
    "parse_raw_snapshot",
    "parse_source_response",
    "MeleeAssemblyError",
    "assemble_parsed_snapshot",
    "assemble_raw_snapshot",
    "MeleeNormalizationError",
    "normalize_parsed_snapshot",
    "normalize_raw_snapshot",
    "MeleePublicationBlocked",
    "MeleeQualityError",
    "build_publication_payload",
    "finalize_event_quality",
]
