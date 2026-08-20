from pathlib import Path
from types import SimpleNamespace

import pytest

from mtgmeta.mtgo import __main__ as mtgo_cli
from mtgmeta.mtgo import fetch


class _Response:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def _event_html(payload: str) -> str:
    return f"<script>{fetch.DECKLIST_MARKER} {payload};</script>"


def test_missing_event_marker_is_a_retryable_source_response():
    with pytest.raises(fetch.MTGOPageUnavailableError):
        fetch.download_event_data(
            "https://www.mtgo.com/decklist/example",
            attempts=1,
            request_get=lambda *_args, **_kwargs: _Response("temporary edge page"),
        )


def test_invalid_event_contract_remains_non_retryable():
    html = _event_html(
        '{"event_id":"1","description":"Example","player_count":"32",'
        '"inplayoffs":"1","decklists":"invalid","standings":[],'
        '"final_rank":[]}'
    )

    with pytest.raises(fetch.MTGOParseError) as raised:
        fetch.download_event_data(
            "https://www.mtgo.com/decklist/example",
            attempts=1,
            request_get=lambda *_args, **_kwargs: _Response(html),
        )

    assert not isinstance(raised.value, fetch.MTGOPageUnavailableError)


def test_month_listing_ignores_cross_month_links():
    html = " ".join(
        (
            "/decklist/pioneer-challenge-2026-08-201",
            "/decklist/pioneer-challenge-2026-07-202",
        )
    )
    waits: list[float] = []

    links = fetch._observe_listing(
        "https://www.mtgo.com/decklists/2026/08",
        "pioneer",
        set(),
        year=2026,
        month=8,
        request_get=lambda *_args, **_kwargs: _Response(html),
        wait=waits.append,
    )

    assert links == ["/decklist/pioneer-challenge-2026-08-201"]
    assert waits == [2, 2]


def test_listing_outage_stops_the_remaining_months(monkeypatch, tmp_path: Path):
    events = tmp_path / "data" / "standard"
    context = SimpleNamespace(repository_root=tmp_path, paths={"events": events})
    monkeypatch.setattr(
        fetch,
        "load_mtgo_event_collection_context",
        lambda *_args, **_kwargs: context,
    )
    calls: list[str] = []

    def unavailable(url, *_args, **_kwargs):
        calls.append(url)
        raise fetch.MTGOFetchError("temporary listing outage")

    monkeypatch.setattr(fetch, "_observe_listing", unavailable)

    summary = fetch.fetch_event_months(
        tmp_path,
        "standard",
        months=[(2026, 8), (2026, 7)],
        inter_event_delay=0,
    )

    assert calls == ["https://www.mtgo.com/decklists/2026/08"]
    assert summary["failed"] == 1
    assert summary["transient_failed"] == 1


@pytest.mark.parametrize(
    ("failed", "transient_failed", "expected"),
    ((0, 0, 0), (1, 1, mtgo_cli.TRANSIENT_FAILURE_EXIT_CODE), (2, 1, 1)),
)
def test_fetch_events_exit_code_distinguishes_transient_failures(
    monkeypatch, tmp_path: Path, failed: int, transient_failed: int, expected: int
):
    summary = {
        "candidates": 0,
        "fetched": 0,
        "skipped": 0,
        "excluded_no_playoff": 0,
        "deferred_incomplete": 0,
        "failed": failed,
        "transient_failed": transient_failed,
        "warnings": [],
        "errors": [],
    }
    monkeypatch.setattr(
        mtgo_cli.fetch,
        "fetch_event_months",
        lambda *_args, **_kwargs: summary,
    )
    args = SimpleNamespace(format_id="standard", months=None)

    assert mtgo_cli._run_fetch_events(args, tmp_path, tmp_path / "formats.yaml") == expected
