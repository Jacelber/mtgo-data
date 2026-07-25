"""P7-07 source-specific production candidate boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validate_melee_candidate import Change, validate_candidate


BASELINE = {
    "schema_version": "1.0.0",
    "event_id": "434455",
    "format": "modern",
    "head": "a" * 40,
}


def _json(path: Path, **updates: object) -> None:
    value = {"source": "melee", "format": "modern", "event_id": "434455"}
    value.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_exact_event_paths_and_new_raw_evidence_are_allowed(tmp_path):
    paths = [
        "data/modern/melee/events/434455.json",
        "data/modern/melee/classifications/434455.json",
        "data/modern/melee/opportunities/434455.json",
        "stats/modern/melee/events/434455/overview.json",
        "stats/modern/melee/events/434455/decks.json",
        "stats/modern/melee/events/434455/matchup.json",
        "stats/modern/melee/events/434455/quality.json",
        "stats/modern/melee/events/434455/meta.json",
    ]
    for path in paths:
        _json(tmp_path / path)
    catalog = tmp_path / "stats/modern/melee/index.json"
    _json(catalog, document_type="event_catalog")
    changes = [Change(" M", path) for path in paths]
    changes += [
        Change(" M", "stats/modern/melee/index.json"),
        Change("??", "data_raw/melee/434455/snapshot/manifest.json"),
    ]

    report, failures = validate_candidate(tmp_path, BASELINE, changes)
    assert failures == []
    assert report["changed_paths"] == 10


def test_cross_source_other_event_deletion_and_raw_mutation_fail(tmp_path):
    changes = [
        Change(" M", "stats/modern/mtgo/meta.json"),
        Change(" M", "stats/modern/melee/events/999999/meta.json"),
        Change(" D", "stats/modern/melee/events/434455/quality.json"),
        Change(" M", "data_raw/melee/434455/old/manifest.json"),
    ]
    _, failures = validate_candidate(tmp_path, BASELINE, changes)
    assert len(failures) == 4
    assert any("outside" in failure for failure in failures)
    assert any("deletion" in failure for failure in failures)
    assert any("immutable" in failure for failure in failures)


def test_changed_json_identity_fails_closed(tmp_path):
    path = "stats/modern/melee/events/434455/meta.json"
    _json(tmp_path / path, source="mtgo", format="standard", event_id="999999")
    _, failures = validate_candidate(tmp_path, BASELINE, [Change(" M", path)])
    assert len(failures) == 3
