from __future__ import annotations

import json
from hashlib import sha256
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
from tools.export_weekly_classification_review import main as export_review_main


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _registry(
    root: Path,
    *,
    public: bool = True,
    state: str = "executable",
    capabilities: list[str] | None = None,
) -> None:
    _write_yaml(
        root / "configs/formats.yaml",
        {
            "schema_version": "1.3.0",
            "formats": [
                {
                    "id": "standard",
                    "display_name": "Standard",
                    "state": state,
                    "public": public,
                    "mtgo": {
                        "enabled": state == "executable",
                        "event_collection_enabled": True,
                        "capabilities": (
                            ["classification"] if capabilities is None else capabilities
                        ),
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


def test_name_bootstrap_separates_classification_from_complete_taxonomy_names(
    tmp_path: Path,
) -> None:
    root = _synthetic_root(
        tmp_path,
        [_player(2, "Lost Card"), _player(1, "Alpha Card")],
    )
    _registry(root, public=False)

    bootstrap = build_mtgo_weekly_review(
        root, "standard", "2026-W35", name_review_bootstrap=True
    )

    assert bootstrap["document_type"] == "weekly_classification_name_bootstrap"
    assert bootstrap["review_status"] == "pending_owner_review"
    assert "classification_review_digest" not in bootstrap
    digest = bootstrap.pop("bootstrap_subject_digest")
    assert digest == sha256(json.dumps(
        bootstrap, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    assert [row["rank"] for row in bootstrap["records"]] == [1, 2]
    assert bootstrap["records"][1]["classification"]["status"] == "classified"
    assert bootstrap["records"][1]["identity"]["parent_id"] == "lost"
    assert bootstrap["records"][1]["identity"]["parent_chinese"] is None
    candidates = {
        row["identity_key"]: row for row in bootstrap["name_candidates"]
    }
    assert set(candidates) == {
        "standard|alpha|none",
        "standard|alpha|one",
        "standard|alpha|two",
        "standard|lost|none",
    }
    assert candidates["standard|alpha|none"]["existing_approved_chinese"] == "甲类"
    assert candidates["standard|alpha|two"]["existing_approved_chinese"] is None
    assert all(row["chinese_suggestion"] is None for row in candidates.values())
    with pytest.raises(ValueError, match="missing approved parent name for lost"):
        build_mtgo_weekly_review(root, "standard", "2026-W35")
    names = yaml.safe_load((root / "configs/mtgo_archetype_names.yaml").read_text(encoding="utf-8"))
    names["names"].append({
        "format": "standard", "parent_id": "lost", "subtype_id": None,
        "english": "Lost", "chinese": "失落", "review_status": "approved",
    })
    _write_yaml(root / "configs/mtgo_archetype_names.yaml", names)
    formal = build_mtgo_weekly_review(root, "standard", "2026-W35")
    for bootstrap_row, formal_row in zip(bootstrap["records"], formal["records"], strict=True):
        for field in (
            "source", "format", "event_id", "event_name", "date", "player_count",
            "high_score_count", "rank", "player", "classification", "priority_reasons",
            "source_locator",
        ):
            assert bootstrap_row[field] == formal_row[field]


@pytest.mark.parametrize(
    ("registry_options", "format_id", "week", "expected"),
    [
        ({"public": True}, "standard", "2026-W35", "public: false"),
        ({"public": False}, "missing", "2026-W35", "unknown format"),
        ({"public": False, "state": "planned", "capabilities": []}, "standard", "2026-W35", "not enabled"),
        ({"public": False, "capabilities": ["statistics"]}, "standard", "2026-W35", "classification"),
        ({"public": False}, "standard", "2099-W01", "has not ended"),
    ],
)
def test_name_bootstrap_rejects_unauthorized_scope_before_writing(
    tmp_path: Path,
    registry_options: dict[str, object],
    format_id: str,
    week: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    _registry(root, **registry_options)  # type: ignore[arg-type]
    output = tmp_path.parent / f"{tmp_path.name}-external" / "review.json"

    result = export_review_main(
        [
            "--repository-root", str(root), "mtgo", "--format", format_id,
            "--week", week, "--name-review-bootstrap", "--output", str(output),
        ]
    )

    assert result == 2
    assert not output.exists()
    assert not output.parent.exists()
    assert expected in capsys.readouterr().out


def test_name_bootstrap_requires_external_output_before_writing(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    _registry(root, public=False)
    internal = root / "diagnostics/review.json"
    assert export_review_main([
        "--repository-root", str(root), "mtgo", "--format", "standard",
        "--week", "2026-W35", "--name-review-bootstrap",
    ]) == 2
    assert export_review_main([
        "--repository-root", str(root), "mtgo", "--format", "standard",
        "--week", "2026-W35", "--name-review-bootstrap", "--output", str(internal),
    ]) == 2
    assert not internal.exists()
    assert not internal.parent.exists()


def test_name_bootstrap_cli_output_supports_existing_mtgo_detail(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path, [_player(17, "Alpha Card", name="Selected")])
    _registry(root, public=False)
    external = tmp_path.parent / f"{tmp_path.name}-external-chain"
    review_path = external / "review.json"
    detail_path = external / "detail.json"

    assert export_review_main([
        "--repository-root", str(root), "mtgo", "--format", "standard",
        "--week", "2026-W35", "--name-review-bootstrap", "--output", str(review_path),
    ]) == 0
    review = json.loads(review_path.read_text(encoding="utf-8"))
    row = review["records"][0]
    assert export_review_main([
        "--repository-root", str(root), "mtgo-detail", "--format", "standard",
        "--event-id", row["event_id"], "--rank", str(row["rank"]),
        "--output", str(detail_path),
    ]) == 0
    assert json.loads(detail_path.read_text(encoding="utf-8"))["player"] == "Selected"


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
            "week": "2026-W35",
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


@pytest.mark.parametrize("with_formal_digest", [False, True])
def test_v2_completion_rejects_name_bootstrap_even_with_formal_digest(
    with_formal_digest: bool,
) -> None:
    review = {
        "document_type": "weekly_classification_name_bootstrap",
        "review_status": "pending_owner_review",
        "format": "standard",
        "week": "2026-W35",
        "event_ids": ["123456"],
        "classifier": {"subject_digest": "a" * 64},
        "bootstrap_subject_digest": "b" * 64,
    }
    if with_formal_digest:
        review["classification_review_digest"] = "c" * 64

    with pytest.raises(ValueError, match="not completion evidence"):
        build_v2_completion_record(
            [review],
            week_id="2026-W35",
            completed_on="2026-09-05",
            evidence="owner-review",
            landing_content_digests={"standard": "d" * 64},
            independent_format=True,
        )


@pytest.mark.parametrize("command", ["completion", "format-completion"])
def test_completion_cli_rejects_name_bootstrap(command: str, tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    _registry(root, public=False)
    review = {
        "document_type": "weekly_classification_name_bootstrap",
        "review_status": "pending_owner_review",
        "format": "standard",
        "week": "2026-W35",
        "event_ids": ["10"],
        "classifier": {"subject_digest": "a" * 64},
        "classification_review_digest": "b" * 64,
    }
    review_path = tmp_path / "bootstrap.json"
    _write_json(review_path, review)
    output = tmp_path.parent / f"{tmp_path.name}-{command}.json"
    common = ["--repository-root", str(root), command, "--week", "2026-W35"]
    if command == "completion":
        arguments = [
            *common,
            "--standard-review", str(review_path),
            "--modern-review", str(review_path),
            "--standard-landing-digest", "c" * 64,
            "--modern-landing-digest", "d" * 64,
        ]
    else:
        arguments = [
            *common,
            "--format", "standard",
            "--review", str(review_path),
            "--landing-digest", "c" * 64,
        ]
    result = export_review_main([
        *arguments,
        "--completed-on", "2026-09-05",
        "--evidence", "owner-review",
        "--output", str(output),
    ])
    assert result == 2
    assert not output.exists()
