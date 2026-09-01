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
