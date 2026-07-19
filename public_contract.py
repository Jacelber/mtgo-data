"""Shared constants and helpers for versioned public JSON output."""

from __future__ import annotations

from typing import Any


PUBLIC_SCHEMA_VERSION = "1.0.0"


def versioned(document: dict[str, Any]) -> dict[str, Any]:
    """Return a public document with the compatibility version first."""
    if "schema_version" in document:
        raise ValueError("public document already contains schema_version")
    return {"schema_version": PUBLIC_SCHEMA_VERSION, **document}
