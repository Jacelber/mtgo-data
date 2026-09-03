from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier_impact import compare_classifier_impact
from mtgmeta.melee.classification import build_classification_overlay_from_paths
from mtgmeta.weekly_review import (
    build_melee_review,
    build_mtgo_weekly_review,
    build_v2_completion_record,
    melee_record_detail,
    mtgo_record_detail,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _registry(root: Path) -> None:
    _write_yaml(
        root / "configs/formats.yaml",
        {
            "schema_version": "1.3.0",
            "formats": [
                {
                    "id": "standard",
                    "display_name": "Standard",
                    "state": "executable",
                    "public": True,
                    "mtgo": {
                        "enabled": True,
                        "event_collection_enabled": True,
                        "capabilities": ["classification"],
                        "paths": {
                            "events": "data/standard",
                            "matches": "data/standard/mtgo/matches",
                            "rules": "my_archetypes/standard.yaml",
                            "statistics": "stats/standard/mtgo",
                            "reports": "reports/standard/mtgo",
                        },
                    },
                }
            ],
        },
    )


def _rules(*, candidate: bool = False) -> dict[str, object]:
    archetypes: list[dict[str, object]] = [
        {
            "id": "alpha",
            "name": "Alpha",
            "priority": 100,
            "subtypes": [
                {"id": "one", "name": "One"},
                {"id": "two", "name": "Two"},
            ],
            "rules": [
                {
                    "id": "alpha-one-rule",
                    "priority": 100,
                    "subtype_id": "one",
                    "conditions": {
                        "all": [
                            {
                                "card": "Other Alpha Card" if candidate else "Alpha Card",
                                "zone": "main",
                            }
                        ]
                    },
                },
                {
                    "id": "alpha-two-rule",
                    "priority": 99,
                    "subtype_id": "two",
                    "conditions": {
                        "all": [
                            {
                                "card": "Alpha Card" if candidate else "Other Alpha Card",
                                "zone": "main",
                            }
                        ]
                    },
                },
            ],
        },
        {
            "id": "lost",
            "name": "Lost",
            "priority": 90,
            "rules": [
                {
                    "id": "lost-rule",
                    "priority": 90,
                    "conditions": {"all": [{"card": "Lost Card", "zone": "main"}]},
                }
            ],
        },
    ]
    if candidate:
        archetypes = [item for item in archetypes if item["id"] != "lost"]
        archetypes.extend(
            [
                {
                    "id": "new-parent",
                    "name": "New Parent",
                    "priority": 80,
                    "rules": [
                        {
                            "id": "new-rule",
                            "priority": 80,
                            "conditions": {"all": [{"card": "New Card", "zone": "main"}]},
                        }
                    ],
                },
                {
                    "id": "conflict-a",
                    "name": "Conflict A",
                    "priority": 70,
                    "rules": [
                        {
                            "id": "conflict-a-rule",
                            "priority": 70,
                            "conditions": {"all": [{"card": "Conflict Card", "zone": "main"}]},
                        }
                    ],
                },
                {
                    "id": "conflict-b",
                    "name": "Conflict B",
                    "priority": 70,
                    "rules": [
                        {
                            "id": "conflict-b-rule",
                            "priority": 70,
                            "conditions": {"all": [{"card": "Conflict Card", "zone": "main"}]},
                        }
                    ],
                },
            ]
        )
    return {"schema_version": "1.0.0", "format": "standard", "archetypes": archetypes}


def _player(rank: int, card: str, *, name: str | None = None) -> dict[str, object]:
    return {
        "player": name or f"Player {rank}",
        "loginid": str(rank),
        "swiss_rank": str(rank),
        "swiss_score": "9",
        "swiss_wins": 3,
        "opp_match_win_pct": "0.5",
        "game_win_pct": "0.5",
        "final_rank": str(rank),
        "main_deck": [{"name": card, "qty": 4}],
        "sideboard": [{"name": "Side Card", "qty": 1}],
    }


def _synthetic_root(tmp_path: Path, players: list[dict[str, object]]) -> Path:
    _registry(tmp_path)
    _write_yaml(tmp_path / "my_archetypes/standard.yaml", _rules())
    _write_yaml(
        tmp_path / "configs/mtgo_archetype_names.yaml",
        {
            "schema_version": "1.0.0",
            "names": [
                {
                    "format": "standard",
                    "parent_id": "alpha",
                    "subtype_id": None,
                    "english": "Alpha",
                    "chinese": "甲类",
                    "review_status": "approved",
                },
                {
                    "format": "standard",
                    "parent_id": "alpha",
                    "subtype_id": "one",
                    "english": "Alpha One",
                    "chinese": "甲类一型",
                    "review_status": "approved",
                },
            ],
        },
    )
    event = {
        "event_id": "10",
        "description": "Synthetic Challenge",
        "format": "CSTANDARD",
        "starttime": "2026-08-30T00:00:00Z",
        "player_count": 40,
        "players": players,
    }
    _write_json(tmp_path / "data/standard/event.json", event)
    _write_json(
        tmp_path / "stats/standard/mtgo/top8/2026-W35.json",
        {
            "format": "standard",
            "week": "2026-W35",
            "events": [{"event_id": "10"}],
        },
    )
    return tmp_path


def test_complete_review_includes_every_published_rank_up_to_32_without_decklists(
    tmp_path: Path,
) -> None:
    root = _synthetic_root(
        tmp_path,
        [_player(rank, "Alpha Card") for rank in range(1, 34)],
    )

    review = build_mtgo_weekly_review(root, "standard", "2026-W35")

    assert review["event_ids"] == ["10"]
    assert review["events"][0]["review_record_count"] == 32
    assert [row["rank"] for row in review["records"]] == list(range(1, 33))
    assert review["decklists_embedded"] is False
    assert all("main_deck" not in row and "sideboard" not in row for row in review["records"])
    assert review["records"][8]["identity"]["subtype_chinese"] == "甲类一型"


def test_owner_selected_record_returns_exact_deck_and_rules(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path, [_player(17, "Alpha Card", name="Selected")])

    detail = mtgo_record_detail(root, "standard", "10", 17)

    assert detail["player"] == "Selected"
    assert detail["main_deck"] == [{"name": "Alpha Card", "qty": 4}]
    assert detail["sideboard"] == [{"name": "Side Card", "qty": 1}]
    assert detail["classification"]["selected"]["rule_id"] == "alpha-one-rule"
    assert detail["source_locator"] == "data/standard/event.json#players/0"


def test_melee_review_ready_is_independent_of_publication_and_separates_unavailable(
    tmp_path: Path,
) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    event_id = "20"
    submitted_id = "participant-submitted"
    missing_id = "participant-missing"
    _write_json(
        root / f"data/standard/melee/events/{event_id}.json",
        {
            "metadata": {
                "event_id": event_id,
                "source": "melee",
                "constructed_format": "standard",
            },
            "participants": [
                {"id": submitted_id, "display_name": "Submitted"},
                {"id": missing_id, "display_name": "Unavailable"},
            ],
            "standings": [
                {"participant_id": submitted_id, "rank": 1},
                {"participant_id": missing_id, "rank": 2},
            ],
            "decklists": [
                {
                    "participant_id": submitted_id,
                    "status": "submitted",
                    "game_format": "standard",
                    "cards": [{"name": "Alpha Card", "quantity": 4, "section": "main"}],
                }
            ],
        },
    )
    event_path = root / f"data/standard/melee/events/{event_id}.json"
    rule_path = root / "my_archetypes/standard.yaml"
    overlay = build_classification_overlay_from_paths(event_path, rule_path, root)
    _write_json(
        root / f"data/standard/melee/classifications/{event_id}.json",
        overlay,
    )

    review = build_melee_review(root, "standard", event_id)

    assert [row["player"] for row in review["available_records"]] == ["Submitted"]
    assert review["unavailable_records"] == [
        {
            "participant_id": missing_id,
            "player": "Unavailable",
            "rank": 2,
            "reason": "missing_or_unavailable_decklist",
        }
    ]
    assert review["machine_priority_records"] == []
    assert "public" not in review and "live" not in review

    detail = melee_record_detail(root, "standard", event_id, submitted_id)
    assert detail["main_deck"] == [
        {"name": "Alpha Card", "quantity": 4, "section": "main"}
    ]
    assert detail["sideboard"] == []
    assert detail["classification"]["selected"]["rule_id"] == "alpha-one-rule"


def test_melee_review_ready_requires_reproducible_current_classification(
    tmp_path: Path,
) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    event_id = "20"
    event_path = root / f"data/standard/melee/events/{event_id}.json"
    _write_json(
        event_path,
        {
            "metadata": {
                "event_id": event_id,
                "source": "melee",
                "constructed_format": "standard",
            },
            "participants": [{"id": "p1", "display_name": "Player"}],
            "standings": [{"participant_id": "p1", "rank": 1}],
            "decklists": [
                {
                    "participant_id": "p1",
                    "status": "submitted",
                    "game_format": "standard",
                    "cards": [
                        {"name": "Alpha Card", "quantity": 4, "section": "main"}
                    ],
                }
            ],
        },
    )
    rule_path = root / "my_archetypes/standard.yaml"
    overlay = build_classification_overlay_from_paths(event_path, rule_path, root)
    overlay["records"][0]["selected"]["subtype_id"] = "tampered"
    _write_json(
        root / f"data/standard/melee/classifications/{event_id}.json",
        overlay,
    )

    with pytest.raises(ValueError, match="cannot be reproduced"):
        build_melee_review(root, "standard", event_id)


def test_retained_corpus_impact_reports_all_unexplained_changes(tmp_path: Path) -> None:
    root = _synthetic_root(
        tmp_path,
        [
            _player(1, "Alpha Card"),
            _player(2, "Lost Card"),
            _player(3, "New Card"),
            _player(4, "Conflict Card"),
        ],
    )
    _write_yaml(root / "candidate.yaml", _rules(candidate=True))
    _write_json(
        root / "expected.json",
        {
            "expected_changes": [
                {
                    "record_id": "mtgo:standard:10:0",
                    "candidate": {
                        "status": "classified",
                        "parent_id": "alpha",
                        "subtype_id": "two",
                        "rule_id": "alpha-two-rule",
                    },
                    "change_kinds": ["subtype_drift", "diagnostic_drift"],
                }
            ]
        },
    )

    impact = compare_classifier_impact(
        root,
        "standard",
        "my_archetypes/standard.yaml",
        "candidate.yaml",
        expected_changes_path="expected.json",
    )

    assert impact["retained_corpus"]["same_input_used_for_both_rules"] is True
    assert impact["retained_corpus"]["record_count"] == 4
    assert impact["status"] == "UNEXPLAINED_IMPACT"
    assert impact["summary"]["subtype_drift_count"] == 1
    assert impact["summary"]["classification_lost_count"] == 1
    assert impact["summary"]["new_unknown_count"] == 1
    assert impact["summary"]["new_conflict_count"] == 1
    assert impact["summary"]["missing_expected_record_ids"] == []
    assert set(impact["summary"]["unexpected_record_ids"]) == {
        "mtgo:standard:10:1",
        "mtgo:standard:10:2",
        "mtgo:standard:10:3",
    }


def test_retained_corpus_impact_has_no_false_change_for_same_rules(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])

    impact = compare_classifier_impact(
        root,
        "standard",
        "my_archetypes/standard.yaml",
        "my_archetypes/standard.yaml",
    )

    assert impact["status"] == "NO_RULE_CHANGE"
    assert impact["changes"] == []


def test_v2_completion_record_binds_full_review_subjects() -> None:
    reviews = [
        {
            "format": format_id,
            "event_ids": ["123456"],
            "classifier": {"subject_digest": digit * 64},
            "classification_review_digest": digit * 64,
        }
        for format_id, digit in (("standard", "a"), ("modern", "b"))
    ]

    record = build_v2_completion_record(
        reviews,
        week_id="2026-W35",
        completed_on="2026-09-03",
        evidence="https://example.test/review",
        landing_content_digests={"standard": "c" * 64, "modern": "d" * 64},
    )

    assert record["review_scope"] == "full_official_classification_v2"
    assert record["formats"]["standard"] == {
        "accepted_event_ids": ["123456"],
        "accepted_classifier_subject": "a" * 64,
        "classification_review_digest": "a" * 64,
        "landing_content_digest": "c" * 64,
    }
