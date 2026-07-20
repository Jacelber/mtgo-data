"""P3-03 tests for format-aware MTGO event IO, normalization, and dispatch."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import batch_mtgo
import classify_standard
import fetch_mtgo
from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo.fetch import (
    MTGOFetchError,
    MTGOParseError,
    MTGOStorageError,
    discover_event_links,
    download_page,
    event_filename,
    extract_event_data,
    fetch_and_store_event,
    fetch_event_months,
    is_event_data_complete,
    load_fetched,
    mark_fetched,
    parse_event_link,
)
from mtgmeta.mtgo.normalize import classify_event, load_rules_for_format, normalize_event


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
            }
        ],
        "final_rank": [{"loginid": "one", "rank": 2}],
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
                "swiss_rank": None,
                "swiss_score": None,
                "swiss_wins": None,
                "opp_match_win_pct": None,
                "game_win_pct": None,
                "final_rank": None,
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


def test_embedded_json_parser_handles_braces_quotes_and_legacy_wrappers():
    html = embedded_html()
    assert extract_event_data(html) == raw_event()
    assert batch_mtgo.extract_data(html) == raw_event()
    assert fetch_mtgo.extract_data(html) == raw_event()
    assert batch_mtgo.extract_data("missing") is None
    with pytest.raises(RuntimeError, match="页面里没找到数据标记"):
        fetch_mtgo.extract_data("missing")
    with pytest.raises(MTGOParseError, match="marker"):
        extract_event_data("missing")
    with pytest.raises(MTGOParseError, match="did not end"):
        extract_event_data("window.MTGO.decklists.data = {")
    malformed = "window.MTGO.decklists.data = {bad};"
    with pytest.raises(json.JSONDecodeError):
        batch_mtgo.extract_data(malformed)
    with pytest.raises(json.JSONDecodeError):
        fetch_mtgo.extract_data(malformed)


def test_completeness_and_normalization_freeze_both_legacy_output_shapes():
    raw = raw_event()
    expected = expected_batch_event()
    assert is_event_data_complete(raw) is True
    assert is_event_data_complete({**raw, "decklists": []}) is False
    assert normalize_event(raw) == expected
    assert batch_mtgo.build_clean_data(raw) == expected
    expected_fetch = dict(expected)
    expected_fetch.pop("inplayoffs")
    assert normalize_event(raw, include_inplayoffs=False) == expected_fetch
    assert fetch_mtgo.build_clean_data(raw) == expected_fetch


def test_download_retry_policy_is_injectable_and_bounded():
    calls = []
    waits = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) < 3:
            raise OSError("temporary")
        return Response("ok")

    assert download_page(
        "https://example.test/event",
        attempts=3,
        retry_delay=1,
        request_get=request,
        sleep=waits.append,
    ) == "ok"
    assert len(calls) == 3
    assert waits == [1, 1]
    assert calls[0][1]["timeout"] == 90
    assert "User-Agent" in calls[0][1]["headers"]

    with pytest.raises(MTGOFetchError, match="after 2 attempts"):
        download_page(
            "https://example.test/fail",
            attempts=2,
            retry_delay=0,
            request_get=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("down")),
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
    assert parse_event_link("/decklist/premodern-challenge-2026-07-201236", FORMATS)[0] == "other"
    assert batch_mtgo.parse_link("/decklist/modern-challenge-2026-07-201238") == (
        "modern",
        "2026-07-20",
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
    assert destination == tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    assert json.loads(destination.read_text(encoding="utf-8")) == expected_batch_event()
    assert len(calls) == 1


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
        f"https://www.mtgo.com{event_link}",
    ]
    assert (tmp_path / "fetched.txt").read_text(encoding="utf-8") == event_link + "\n"
    destination = tmp_path / "data" / "standard" / "Standard_Challenge_32_12345.json"
    assert json.loads(destination.read_text(encoding="utf-8")) == expected_batch_event()


def test_non_executable_format_event_collection_uses_its_own_path(tmp_path):
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
    with pytest.raises(DisabledFormatError, match="not enabled"):
        load_rules_for_format(tmp_path, "modern", registry_path=REGISTRY)


def test_collection_disabled_format_fails_before_ledger_network_or_storage(tmp_path):
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    modern["mtgo"]["event_collection_enabled"] = False
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
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


def test_standard_classification_dispatch_matches_the_legacy_parent_api():
    event_path = ROOT / "data" / "standard" / "Standard_Challenge_32_12838092.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    rule_set = load_rules_for_format(ROOT, "standard")
    results = classify_event(event, rule_set)
    legacy_rules = classify_standard.load_rules()
    assert len(results) == len(event["players"])
    for player, result in zip(event["players"], results, strict=True):
        main, side = classify_standard.deck_to_counts(player)
        assert result.archetype_name == classify_standard.match_archetype(main, side, legacy_rules)

    with pytest.raises(DisabledFormatError, match="not enabled"):
        load_rules_for_format(ROOT, "modern")


def test_p3_03_target_modules_exist_and_production_workflow_is_unchanged():
    contract = json.loads(
        (ROOT / "tests" / "fixtures" / "mtgo" / "format_pipeline_contract.json").read_text(
            encoding="utf-8"
        )
    )
    unit = next(item for item in contract["migration_units"] if item["task"] == "P3-03")
    assert all((ROOT / path).is_file() for path in unit["target_modules"])
    workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
    assert "python -B batch_mtgo.py" not in workflow
    assert "python -B -m mtgmeta.mtgo" in workflow
