"""P10-04 minimized-resource Schema and supplemental scan tests."""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

from mtgmeta.melee.privacy_validation import (
    MeleeResourceValidationError,
    scan_prohibited_resource_keys,
    validate_minimized_resource,
)


REF = "melee-v3-" + "a" * 64
DECKLIST_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def documents():
    return {
        "tournament": {
            "schema_version": "1.0.0",
            "resource_type": "tournament",
            "tournament": {"source_event_id": "434455", "name": "Fixture Event"},
            "rounds": [{"source_round_id": "101", "label": "Round 1", "number": 1}],
        },
        "standings": {
            "schema_version": "1.0.0",
            "resource_type": "standings",
            "records_total": 1,
            "standings": [{
                "source_standing_id": "7",
                "participant_ref": REF,
                "display_name": "Alpha",
                "rank": 1,
                "match_points": 3,
            }],
            "decklist_references": [{
                "source_decklist_id": DECKLIST_ID,
                "participant_ref": REF,
                "url": f"https://melee.gg/Decklist/GetDecklistDetails?id={DECKLIST_ID}",
            }],
        },
        "matches": {
            "schema_version": "1.0.0",
            "resource_type": "matches",
            "records_total": 1,
            "matches": [{
                "source_match_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "source_round_id": "101",
                "competitors": [{"participant_ref": REF, "match_points": 3}],
                "table_number": 1,
            }],
        },
        "decklist": {
            "schema_version": "1.0.0",
            "resource_type": "decklist",
            "decklists": [{
                "source_decklist_id": DECKLIST_ID,
                "participant_ref": REF,
                "format_text": "Modern",
                "cards": [{"name": "Fixture Card", "quantity": 4, "section_text": "Main Deck"}],
            }],
        },
    }


def test_schema_accepts_every_minimized_resource_family(documents):
    for resource_type, document in documents.items():
        validate_minimized_resource(document, context=resource_type)


@pytest.mark.parametrize("resource_type", ["tournament", "standings", "matches", "decklist"])
def test_schema_rejects_unknown_top_level_fields(documents, resource_type):
    document = deepcopy(documents[resource_type])
    document["unexpected"] = True
    with pytest.raises(MeleeResourceValidationError, match="Schema validation failed"):
        validate_minimized_resource(document)


def test_schema_rejects_unknown_nested_fields_and_invalid_participant_refs(documents):
    document = deepcopy(documents["standings"])
    document["standings"][0]["unexpected"] = True
    with pytest.raises(MeleeResourceValidationError, match="Schema validation failed"):
        validate_minimized_resource(document)

    document = deepcopy(documents["standings"])
    document["standings"][0]["participant_ref"] = "enumerable-source-id"
    with pytest.raises(MeleeResourceValidationError, match="Schema validation failed"):
        validate_minimized_resource(document)


def test_supplemental_scan_checks_keys_not_values(documents):
    document = deepcopy(documents["decklist"])
    document["decklists"][0]["Username"] = "private-login"
    assert scan_prohibited_resource_keys(document) == ("$.decklists[0].Username",)

    document = deepcopy(documents["decklist"])
    document["decklists"][0]["cards"][0]["name"] = "Username"
    assert scan_prohibited_resource_keys(document) == ()
    validate_minimized_resource(document)


def test_supplemental_scan_remains_a_gate_if_a_future_schema_allows_a_bad_key(
    documents, tmp_path
):
    permissive_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    }
    schema_path = tmp_path / "permissive.schema.json"
    schema_path.write_text(json.dumps(permissive_schema), encoding="utf-8")
    document = deepcopy(documents["decklist"])
    document["decklists"][0]["Username"] = "private-login"

    with pytest.raises(MeleeResourceValidationError, match="prohibited persisted key"):
        validate_minimized_resource(document, schema_path=schema_path)


def test_schema_loading_fails_closed(documents, tmp_path):
    with pytest.raises(MeleeResourceValidationError, match="cannot load"):
        validate_minimized_resource(
            documents["tournament"], schema_path=tmp_path / "missing.schema.json"
        )
