"""Committed P7-02 source and normalized-input reproducibility gate."""

from __future__ import annotations

from pathlib import Path

from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.retention import retain_normalized_event


ROOT = Path(__file__).resolve().parents[1]
EVENT_ID = "434455"
SNAPSHOT_ID = "20260724T092458Z-01"
RAW_ROOT = ROOT / "data_raw"
SNAPSHOT = RAW_ROOT / "melee" / EVENT_ID / SNAPSHOT_ID
NORMALIZED = ROOT / "data" / "modern" / "melee" / "events" / f"{EVENT_ID}.json"
REGISTRY = ROOT / "configs" / "melee_events.yaml"


def test_raw_source_files_are_excluded_from_git_text_normalization():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()

    assert "data_raw/** -text -eol" in attributes


def test_committed_reference_event_rebuilds_byte_identically(tmp_path):
    event = load_melee_event_registry(REGISTRY).require_fetchable(EVENT_ID)

    first = retain_normalized_event(
        event,
        SNAPSHOT,
        raw_root=RAW_ROOT,
        data_root=tmp_path / "data",
    )
    second = retain_normalized_event(
        event,
        SNAPSHOT,
        raw_root=RAW_ROOT,
        data_root=tmp_path / "data",
    )

    assert first.normalized_path.read_bytes() == NORMALIZED.read_bytes()
    assert first.reused is False
    assert second.reused is True
    assert first.snapshot_manifest_sha256 == (
        "d037d03c6b104abfed0ff33138f1738bd0aa02cd27c3e5789e135a9b539f359e"
    )
    assert first.normalized_sha256 == (
        "0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710"
    )
    assert first.response_count == 483
    assert first.participant_count == first.decklist_count == 362
    assert first.round_count == 19
    assert first.match_count == 2296
    assert first.eligible_constructed_match_count == 1394
    assert first.quality_status == "warning"
    assert first.quality_issue_codes == ("disqualified_participant_matches_excluded",)
