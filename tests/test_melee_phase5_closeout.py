"""P5-08 reduced-fixture acceptance test for the complete Phase 5 boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import validate_schemas as schemas
from mtgmeta.melee import (
    DisabledMeleeEventError,
    MeleePublicationBlocked,
    build_publication_payload,
    finalize_event_quality,
    load_melee_event_registry,
    normalize_raw_snapshot,
)
from mtgmeta.melee.client import fetch_raw_event


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "source_snapshot"
WHITELIST = ROOT / "configs" / "melee_events.yaml"
NORMALIZED_AT = "2026-07-21T15:00:00Z"


def _registry():
    return load_melee_event_registry(WHITELIST)


def _fixture_hashes() -> dict[str, str]:
    return {
        path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(FIXTURE.iterdir())
        if path.is_file()
    }


def test_real_reference_event_remains_disabled_before_network_or_archive_side_effects(tmp_path):
    registry = _registry()
    event = registry.get("434455")
    raw_root = tmp_path / "raw"
    network_calls: list[str] = []

    assert event.enabled is False
    assert tuple(request.url for request in event.raw_requests) == (
        "https://melee.gg/Tournament/View/434455",
    )
    with pytest.raises(DisabledMeleeEventError, match="disabled"):
        fetch_raw_event(
            event.id,
            registry,
            raw_root,
            request_get=lambda url, **_kwargs: network_calls.append(url),
        )
    assert network_calls == []
    assert not raw_root.exists()


def test_reduced_fixture_crosses_every_offline_phase5_boundary_deterministically():
    registry = _registry()
    event = registry.get("434455")
    fixture_before = _fixture_hashes()
    loaded, schema_registry = schemas.load_schemas(ROOT / "schemas")
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))

    assert schemas.validate_instance(
        manifest,
        loaded["melee-raw-archive.schema.json"],
        schema_registry,
    ) == []

    first_normalized = normalize_raw_snapshot(
        FIXTURE,
        event,
        normalized_at=NORMALIZED_AT,
    )
    second_normalized = normalize_raw_snapshot(
        FIXTURE,
        event,
        normalized_at=NORMALIZED_AT,
    )
    assert first_normalized == second_normalized
    assert schemas.validate_instance(
        first_normalized,
        loaded["melee-event.schema.json"],
        schema_registry,
    ) == []

    blocked = finalize_event_quality(first_normalized, event)
    assert blocked["quality"]["status"] == "blocked"
    assert blocked["quality"]["publishable"] is False
    assert "event_not_enabled" in {
        issue["code"] for issue in blocked["quality"]["issues"]
    }
    with pytest.raises(MeleePublicationBlocked, match="event_not_enabled"):
        build_publication_payload(first_normalized, event)

    enabled_for_acceptance_test = replace(event, enabled=True)
    first_payload = build_publication_payload(
        first_normalized,
        enabled_for_acceptance_test,
    )
    second_payload = build_publication_payload(
        second_normalized,
        enabled_for_acceptance_test,
    )
    assert first_payload == second_payload
    assert hashlib.sha256(first_payload).hexdigest() == hashlib.sha256(second_payload).hexdigest()

    published = json.loads(first_payload)
    assert published["quality"]["status"] == "warning"
    assert published["quality"]["publishable"] is True
    assert {issue["code"] for issue in published["quality"]["issues"]} == {
        "decklist_not_available"
    }
    assert schemas.validate_instance(
        published,
        loaded["melee-event.schema.json"],
        schema_registry,
    ) == []

    matches = {match["source_record_id"]: match for match in published["matches"]}
    assert matches["match-source-1"]["constructed_statistics_eligible"] is False
    assert matches["match-source-4"]["played"] is False
    assert matches["match-source-4"]["matchup_eligible"] is False
    assert matches["match-source-4-played"]["constructed_statistics_eligible"] is True
    assert matches["match-source-4-played"]["matchup_eligible"] is True
    assert _fixture_hashes() == fixture_before


def test_closeout_fixture_does_not_create_production_or_public_output_paths():
    event = _registry().get("434455")
    before = {
        path: path.exists()
        for path in (
            ROOT / "data" / "modern" / "melee" / "events" / "434455.json",
            ROOT / "stats" / "modern" / "melee" / "events" / "434455",
            ROOT / "melee" / "index.html",
        )
    }
    normalized = normalize_raw_snapshot(FIXTURE, event, normalized_at=NORMALIZED_AT)
    with pytest.raises(MeleePublicationBlocked):
        build_publication_payload(normalized, event)
    assert {path: path.exists() for path in before} == before
    assert all(existed is False for existed in before.values())
