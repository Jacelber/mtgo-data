"""P3-05 format-aware Videre and matchup regression coverage."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import shutil
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import DisabledFormatError, UnknownFormatError
from mtgmeta.mtgo.matchup import (
    MTGOMatchupError,
    build_all_matchups,
    event_ids_from_fetched,
    fetch_all_matches,
    fetch_and_store_matches,
)


def make_repository(tmp_path: Path) -> Path:
    (tmp_path / "configs").mkdir()
    shutil.copyfile(ROOT / "configs" / "formats.yaml", tmp_path / "configs" / "formats.yaml")
    return tmp_path


def test_event_discovery_selects_only_the_explicit_format(tmp_path):
    source = tmp_path / "fetched.txt"
    source.write_text(
        "\n".join(
            [
                "/decklist/standard-challenge-32-2026-07-1812345001",
                "/decklist/pauper-challenge-32-2026-07-1812345002",
                "/decklist/standard-challenge-64-2026-07-1912345003",
                "/decklist/standard-challenge-32-2026-07-1812345001",
            ]
        ),
        encoding="utf-8",
    )
    assert event_ids_from_fetched(source, "standard") == ["12345001", "12345003"]
    assert event_ids_from_fetched(source, "pauper") == ["12345002"]


def test_videre_pagination_preserves_all_rows_and_offsets():
    calls = []

    def getter(format_id, params):
        calls.append((format_id, dict(params)))
        if params["offset"] == 0:
            return {"data": [{"round": 1}], "meta": {"has_more": True, "next_offset": 500}}
        return {"data": [{"round": 2}], "meta": {"has_more": False}}

    assert fetch_all_matches("standard", "123", api_getter=getter) == [
        {"round": 1},
        {"round": 2},
    ]
    assert [call[1]["offset"] for call in calls] == [0, 500]
    assert {call[0] for call in calls} == {"standard"}


def test_standard_fetch_uses_registry_match_path_and_skip_contract(tmp_path):
    root = make_repository(tmp_path)
    calls = []

    def fetcher(format_id, event_id):
        calls.append((format_id, event_id))
        return [{"player": "A", "opponent": "B", "result": "win", "round": 1}]

    first = fetch_and_store_matches(
        root,
        "standard",
        event_ids=["123"],
        api_fetcher=fetcher,
        sleep=lambda _: None,
    )
    destination = root / "data" / "standard" / "mtgo" / "matches" / "123.json"
    assert first["fetched"] == 1
    assert destination.is_file()
    assert json.loads(destination.read_text(encoding="utf-8"))["event_id"] == 123
    second = fetch_and_store_matches(
        root,
        "standard",
        event_ids=["123"],
        api_fetcher=fetcher,
        sleep=lambda _: None,
    )
    assert second["skipped"] == 1
    assert calls == [("standard", "123")]


@pytest.mark.parametrize("format_id,error", [("pauper", DisabledFormatError), ("missing", UnknownFormatError)])
def test_unavailable_formats_fail_before_network_or_output(tmp_path, format_id, error):
    root = make_repository(tmp_path)
    called = False

    def fetcher(_format_id, _event_id):
        nonlocal called
        called = True
        return []

    with pytest.raises(error):
        fetch_and_store_matches(root, format_id, event_ids=["123"], api_fetcher=fetcher)
    assert called is False
    assert not (root / "data" / format_id).exists()


def test_unsafe_event_id_is_rejected_before_network_and_storage(tmp_path):
    root = make_repository(tmp_path)
    called = False

    def fetcher(_format_id, _event_id):
        nonlocal called
        called = True
        return []

    with pytest.raises(MTGOMatchupError, match="digits only"):
        fetch_and_store_matches(root, "standard", event_ids=["../escape"], api_fetcher=fetcher)
    assert called is False
    assert not (root / "data").exists()


@pytest.mark.committed_baseline
def test_fixed_reference_standard_matchups_are_byte_identical(tmp_path):
    import stats_matchup

    written, statistics = stats_matchup.build_all_matchups(
        today=date(2026, 7, 19),
        generated_at="2026-07-19T21:00:07",
        output_directory=tmp_path,
    )
    assert {weeks: values["counted"] for weeks, values in statistics.items()} == {
        1: 619,
        4: 2564,
        12: 6732,
        36: 8247,
    }
    for filename, path in written.items():
        assert path.read_bytes() == (ROOT / "stats" / "standard" / "mtgo" / filename).read_bytes()


def test_disabled_matchup_generation_has_no_output_side_effect(tmp_path):
    output = tmp_path / "output"
    with pytest.raises(DisabledFormatError):
        build_all_matchups(ROOT, "pauper", output_directory=output)
    assert not output.exists()


def test_legacy_standard_wrapper_matches_shared_event_mapping():
    import stats_matchup

    legacy = stats_matchup.load_official_events(stats_matchup.load_rules())
    from mtgmeta.mtgo.matchup import load_official_events

    assert legacy == load_official_events(ROOT, "standard")


def test_legacy_fetch_wrapper_selects_standard(monkeypatch):
    import fetch_videre_matches

    captured = {}

    def fake_fetch(root, format_id, **kwargs):
        captured.update(root=root, format_id=format_id, kwargs=kwargs)
        return {
            "requested": 1,
            "fetched": 0,
            "skipped": 1,
            "not_found": 0,
            "failed": 0,
            "missing_event_ids": [],
            "errors": [],
        }

    monkeypatch.setattr(fetch_videre_matches._shared, "fetch_and_store_matches", fake_fetch)
    assert fetch_videre_matches.main(["123"]) == 0
    assert captured["format_id"] == "standard"
    assert captured["kwargs"]["event_ids"] == ["123"]
