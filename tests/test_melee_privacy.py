"""P10-03 future-event persistence and participant-reference contract."""

from __future__ import annotations

import json

import pytest

from mtgmeta.melee.parser import SourceArtifact
from mtgmeta.melee.privacy import (
    MeleePrivacyError,
    ParticipantPseudonymizer,
    minimize_source_response,
)


TEST_KEY = b"p10-03-test-key-material-is-not-secret"


def artifact(resource_type: str, **context) -> SourceArtifact:
    return SourceArtifact(
        request_id=resource_type,
        resource_type=resource_type,
        page=1,
        url={
            "standings": "https://melee.gg/Standing/GetRoundStandings",
            "matches": "https://melee.gg/Match/GetRoundMatches/101",
            "decklist": "https://melee.gg/Decklist/GetDecklistDetails?id=11111111-1111-1111-1111-111111111111",
        }[resource_type],
        path=f"{resource_type}-001.json",
        expected_content_type="json",
        sha256="0" * 64,
        bytes=1,
        **context,
    )


def test_participant_references_are_stable_inside_event_and_unlinkable_across_events():
    first = ParticipantPseudonymizer("434455", TEST_KEY, "test-2026-08")
    same = ParticipantPseudonymizer("434455", TEST_KEY, "test-2026-08")
    other_event = ParticipantPseudonymizer("419742", TEST_KEY, "test-2026-08")

    assert first.reference("11") == same.reference("11")
    assert first.reference("11") != first.reference("12")
    assert first.reference("11") != other_event.reference("11")
    assert first.reference("11").startswith("melee-v3-")


@pytest.mark.parametrize(
    ("key", "key_id", "message"),
    [
        (b"short", "test", "at least 32 bytes"),
        (TEST_KEY, "Not Allowed", "key ID"),
    ],
)
def test_participant_hmac_contract_fails_closed(key, key_id, message):
    with pytest.raises(MeleePrivacyError, match=message):
        ParticipantPseudonymizer("434455", key, key_id)


def test_standings_allowlist_preserves_display_name_but_drops_account_fields():
    source = {
        "recordsTotal": 1,
        "data": [{
            "ID": 7,
            "Rank": 1,
            "Points": 3,
            "MatchRecord": "1-0-0",
            "Team": {
                "StatusDescription": "Active",
                "Players": [{
                    "ID": 11,
                    "DisplayName": "Alpha",
                    "DisplayNameLastFirst": "Alpha",
                    "Username": "private-login",
                    "ScreenName": "private-screen",
                    "PronounsDescription": "unused",
                    "LanguageDescription": "unused",
                    "ProfileImageVersion": 99,
                }],
            },
            "Decklists": [{
                "DecklistId": "11111111-1111-1111-1111-111111111111",
                "PlayerId": 11,
                "DecklistName": "unused personal label",
            }],
        }],
    }
    result = minimize_source_response(
        json.dumps(source).encode(),
        artifact("standings", source_round_id="101"),
        ParticipantPseudonymizer("434455", TEST_KEY, "test-2026-08"),
    )
    persisted = json.loads(result.body)

    assert persisted["records_total"] == 1
    assert persisted["standings"][0]["display_name"] == "Alpha"
    assert persisted["standings"][0]["participant_ref"].startswith("melee-v3-")
    assert set(persisted["standings"][0]) == {
        "source_standing_id", "participant_ref", "display_name", "rank",
        "match_points", "record_text", "status_text",
    }
    assert set(persisted["decklist_references"][0]) == {
        "source_decklist_id", "participant_ref", "url",
    }
    serialized = result.body.decode()
    for forbidden in (
        "DisplayNameLastFirst", "Username", "ScreenName", "PronounsDescription",
        "LanguageDescription", "ProfileImageVersion", "DecklistName", "PlayerId",
        "private-login", "private-screen",
    ):
        assert forbidden not in serialized


def test_matches_and_decklists_persist_only_statistical_fields():
    pseudonymizer = ParticipantPseudonymizer("434455", TEST_KEY, "test-2026-08")
    matches = {
        "recordsTotal": 1,
        "data": [{
            "Guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "RoundId": 101,
            "HasResult": True,
            "ResultString": "2-0-0",
            "TableNumber": 4,
            "ByeReasonDescription": None,
            "LossReasonDescription": None,
            "Competitors": [{
                "Team": {"Players": [{
                    "ID": 11, "DisplayName": "Alpha", "Username": "private-login",
                }]},
                "GameWins": 2,
                "GameByes": 0,
            }],
        }],
    }
    minimized_match = minimize_source_response(
        json.dumps(matches).encode(),
        artifact("matches", source_round_id="101"),
        pseudonymizer,
    ).body
    match_document = json.loads(minimized_match)
    assert set(match_document["matches"][0]) == {
        "source_match_id", "source_round_id", "competitors", "result_text",
        "status_text", "table_number",
    }
    assert set(match_document["matches"][0]["competitors"][0]) == {
        "participant_ref", "outcome_text", "match_points",
    }
    assert "Username" not in minimized_match.decode()
    assert "DisplayName" not in minimized_match.decode()

    participant_ref = pseudonymizer.reference("11")
    decklist = {
        "Guid": "11111111-1111-1111-1111-111111111111",
        "FormatName": "Modern",
        "DecklistName": "unused personal label",
        "LinkToCards": "unused",
        "Records": [{
            "c": 0,
            "n": "Fixture Card",
            "q": 4,
            "SetCode": "TST",
            "Language": "English",
            "Treatment": "Foil",
        }],
    }
    minimized_decklist = minimize_source_response(
        json.dumps(decklist).encode(),
        artifact(
            "decklist",
            source_decklist_id="11111111-1111-1111-1111-111111111111",
            participant_ref=participant_ref,
        ),
        pseudonymizer,
    ).body
    decklist_document = json.loads(minimized_decklist)
    assert set(decklist_document["decklists"][0]) == {
        "source_decklist_id", "participant_ref", "format_text", "cards",
    }
    assert set(decklist_document["decklists"][0]["cards"][0]) == {
        "name", "quantity", "section_text",
    }
    for forbidden in ("DecklistName", "LinkToCards", "SetCode", "Language", "Treatment"):
        assert forbidden not in minimized_decklist.decode()
