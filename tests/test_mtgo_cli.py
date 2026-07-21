"""P3-07 tests for the explicit MTGO command entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtgmeta.mtgo import __main__ as cli


ROOT = Path(__file__).resolve().parents[1]


def test_parser_requires_an_explicit_format(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["build-statistics"])
    assert exc_info.value.code == 2
    assert "--format" in capsys.readouterr().err


def test_disabled_format_fails_before_runner_side_effects(monkeypatch, capsys):
    calls = []
    monkeypatch.setitem(cli.RUNNERS, "build-statistics", lambda *_args: calls.append(True))
    assert cli.main(["--root", str(ROOT), "--format", "pauper", "build-statistics"]) == 2
    assert calls == []
    assert "not enabled" in capsys.readouterr().err


def test_event_and_match_fetch_arguments_are_forwarded(monkeypatch):
    captured = {}

    def fake_events(root, format_id, **kwargs):
        captured["events"] = (root, format_id, kwargs)
        return {
            "candidates": 2,
            "fetched": 1,
            "skipped": 1,
            "excluded_no_playoff": 0,
            "deferred_incomplete": 0,
            "failed": 0,
            "warnings": [],
            "errors": [],
        }

    def fake_matches(root, format_id, **kwargs):
        captured["matches"] = (root, format_id, kwargs)
        return {
            "requested": 1,
            "fetched": 1,
            "skipped": 0,
            "not_found": 0,
            "failed": 0,
            "errors": [],
        }

    monkeypatch.setattr(cli.fetch, "fetch_event_months", fake_events)
    monkeypatch.setattr(cli.matchup, "fetch_and_store_matches", fake_matches)
    assert cli.main([
        "--root", str(ROOT), "--format", "modern", "fetch-events", "--month", "2026-07"
    ]) == 0
    assert cli.main([
        "--root", str(ROOT), "--format", "standard", "fetch-matches", "123", "--force"
    ]) == 0
    assert captured["events"][0:2] == (ROOT, "modern")
    assert captured["events"][2]["months"] == [(2026, 7)]
    assert captured["matches"][0:2] == (ROOT, "standard")
    assert captured["matches"][2]["event_ids"] == ["123"]
    assert captured["matches"][2]["force"] is True


def test_event_fetch_reports_deferred_events_without_failing(monkeypatch, capsys):
    source = "https://www.mtgo.com/decklist/legacy-pending"
    monkeypatch.setattr(
        cli.fetch,
        "fetch_event_months",
        lambda *_args, **_kwargs: {
            "candidates": 1,
            "fetched": 0,
            "skipped": 0,
            "excluded_no_playoff": 0,
            "deferred_incomplete": 1,
            "failed": 0,
            "warnings": [(source, "MTGO event decklists have not been published yet")],
            "errors": [],
        },
    )
    assert cli.main(["--root", str(ROOT), "--format", "legacy", "fetch-events"]) == 0
    captured = capsys.readouterr()
    assert "deferred=1 failed=0" in captured.out
    assert f"DEFERRED {source}" in captured.err


def test_event_fetch_keeps_persistent_parse_errors_fatal(monkeypatch, capsys):
    source = "https://www.mtgo.com/decklist/legacy-malformed"
    monkeypatch.setattr(
        cli.fetch,
        "fetch_event_months",
        lambda *_args, **_kwargs: {
            "candidates": 1,
            "fetched": 0,
            "skipped": 0,
            "excluded_no_playoff": 0,
            "deferred_incomplete": 0,
            "failed": 1,
            "warnings": [],
            "errors": [(source, "MTGO decklist marker was not found")],
        },
    )
    assert cli.main(["--root", str(ROOT), "--format", "legacy", "fetch-events"]) == 1
    assert f"ERROR {source}" in capsys.readouterr().err


def test_statistics_matchups_pickup_and_metadata_dispatch(monkeypatch):
    captured = []
    output = ROOT / "stats" / "standard" / "mtgo"
    monkeypatch.setattr(
        cli.stats,
        "build_all_stats",
        lambda root, format_id, **kwargs: captured.append(("stats", root, format_id, kwargs))
        or {"index.json": output / "index.json"},
    )
    monkeypatch.setattr(
        cli.matchup,
        "build_all_matchups",
        lambda root, format_id, **kwargs: captured.append(("matchups", root, format_id, kwargs))
        or ({"matchup_index.json": output / "matchup_index.json"}, {1: {"counted": 7}}),
    )
    monkeypatch.setattr(
        cli.pickup,
        "generate_candidates",
        lambda root, format_id, **kwargs: captured.append(("candidates", root, format_id, kwargs))
        or {
            "candidate_path": output / "pickup" / "candidates_2026-W28.yaml",
            "skipped_existing": True,
        },
    )
    monkeypatch.setattr(
        cli.pickup,
        "generate_metadata",
        lambda root, format_id, **kwargs: captured.append(("metadata", root, format_id, kwargs))
        or output / "meta.json",
    )
    base = ["--root", str(ROOT), "--format", "standard"]
    assert cli.main(base + ["build-statistics"]) == 0
    assert cli.main(base + ["build-matchups"]) == 0
    assert cli.main(base + ["pickup", "candidates", "--if-absent"]) == 0
    assert cli.main(base + ["generate-metadata"]) == 0
    assert [entry[0] for entry in captured] == ["stats", "matchups", "candidates", "metadata"]
    assert captured[2][3]["preserve_existing"] is True


def test_invalid_month_is_rejected_by_argparse():
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--format", "standard", "fetch-events", "--month", "2026-13"])
    assert exc_info.value.code == 2


def test_collection_disabled_format_fails_before_runner(monkeypatch, tmp_path, capsys):
    registry = __import__("yaml").safe_load(
        (ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8")
    )
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    modern["mtgo"]["event_collection_enabled"] = False
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(
        __import__("yaml").safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setitem(cli.RUNNERS, "fetch-events", lambda *_args: calls.append(True))
    assert cli.main([
        "--root", str(ROOT), "--registry", str(registry_path),
        "--format", "modern", "fetch-events",
    ]) == 2
    assert calls == []
    assert "event collection" in capsys.readouterr().err
