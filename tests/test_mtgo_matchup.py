"""P3-05 format-aware Videre and matchup regression coverage."""

from __future__ import annotations

from datetime import date
import io
import json
from pathlib import Path
import shutil
import sys
import urllib.error

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import DisabledFormatError, UnknownFormatError
from mtgmeta.rules import (
    ArchetypeDefinition,
    CardCondition,
    ClassificationRule,
    RuleSet,
    SubtypeDefinition,
)
from mtgmeta.mtgo import matchup
from mtgmeta.mtgo.completeness import build_videre_coverage
from mtgmeta.mtgo.matchup import (
    MatchupIdentity,
    MTGOMatchupError,
    VidereUnavailable,
    accumulate_hierarchical_event,
    aggregate_matchup_counts,
    build_all_matchups,
    build_hierarchical_window,
    build_matchup_hierarchy,
    event_ids_from_fetched,
    api_get,
    fetch_all_matches,
    fetch_and_store_matches,
    load_hierarchical_events_from_directory,
    rollup_matchup_counts,
)


class VidereResponse:
    def __init__(self, value):
        self.body = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


def videre_http_error(code, body=None):
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    return urllib.error.HTTPError(
        "https://example.test/videre",
        code,
        "test error",
        {},
        io.BytesIO(payload),
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
                "/decklist/premodern-challenge-32-2026-07-1812345004",
                "/decklist/modern-challenge-32-2026-07-1812345005",
            ]
        ),
        encoding="utf-8",
    )
    assert event_ids_from_fetched(source, "standard") == ["12345001", "12345003"]
    assert event_ids_from_fetched(source, "pauper") == ["12345002"]
    assert event_ids_from_fetched(source, "modern") == ["12345005"]


@pytest.mark.parametrize("status", (408, 429, 503, 599))
def test_videre_request_retries_transient_http_error_then_returns_success(
    status,
    caplog,
):
    outcomes = [
        videre_http_error(status),
        VidereResponse({"data": [], "meta": {"has_more": False}}),
    ]
    waits = []

    def opener(_request, *, timeout):
        assert timeout == 30
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    result = api_get(
        "modern",
        {"event_id": "12838888"},
        opener=opener,
        retry_delay=2,
        sleep=waits.append,
    )
    assert result == {"data": [], "meta": {"has_more": False}}
    assert waits == [2]
    assert f"attempt 1/3 failed with HTTP Error {status}" in caplog.text


@pytest.mark.parametrize(
    "failure",
    (
        TimeoutError("timed out"),
        ConnectionError("connection reset"),
        urllib.error.URLError("temporary transport failure"),
    ),
    ids=("timeout", "connection-error", "url-error"),
)
def test_videre_request_retries_transport_failure_then_returns_success(failure):
    outcomes = [
        failure,
        VidereResponse({"data": [], "meta": {"has_more": False}}),
    ]
    waits = []

    def opener(_request, **_kwargs):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    result = api_get(
        "modern",
        {"event_id": "12838888"},
        opener=opener,
        retry_delay=1,
        sleep=waits.append,
    )
    assert result == {"data": [], "meta": {"has_more": False}}
    assert waits == [1]


def test_videre_request_retries_408_then_preserves_no_results_contract():
    outcomes = [
        videre_http_error(408),
        videre_http_error(400, {"message": "No results found."}),
    ]
    waits = []

    def opener(_request, **_kwargs):
        raise outcomes.pop(0)

    with pytest.raises(matchup.NoResults):
        api_get(
            "modern",
            {"event_id": "12838888"},
            opener=opener,
            retry_delay=1,
            sleep=waits.append,
        )
    assert waits == [1]


def test_videre_request_exhausts_bounded_retries_as_source_unavailable():
    calls = []
    waits = []

    def opener(_request, **_kwargs):
        calls.append(True)
        raise videre_http_error(408)

    with pytest.raises(VidereUnavailable) as captured:
        api_get(
            "modern",
            {"event_id": "12838888"},
            opener=opener,
            attempts=3,
            retry_delay=1,
            sleep=waits.append,
        )
    assert isinstance(captured.value.__cause__, urllib.error.HTTPError)
    assert captured.value.__cause__.code == 408
    assert len(calls) == 3
    assert waits == [1, 1]


def test_videre_request_does_not_retry_non_transient_http_error():
    calls = []
    waits = []

    def opener(_request, **_kwargs):
        calls.append(True)
        raise videre_http_error(404)

    with pytest.raises(urllib.error.HTTPError) as captured:
        api_get(
            "modern",
            {"event_id": "123"},
            opener=opener,
            retry_delay=1,
            sleep=waits.append,
        )
    assert captured.value.code == 404
    assert len(calls) == 1
    assert waits == []


@pytest.mark.parametrize(
    "options",
    (
        {"attempts": 0},
        {"attempts": True},
        {"timeout": 0},
        {"timeout": True},
        {"retry_delay": -1},
        {"retry_delay": True},
    ),
)
def test_videre_request_rejects_invalid_retry_limits(options):
    with pytest.raises(ValueError):
        api_get("modern", {"event_id": "123"}, **options)


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


def test_transient_videre_outage_is_reported_as_missing_without_blocking_other_events(tmp_path):
    root = make_repository(tmp_path)

    def fetcher(_format_id, event_id):
        if event_id == "123":
            raise VidereUnavailable("HTTP Error 503: Service Unavailable")
        return [{"player": "A", "opponent": "B", "result": "win", "round": 1}]

    summary = fetch_and_store_matches(
        root,
        "standard",
        event_ids=["123", "124"],
        api_fetcher=fetcher,
        sleep=lambda _: None,
    )

    assert summary["source_unavailable"] == 1
    assert summary["source_unavailable_event_ids"] == ["123"]
    assert summary["missing_event_ids"] == ["123"]
    assert summary["warnings"] == [("123", "HTTP Error 503: Service Unavailable")]
    assert summary["fetched"] == 1
    assert summary["failed"] == 0
    matches = root / "data" / "standard" / "mtgo" / "matches"
    assert (matches / "124.json").is_file()

    coverage = build_videre_coverage(
        [
            (date(2026, 7, 18), {"event_id": 123}),
            (date(2026, 7, 19), {"event_id": 124}),
        ],
        matches,
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
    )
    assert coverage["available_event_ids"] == ["124"]
    assert coverage["missing_event_ids"] == ["123"]
    assert coverage["completeness_rate"] == 0.5


def test_non_transient_match_fetch_error_remains_fatal(tmp_path):
    root = make_repository(tmp_path)

    def fetcher(_format_id, _event_id):
        raise MTGOMatchupError("Videre response data must be a list of objects")

    summary = fetch_and_store_matches(
        root,
        "standard",
        event_ids=["123"],
        api_fetcher=fetcher,
    )

    assert summary["source_unavailable"] == 0
    assert summary["failed"] == 1
    assert summary["errors"] == [
        ("123", "Videre response data must be a list of objects")
    ]


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


def test_draws_count_as_half_a_win_for_rate_and_wilson_input():
    emitted = matchup._emit_cell(
        {"wins": 1, "losses": 0, "draws": 1},
        False,
    )
    assert emitted["win_rate"] == 0.75
    assert emitted["ci_half"] == round(matchup.wilson_half_width(1.5, 2), 4)


def test_literal_match_record_counts_draws_only_in_the_denominator():
    emitted = matchup._emit_cell(
        {"wins": 1, "losses": 0, "draws": 1},
        False,
    )
    assert emitted["win_rate"] == 0.75
    assert emitted["literal_record"] == {
        "wins": 1,
        "losses": 0,
        "draws": 1,
        "matches": 2,
        "win_rate": 0.5,
        "win_rate_method": "wins_over_valid_matches",
        "confidence_interval_95": {
            "lower": 0.094529,
            "upper": 0.905471,
        },
    }


def test_identity_match_records_include_mirrors_without_replacing_non_mirror():
    matrix = {
        "alpha": {
            "alpha": {"wins": 1, "losses": 1, "draws": 0},
            "beta": {"wins": 2, "losses": 1, "draws": 1},
        },
        "beta": {
            "alpha": {"wins": 1, "losses": 2, "draws": 1},
        },
    }
    records = matchup._emit_match_records(matrix, ["alpha", "beta"])
    assert records["alpha"]["all_matches"]["matches"] == 6
    assert records["alpha"]["all_matches"]["win_rate"] == 0.5
    assert records["alpha"]["non_mirror"]["matches"] == 4
    assert records["alpha"]["non_mirror"]["win_rate"] == 0.5
    assert records["alpha"]["mirror_match_count"] == 1
    assert records["beta"]["all_matches"] == records["beta"]["non_mirror"]
    assert records["beta"]["mirror_match_count"] == 0


def test_modern_hierarchy_uses_stable_parent_and_composite_subtype_ids():
    rules = matchup.load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    hierarchy = build_matchup_hierarchy(rules)
    assert len(hierarchy["parents"]) == 127
    assert len(hierarchy["leaves"]) == 176
    assert sum(item["expandable"] for item in hierarchy["parents"]) == 19
    broodscale = next(
        item for item in hierarchy["parents"] if item["id"] == "broodscale-combo"
    )
    assert broodscale == {
        "id": "broodscale-combo",
        "name": "Broodscale Combo",
        "expandable": True,
        "subtype_ids": [
            "broodscale-combo/golgari",
            "broodscale-combo/gruul",
            "broodscale-combo/mono-green",
            "broodscale-combo/simic",
        ],
    }


def _hierarchical_rule_set() -> RuleSet:
    return RuleSet(
        schema_version="1.0.0",
        format="modern",
        archetypes=(
            ArchetypeDefinition(
                id="alpha",
                name="Alpha",
                priority=100,
                subtypes=(
                    SubtypeDefinition("one", "One", "alpha"),
                    SubtypeDefinition("two", "Two", "alpha"),
                ),
                rules=(
                    ClassificationRule(
                        "alpha-one",
                        100,
                        "one",
                        (CardCondition("Alpha One", "main", min_count=1),),
                    ),
                    ClassificationRule(
                        "alpha-two",
                        90,
                        "two",
                        (CardCondition("Alpha Two", "main", min_count=1),),
                    ),
                ),
            ),
            ArchetypeDefinition(
                id="beta",
                name="Beta",
                priority=80,
                subtypes=(),
                rules=(
                    ClassificationRule(
                        "beta-primary",
                        80,
                        None,
                        (CardCondition("Beta Card", "main", min_count=1),),
                    ),
                ),
            ),
        ),
    )


def _identity(parent, name, subtype=None, subtype_name=None):
    return MatchupIdentity(parent, name, subtype, subtype_name)


def test_hierarchical_counts_roll_up_without_losing_sibling_matchups(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    (matches / "123.json").write_text(
        json.dumps(
            {
                "event_id": 123,
                "matches": [
                    {
                        "player": "A1",
                        "opponent": "A2",
                        "result": "win",
                        "round": 1,
                    },
                    {
                        "player": "A2",
                        "opponent": "A1",
                        "result": "loss",
                        "round": 1,
                    },
                    {
                        "player": "A1",
                        "opponent": "B",
                        "result": "loss",
                        "round": 2,
                    },
                    {
                        "player": "B",
                        "opponent": "A2",
                        "result": "draw",
                        "round": 3,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    identities = {
        "A1": _identity("alpha", "Alpha", "one", "One"),
        "A2": _identity("alpha", "Alpha", "two", "Two"),
        "B": _identity("beta", "Beta"),
    }
    leaf_matrix = {}
    stats = {
        key: 0
        for key in (
            "no_match_file",
            "physical_matches",
            "dedup_skipped",
            "counted",
            "dropped_unmapped",
            "cross_matches",
            "mirror_matches",
            "drop_reason_unknown_deck",
            "drop_reason_not_in_official",
        )
    }
    accumulate_hierarchical_event(
        matches,
        "123",
        identities,
        set(identities),
        leaf_matrix,
        set(),
        stats,
    )
    assert stats["physical_matches"] == 3
    assert stats["dedup_skipped"] == 1
    assert stats["counted"] == 3
    assert stats["mirror_matches"] == 1
    assert stats["cross_matches"] == 2
    assert leaf_matrix["alpha/one"]["alpha/two"] == {
        "wins": 1,
        "losses": 0,
        "draws": 0,
    }
    parent = rollup_matchup_counts(
        leaf_matrix,
        {
            "alpha/one": "alpha",
            "alpha/two": "alpha",
            "beta": "beta",
        },
    )
    assert parent["alpha"]["alpha"] == {
        "wins": 1,
        "losses": 1,
        "draws": 0,
    }
    assert parent["alpha"]["beta"] == {
        "wins": 0,
        "losses": 1,
        "draws": 1,
    }
    assert parent["beta"]["alpha"] == {
        "wins": 1,
        "losses": 0,
        "draws": 1,
    }
    identity = {leaf_id: leaf_id for leaf_id in leaf_matrix}
    leaf_to_parent = {
        "alpha/one": "alpha",
        "alpha/two": "alpha",
        "beta": "beta",
    }
    subtype_against_parent = aggregate_matchup_counts(
        leaf_matrix,
        identity,
        leaf_to_parent,
    )
    parent_against_subtype = aggregate_matchup_counts(
        leaf_matrix,
        leaf_to_parent,
        identity,
    )
    assert subtype_against_parent["alpha/one"]["alpha"]["wins"] == 1
    assert subtype_against_parent["alpha/two"]["alpha"]["losses"] == 1
    assert parent_against_subtype["alpha"]["alpha/one"]["losses"] == 1
    assert parent_against_subtype["alpha"]["alpha/two"]["wins"] == 1


def test_hierarchical_window_exposes_parent_and_leaf_views(tmp_path):
    matches = tmp_path / "matches"
    matches.mkdir()
    (matches / "123.json").write_text(
        json.dumps(
            {
                "event_id": 123,
                "matches": [
                    {
                        "player": "A1",
                        "opponent": "B",
                        "result": "win",
                        "round": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    identities = {
        "A1": _identity("alpha", "Alpha", "one", "One"),
        "B": _identity("beta", "Beta"),
    }
    modern_rules = _hierarchical_rule_set()
    standard_rules = RuleSet(
        modern_rules.schema_version,
        "standard",
        modern_rules.archetypes,
    )
    document, stats = build_hierarchical_window(
        [(date(2026, 7, 13), "123", identities, set(identities))],
        date(2026, 7, 13),
        1,
        matches_directory=matches,
        format_id="standard",
        rule_set=standard_rules,
    )
    assert stats["counted"] == 1
    assert document["hierarchical"] is True
    assert document["canonical_level"] == "leaf"
    assert document["parent_order"] == ["alpha", "beta"]
    assert document["leaf_order"] == ["alpha/one", "beta"]
    assert document["parent_matrix"]["alpha"]["beta"]["wins"] == 1
    assert document["leaf_matrix"]["alpha/one"]["beta"]["wins"] == 1
    assert document["archetype_order"] == ["Alpha", "Beta"]
    assert document["overall"] == {
        "Alpha": document["parent_overall"]["alpha"],
        "Beta": document["parent_overall"]["beta"],
    }
    parent_names = {"alpha": "Alpha", "beta": "Beta"}
    assert document["matrix"] == {
        parent_names[row_id]: {
            parent_names[column_id]: cell
            for column_id, cell in columns.items()
        }
        for row_id, columns in document["parent_matrix"].items()
    }
    assert next(
        item for item in document["hierarchy"]["parents"] if item["id"] == "alpha"
    )["expandable"] is True


def test_subtype_defining_parent_without_selection_is_blocking():
    rules = _hierarchical_rule_set()
    broken = RuleSet(
        rules.schema_version,
        rules.format,
        (
            ArchetypeDefinition(
                id="alpha",
                name="Alpha",
                priority=100,
                subtypes=rules.archetypes[0].subtypes,
                rules=(
                    ClassificationRule(
                        "alpha-null",
                        100,
                        None,
                        (CardCondition("Alpha One", "main", min_count=1),),
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(MTGOMatchupError, match="defines subtypes but selected none"):
        matchup._classify_identity(
            {"main_deck": [{"name": "Alpha One", "qty": 4}], "side_deck": []},
            broken,
        )


def test_hierarchical_loader_rejects_cross_format_input(tmp_path):
    events = tmp_path / "events"
    events.mkdir()
    (events / "premodern.json").write_text(
        json.dumps(
            {
                "event_id": "123",
                "format": "CPREMODERN",
                "starttime": "2026-07-13 00:00:00.0",
                "players": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(MTGOMatchupError, match="cross-format event input rejected"):
        load_hierarchical_events_from_directory(
            events,
            _hierarchical_rule_set(),
            repository_root=tmp_path,
            format_id="modern",
        )


def test_committed_modern_leaf_counts_conserve_every_parent_rollup():
    committed_directory = ROOT / "stats" / "modern" / "mtgo"
    index = json.loads(
        (committed_directory / "matchup_index.json").read_text(encoding="utf-8")
    )
    for entry in index["ranges"]:
        document = json.loads(
            (committed_directory / entry["file"]).read_text(encoding="utf-8")
        )
        leaf_to_parent = {
            leaf["id"]: leaf["parent_id"]
            for leaf in document["hierarchy"]["leaves"]
        }
        leaf_counts = {
            row_id: {
                column_id: {
                    field: cell[field] for field in ("wins", "losses", "draws")
                }
                for column_id, cell in columns.items()
            }
            for row_id, columns in document["leaf_matrix"].items()
        }
        parent_counts = rollup_matchup_counts(leaf_counts, leaf_to_parent)
        emitted_parent_counts = {
            row_id: {
                column_id: {
                    field: cell[field] for field in ("wins", "losses", "draws")
                }
                for column_id, cell in columns.items()
            }
            for row_id, columns in document["parent_matrix"].items()
        }
        assert parent_counts == emitted_parent_counts
        assert sum(
            sum(cell.values())
            for columns in leaf_counts.values()
            for cell in columns.values()
        ) == entry["counted_matches"] * 2


def test_disabled_matchup_generation_has_no_output_side_effect(tmp_path):
    output = tmp_path / "output"
    with pytest.raises(DisabledFormatError):
        build_all_matchups(ROOT, "pauper", output_directory=output)
    assert not output.exists()
