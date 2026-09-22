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


def test_completion_acceptance_event_membership_is_order_independent() -> None:
    from tools.export_weekly_classification_review import _same_event_ids

    assert _same_event_ids(["12853708", "12853715"], ["12853715", "12853708"])
    assert not _same_event_ids(["12853708", "12853715"], ["12853708"])
    assert not _same_event_ids(["12853708", "12853708"], ["12853708"])


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


@pytest.mark.parametrize("change, expected", [("none", "current"), ("engine", "equivalent"),
                                              ("cards", "changed")])
def test_real_weekly_producer_continues_across_feature_readiness_and_completion(tmp_path, monkeypatch, change, expected):
    from copy import deepcopy
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta import classifier
    from mtgmeta.mtgo import publication, review_submission as submission
    from tools import build_weekly_review_web as web
    from tools import generate_weekly_maintenance_readiness as ready

    root = _synthetic_root(tmp_path / "repo", [_player(1, "Alpha Card")])
    event_path = root / "data/standard/event.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["starttime"] = "2026-09-15T00:00:00Z"
    _write_json(event_path, event)
    raw = build_mtgo_weekly_review(root, "standard", "2026-W38")
    assert "deck_material_digest" in raw["records"][0]
    assert not {"main_deck", "sideboard", "reference"} & raw["records"][0].keys()
    enriched = deepcopy(raw)
    enriched["records"][0].update(main_deck=event["players"][0]["main_deck"],
                                  sideboard=event["players"][0]["sideboard"], reference="W38-standard-10-01")
    packet = submission.full_classification_packet(enriched)
    assert submission.classification_comparison_packet(raw) == packet
    with pytest.raises(ValueError, match="complete deck material"):
        submission.full_classification_packet(raw)

    def accept(value):
        return submission.record_decision(value, None, list(value["dimensions"]),
            evidence="synthetic Owner acceptance", accepted_on="2026-09-21", entrypoint="synthetic review")
    admission = {"week": raw["week"], "kind": "owner_accepted_full_classification", "event_ids": raw["event_ids"],
        "accepted_classifier_subject": raw["classifier"]["subject_digest"],
        "classification_review_digest": raw["classification_review_digest"],
        "evidence": "synthetic", "accepted_on": "2026-09-21",
        "classification_acceptance": {"submission": packet, "decisions": accept(packet)}}
    completed = build_v2_completion_record([raw], week_id=raw["week"], completed_on="2026-09-21",
        evidence="synthetic", landing_content_digests={"standard": "c" * 64}, independent_format=True)
    preview = submission.make_packet("preview", "standard", raw["week"], {"final_page": "synthetic"}, bindings={})
    accepted_preview = {"submission": preview, "decisions": accept(preview), "publication": {
        "health": "passed", "operation": "op", "package": "package", "preview_digest": preview["digest"]}}
    completed["formats"]["standard"]["preview_acceptance"] = accepted_preview
    registry = {"schema_version": "1.2.0", "records": [completed],
        "data_admissions": {"formats": {"standard": {"weekly_acceptances": [admission]}}}}
    registry_path = root / "configs/mtgo_weekly_review_completions.yaml"
    _write_yaml(registry_path, registry)
    saved = registry_path.read_bytes()
    _write_json(root / "stats/standard/mtgo/landing/current.json", {"week": {"id": raw["week"]}})
    _write_json(root / "stats/standard/mtgo/landing/features/2026-W38.json",
                {"format": "standard", "week": {"id": raw["week"]}, "content_digest": "c" * 64})
    monkeypatch.setattr(submission, "preview_packet", lambda *a: preview)
    monkeypatch.setattr(ready, "_landing_content_digest", lambda *a: "c" * 64)
    monkeypatch.setattr(publication, "resolve_scope", lambda *a: SimpleNamespace(event_ids={"10"}, week=date(2026, 9, 14)))
    monkeypatch.setattr(publication, "inspect_publication", lambda *a: [])
    if change == "engine":
        monkeypatch.setattr(classifier, "CLASSIFIER_ENGINE_VERSION", "synthetic-next-version")
    if change == "cards":
        event["players"][0]["sideboard"][0]["qty"] = 2
        _write_json(event_path, event)
    current = build_mtgo_weekly_review(root, "standard", raw["week"])
    assert submission.classification_validity(admission, current)["state"] == expected
    assert bool(web.accepted_classification(registry, current)) == (expected != "changed")
    state = ready._completion_state(root, raw["week"], format_id="standard")
    assert state["historical_state"] == "verified"
    assert state["state"] == ("stale" if expected == "changed" else "verified")
    current_path, preview_path, output = (tmp_path / name for name in ("review.json", "preview.json", "completion.json"))
    _write_json(current_path, current)
    _write_json(preview_path, {"standard": accepted_preview})
    result = export_review_main(["--repository-root", str(root), "format-completion", "--week", raw["week"],
        "--format", "standard", "--review", str(current_path), "--landing-digest", "c" * 64,
        "--preview-acceptances", str(preview_path), "--completed-on", "2026-09-21",
        "--evidence", "synthetic", "--output", str(output)])
    assert result == (2 if expected == "changed" else 0)
    assert output.exists() == (expected != "changed")
    if output.exists():
        assert json.loads(output.read_text(encoding="utf-8"))["formats"]["standard"]["classification_submission"] == submission.classification_comparison_packet(current)
    assert registry_path.read_bytes() == saved


def test_legacy_raw_review_completion_keeps_its_existing_evidence_contract(tmp_path):
    root = _synthetic_root(tmp_path, [_player(1, "Alpha Card")])
    raw = build_mtgo_weekly_review(root, "standard", "2026-W35")
    assert "deck_material_digest" not in raw["records"][0]
    completed = build_v2_completion_record([raw], week_id=raw["week"], completed_on="2026-09-01",
        evidence="synthetic", landing_content_digests={"standard": "c" * 64}, independent_format=True)
    assert "classification_submission" not in completed["formats"]["standard"]
    assert completed["formats"]["standard"]["classification_review_digest"] == raw["classification_review_digest"]


@pytest.fixture
def supplement_case(tmp_path, monkeypatch):
    """Real review producer, preview reader, package extraction and completion validator."""
    from copy import deepcopy
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta.mtgo import publication, review_submission as review
    from tools.delivery import packages

    root = _synthetic_root(tmp_path / "repo", [_player(1, "Alpha Card")])
    source = root / "data/standard/event.json"
    original_event = json.loads(source.read_text(encoding="utf-8"))
    original_event["starttime"] = "2026-09-15T00:00:00Z"
    _write_json(source, original_event)
    week = {"id": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"}
    landing = root / "stats/standard/mtgo/landing"
    files = {key: f"weeks/2026-W38/{key}.json" for key in ("range", "completeness", "environment_decks", "feature_decks")}
    page = {"week": week, "format": "standard", "classifier": {"digest": "fixture"},
            "data_files": files, "features": {"items": []}, "environment": {"rows": []}}
    _write_json(landing / "current.json", page)
    _write_json(landing / "features/2026-W38.json", {"week": week, "format": "standard",
                "features": {"items": []}, "content_digest": "c" * 64})
    _write_json(landing / "features/index.json", {"format": "standard", "weeks": [
        {"week": week["id"], "file": "2026-W38.json", "feature_count": 0}]})
    for key, relative in files.items():
        _write_json(landing / relative, {"format": "standard", "classifier_digest": "fixture",
            "period": {"start": "2026-08-24" if key == "feature_decks" else week["start"], "end": week["end"]}})
    for relative, text in {"index.html": '<script src="assets/js/phase8/app.js"></script><script src="assets/js/phase8/archetype-visuals.js"></script>', "melee/index.html": "synthetic", "stats/catalog.json": "{}",
        "stats/standard/archetype_names.json": '{"names":[]}', "assets/js/phase8/app.js": "/* synthetic */",
        "assets/js/phase8/archetype-visuals.js": 'const manaIdentities = Object.freeze({\n  standard: Object.freeze({\n  }),\n});'}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    def accept(packet):
        return review.record_decision(packet, None, list(packet["dimensions"]), evidence="synthetic Owner acceptance",
            accepted_on="2026-09-21", entrypoint="https://example.invalid/synthetic")
    raw = build_mtgo_weekly_review(root, "standard", week["id"])
    completion = build_v2_completion_record([raw], week_id=week["id"], completed_on="2026-09-21",
        evidence="original synthetic completion", landing_content_digests={"standard": "c" * 64}, independent_format=True)
    preview = review.preview_packet(root, "standard")
    completion["formats"]["standard"]["preview_acceptance"] = {"submission": preview, "decisions": accept(preview),
        "publication": {"health": "passed", "operation": "original-op", "package": "original-package", "preview_digest": preview["digest"]}}
    original = deepcopy(completion)
    registry = {"schema_version": "1.2.0", "records": [completion],
        "weekly_maintenance": {"standard": {"start_week": "2026-W38"}},
        "data_admissions": {"formats": {"standard": {"weekly_acceptances": []}}}}
    ids = {"10"}
    monkeypatch.setattr(publication, "resolve_scope", lambda *a: SimpleNamespace(week=date(2026,9,14),
        event_ids=ids, pending_event_ids=set(), subject_digest=review.digest(sorted(ids))))
    # Admission selection and generated-output audit have their own tests. Here
    # only these external prerequisites are substituted; bytes are checked for real.
    monkeypatch.setattr(publication, "inspect_publication", lambda *a: [])
    def advance(event_id):
        event = deepcopy(original_event)
        event["event_id"] = event_id
        _write_json(root / f"data/standard/{event_id}.json", event)
        ids.add(event_id)
        current = build_mtgo_weekly_review(root, "standard", week["id"])
        enriched = deepcopy(current)
        for row in enriched["records"]:
            row.update(main_deck=event["players"][0]["main_deck"], sideboard=event["players"][0]["sideboard"],
                       reference=f"event-{row['event_id']}")
        packet = review.full_classification_packet(enriched)
        admission = {"week": week["id"], "kind": "owner_accepted_full_classification", "event_ids": current["event_ids"],
            "accepted_classifier_subject": current["classifier"]["subject_digest"],
            "classification_review_digest": current["classification_review_digest"], "evidence": "synthetic", "accepted_on": "2026-09-28",
            "classification_acceptance": {"submission": packet, "decisions": accept(packet)}}
        registry["data_admissions"]["formats"]["standard"]["weekly_acceptances"] = [admission]
        _write_yaml(root / "configs/mtgo_weekly_review_completions.yaml", registry)
        _write_json(root / "stats/standard/mtgo/events.json", {"event_ids": sorted(ids)})
        _write_json(root / "stats/standard/mtgo/meta.json", {"publication": publication.publication_binding(root, "standard")})
        candidate = tmp_path / f"package-{event_id}"
        manifest = packages.prepare(root, candidate, target="Jacelber/mtgo-data", source="synthetic")
        state = {"pending": None, "current": {"health": "passed", "operation": f"op-{event_id}", "package": manifest["id"]}}
        return candidate, state
    return SimpleNamespace(root=root, registry=registry, completion=completion, original=original,
        advance=advance, accept=accept, tmp=tmp_path)


def test_supplement_cli_appends_two_facts_and_closes_readiness_without_rewriting_history(supplement_case, monkeypatch):
    from copy import deepcopy
    import sys
    from types import SimpleNamespace
    from mtgmeta.mtgo import supplement_completion as supplement, review_submission as review, classification
    from tools import review_submission as cli, generate_weekly_maintenance_readiness as ready
    case = supplement_case
    monkeypatch.setattr(ready, "_intentional_unknowns", lambda *a, **k: {"standard": {}})
    monkeypatch.setattr(classification, "audit_mtgo_classification", lambda *a: SimpleNamespace(reports={
        "unknown_decks": {"records": []}, "index": {"summary": {"strict_validation": "pass"}}}))
    def readiness():
        result = ready._independent_readiness(case.root, case.registry, publication_sha="a"*40, production_run_id="1",
            production_run_attempt="1", source_sha="b"*40, generated_at="2026-10-05T00:00:00Z")
        import jsonschema
        jsonschema.validate(result, json.loads((Path(__file__).resolve().parents[1] /
            "schemas/weekly-maintenance-readiness.schema.json").read_text(encoding="utf-8")))
        return result["formats"][0]
    prior_id = None
    for event_id, completed_on in [("11", "2026-09-29"), ("12", "2026-10-01")]:
        candidate, state = case.advance(event_id)
        assert readiness()["outstanding_supplement_weeks"] == ["2026-W38"]
        assert review.resume_summary(case.root, "standard", "2026-W38")["supplement_completion"]["pending_event_ids"] == [event_id]
        registry_path = case.root / "configs/mtgo_weekly_review_completions.yaml"
        saved = registry_path.read_bytes()
        state_path, output = case.tmp / f"state-{event_id}.json", case.tmp / f"fact-{event_id}.json"
        _write_json(state_path, state)
        monkeypatch.setattr(sys, "argv", ["review_submission", "--root", str(case.root), "supplement-completion",
            "--format", "standard", "--week", "2026-W38", "--candidate", str(candidate), "--publication-state", str(state_path),
            "--completed-on", completed_on, "--evidence", "synthetic supplement closeout", "--output", str(output)])
        cli.main()
        assert registry_path.read_bytes() == saved
        fact = json.loads(output.read_text(encoding="utf-8"))
        assert fact["covered_event_ids"] == [event_id]
        assert fact["preview"]["mode"] == "retained"
        assert "content_acceptance" not in fact and "acceptance" not in fact["preview"]
        if prior_id: assert fact["previous"] == prior_id
        prior_id = fact["id"]
        case.completion["formats"]["standard"].setdefault("supplements", []).append(fact)
        _write_yaml(registry_path, case.registry)
        result = readiness()
        assert result["outstanding_supplement_weeks"] == [] and result["review_week"] is None
        assert result["completed_reviews"] == ["2026-W38"]
        assert ready._completion_state(case.root, "2026-W38", format_id="standard")["state"] == "verified"
        resumed = review.resume_summary(case.root, "standard", "2026-W38")
        assert resumed["completion"] == "confirmed_recorded"
        assert resumed["supplement_completion"]["pending_event_ids"] == []
        assert resumed["publication_evidence"]["package"] == state["current"]["package"]
        preserved = deepcopy(case.completion)
        preserved["formats"]["standard"].pop("supplements")
        assert preserved == case.original
    proof = supplement.coverage(case.root, case.completion, "standard")
    assert proof["covered_event_ids"] == ["10", "11", "12"] and len(proof["valid_supplements"]) == 2


@pytest.mark.parametrize("failure", ["unknown", "pending", "wrong_package", "changed_bytes", "missing_admission", "changed_page"])
def test_supplement_export_requires_actual_acceptance_and_confirmed_package(supplement_case, failure):
    from mtgmeta.mtgo import supplement_completion as supplement
    case = supplement_case
    candidate, state = case.advance("11")
    if failure == "unknown": state["current"]["health"] = "unknown"
    elif failure == "pending": state["pending"] = {"operation": "other"}
    elif failure == "wrong_package": state["current"]["package"] = "other"
    elif failure == "changed_bytes": _write_json(case.root / "stats/standard/mtgo/events.json", {"event_ids": ["10"]})
    elif failure == "missing_admission":
        case.registry["data_admissions"]["formats"]["standard"]["weekly_acceptances"] = []
        _write_yaml(case.root / "configs/mtgo_weekly_review_completions.yaml", case.registry)
    else:
        (case.root / "assets/js/phase8/app.js").write_text("/* changed page */")
        from tools.delivery import packages
        candidate = case.tmp / "changed-page-package"
        manifest = packages.prepare(case.root, candidate, target="Jacelber/mtgo-data", source="synthetic")
        state["current"]["package"] = manifest["id"]
    with pytest.raises(ValueError):
        supplement.build(case.root, case.completion, "standard", candidate=candidate, state=state,
                         completed_on="2026-09-29", evidence="synthetic")
    assert case.completion == case.original


@pytest.mark.parametrize("failure", ["wrong_week", "wrong_format", "missing_evidence", "unknown", "wrong_base", "duplicate", "classification", "retained_changed", "missing_publication", "wrong_data_scope"])
def test_invalid_supplements_never_extend_coverage_or_revoke_original(supplement_case, failure):
    from copy import deepcopy
    from mtgmeta.mtgo import supplement_completion as supplement, review_submission as review
    from tools import generate_weekly_maintenance_readiness as ready
    case = supplement_case
    candidate, state = case.advance("11")
    fact = supplement.build(case.root, case.completion, "standard", candidate=candidate, state=state,
                            completed_on="2026-09-29", evidence="synthetic")
    if failure == "wrong_week": fact["week"] = "2026-W39"
    elif failure == "wrong_format": fact["format"] = "modern"
    elif failure == "missing_evidence": fact["evidence"] = ""
    elif failure == "unknown": fact["publication"]["health"] = "unknown"
    elif failure == "wrong_base": fact["base_completion"] = "f" * 64
    elif failure == "duplicate": fact["covered_event_ids"] = ["10"]
    elif failure == "classification": fact["classification_admission"]["event_ids"] = ["10"]
    elif failure == "missing_publication": fact.pop("publication")
    elif failure == "wrong_data_scope": fact["data_publication"]["event_ids"] = ["10"]
    else:
        fact["preview"]["submission"]["dimensions"]["final_page"]["product_digest"] = "changed"
        packet = fact["preview"]["submission"]
        packet["digest"] = review.digest({k:v for k,v in packet.items() if k != "digest"})
    fact["id"] = review.digest({k:v for k,v in fact.items() if k != "id"})
    case.completion["formats"]["standard"]["supplements"] = [fact]
    _write_yaml(case.root / "configs/mtgo_weekly_review_completions.yaml", case.registry)
    result = supplement.coverage(case.root, case.completion, "standard")
    assert result["covered_event_ids"] == ["10"] and result["problems"]
    assert ready._completion_state(case.root, "2026-W38", format_id="standard")["historical_state"] == "verified"
    preserved = deepcopy(case.completion)
    preserved["formats"]["standard"].pop("supplements")
    assert preserved == case.original


@pytest.mark.parametrize("acceptance", ["none", "preview_only", "both"])
def test_changed_supplement_page_requires_corresponding_accepted_dimensions(supplement_case, monkeypatch, acceptance):
    from copy import deepcopy
    from mtgmeta.mtgo import supplement_completion as supplement, review_submission as review
    from tools.delivery import packages
    case = supplement_case
    case.advance("11")
    (case.root / "assets/js/phase8/app.js").write_text("/* actual changed renderer */")
    actual = review.preview_packet(case.root, "standard")
    envelope = {"submission": actual, "decisions": case.accept(actual)}
    body = {"top_copy": {"items": []}, "features": {"items": [], "explicit_empty": True}}
    content = review.make_content_packet(case.root, "standard", "2026-W38", body, {"rows": []}, {"names": []}, bindings={})
    source = {"format": "standard", "week": {"id": "2026-W38"}, "review": body,
        "bindings": {"bilingual_catalog_digest": review.name_digest(content)},
        "acceptance": {"submission": content, "decisions": case.accept(content)}}
    if acceptance == "preview_only": source["acceptance"]["decisions"]["decisions"] = {}
    _write_yaml(case.root / "stats/standard/mtgo/landing/review/2026-W38.yaml", source)
    # Only the statistics/selection producer is substituted; document validation,
    # scoped decisions, actual preview and archive checks remain real.
    monkeypatch.setattr(review, "content_packet", lambda *a: deepcopy(content))
    candidate = case.tmp / "changed-page"
    manifest = packages.prepare(case.root, candidate, target="Jacelber/mtgo-data", source="synthetic")
    state = {"pending": None, "current": {"health": "passed", "operation": "changed", "package": manifest["id"]}}
    kwargs = dict(candidate=candidate, state=state, completed_on="2026-09-29", evidence="synthetic",
                  preview_acceptance=envelope if acceptance != "none" else None)
    if acceptance != "both":
        with pytest.raises(ValueError): supplement.build(case.root, case.completion, "standard", **kwargs)
        return
    fact = supplement.build(case.root, case.completion, "standard", **kwargs)
    assert fact["preview"]["mode"] == "accepted"
    assert fact["preview"]["acceptance"] == envelope
    assert fact["content_acceptance"] == source["acceptance"]
    assert case.completion == case.original
    case.completion["formats"]["standard"]["supplements"] = [fact]
    _write_yaml(case.root / "configs/mtgo_weekly_review_completions.yaml", case.registry)
    result = supplement.coverage(case.root, case.completion, "standard")
    assert result["covered_event_ids"] == ["10", "11"] and not result["problems"]
    supplement.validate_current_preview(case.root, "standard", result["effective"])
    from tools import generate_weekly_maintenance_readiness as ready
    assert ready._completion_state(case.root, "2026-W38", format_id="standard")["state"] == "verified"


def test_supplement_chain_rejects_reordering_and_preserves_first_valid_fact(supplement_case):
    from copy import deepcopy
    from mtgmeta.mtgo import supplement_completion as supplement
    case = supplement_case
    candidate, state = case.advance("11")
    first = supplement.build(case.root, case.completion, "standard", candidate=candidate, state=state,
                             completed_on="2026-09-29", evidence="synthetic first")
    subject = case.completion["formats"]["standard"]
    subject["supplements"] = [first]
    candidate, state = case.advance("12")
    second = supplement.build(case.root, case.completion, "standard", candidate=candidate, state=state,
                              completed_on="2026-10-01", evidence="synthetic second")
    subject["supplements"] = [second, first]
    result = supplement.coverage(case.root, case.completion, "standard")
    assert result["covered_event_ids"] == ["10", "11"] and result["problems"]
    subject["supplements"] = [first, deepcopy(first)]
    result = supplement.coverage(case.root, case.completion, "standard")
    assert result["covered_event_ids"] == ["10", "11"] and len(result["valid_supplements"]) == 1
    assert result["problems"]
    subject["supplements"] = [first, second]
    case.completion["completed_on"] = "2026-09-22"
    result = supplement.coverage(case.root, case.completion, "standard")
    assert result["covered_event_ids"] == ["10"] and len(result["problems"]) == 2


def test_legacy_preview_continues_through_resume_archive_and_supplement(supplement_case, monkeypatch):
    from copy import deepcopy
    import sys
    from mtgmeta.mtgo import review_submission as review, supplement_completion as supplement
    from tools import review_submission as cli, generate_weekly_maintenance_readiness as ready
    case = supplement_case
    legacy = case.completion["formats"]["standard"]["preview_acceptance"]
    packet = legacy["submission"]
    packet["bindings"].pop("renderer_selection")
    for name in ("app-tabletop.js", "tabletop-controller.js"):
        path = f"assets/js/phase8/{name}"
        (case.root / path).write_text("/* old unrelated renderer */")
        for resources in (packet["bindings"]["renderer_resources"], packet["dimensions"]["final_page"]["renderer_resources"]):
            resources[path] = review.hashlib_sha(case.root / path)
    packet["digest"] = review.digest({k:v for k,v in packet.items() if k != "digest"})
    legacy["decisions"] = case.accept(packet)
    legacy["publication"]["preview_digest"] = packet["digest"]
    original = deepcopy(case.completion)
    candidate, state = case.advance("11")
    # A later change to unloaded Tabletop code must not demand a new MTGO decision.
    (case.root / "assets/js/phase8/app-tabletop.js").write_text("/* new unrelated renderer */")
    review.validate_completion(case.root, "standard", "2026-W38", case.completion["formats"]["standard"])
    resumed = review.resume_summary(case.root, "standard", "2026-W38", envelope=legacy)
    assert resumed["pending_decisions"] == [] and resumed["preview"] == "accepted_recorded"
    acceptance, publication, output = (case.tmp / name for name in ("legacy-preview.json", "publication.json", "completion-proof.json"))
    _write_json(acceptance, legacy)
    _write_json(publication, state)
    monkeypatch.setattr(sys, "argv", ["review_submission", "--root", str(case.root), "completion",
        "--acceptance", str(acceptance), "--candidate", str(candidate), "--publication-state", str(publication), "--output", str(output)])
    cli.main()
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["submission"] == legacy["submission"] and exported["decisions"] == legacy["decisions"]
    assert exported["publication"]["package"] == state["current"]["package"]
    fact = supplement.build(case.root, case.completion, "standard", candidate=candidate, state=state,
                            completed_on="2026-09-29", evidence="synthetic supplement")
    assert fact["preview"]["mode"] == "retained" and "content_acceptance" not in fact
    assert case.completion == original
    case.completion["formats"]["standard"]["supplements"] = [fact]
    _write_yaml(case.root / "configs/mtgo_weekly_review_completions.yaml", case.registry)
    result = supplement.coverage(case.root, case.completion, "standard")
    assert not result["problems"] and result["covered_event_ids"] == ["10", "11"]
    supplement.validate_current_preview(case.root, "standard", result["effective"])
    assert ready._completion_state(case.root, "2026-W38", format_id="standard")["state"] == "verified"
    (case.root / "assets/js/phase8/app.js").write_text("/* loaded renderer actually changed */")
    with pytest.raises(ValueError): supplement.validate_current_preview(case.root, "standard", result["effective"])
