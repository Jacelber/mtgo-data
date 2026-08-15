"""Minimum pre-persistence Melee privacy boundary contract."""

from __future__ import annotations

import json

import pytest

from mtgmeta.melee.privacy_validation import (
    MeleeResourceValidationError,
    validate_minimized_resource,
)


def test_smallest_minimized_resource_is_schema_valid():
    validate_minimized_resource(
        {
            "schema_version": "1.0.0",
            "resource_type": "tournament",
            "tournament": {"source_event_id": "434455", "name": "Fixture"},
            "rounds": [],
        }
    )


def test_prohibited_key_remains_blocking_with_a_permissive_schema(tmp_path):
    schema_path = tmp_path / "permissive.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MeleeResourceValidationError, match="prohibited persisted key"):
        validate_minimized_resource(
            {"resource_type": "decklist", "Username": "private-login"},
            schema_path=schema_path,
        )
