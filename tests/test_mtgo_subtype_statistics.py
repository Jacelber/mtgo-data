"""Hierarchical parent/subtype contracts for MTGO range statistics."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from mtgmeta.config import load_rule_set
from mtgmeta.mtgo import stats
from mtgmeta.rules import build_rule_set


ROOT = Path(__file__).resolve().parents[1]
PARENT_FIELDS = (
    "name",
    "count",
    "high_score_count",
    "high_score_share",
    "top8_count",
    "top8_share",
    "conversion",
    "avg_points_per_round",
    "avg_deviation",
)


def subtype_rules():
    return build_rule_set(
        {
            "schema_version": "1.0.0",
            "format": "modern",
            "archetypes": [
                {
                    "id": "engine",
                    "name": "Engine",
                    "priority": 100,
                    "subtypes": [
                        {"id": "alpha", "name": "Alpha"},
                        {"id": "beta", "name": "Beta"},
                        {"id": "gamma", "name": "Gamma"},
                    ],
                    "rules": [
                        {
                            "id": "engine-alpha",
                            "priority": 103,
                            "subtype_id": "alpha",
                            "conditions": {"all": [{"card": "Alpha Card"}]},
                        },
                        {
                            "id": "engine-beta",
                            "priority": 102,
                            "subtype_id": "beta",
                            "conditions": {"all": [{"card": "Beta Card"}]},
                        },
                        {
                            "id": "engine-gamma",
                            "priority": 101,
                            "subtype_id": "gamma",
                            "conditions": {"all": [{"card": "Gamma Card"}]},
                        },
                    ],
                },
                {
                    "id": "other",
                    "name": "Other",
                    "priority": 50,
                    "subtypes": [],
                    "rules": [
                        {
                            "id": "other-core",
                            "priority": 50,
                            "subtype_id": None,
                            "conditions": {"all": [{"card": "Other Card"}]},
                        }
                    ],
                },
            ],
        }
    )


def player(card: str, score: int, rank: int):
    return {
        "player": f"{card}-{score}-{rank}",
        "swiss_score": score,
        "final_rank": rank,
        "main_deck": [{"name": card, "qty": 4}],
        "sideboard": [],
    }


def test_process_event_retains_selected_subtype_identity():
    rules = subtype_rules()
    processed = stats.process_event(
        {
            "player_count": 8,
            "starttime": "2026-07-20T00:00:00Z",
            "players": [player("Alpha Card", 9, 1)],
        },
        rules,
    )
    record = processed["records"][0]
    assert record["archetype_id"] == "engine"
    assert record["subtype_id"] == "alpha"
    assert record["subtype"] == "Alpha"


def test_parent_and_subtype_range_counts_conserve_with_zero_sample_taxonomy():
    rules = subtype_rules()
    records = stats.process_event(
        {
            "player_count": 8,
            "starttime": "2026-07-20T00:00:00Z",
            "players": [
                player("Alpha Card", 9, 1),
                player("Alpha Card", 3, 9),
                player("Beta Card", 6, 4),
                player("Other Card", 0, 12),
            ],
        },
        rules,
    )["records"]
    result = stats.aggregate(records, include_archetype_ids=True, rules=rules)
    parent_only = stats.aggregate(records)
    engine = next(item for item in result["archetypes"] if item["id"] == "engine")
    children = {item["id"]: item for item in engine["subtypes"]}

    assert engine["count"] == sum(item["count"] for item in children.values()) == 3
    assert engine["high_score_count"] == sum(
        item["high_score_count"] for item in children.values()
    )
    assert engine["top8_count"] == sum(
        item["top8_count"] for item in children.values()
    )
    assert children["alpha"]["count"] == 2
    assert children["alpha"]["parent_share"] == 0.6667
    assert children["alpha"]["high_score_share"] == 0.5
    assert children["alpha"]["top8_share"] == 0.5
    assert children["alpha"]["conversion"] == 1.0
    assert children["alpha"]["avg_points_per_round"] == 2.0
    assert children["beta"]["count"] == 1
    assert children["gamma"]["count"] == 0
    assert children["gamma"]["avg_points_per_round"] is None
    assert children["gamma"]["parent_share"] == 0
    assert "subtypes" not in next(
        item for item in result["archetypes"] if item["id"] == "other"
    )
    assert [
        {key: item[key] for key in PARENT_FIELDS if key in item}
        for item in result["archetypes"]
    ] == [
        {key: item[key] for key in PARENT_FIELDS if key in item}
        for item in parent_only["archetypes"]
    ]


def test_attaching_subtype_decks_preserves_parent_construction():
    rules = subtype_rules()
    records = stats.process_event(
        {
            "player_count": 8,
            "players": [
                player("Alpha Card", 9, 1),
                player("Beta Card", 6, 4),
            ],
        },
        rules,
    )["records"]
    parent_decks = {
        "Engine": {
            "archetype_id": "engine",
            "best_deck": {"player": "Parent Best"},
            "average_deck": {"sample_size": 2},
        }
    }
    expected_parent = deepcopy(parent_decks["Engine"])

    stats.attach_subtype_decks(parent_decks, records, {}, rules)

    assert {
        key: parent_decks["Engine"][key]
        for key in ("archetype_id", "best_deck", "average_deck")
    } == expected_parent
    assert [item["id"] for item in parent_decks["Engine"]["subtypes"]] == [
        "alpha",
        "beta",
        "gamma",
    ]


def test_null_subtype_under_subtype_defining_parent_fails_closed():
    rules = build_rule_set(
        {
            "schema_version": "1.0.0",
            "format": "modern",
            "archetypes": [
                {
                    "id": "engine",
                    "name": "Engine",
                    "priority": 100,
                    "subtypes": [{"id": "alpha", "name": "Alpha"}],
                    "rules": [
                        {
                            "id": "engine-alpha",
                            "priority": 101,
                            "subtype_id": "alpha",
                            "conditions": {"all": [{"card": "Alpha Card"}]},
                        },
                        {
                            "id": "engine-unassigned",
                            "priority": 100,
                            "subtype_id": None,
                            "conditions": {"all": [{"card": "Unassigned Card"}]},
                        },
                    ],
                }
            ],
        }
    )
    try:
        stats.process_event(
            {
                "player_count": 8,
                "players": [player("Unassigned Card", 3, 10)],
            },
            rules,
        )
    except stats.MTGOStatisticsError as exc:
        assert "has no selected subtype" in str(exc)
    else:
        raise AssertionError("null subtype under subtype-defining parent was accepted")


def test_committed_ranges_cover_taxonomy_and_conserve_parent_counts():
    for format_id in ("standard", "modern"):
        rules = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
        taxonomy = {
            parent.id: [subtype.id for subtype in parent.subtypes]
            for parent in rules.archetypes
            if parent.subtypes
        }
        for weeks in (1, 4, 12, 36):
            output = ROOT / "stats" / format_id / "mtgo"
            range_document = json.loads(
                (output / f"range_{weeks}w.json").read_text(encoding="utf-8")
            )
            decks_document = json.loads(
                (output / f"decks_{weeks}w.json").read_text(encoding="utf-8")
            )
            for parent in range_document["archetypes"]:
                assert parent["id"]
                expected_subtypes = taxonomy.get(parent["id"])
                deck_entry = decks_document["decks"][parent["name"]]
                assert deck_entry["archetype_id"] == parent["id"]
                if expected_subtypes is None:
                    assert "subtypes" not in parent
                    assert "subtypes" not in deck_entry
                    continue
                assert [item["id"] for item in parent["subtypes"]] == expected_subtypes
                assert [item["id"] for item in deck_entry["subtypes"]] == expected_subtypes
                assert all(
                    item["parent_id"] == parent["id"]
                    for item in parent["subtypes"]
                )
                assert sum(item["count"] for item in parent["subtypes"]) == parent["count"]
                assert sum(
                    item["high_score_count"] for item in parent["subtypes"]
                ) == parent["high_score_count"]
                assert sum(
                    item["top8_count"] for item in parent["subtypes"]
                ) == parent["top8_count"]


def test_committed_subtype_construction_uses_each_childs_own_four_week_sample():
    for format_id in ("standard", "modern"):
        output = ROOT / "stats" / format_id / "mtgo"
        range_document = json.loads(
            (output / "range_4w.json").read_text(encoding="utf-8")
        )
        decks_document = json.loads(
            (output / "decks_4w.json").read_text(encoding="utf-8")
        )
        for parent in range_document["archetypes"]:
            if "subtypes" not in parent:
                continue
            children = {
                item["id"]: item
                for item in decks_document["decks"][parent["name"]]["subtypes"]
            }
            for statistics in parent["subtypes"]:
                construction = children[statistics["id"]]
                count = statistics["count"]
                assert (construction["best_deck"] is None) == (count == 0)
                assert construction["average_deck"]["sample_size"] == (
                    count if count >= stats.MIN_SAMPLE else 0
                )
