"""Unranked DQ identity recovery preserves source, privacy and exclusions."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest
import requests

from mtgmeta.melee.client import fetch_complete_event
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.normalize import normalize_parsed_snapshot
from mtgmeta.melee.parser import SourceArtifact, parse_raw_snapshot, parse_minimized_response
from mtgmeta.melee.privacy import minimize_source_response
from tests.melee_synthetic import source_fixture, STAMP

ROOT = Path(__file__).resolve().parents[1]
DECK = "00000000-0000-0000-0000-000000000002"


def participant(status="Disqualified", pid="2"):
    raw = json.dumps({"name": "DQ player", "status": status, "rank": None, "points": None,
        "username": "private-account", "twitterHandle": "private-social",
        "decklists": [{"id": DECK, "name": "Source deck"}]}).encode()
    artifact = SourceArtifact("participant", "participant", 1,
        f"https://melee.gg/Player/GetPlayerDetails?id={pid}", "participant-2.json", "json",
        sha256(raw).hexdigest(), len(raw), method="GET", source_participant_id=pid)
    return raw, artifact


def test_minimized_dq_has_no_rank_score_or_profile_fields():
    raw, artifact = participant()
    result = minimize_source_response(raw, artifact, event_id="900001")
    doc = json.loads(result.body)
    assert doc["participant"] == {"source_participant_id": "2", "display_name": "DQ player",
                                  "status_text": "Disqualified"}
    assert b"private-account" not in result.body and b"private-social" not in result.body
    page = parse_minimized_response(result.body, artifact, expected_schema_version="2.0.0")
    assert page.standings[0].rank is None and page.standings[0].match_points is None
    with pytest.raises(ValueError, match="identity"):
        parse_minimized_response(result.body, replace(artifact, source_participant_id="3"))


@pytest.mark.parametrize("status", ["Active", "Dropped", None])
def test_missing_identity_requires_explicit_dq(status):
    raw, artifact = participant(status)
    with pytest.raises(ValueError, match="explicitly Disqualified"):
        minimize_source_response(raw, artifact, event_id="900001")


def test_unranked_dq_preserves_matches_and_excludes_both_sides(tmp_path):
    event, _, _, snapshot = source_fixture(tmp_path)
    original = parse_raw_snapshot(snapshot)
    pages = tuple(replace(p, standings=tuple(s for s in p.standings if s.source_participant_id != "2"))
                  for p in original.pages)
    raw, artifact = participant()
    supplement = minimize_source_response(raw, artifact, event_id=event.id).page
    parsed = replace(original, pages=(*pages, supplement))
    document = normalize_parsed_snapshot(parsed, event, normalized_at=STAMP)
    assert len(document["participants"]) == 4
    dq = next(p for p in document["participants"] if p["source_id"] == "2")
    assert dq["status"] == "disqualified"
    standing = next(s for s in document["standings"] if s["participant_id"] == dq["id"])
    assert standing["rank"] is None and standing["match_points"] is None
    assert len(document["matches"]) == sum(len(p.matches) for p in original.pages)
    affected = [m for m in document["matches"] if any(c["participant_id"] == dq["id"] for c in m["competitors"])]
    assert affected
    assert all(not m["constructed_statistics_eligible"] and not m["matchup_eligible"] for m in affected)


def test_collector_fetches_only_orphan_identity_and_its_deck(tmp_path):
    calls = []
    raw_dq, _ = participant()
    def send(method, url, **kwargs):
        calls.append(url)
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if '/Tournament/View/' in url:
            body = '<title>Fixture | Melee</title><button class="round-selector" data-id="1" data-name="Round 1" data-is-completed="True"></button>'
        elif '/Standing/' in url:
            body = {"recordsTotal": 1, "data": [{"ID": 1, "Rank": 1, "Points": 3,
                "Team": {"ID": 1, "StatusDescription": "Active", "Players": [{"ID": 1, "DisplayName": "Player 1"}]}}]}
        elif '/Match/' in url:
            body = {"recordsTotal": 1, "data": [{"Guid": "match-one", "RoundId": "1", "HasResult": True,
                "ResultString": "DQ player won 2-0-0", "Competitors": [
                    {"Team": {"ID": int(pid), "Players": [{"ID": int(pid), "DisplayName": "Player " + pid}]},
                     "GameWins": wins} for pid, wins in [("1", 0), ("2", 2)]]}]}
        elif '/Player/' in url:
            body = json.loads(raw_dq)
        else:
            assert url.endswith(DECK)
            body = {"Guid": DECK, "FormatName": "Modern", "Records": [{"c": 0, "n": "Mountain", "q": 60}]}
        response._content = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        response._content_consumed = True
        return response
    result = fetch_complete_event("405588", load_melee_event_registry(ROOT / 'configs/melee_events.yaml'),
        tmp_path, request_send=send, request_delay=0, review_standings_round_id="1")
    parsed = parse_raw_snapshot(result.archive_path)
    assert len(calls) == 5
    assert [u for u in calls if '/Player/' in u] == ['https://melee.gg/Player/GetPlayerDetails?id=2']
    assert any(d.source_participant_id == "2" for p in parsed.pages for d in p.decklists)
