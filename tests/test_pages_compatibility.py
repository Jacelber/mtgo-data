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


def test_current_event_projection_allows_classification_but_protects_facts():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "tests/fixtures/melee/434455_compatibility_manifest.json").read_bytes())
    projection = next(p for p in manifest["catalog_projections"] if p["role"] == "format_event_entry")
    document = {**projection["root_requirements"], "active_taxonomy": {"taxonomy_sha256": "a" * 64},
                "events": [{**deepcopy(projection["expected"]), "matchup_compatibility": {"taxonomy_sha256": "a" * 64}, "quality_status": "pass"}]}
    _validate_catalog_projection(document, projection)
    document["events"][0]["name"] = "changed source identity"
    with pytest.raises(PublicationError, match="selected value changed"):
        _validate_catalog_projection(document, projection)


def test_fixed_reference_is_independent_of_current_products():
    import hashlib
    import zipfile
    root = Path(__file__).resolve().parents[1]
    live = json.loads((root / "tests/fixtures/melee/434455_compatibility_manifest.json").read_bytes())
    fixture = root / live["reference_fixture"]["path"]
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == live["reference_fixture"]["sha256"]
    with zipfile.ZipFile(fixture) as archive:
        reference = json.loads(archive.read("manifest.json"))
        for record in reference["exact_files"]:
            payload = archive.read(record["path"])
            assert len(payload) == record["bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        for projection in reference["catalog_projections"]:
            _validate_catalog_projection(json.loads(archive.read(projection["path"])), projection)
    assert [r["role"] for r in live["exact_files"]] == ["normalized_event"]
