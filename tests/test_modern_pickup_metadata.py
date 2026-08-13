"""P6-07 Modern Pickup, metadata, and hierarchy catalog contracts."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from mtgmeta.mtgo import pickup


REFERENCE_TODAY = date(2026, 7, 23)
MODERN_STATS = ROOT / "stats" / "modern" / "mtgo"


def test_modern_hierarchy_catalog_is_complete_stable_and_matchup_aligned(tmp_path):
    destination = pickup.generate_hierarchy_catalog(
        ROOT,
        "modern",
        rules_updated="2026-07-23T00:00:00+09:00",
        output_directory=tmp_path,
    )
    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["format"] == "modern"
    assert document["summary"] == {
        "parents": 127,
        "leaves": 176,
        "expandable_parents": 19,
    }
    assert all(
        parent["expandable"] == (len(parent["subtype_ids"]) >= 2)
        for parent in document["parents"]
    )
    matchup = json.loads((MODERN_STATS / "matchup_36w.json").read_text(encoding="utf-8"))
    assert document["parents"] == matchup["hierarchy"]["parents"]
    assert document["leaves"] == matchup["hierarchy"]["leaves"]


def test_modern_metadata_reports_partial_videre_coverage_without_public_pickup(tmp_path):
    destination = pickup.generate_metadata(
        ROOT,
        "modern",
        rules_updated="2026-07-23T00:00:00+09:00",
        data_updated="2026-07-23T00:00:00+09:00",
        output_directory=tmp_path,
    )
    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["statistics_catalog"] == "index.json"
    assert document["matchup_catalog"] == "matchup_index.json"
    assert document["hierarchy_catalog"] == "archetype_hierarchy.json"
    assert document["top8_catalog"] == "top8/index.json"
    assert document["pickup_catalog"] is None
    assert document["matchup_source"] == "Videre"
    official_ids = {
        str(event["event_id"])
        for path in (ROOT / "data" / "modern").glob("*.json")
        if (event := json.loads(path.read_text(encoding="utf-8"))).get("format")
        == "CMODERN"
        and event.get("event_id") is not None
    }
    archive_ids = {
        str(archive["event_id"])
        for path in (ROOT / "data" / "modern" / "mtgo" / "matches").glob("*.json")
        if (archive := json.loads(path.read_text(encoding="utf-8"))).get("event_id")
        is not None
    }
    overlap = official_ids & archive_ids
    coverage = document["matchup_coverage"]
    assert coverage == {
        "official_events": len(official_ids),
        "events_with_archives": len(overlap),
        "events_without_archives": len(official_ids - archive_ids),
        "stored_archives": len(archive_ids),
        "archives_outside_official_events": len(archive_ids - official_ids),
    }
    assert coverage["events_without_archives"] > 0


def test_committed_modern_pickup_uses_stable_ids_and_manual_approval_fields():
    known_document = json.loads(
        (MODERN_STATS / "pickup" / "known_archetypes.json").read_text(
            encoding="utf-8"
        )
    )
    assert "known" not in known_document
    assert known_document["known_ids"] == sorted(set(known_document["known_ids"]))
    assert len(known_document["known_ids"]) == 126

    document = yaml.safe_load(
        (MODERN_STATS / "pickup" / "candidates_2026-W29.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert document["new_archetypes"] == []
    entries = document["existing_changes"] + document["new_archetypes"]
    assert entries
    assert all(entry["archetype_id"] for entry in entries)
    assert all("subtype_id" in entry and "subtype" in entry for entry in entries)
    assert {entry["source"] for entry in entries} <= {"existing", "new"}

    selected = dict(document["existing_changes"][0])
    selected["approved"] = True
    selected["comment_zh"] = "人工审核"
    published_entry = pickup._approved_entries(
        {"existing_changes": [selected]}, "existing_changes"
    )[0]
    assert published_entry["archetype_id"] == selected["archetype_id"]
    assert published_entry["subtype_id"] == selected["subtype_id"]
    assert published_entry["subtype"] == selected["subtype"]
    assert published_entry["comment_zh"] == "人工审核"
    assert "approved" not in published_entry


def test_modern_known_state_initialization_refuses_implicit_overwrite(tmp_path):
    assert pickup.initialize_known_state(
        ROOT,
        "modern",
        today=REFERENCE_TODAY,
        output_directory=tmp_path,
    )
    try:
        pickup.initialize_known_state(
            ROOT,
            "modern",
            today=REFERENCE_TODAY,
            output_directory=tmp_path,
        )
    except pickup.MTGOPickupError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("known state initialization must not overwrite existing state")
