from copy import deepcopy
import json
from pathlib import Path

import pytest

from build_pages_artifact import PublicationError, _validate_catalog_projection


PROJECTION = {
    "root_requirements": {"schema_version": "1.0.0"},
    "selection": [
        {"collection": "events", "field": "event_id", "equals": "434455"}
    ],
    "expected": {"event_id": "434455", "path": "events/434455/overview.json"},
    "expansion_policy": "allow_unselected_entries_and_volatile_root_fields",
}


def test_catalog_projection_allows_unrelated_growth():
    document = {
        "schema_version": "1.0.0",
        "generated_at": "volatile",
        "events": [
            PROJECTION["expected"],
            {"event_id": "441441", "path": "events/441441/overview.json"},
        ],
    }
    _validate_catalog_projection(document, PROJECTION)


@pytest.mark.parametrize(
    "document,projection",
    [
        ({"schema_version": "2.0.0", "events": [PROJECTION["expected"]]}, PROJECTION),
        ({"schema_version": "1.0.0", "events": []}, PROJECTION),
        (
            {"schema_version": "1.0.0", "events": [PROJECTION["expected"]] * 2},
            PROJECTION,
        ),
        (
            {"schema_version": "1.0.0", "events": [PROJECTION["expected"]]},
            {**PROJECTION, "expansion_policy": "undefined"},
        ),
    ],
)
def test_catalog_projection_rejects_drift_or_undefined_state(document, projection):
    with pytest.raises(PublicationError):
        _validate_catalog_projection(document, projection)


def test_protected_event_survives_an_unrelated_active_taxonomy_update():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "tests/fixtures/melee/434455_compatibility_manifest.json").read_bytes())
    projection = next(p for p in manifest["catalog_projections"] if p["role"] == "format_event_entry")
    document = {
        **projection["root_requirements"],
        "active_taxonomy": {
            "schema_version": "1.0.0",
            "taxonomy_schema_version": "1.1.0",
            "taxonomy_sha256": "a" * 64,
        },
        "events": [deepcopy(projection["expected"])],
    }
    _validate_catalog_projection(document, projection)
    document["events"][0]["matchup_compatibility"]["taxonomy_sha256"] = "a" * 64
    with pytest.raises(PublicationError, match="selected value changed"):
        _validate_catalog_projection(document, projection)
