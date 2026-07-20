"""Contracts for the separately authorized Melee ingestion pipeline.

Phase 5 starts with schemas and stored fixtures. Importing this package performs
no network access and does not authorize fetching or publication.
"""

WHITELIST_SCHEMA_VERSION = "1.0.0"
NORMALIZED_EVENT_SCHEMA_VERSION = "1.0.0"

__all__ = ["WHITELIST_SCHEMA_VERSION", "NORMALIZED_EVENT_SCHEMA_VERSION"]
