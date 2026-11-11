"""Completed v3 archives remain readable without the retired HMAC writer/key."""
from datetime import date
import json

import pytest

from melee_synthetic import STAMP, digest, write_json
from mtgmeta.melee.config import MeleeEventDefinition, MeleePhaseDefinition
from mtgmeta.melee.integrity import MeleeSourceIntegrityError, validate_retained_source
from mtgmeta.melee.normalize import normalize_raw_snapshot
from mtgmeta.melee.parser import parse_raw_snapshot
from mtgmeta.melee.quality import finalize_event_quality


REFS = ("melee-v3-" + "a" * 64, "melee-v3-" + "b" * 64)
DECKS = tuple(f"00000000-0000-0000-0000-00000000000{n}" for n in (1, 2))


@pytest.fixture
def v3_source(tmp_path):
    # Hand-authored persisted resources: two players, one round, one played win.
    # These opaque references model an already completed archive, not HMAC output
    # computed with a test secret. No production archive is read or rewritten.
    event = MeleeEventDefinition(
        id="900003", url="https://melee.gg/Tournament/View/900003",
        name="Invented V3 Open", start_date=date(2026, 1, 1), end_date=date(2026, 1, 1),
        format="modern", series="synthetic", structure="constructed_single_stage",
        enabled=True, review_status="verified", mixed_format=False, raw_requests=(),
        include_playoffs=False,
        phases=(MeleePhaseDefinition("constructed", "day1", "constructed", "modern", True, (1,), ()),),
        advancement=None, reviewed_overrides=(), constructed_game_format="modern",
        source_evidence=(), special_handling=(), notes="Independent retained v3 fixture",
    )
    snapshot = tmp_path / "data_raw/melee/900003/20260101T000000Z-01"
    responses = []

    def resource(name, kind, value, *, participant=None, deck=None):
        path = write_json(snapshot / name, {"schema_version": "1.0.0", "resource_type": kind, **value})
        responses.append({
            "request_id": name.removesuffix(".json").replace("-", "_"), "resource_type": kind, "page": 1,
            "url": event.url, "path": name, "expected_content_type": "json",
            "response_content_type": "application/json", "etag": None, "last_modified": None,
            "status_code": 200, "attempts": 1, "sha256": digest(path), "bytes": path.stat().st_size,
            "method": "POST" if kind in {"matches", "standings"} else "GET",
            "request_body_sha256": "e" * 64 if kind in {"matches", "standings"} else None,
            "source_round_id": "1" if kind in {"matches", "standings"} else None,
            "participant_ref": participant, "source_decklist_id": deck,
            "persisted_content_type": "json", "source_sha256": "c" * 64, "source_bytes": 1000,
        })

    resource("tournament-001.json", "tournament", {
        "tournament": {"source_event_id": event.id, "name": event.name},
        "rounds": [{"source_round_id": "1", "label": "Round 1", "number": 1}],
    })
    resource("standings-001.json", "standings", {
        "records_total": 2,
        "standings": [{"source_standing_id": str(n), "participant_ref": ref,
                       "display_name": f"Player {n}", "rank": n, "match_points": points,
                       "status_text": "Active"}
                      for n, ref, points in ((1, REFS[0], 3), (2, REFS[1], 0))],
        "decklist_references": [{"source_decklist_id": deck, "participant_ref": ref,
                                 "url": f"https://melee.gg/Decklist/GetDecklistDetails?id={deck}"}
                                for ref, deck in zip(REFS, DECKS, strict=True)],
    })
    resource("matches-001.json", "matches", {"records_total": 1, "matches": [{
        "source_match_id": "v3-match-1", "source_round_id": "1",
        "competitors": [{"participant_ref": REFS[0], "outcome_text": "Win", "match_points": 3},
                        {"participant_ref": REFS[1], "outcome_text": "Loss", "match_points": 0}],
    }]})
    for n, (ref, deck) in enumerate(zip(REFS, DECKS, strict=True), 1):
        resource(f"deck-{n}.json", "decklist", {"decklists": [{
            "source_decklist_id": deck, "participant_ref": ref,
            "cards": [{"name": "Island", "quantity": 60, "section_text": "Main Deck"}],
        }]}, participant=ref, deck=deck)
    write_json(snapshot / "manifest.json", {
        "schema_version": "3.0.0", "source": "melee", "event_id": event.id,
        "event_url": event.url, "fetched_at": STAMP,
        "participant_identity": {"scheme": "hmac-sha256-event-v1", "key_id": "retired-fixture-key"},
        "responses": responses,
    })
    document = normalize_raw_snapshot(snapshot, event, normalized_at=STAMP,
        raw_artifact_prefix=snapshot.relative_to(tmp_path).as_posix())
    document = finalize_event_quality(document, event)
    path = write_json(tmp_path / "data/modern/melee/events/900003.json", document)
    return event, snapshot, path


def test_complete_v3_source_passes_generic_integrity_without_secret_or_pages(tmp_path, v3_source):
    event, snapshot, path = v3_source
    before = {p: p.read_bytes() for p in [path, *snapshot.iterdir()]}
    parsed = parse_raw_snapshot(snapshot)
    assert parsed.participant_identity_scheme == "hmac-sha256-event-v1"
    assert parsed.participant_key_id == "retired-fixture-key"
    document = json.loads(path.read_bytes())
    assert {p["source_id"] for p in document["participants"]} == set(REFS)
    assert len(document["rounds"]) == len(document["matches"]) == 1
    assert len(document["decklists"]) == 2
    assert validate_retained_source(tmp_path, event) == set(before)
    assert {p: p.read_bytes() for p in before} == before
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("damage,reason", [
    ("scheme", "Schema validation|unsupported participant identity"),
    ("resource_version", "minimized resource contract does not match raw archive"),
    ("participant_context", "decklist participant identity does not match manifest"),
    ("bytes", "byte count does not match manifest"),
    ("normalized_identity", "retained participants identities differ from source"),
])
def test_generic_integrity_rejects_corrupt_or_misidentified_v3(tmp_path, v3_source, damage, reason):
    event, snapshot, path = v3_source
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    if damage == "scheme":
        manifest["participant_identity"]["scheme"] = "source-participant-id-v1"
    elif damage == "resource_version":
        resource = snapshot / "tournament-001.json"
        document = json.loads(resource.read_bytes())
        document["schema_version"] = "2.0.0"
        write_json(resource, document)
        # A coherent file hash must not disguise the wrong resource contract.
        manifest["responses"][0].update(sha256=digest(resource), bytes=resource.stat().st_size)
    elif damage == "participant_context":
        manifest["responses"][-1]["participant_ref"] = REFS[0]
    elif damage == "bytes":
        resource = snapshot / "deck-1.json"
        resource.write_bytes(resource.read_bytes() + b" ")
    else:
        document = json.loads(path.read_bytes())
        document["participants"][0]["source_id"] = "melee-v3-" + "d" * 64
        write_json(path, document)
    write_json(snapshot / "manifest.json", manifest)
    with pytest.raises(MeleeSourceIntegrityError, match=reason):
        validate_retained_source(tmp_path, event)
