import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import validate_schemas as schemas
from mtgmeta.melee import (
    MeleePublicationBlocked,
    MeleeQualityError,
    build_publication_payload,
    finalize_event_quality,
    load_melee_event_registry,
    normalize_raw_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "source_snapshot"
NORMALIZED_AT = "2026-07-21T14:00:00Z"


def event_definition():
    return load_melee_event_registry(ROOT / "configs" / "melee_events.yaml").events[0]


def normalized():
    return normalize_raw_snapshot(
        FIXTURE, event_definition(), normalized_at=NORMALIZED_AT
    )


def issue_codes(document):
    return {item["code"] for item in document["quality"]["issues"]}


def test_disabled_event_is_assessed_but_fails_closed_at_publication_boundary():
    source = normalized()
    original = copy.deepcopy(source)
    assessed = finalize_event_quality(source, event_definition())

    assert source == original
    assert assessed["quality"]["status"] == "blocked"
    assert assessed["quality"]["publishable"] is False
    assert "event_not_enabled" in issue_codes(assessed)
    warning = next(
        item for item in assessed["quality"]["issues"] if item["code"] == "decklist_not_available"
    )
    assert warning["blocking"] is False
    with pytest.raises(MeleePublicationBlocked, match="event_not_enabled"):
        build_publication_payload(source, event_definition())


def test_verified_enabled_event_with_only_missing_decklist_warning_is_publishable():
    event = replace(event_definition(), enabled=True)
    assessed = finalize_event_quality(normalized(), event)

    assert assessed["quality"]["status"] == "warning"
    assert assessed["quality"]["publishable"] is True
    assert issue_codes(assessed) == {"decklist_not_available"}
    assert all(not item["blocking"] for item in assessed["quality"]["issues"])


def test_publication_payload_is_canonical_idempotent_and_schema_valid():
    event = replace(event_definition(), enabled=True)
    source = normalized()
    reordered = {key: source[key] for key in reversed(source)}

    first = build_publication_payload(source, event)
    second = build_publication_payload(source, event)
    third = build_publication_payload(reordered, event)
    assert first == second == third
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
    assert first.endswith(b"\n")

    document = json.loads(first)
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        document, loaded["melee-event.schema.json"], registry
    ) == []


def test_schema_failure_stops_assessment_before_publication():
    malformed = normalized()
    malformed["schema_version"] = "1.0.0"
    with pytest.raises(MeleeQualityError, match="Schema validation"):
        finalize_event_quality(malformed, replace(event_definition(), enabled=True))
    with pytest.raises(MeleeQualityError, match="Schema validation"):
        build_publication_payload(malformed, replace(event_definition(), enabled=True))


def test_cross_record_and_eligibility_errors_are_blocking():
    source = normalized()
    eligible = next(item for item in source["matches"] if item["constructed_statistics_eligible"])
    eligible["constructed_statistics_eligible"] = False
    eligible["matchup_eligible"] = False
    source["standings"][0]["participant_id"] = "missing-participant"

    assessed = finalize_event_quality(source, replace(event_definition(), enabled=True))
    assert assessed["quality"]["publishable"] is False
    assert {"invalid_match_eligibility", "dangling_participant_reference"} <= issue_codes(assessed)


def test_missing_raw_integrity_evidence_blocks_publication():
    source = normalized()
    source["provenance"]["raw_artifacts"][0].pop("sha256")
    assessed = finalize_event_quality(source, replace(event_definition(), enabled=True))
    assert assessed["quality"]["publishable"] is False
    assert "raw_artifact_missing_sha256" in issue_codes(assessed)


def test_tampered_nonplayed_points_block_publication():
    source = normalized()
    bye = next(
        item
        for item in source["matches"]
        if item["competitors"][0]["result_type"] == "bye"
    )
    bye["competitors"][0]["match_points"] = 0
    assessed = finalize_event_quality(source, replace(event_definition(), enabled=True))
    assert assessed["quality"]["publishable"] is False
    assert "invalid_match_result" in issue_codes(assessed)


def test_no_verified_constructed_swiss_match_blocks_publication():
    source = normalized()
    source["matches"] = []
    assessed = finalize_event_quality(source, replace(event_definition(), enabled=True))
    assert assessed["quality"]["status"] == "blocked"
    assert "no_constructed_swiss_matches" in issue_codes(assessed)


def test_quality_gate_has_no_network_or_output_writer_dependency():
    source = (ROOT / "src" / "mtgmeta" / "melee" / "quality.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "requests." not in source
    assert ".write_" not in source
    assert "open(" not in source
