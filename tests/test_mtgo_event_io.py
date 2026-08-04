"""P3-03 tests for format-aware MTGO event IO, normalization, and dispatch."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from mtgmeta.classifier import classify_deck
from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo.fetch import (
    MTGOFetchError,
    MTGOIncompleteEventError,
    MTGOParseError,
    MTGOStorageError,
    discover_event_links,
    download_event_data,
    download_page,
    event_filename,
    extract_event_data,
    fetch_and_store_event,
    fetch_event_months,
    is_event_data_complete,
    load_fetched,
    mark_fetched,
    parse_event_link,
    refresh_existing_event,
)
from mtgmeta.mtgo.normalize import (
    classify_event,
    load_rules_for_format,
    normalize_event,
)
import validate_schemas


REGISTRY = ROOT / "configs" / "formats.yaml"
FORMATS = ("standard", "legacy", "pioneer", "pauper", "vintage", "modern")


def raw_event():
    return {
        "event_id": "12345",
        "description": "Standard Challenge 32",
        "format": "CSTANDARD",
        "starttime": "2026-07-20T12:00:00Z",
        "player_count": {"players": 2},
        "inplayoffs": "1",
        "standings": [
            {
                "loginid": "one",
                "rank": 1,
                "score": "18",
                "opponentmatchwinpercentage": "0.625",
                "gamewinpercentage": "0.700",
            },
            {
                "loginid": "two",
                "rank": 2,
                "score": "15",
                "opponentmatchwinpercentage": "0.500",
                "gamewinpercentage": "0.600",
            },
        ],
        "final_rank": [
            {"loginid": "one", "rank": 2},
            {"loginid": "two", "rank": 1},
        ],
        "decklists": [
            {
                "loginid": "one",
                "player": "Player One",
                "main_deck": [
                    {"qty": "4", "card_attributes": {"card_name": ' Brace } "Card" '}}
                ],
                "sideboard_deck": [
                    {"qty": 2, "card_attributes": {"card_name": "Side Card"}}
                ],
            },
            {
                "loginid": "two",
                "player": "Player Two",
                "main_deck": [
                    {"qty": 3, "card_attributes": {"card_name": "Main Card"}}
                ],
                "sideboard_deck": [],
            },
        ],
    }


def expected_batch_event():
    return {
        "event_id": "12345",
        "description": "Standard Challenge 32",
        "format": "CSTANDARD",
        "starttime": "2026-07-20T12:00:00Z",
        "player_count": 2,
        "inplayoffs": "1",
        "players": [
            {
                "player": "Player One",
                "loginid": "one",
                "swiss_rank": 1,
                "swiss_score": "18",
                "swiss_wins": 6,
                "opp_match_win_pct": "0.625",
                "game_win_pct": "0.700",
                "final_rank": 2,
                "main_deck": [{"name": 'Brace } "Card"', "qty": 4}],
                "sideboard": [{"name": "Side Card", "qty": 2}],
            },
            {
                "player": "Player Two",
                "loginid": "two",
                "swiss_rank": 2,
                "swiss_score": "15",
                "swiss_wins": 5,
                "opp_match_win_pct": "0.500",
                "game_win_pct": "0.600",
                "final_rank": 1,
                "main_deck": [{"name": "Main Card", "qty": 3}],
                "sideboard": [],
            },
        ],
    }


def embedded_html(data=None):
    payload = raw_event() if data is None else data
    return f"<script>window.MTGO.decklists.data = {json.dumps(payload)};</script>"


class Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_embedded_json_parser_handles_braces_and_quotes():
    html = embedded_html()
    assert extract_event_data(html) == raw_event()
    with pytest.raises(MTGOParseError, match="marker"):
        extract_event_data("missing")
    with pytest.raises(MTGOParseError, match="did not end"):
        extract_event_data("window.MTGO.decklists.data = {")
    malformed = "window.MTGO.decklists.data = {bad};"
    with pytest.raises(MTGOParseError, match="invalid"):
        extract_event_data(malformed)


def test_completeness_and_normalization_freeze_both_supported_output_shapes():
    raw = raw_event()
    expected = expected_batch_event()
    assert is_event_data_complete(raw) is True
    assert is_event_data_complete({**raw, "decklists": []}) is False
    assert is_event_data_complete({**raw, "standings": []}) is False
    assert is_event_data_complete({**raw, "final_rank": []}) is False
    without_playoff_marker = {
        key: value for key, value in raw.items() if key != "inplayoffs"
    }
    assert is_event_data_complete(without_playoff_marker) is False
    assert (
        is_event_data_complete(
            {
                **raw,
                "inplayoffs": "0",
                "standings": [],
                "final_rank": [],
            }
        )
        is True
    )
    assert normalize_event(raw) == expected
    expected_fetch = dict(expected)
    expected_fetch.pop("inplayoffs")
    assert normalize_event(raw, include_inplayoffs=False) == expected_fetch


def test_download_retry_policy_is_injectable_and_bounded():
    calls = []
    waits = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) < 3:
            raise OSError("temporary")
        return Response("ok")

    assert (
        download_page(
            "https://example.test/event",
            attempts=3,
            retry_delay=1,
            request_get=request,
            sleep=waits.append,
        )
        == "ok"
    )
    assert len(calls) == 3
    assert waits == [1, 1]
    assert calls[0][1]["timeout"] == 90
    assert "User-Agent" in calls[0][1]["headers"]

    with pytest.raises(MTGOFetchError, match="after 2 attempts"):
        download_page(
            "https://example.test/fail",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OSError("down")
            ),
        )


def test_event_download_retries_parse_failures_until_complete():
    calls = []
    waits = []

    def request(_url, **_kwargs):
        calls.append(True)
        return Response("missing" if len(calls) == 1 else embedded_html())

    assert (
        download_event_data(
            "https://example.test/event",
            attempts=2,
            retry_delay=1,
            request_get=request,
            sleep=waits.append,
        )
        == raw_event()
    )
    assert len(calls) == 2
    assert waits == [1]


def test_event_download_retries_partial_publication_until_complete():
    calls = []
    partial = raw_event()
    del partial["player_count"]

    def request(_url, **_kwargs):
        calls.append(True)
        return Response(embedded_html(partial if len(calls) == 1 else raw_event()))

    assert (
        download_event_data(
            "https://example.test/event",
            attempts=2,
            retry_delay=0,
            request_get=request,
        )
        == raw_event()
    )
    assert len(calls) == 2


def test_event_download_retries_until_standings_cover_every_deck():
    calls = []
    partial = {**raw_event(), "standings": raw_event()["standings"][:1]}

    def request(_url, **_kwargs):
        calls.append(True)
        return Response(embedded_html(partial if len(calls) == 1 else raw_event()))

    assert (
        download_event_data(
            "https://example.test/event",
            attempts=2,
            retry_delay=0,
            request_get=request,
        )
        == raw_event()
    )
    assert len(calls) == 2


def test_event_download_rejects_duplicate_source_player_ids():
    duplicate = raw_event()
    duplicate["standings"] = [
        duplicate["standings"][0],
        {**duplicate["standings"][1], "loginid": "one"},
    ]
    with pytest.raises(MTGOParseError, match="duplicate standings loginid"):
        download_event_data(
            "https://example.test/duplicate",
            attempts=1,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(duplicate)),
        )


def test_event_download_distinguishes_missing_from_invalid_swiss_values():
    missing = raw_event()
    missing["standings"] = [
        missing["standings"][0],
        {**missing["standings"][1], "score": None},
    ]
    with pytest.raises(MTGOIncompleteEventError, match="missing rank or score"):
        download_event_data(
            "https://example.test/missing-score",
            attempts=1,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(missing)),
        )

    invalid = raw_event()
    invalid["standings"] = [
        invalid["standings"][0],
        {**invalid["standings"][1], "score": "not-a-score"},
    ]
    with pytest.raises(MTGOParseError, match=r"standings\[1\]\.score is invalid"):
        download_event_data(
            "https://example.test/invalid-score",
            attempts=1,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(invalid)),
        )


def test_event_download_distinguishes_pending_decklists_from_parse_failure():
    pending = {**raw_event(), "decklists": []}
    with pytest.raises(MTGOIncompleteEventError, match="not been published"):
        download_event_data(
            "https://example.test/pending",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(pending)),
        )
    with pytest.raises(MTGOParseError, match="marker"):
        download_event_data(
            "https://example.test/malformed",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response("missing"),
        )


def test_event_download_distinguishes_partial_publication_from_invalid_field_type():
    partial = raw_event()
    del partial["player_count"]
    with pytest.raises(MTGOIncompleteEventError, match="missing fields: player_count"):
        download_event_data(
            "https://example.test/partial",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(partial)),
        )

    invalid = {**raw_event(), "decklists": {}}
    with pytest.raises(MTGOParseError, match="decklists must be a list"):
        download_event_data(
            "https://example.test/invalid",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(invalid)),
        )


def test_event_download_does_not_hide_final_invalid_data_behind_earlier_pending_data():
    responses = [
        {**raw_event(), "decklists": []},
        {**raw_event(), "decklists": {}},
    ]

    def request(_url, **_kwargs):
        return Response(embedded_html(responses.pop(0)))

    with pytest.raises(MTGOParseError, match="decklists must be a list"):
        download_event_data(
            "https://example.test/invalid-after-pending",
            attempts=2,
            retry_delay=0,
            request_get=request,
        )


def test_link_discovery_is_exact_and_does_not_confuse_premodern_or_leagues():
    html = " ".join(
        [
            "/decklist/standard-challenge-32-2026-07-201234",
            "/decklist/modern-league-2026-07-201235",
            "/decklist/premodern-challenge-2026-07-201236",
            "/decklist/pauper-challenge-2026-07-201237",
            "/decklist/standard-event-without-date",
        ]
    )
    assert discover_event_links(html, FORMATS) == [
        "/decklist/pauper-challenge-2026-07-201237",
        "/decklist/standard-challenge-32-2026-07-201234",
    ]
    assert (
        parse_event_link("/decklist/premodern-challenge-2026-07-201236", FORMATS)[0]
        == "other"
    )


def test_fetched_record_and_filename_storage_are_deterministic(tmp_path):
    record = tmp_path / "fetched.txt"
    assert load_fetched(record) == set()
    mark_fetched(record, "/decklist/standard-one")
    mark_fetched(record, "/decklist/standard-two")
    assert load_fetched(record) == {
        "/decklist/standard-one",
        "/decklist/standard-two",
    }
    assert event_filename(expected_batch_event()) == "Standard_Challenge_32_12345.json"
    unsafe = dict(expected_batch_event(), description="../escape")
    with pytest.raises(MTGOStorageError, match="unsafe"):
        event_filename(unsafe)


def test_disabled_format_fails_before_network_or_filesystem_side_effects(tmp_path):
    calls = []

    with pytest.raises(DisabledFormatError, match="not enabled"):
        fetch_and_store_event(
            tmp_path,
            "pauper",
            "https://www.mtgo.com/decklist/pauper-challenge-2026-07-201237",
            registry_path=REGISTRY,
            request_get=lambda *_args, **_kwargs: calls.append(True),
        )
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_standard_fetch_uses_registry_path_and_normalizes_before_storage(tmp_path):
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        return Response(embedded_html())

    destination = fetch_and_store_event(
        tmp_path,
        "standard",
        "https://www.mtgo.com/decklist/standard-challenge-32-2026-07-201234",
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
    )
    assert (
        destination
        == tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    )
    assert json.loads(destination.read_text(encoding="utf-8")) == expected_batch_event()
    assert len(calls) == 1


def test_controlled_refresh_replaces_only_matching_existing_event(tmp_path):
    existing = expected_batch_event()
    existing["players"][1]["swiss_score"] = "12"
    existing["players"][1]["swiss_wins"] = 4
    destination = tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    destination.parent.mkdir(parents=True)
    destination.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    refreshed = refresh_existing_event(
        tmp_path,
        "standard",
        "https://www.mtgo.com/decklist/standard-challenge-32-2026-07-2012345",
        registry_path=REGISTRY,
        request_get=lambda *_args, **_kwargs: Response(embedded_html()),
        sleep=lambda _seconds: None,
    )

    assert refreshed == destination
    assert json.loads(destination.read_text(encoding="utf-8")) == expected_batch_event()
    assert b"\r\n" not in destination.read_bytes()
    assert not (tmp_path / "fetched.txt").exists()
    assert not list(destination.parent.glob("*.tmp"))


def test_controlled_refresh_preserves_original_when_identity_or_placement_changes(
    tmp_path,
):
    destination = tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    destination.parent.mkdir(parents=True)
    destination.write_text(
        json.dumps(expected_batch_event(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    original = destination.read_bytes()
    changed = raw_event()
    changed["final_rank"] = [
        changed["final_rank"][0],
        {**changed["final_rank"][1], "rank": 3},
    ]

    with pytest.raises(MTGOStorageError, match="final ranks changed"):
        refresh_existing_event(
            tmp_path,
            "standard",
            "https://www.mtgo.com/decklist/standard-challenge-32-2026-07-2012345",
            registry_path=REGISTRY,
            request_get=lambda *_args, **_kwargs: Response(embedded_html(changed)),
            sleep=lambda _seconds: None,
        )

    assert destination.read_bytes() == original
    assert not list(destination.parent.glob("*.tmp"))


def test_format_aware_month_fetch_preserves_playoff_filter_and_ledger(tmp_path):
    event_link = "/decklist/standard-challenge-32-2026-07-201234"
    listing = f'<a href="{event_link}">event</a>'
    calls = []

    def request(url, **kwargs):
        calls.append(url)
        return Response(listing if "/decklists/" in url else embedded_html())

    summary = fetch_event_months(
        tmp_path,
        "standard",
        months=[(2026, 7)],
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["fetched"] == 1
    assert summary["failed"] == 0
    assert calls == [
        "https://www.mtgo.com/decklists/2026/07",
        "https://www.mtgo.com/decklists/2026/07",
        "https://www.mtgo.com/decklists/2026/07",
        f"https://www.mtgo.com{event_link}",
    ]
    assert (tmp_path / "fetched.txt").read_text(encoding="utf-8") == event_link + "\n"
    destination = tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    assert json.loads(destination.read_text(encoding="utf-8")) == expected_batch_event()


def test_month_listing_regression_retries_unions_and_fails_if_still_incomplete(
    tmp_path,
):
    known = "/decklist/modern-challenge-32-2026-08-0112849467"
    fresh = "/decklist/modern-challenge-64-2026-08-0212849474"
    (tmp_path / "fetched.txt").write_text(known + "\n", encoding="utf-8")
    listings = [fresh, fresh, fresh]

    def request(url, **_kwargs):
        assert "/decklists/" in url
        return Response(listings.pop(0))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 8)],
        now=datetime(2026, 8, 4),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["failed"] == 1
    assert summary["candidates"] == 0
    assert "listing omitted 1 previously known event link" in summary["errors"][0][1]
    assert not (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").exists()


def test_month_listing_retry_unions_observations_and_persists_deferred_state(tmp_path):
    known = "/decklist/modern-challenge-32-2026-08-0112849467"
    late = "/decklist/modern-challenge-64-2026-08-0212849474"
    (tmp_path / "fetched.txt").write_text(known + "\n", encoding="utf-8")
    listings = [late, f"{known} {late}", late]
    pending = {**raw_event(), "description": "Modern Challenge 64", "decklists": []}

    def request(url, **_kwargs):
        if "/decklists/" in url:
            return Response(listings.pop(0))
        return Response(embedded_html(pending))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 8)],
        now=datetime(2026, 8, 3),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["candidates"] == 2
    assert summary["skipped"] == 1
    assert summary["deferred_incomplete"] == 1
    state = json.loads(
        (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["events"] == [
        {
            "link": known,
            "event_date": "2026-08-01",
            "status": "processed",
        },
        {
            "link": late,
            "event_date": "2026-08-02",
            "status": "deferred_incomplete",
        },
    ]
    loaded, schema_registry = validate_schemas.load_schemas(ROOT / "schemas")
    assert (
        validate_schemas.validate_instance(
            state,
            loaded["mtgo-event-discovery.schema.json"],
            schema_registry,
        )
        == []
    )


def test_new_month_unions_three_observations_without_prior_links(tmp_path):
    first = "/decklist/modern-challenge-32-2026-08-0112849467"
    late = "/decklist/modern-challenge-64-2026-08-0212849474"
    listings = [first, late, first]
    pending = {**raw_event(), "description": "Modern Challenge 64", "decklists": []}

    def request(url, **_kwargs):
        if "/decklists/" in url:
            return Response(listings.pop(0))
        return Response(embedded_html(pending))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 8)],
        now=datetime(2026, 8, 3),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )

    assert summary["candidates"] == 2
    assert summary["deferred_incomplete"] == 2
    state = json.loads(
        (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").read_text()
    )
    assert [item["link"] for item in state["events"]] == [first, late]


def test_month_fetch_defers_listed_event_until_decklists_are_published(tmp_path):
    event_link = "/decklist/legacy-challenge-32-2026-07-1912847711"
    pending = {**raw_event(), "description": "Legacy Challenge 32", "decklists": []}

    def request(url, **_kwargs):
        return Response(event_link if "/decklists/" in url else embedded_html(pending))

    summary = fetch_event_months(
        tmp_path,
        "legacy",
        months=[(2026, 7)],
        now=datetime(2026, 7, 20),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["deferred_incomplete"] == 1
    assert summary["failed"] == 0
    assert summary["warnings"] == [
        (
            f"https://www.mtgo.com{event_link}",
            "MTGO event decklists have not been published yet after 5 attempts; "
            "will retry on a later scheduled run",
        )
    ]
    assert not (tmp_path / "fetched.txt").exists()
    assert not list((tmp_path / "data" / "legacy").glob("*.json"))
    state = json.loads(
        (tmp_path / "data" / "legacy" / "mtgo" / "discovery.json").read_text()
    )
    assert state["events"] == [
        {
            "link": event_link,
            "event_date": "2026-07-19",
            "status": "deferred_incomplete",
        }
    ]


def test_month_fetch_defers_recent_partial_event_without_writing(tmp_path):
    event_link = "/decklist/modern-challenge-32-2026-07-2512848201"
    partial = {**raw_event(), "description": "Modern Challenge 32"}
    del partial["player_count"]

    def request(url, **_kwargs):
        return Response(event_link if "/decklists/" in url else embedded_html(partial))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 7)],
        now=datetime(2026, 7, 26),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["deferred_incomplete"] == 1
    assert summary["failed"] == 0
    assert summary["warnings"] == [
        (
            f"https://www.mtgo.com{event_link}",
            "MTGO event publication is incomplete (missing fields: player_count) "
            "after 5 attempts; will retry on a later scheduled run",
        )
    ]
    assert not (tmp_path / "fetched.txt").exists()
    assert not list((tmp_path / "data" / "modern").glob("*.json"))
    state = json.loads(
        (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").read_text()
    )
    assert state["events"][0]["status"] == "deferred_incomplete"


def test_month_fetch_defers_recent_event_with_missing_standings_without_writing(
    tmp_path,
):
    event_link = "/decklist/modern-challenge-64-2026-07-2712849000"
    partial = {**raw_event(), "description": "Modern Challenge 64", "standings": []}

    def request(url, **_kwargs):
        return Response(event_link if "/decklists/" in url else embedded_html(partial))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 7)],
        now=datetime(2026, 7, 27),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["deferred_incomplete"] == 1
    assert summary["failed"] == 0
    assert "standings have not been published" in summary["warnings"][0][1]
    assert not (tmp_path / "fetched.txt").exists()
    assert not list((tmp_path / "data" / "modern").glob("*.json"))
    state = json.loads(
        (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").read_text()
    )
    assert state["events"][0]["status"] == "deferred_incomplete"


def test_month_fetch_escalates_partial_event_after_grace_period(tmp_path):
    event_link = "/decklist/modern-challenge-32-2026-07-2512848201"
    partial = {**raw_event(), "description": "Modern Challenge 32"}
    del partial["player_count"]

    def request(url, **_kwargs):
        return Response(event_link if "/decklists/" in url else embedded_html(partial))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 7)],
        now=datetime(2026, 7, 28),
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["deferred_incomplete"] == 0
    assert summary["failed"] == 1
    assert summary["errors"] == [
        (
            f"https://www.mtgo.com{event_link}",
            "MTGO event publication is incomplete (missing fields: player_count) "
            "after 5 attempts; event is outside the 2-day publication grace period",
        )
    ]
    assert not (tmp_path / "fetched.txt").exists()
    assert not list((tmp_path / "data" / "modern").glob("*.json"))
    state = json.loads(
        (tmp_path / "data" / "modern" / "mtgo" / "discovery.json").read_text()
    )
    assert state["events"][0]["status"] == "discovered"


def test_month_fetch_keeps_persistent_parse_failure_fatal(tmp_path):
    event_link = "/decklist/legacy-challenge-32-2026-07-1912847711"

    def request(url, **_kwargs):
        return Response(event_link if "/decklists/" in url else "missing")

    summary = fetch_event_months(
        tmp_path,
        "legacy",
        months=[(2026, 7)],
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["deferred_incomplete"] == 0
    assert summary["failed"] == 1
    assert summary["errors"][0][1] == "MTGO decklist marker was not found"
    assert not (tmp_path / "fetched.txt").exists()


def test_modern_event_collection_and_classification_use_their_own_paths(tmp_path):
    calls = []
    modern = raw_event()
    modern["description"] = "Modern Challenge 32"
    modern["format"] = "CMODERN"
    event_link = "/decklist/modern-challenge-32-2026-07-201234"

    def request(url, **kwargs):
        calls.append(url)
        return Response(event_link if "/decklists/" in url else embedded_html(modern))

    summary = fetch_event_months(
        tmp_path,
        "modern",
        months=[(2026, 7)],
        registry_path=REGISTRY,
        request_get=request,
        sleep=lambda _seconds: None,
        inter_event_delay=0,
    )
    assert summary["fetched"] == 1
    assert summary["failed"] == 0
    assert (tmp_path / "data" / "modern" / "Modern_Challenge_32_12345.json").exists()
    rule_path = tmp_path / "my_archetypes" / "modern.yaml"
    rule_path.parent.mkdir(parents=True)
    rule_path.write_bytes((ROOT / "my_archetypes" / "modern.yaml").read_bytes())
    assert (
        load_rules_for_format(tmp_path, "modern", registry_path=REGISTRY).format
        == "modern"
    )


def test_collection_disabled_format_fails_before_ledger_network_or_storage(tmp_path):
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    modern["mtgo"]["event_collection_enabled"] = False
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(
        yaml.safe_dump(registry, sort_keys=False), encoding="utf-8"
    )
    calls = []
    with pytest.raises(DisabledFormatError, match="event collection"):
        fetch_event_months(
            tmp_path,
            "modern",
            months=[(2026, 7)],
            registry_path=registry_path,
            request_get=lambda *_args, **_kwargs: calls.append(True),
        )
    assert calls == []
    assert not (tmp_path / "fetched.txt").exists()
    assert not (tmp_path / "data").exists()


def test_url_format_mismatch_fails_before_network_or_storage(tmp_path):
    calls = []
    with pytest.raises(MTGOFetchError, match="does not identify"):
        fetch_and_store_event(
            tmp_path,
            "standard",
            "https://www.mtgo.com/decklist/pauper-challenge-2026-07-201237",
            registry_path=REGISTRY,
            request_get=lambda *_args, **_kwargs: calls.append(True),
        )
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_standard_classification_dispatch_matches_the_package_classifier():
    event_path = ROOT / "data" / "standard" / "Standard_Challenge_32_12838092.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    rule_set = load_rules_for_format(ROOT, "standard")
    results = classify_event(event, rule_set)
    assert len(results) == len(event["players"])
    for player, result in zip(event["players"], results, strict=True):
        assert result == classify_deck(rule_set, player)

    modern_rules = load_rules_for_format(ROOT, "modern")
    assert modern_rules.format == "modern"
    assert modern_rules.format != rule_set.format


def test_p3_03_target_modules_exist_and_production_workflow_is_unchanged():
    contract = json.loads(
        (
            ROOT / "tests" / "fixtures" / "mtgo" / "format_pipeline_contract.json"
        ).read_text(encoding="utf-8")
    )
    unit = next(item for item in contract["migration_units"] if item["task"] == "P3-03")
    assert all((ROOT / path).is_file() for path in unit["target_modules"])
    workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(
        encoding="utf-8"
    )
    assert "python -B batch_mtgo.py" not in workflow
    assert "python -B -m mtgmeta.mtgo" in workflow
