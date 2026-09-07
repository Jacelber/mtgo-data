"""Focused contract tests for direct public Melee participant identifiers."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from mtgmeta.melee.client import RawResponseRecord, _checkpoint_payload
from mtgmeta.melee.config import (
    MeleeConfigError,
    load_melee_event_registry,
    parse_melee_event_text,
)
from mtgmeta.melee.normalize import _source_result
from mtgmeta.melee.parser import (
    MeleeSourceParseError,
    SourceArtifact,
    SourceCompetitor,
    SourceMatch,
    parse_minimized_response,
    parse_raw_snapshot,
)
from mtgmeta.melee.privacy import minimize_source_response


ROOT = Path(__file__).resolve().parents[1]
DECKLIST_ID = "12345678-1234-1234-1234-123456789abc"
LEGACY_REF = "melee-v3-" + "a" * 64


def _artifact(*, body: bytes, source_participant_id: str | None = None) -> SourceArtifact:
    return SourceArtifact(
        request_id="decklist",
        resource_type="decklist",
        page=1,
        url=f"https://melee.gg/Decklist/GetDecklistDetails?id={DECKLIST_ID}",
        path=f"decklist-{DECKLIST_ID}.json",
        expected_content_type="json",
        sha256=sha256(body).hexdigest(),
        bytes=len(body),
        method="GET",
        source_participant_id=source_participant_id,
        source_decklist_id=DECKLIST_ID,
        persisted_content_type="json",
        source_sha256="b" * 64,
        source_bytes=321,
    )


def _write_snapshot(
    tmp_path,
    *,
    schema_version: str,
    participant: str,
    minimized_version: str | None = None,
):
    minimized_version = minimized_version or (
        "1.0.0" if schema_version == "3.0.0" else "2.0.0"
    )
    resource_identity_key = (
        "participant_ref" if minimized_version == "1.0.0" else "source_participant_id"
    )
    manifest_identity_key = (
        "participant_ref" if schema_version == "3.0.0" else "source_participant_id"
    )
    resource_participant = LEGACY_REF if minimized_version == "1.0.0" else participant
    resource = {
        "schema_version": minimized_version,
        "resource_type": "decklist",
        "decklists": [
            {
                "source_decklist_id": DECKLIST_ID,
                resource_identity_key: resource_participant,
                "cards": [{"name": "Fixture Card", "quantity": 4, "section_text": "Main Deck"}],
            }
        ],
    }
    body = (json.dumps(resource, sort_keys=True, separators=(",", ":")) + "\n").encode()
    artifact = _artifact(
        body=body,
        source_participant_id=participant if schema_version == "4.0.0" else None,
    )
    record = {
        "request_id": artifact.request_id,
        "resource_type": artifact.resource_type,
        "page": artifact.page,
        "url": artifact.url,
        "path": artifact.path,
        "expected_content_type": artifact.expected_content_type,
        "response_content_type": "application/json",
        "etag": None,
        "last_modified": None,
        "status_code": 200,
        "attempts": 1,
        "sha256": artifact.sha256,
        "bytes": artifact.bytes,
        "method": artifact.method,
        "request_body_sha256": None,
        "source_round_id": None,
        "source_decklist_id": artifact.source_decklist_id,
        manifest_identity_key: participant,
        "persisted_content_type": artifact.persisted_content_type,
        "source_sha256": artifact.source_sha256,
        "source_bytes": artifact.source_bytes,
    }
    identity = (
        {"scheme": "hmac-sha256-event-v1", "key_id": "legacy-2026"}
        if schema_version == "3.0.0"
        else {"scheme": "source-participant-id-v1"}
    )
    snapshot = tmp_path / schema_version
    snapshot.mkdir()
    (snapshot / artifact.path).write_bytes(body)
    (snapshot / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "source": "melee",
                "event_id": "434455",
                "event_url": "https://melee.gg/Tournament/View/434455",
                "fetched_at": "2026-08-30T00:00:00Z",
                "participant_identity": identity,
                "responses": [record],
            }
        ),
        encoding="utf-8",
    )
    return snapshot


def test_minimizer_copies_public_source_participant_id_without_hmac():
    source = json.dumps(
        {
            "Guid": DECKLIST_ID,
            "FormatName": "Modern",
            "Records": [{"n": "Fixture Card", "q": 4, "c": 0}],
        }
    ).encode()
    artifact = _artifact(body=source, source_participant_id="123456")

    result = minimize_source_response(source, artifact, event_id="434455")
    persisted = json.loads(result.body)

    assert persisted["schema_version"] == "2.0.0"
    assert persisted["decklists"][0]["source_participant_id"] == "123456"
    assert "participant_ref" not in result.body.decode()


def test_explicitly_empty_real_decklist_round_trips_without_a_fabricated_deck():
    source = json.dumps(
        {
            "Guid": DECKLIST_ID,
            "FormatName": "Pauper",
            "Records": [],
            "Components": [],
        }
    ).encode()
    artifact = _artifact(body=source, source_participant_id="123456")

    result = minimize_source_response(source, artifact, event_id="438329")
    persisted = json.loads(result.body)
    restored = parse_minimized_response(
        result.body,
        _artifact(body=result.body, source_participant_id="123456"),
        expected_schema_version="2.0.0",
    )

    assert persisted == {
        "schema_version": "2.0.0",
        "resource_type": "decklist",
        "decklists": [],
    }
    assert result.page.decklists == ()
    assert restored.decklists == ()


def test_nonempty_unrecognized_real_decklist_still_fails_closed():
    source = json.dumps(
        {
            "Guid": DECKLIST_ID,
            "FormatName": "Pauper",
            "Records": [{"n": "Fixture Card", "q": 4, "c": 7}],
            "Components": [],
        }
    ).encode()

    with pytest.raises(MeleeSourceParseError, match="no recognized cards"):
        minimize_source_response(
            source,
            _artifact(body=source, source_participant_id="123456"),
            event_id="438329",
        )


def _qualified_source_match() -> SourceMatch:
    competitor = SourceCompetitor("123456", "Qualified", 3)
    return SourceMatch(
        source_match_id="match-1",
        source_round_id="round-1",
        competitor_source_ids=(competitor.source_participant_id,),
        competitor_results=(competitor,),
        result_text=None,
        status_text="Qualified",
        table_number=None,
    )


def test_registry_31_can_distinguish_qualified_bye_from_legacy_top8_lock():
    registry = load_melee_event_registry(ROOT / "configs" / "melee_events.yaml")
    legacy_event = registry.get("434455")
    bye_event = registry.get("438329")

    assert _source_result(_qualified_source_match(), legacy_event) == (
        False,
        [
            {
                "source_participant_id": "123456",
                "result_type": "awarded_win_top8_lock",
                "match_points": 3,
            }
        ],
    )
    assert _source_result(_qualified_source_match(), bye_event) == (
        False,
        [
            {
                "source_participant_id": "123456",
                "result_type": "bye",
                "match_points": 3,
            }
        ],
    )


def test_registry_30_rejects_new_qualified_result_interpretation():
    registry_text = (ROOT / "configs" / "melee_events.yaml").read_text(
        encoding="utf-8"
    ).replace(
        'schema_version: "3.1.0"', 'schema_version: "3.0.0"', 1
    ).replace(
        "      top8_lock_supported: true",
        "      top8_lock_supported: true\n      qualified_result_type: bye",
        1,
    )

    with pytest.raises(MeleeConfigError, match="unsupported"):
        parse_melee_event_text(registry_text)


def test_paupergeddon_registry_admission_is_exact_and_fetchable():
    registry = load_melee_event_registry(ROOT / "configs" / "melee_events.yaml")
    event = registry.require_fetchable("438329")

    assert registry.schema_version == "3.1.0"
    assert (
        event.url,
        event.name,
        event.start_date.isoformat(),
        event.end_date.isoformat(),
        event.format,
        event.series,
        event.structure,
        event.mixed_format,
        event.include_playoffs,
        event.constructed_game_format,
    ) == (
        "https://melee.gg/Tournament/View/438329",
        "Paupergeddon Summer 2026 Main Event",
        "2026-07-11",
        "2026-07-12",
        "pauper",
        "paupergeddon",
        "constructed_day2",
        False,
        True,
        "pauper",
    )
    assert [
        (phase.id, phase.stage, phase.swiss, phase.rounds, phase.source_labels)
        for phase in event.phases
    ] == [
        ("day1_pauper", "day1", True, tuple(range(1, 9)), ()),
        ("day2_pauper", "day2", True, tuple(range(9, 15)), ()),
        ("top8_pauper", "playoff", False, (), ("Quarterfinals", "Semifinals", "Finals")),
    ]
    assert event.advancement is not None
    assert (
        event.advancement.day2_after_round,
        event.advancement.day2_minimum_match_points,
        event.advancement.top8_lock_supported,
        event.advancement.qualified_result_type,
    ) == (8, 18, None, "bye")
    assert event.source_evidence == (
        "https://melee.gg/Tournament/View/438329",
        "https://paupergeddon.com/",
    )


def test_checkpoint_v3_declares_direct_identity_without_a_key():
    record = RawResponseRecord(
        request_id="decklist",
        resource_type="decklist",
        page=1,
        url=f"https://melee.gg/Decklist/GetDecklistDetails?id={DECKLIST_ID}",
        path=f"decklist-{DECKLIST_ID}.json",
        expected_content_type="json",
        response_content_type="application/json",
        etag=None,
        last_modified=None,
        status_code=200,
        attempts=1,
        sha256="a" * 64,
        bytes=123,
        method="GET",
        source_participant_id="123456",
        source_decklist_id=DECKLIST_ID,
        persisted_content_type="json",
        source_sha256="b" * 64,
        source_bytes=321,
    )
    checkpoint = _checkpoint_payload(
        event_id="434455",
        event_url="https://melee.gg/Tournament/View/434455",
        fetched_at="2026-08-30T00:00:00Z",
        destination_name="20260830T000000Z-01",
        records={record.path: record},
        planned_responses=None,
        plan_sha256=None,
    )

    assert checkpoint["schema_version"] == "3.0.0"
    assert checkpoint["participant_identity"] == {"scheme": "source-participant-id-v1"}
    assert checkpoint["responses"][0]["source_participant_id"] == "123456"
    assert "participant_ref" not in checkpoint["responses"][0]


def test_raw_v4_direct_identity_and_historical_v3_identity_are_both_readable(tmp_path):
    direct = parse_raw_snapshot(
        _write_snapshot(tmp_path, schema_version="4.0.0", participant="123456")
    )
    legacy = parse_raw_snapshot(
        _write_snapshot(tmp_path, schema_version="3.0.0", participant=LEGACY_REF)
    )

    assert direct.participant_identity_scheme == "source-participant-id-v1"
    assert direct.pages[0].decklists[0].source_participant_id == "123456"
    assert direct.participant_key_id is None
    assert legacy.participant_identity_scheme == "hmac-sha256-event-v1"
    assert legacy.pages[0].decklists[0].source_participant_id == LEGACY_REF
    assert legacy.participant_key_id == "legacy-2026"


def test_raw_v4_rejects_a_legacy_minimized_resource_contract(tmp_path):
    snapshot = _write_snapshot(
        tmp_path,
        schema_version="4.0.0",
        participant="123456",
        minimized_version="1.0.0",
    )

    with pytest.raises(MeleeSourceParseError, match="does not match raw archive"):
        parse_raw_snapshot(snapshot)
