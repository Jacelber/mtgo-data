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
from mtgmeta.rules import (
    ArchetypeDefinition,
    CardCondition,
    ClassificationRule,
    RuleSet,
    SubtypeDefinition,
)
from mtgmeta.mtgo import matchup
from mtgmeta.mtgo.matchup import (
    MatchupIdentity,
    MTGOMatchupError,
    accumulate_hierarchical_event,
    aggregate_matchup_counts,
    build_all_matchups,
    build_hierarchical_window,
    build_matchup_hierarchy,
    event_ids_from_fetched,
    fetch_all_matches,
    fetch_and_store_matches,
    load_hierarchical_events_from_directory,
    rollup_matchup_counts,
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


def test_draws_count_as_half_a_win_for_rate_and_wilson_input():
    emitted = matchup._emit_cell(
        {"wins": 1, "losses": 0, "draws": 1},
        False,
    )
    assert emitted["win_rate"] == 0.75
    assert emitted["ci_half"] == round(matchup.wilson_half_width(1.5, 2), 4)


def test_modern_hierarchy_uses_stable_parent_and_composite_subtype_ids():
    rules = matchup.load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    hierarchy = build_matchup_hierarchy(rules)
    assert len(hierarchy["parents"]) == 55
    assert len(hierarchy["leaves"]) == 92
    assert sum(item["expandable"] for item in hierarchy["parents"]) == 17
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
    document, stats = build_hierarchical_window(
        [(date(2026, 7, 13), "123", identities, set(identities))],
        date(2026, 7, 13),
        1,
        matches_directory=matches,
        format_id="modern",
        rule_set=_hierarchical_rule_set(),
    )
    assert stats["counted"] == 1
    assert document["hierarchical"] is True
    assert document["canonical_level"] == "leaf"
    assert document["parent_order"] == ["alpha", "beta"]
    assert document["leaf_order"] == ["alpha/one", "beta"]
    assert document["parent_matrix"]["alpha"]["beta"]["wins"] == 1
    assert document["leaf_matrix"]["alpha/one"]["beta"]["wins"] == 1
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


@pytest.mark.committed_baseline
def test_fixed_reference_standard_matchups_are_byte_identical(tmp_path):
    import stats_matchup

    committed_index = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "matchup_index.json").read_text(
            encoding="utf-8"
        )
    )
    reference_date = date.fromisoformat(committed_index["generated"][:10])
    written, statistics = stats_matchup.build_all_matchups(
        today=reference_date,
        generated_at=committed_index["generated"],
        output_directory=tmp_path,
    )
    assert {weeks: values["counted"] for weeks, values in statistics.items()} == {
        item["weeks"]: item["counted_matches"] for item in committed_index["ranges"]
    }
    for filename, path in written.items():
        assert path.read_bytes() == (ROOT / "stats" / "standard" / "mtgo" / filename).read_bytes()


@pytest.mark.committed_baseline
def test_fixed_reference_modern_matchups_are_byte_identical(tmp_path):
    committed_directory = ROOT / "stats" / "modern" / "mtgo"
    committed_index = json.loads(
        (committed_directory / "matchup_index.json").read_text(encoding="utf-8")
    )
    reference_date = date.fromisoformat(committed_index["generated"][:10])
    written, statistics = build_all_matchups(
        ROOT,
        "modern",
        today=reference_date,
        generated_at=committed_index["generated"],
        output_directory=tmp_path,
    )
    assert {weeks: values["counted"] for weeks, values in statistics.items()} == {
        item["weeks"]: item["counted_matches"]
        for item in committed_index["ranges"]
    }
    for filename, path in written.items():
        assert path.read_bytes() == (committed_directory / filename).read_bytes()


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
