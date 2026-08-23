from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import yaml
import pytest
from jsonschema import Draft202012Validator

from mtgmeta.mtgo import landing


WEEK = "2026-W33"
DIGEST = "a" * 64
FACT_DIGEST = "b" * 64
POLICY_DIGEST = "e" * 64
VISUAL_DIGEST = "f" * 64
PICKUP_DIGEST = "d" * 64
ROOT = Path(__file__).resolve().parents[1]


def _candidate(*, approved: bool = False) -> dict:
    entry = {
        "archetype_id": "example-parent",
        "subtype_id": None,
        "archetype": "Example Parent",
        "event_id": "100",
        "deck_id": "deck-100",
        "deck_fingerprint_sha256": "c" * 64,
        "player": "Example",
        "final_rank": 1,
        "player_count": 32,
        "starttime": "2026-08-10 00:00:00.0",
        "approved": approved,
        "comment_zh": "",
        "comment_en": "",
        "candidate_reasons": [
            {
                "type": "new_archetype",
                "prior_record_count_under_current_classifier": 0,
            }
        ],
        "main_deck": [
            {"name": "Card One", "qty": 4},
            {"name": "Card Two", "qty": 4},
            {"name": "Card Three", "qty": 4},
            {"name": "Card Four", "qty": 4},
        ],
        "side_deck": [],
    }
    if approved:
        entry["landing"] = {
            "approved": True,
            "category": "new_deck",
            "order": 1,
            "headline_zh": "人工标题",
            "headline_en": "Human headline",
            "positioning_zh": "人工可独立改写。",
            "positioning_en": "Human copy may be independent.",
            "featured_cards": ["Card One", "Card Two", "Card Three", "Card Four"],
        }
    return {
        "week": WEEK,
        "source_event_ids": ["100"],
        "classifier_digest": DIGEST,
        "selection_policy_digest": POLICY_DIGEST,
        "visual_metadata_digest": VISUAL_DIGEST if approved else None,
        "landing_visual_diagnostics": [],
        "machine_fact_digest": FACT_DIGEST if approved else None,
        "existing_changes": [],
        "new_archetypes": [entry],
    }


def _published_pickup() -> dict:
    return {
        "schema_version": "1.1.0",
        "format": "standard",
        "source": "mtgo",
        "week": WEEK,
        "start": "2026-08-10",
        "end": "2026-08-16",
        "source_event_ids": ["100"],
        "classifier_digest": DIGEST,
        "selection_policy_digest": POLICY_DIGEST,
        "existing_changes": [
            {
                "archetype_id": "example-parent",
                "subtype_id": None,
                "subtype": None,
                "archetype": "Example Parent",
                "event_id": "100",
                "deck_id": "a" * 20,
                "deck_fingerprint_sha256": "c" * 64,
                "player": "Example",
                "final_rank": 1,
                "player_count": 32,
                "starttime": "2026-08-10 00:00:00.0",
                "reason_types": ["return", "new_card"],
                "comment_zh": "已经审核的中文 Pickup 内容",
                "comment_en": "Reviewed Pickup copy",
            }
        ],
        "new_archetypes": [],
    }


def _link_catalog() -> list[dict]:
    return [
        {
            "link_id": f"deck:{'a' * 20}",
            "archetype_id": "example-parent",
            "display_name": "Example Parent",
            "event_id": "100",
            "deck_id": "a" * 20,
            "deck_fingerprint_sha256": "c" * 64,
            "player": "Example",
            "final_rank": 1,
            "starttime": "2026-08-10 00:00:00.0",
        }
    ]


def test_no_event_document_is_schema_shaped_without_candidates(monkeypatch, tmp_path):
    context = SimpleNamespace(paths={"statistics": tmp_path / "stats"})
    rules = SimpleNamespace(archetypes=())
    monkeypatch.setattr(landing, "load_mtgo_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(landing, "load_rules_for_format", lambda *args, **kwargs: rules)
    monkeypatch.setattr(landing.stats, "load_all_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(landing, "classifier_digest", lambda value: DIGEST)
    monkeypatch.setattr(
        landing.pickup,
        "load_pickup_policy",
        lambda *args, **kwargs: {"schema_version": "1.0"},
    )
    monkeypatch.setattr(
        landing,
        "load_visual_metadata",
        lambda *args, **kwargs: {
            "schema_version": "1.0",
            "formats": {"standard": {"parents": {}, "subtypes": {}}},
        },
    )

    review_status, document = landing.build_document(
        tmp_path,
        "standard",
        today=date(2026, 8, 18),
    )

    assert review_status == "not_applicable"
    assert document["week"] == {
        "id": WEEK,
        "start": "2026-08-10",
        "end": "2026-08-16",
    }
    assert document["state"] == "no_events"
    assert document["source_event_ids"] == []
    assert document["comparison"] == {
        "available": False,
        "unavailable_reason": "no_current_events",
    }
    assert document["environment"]["rows"] == []
    assert document["schema_version"] == "1.1.0"
    assert document["weekly_summary"] == {"week": WEEK, "items": []}
    assert "observations" not in document
    assert document["features"]["items"] == []
    schema = json.loads(
        (ROOT / "schemas" / "mtgo-landing.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(document)) == []


def test_current_landing_uses_one_private_review_without_published_pickup(monkeypatch):
    monkeypatch.setattr(
        landing,
        "_load_published_pickup",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Landing must not read a separately published Pickup week")
        ),
    )

    review_status, document = landing.build_document(
        ROOT,
        "standard",
        today=date(2026, 8, 18),
    )

    assert review_status == "current"
    assert len(document["weekly_summary"]["items"]) == 9
    assert len(document["features"]["items"]) == 14
    assert all(item["headline"]["zh"] for item in document["features"]["items"])
    assert all(item["headline"]["en"] for item in document["features"]["items"])


def test_cross_field_population_mismatch_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["environment"]["other_classified"]["current"]["count"] += 1

    with pytest.raises(landing.MTGOLandingError, match="decomposition"):
        landing.validate_document(document)


def test_weekly_summary_duplicate_order_fails_closed():
    document = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "landing" / "current.json").read_text(
            encoding="utf-8"
        )
    )
    document["schema_version"] = "1.1.0"
    document.pop("observations", None)
    document["weekly_summary"] = {
        "week": document["week"]["id"],
        "items": [
            {"order": 1, "text": {"zh": "甲", "en": ""}, "deck_links": []},
            {"order": 1, "text": {"zh": "乙", "en": ""}, "deck_links": []},
        ],
    }
    document["review_binding"]["pickup_document_digest"] = PICKUP_DIGEST
    document["review_binding"]["summary_fact_digest"] = FACT_DIGEST

    with pytest.raises(landing.MTGOLandingError, match="summary order"):
        landing.validate_document(document)


def test_unreviewed_candidate_receives_fact_binding_and_default_landing_fields(
    tmp_path,
):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(_candidate()), encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    updated = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert status == "current"
    assert features == []
    assert updated["machine_fact_digest"] == FACT_DIGEST
    assert updated["new_archetypes"][0]["landing"] == {
        "approved": False,
        "category": "new_deck",
        "order": None,
        "headline_zh": "",
        "headline_en": "",
        "positioning_zh": "",
        "positioning_en": "",
        "featured_cards": [],
    }


def test_reviewed_feature_is_public_without_internal_approval_or_comments(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(_candidate(approved=True)), encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    assert status == "current"
    assert len(features) == 1
    feature = features[0]
    assert feature["category"] == "new_deck"
    assert feature["headline"]["zh"] == "人工标题"
    assert [card["name"] for card in feature["featured_cards"]] == [
        "Card One",
        "Card Two",
        "Card Three",
        "Card Four",
    ]
    serialized = json.dumps(feature, ensure_ascii=False)
    assert "approved" not in serialized
    assert "comment_zh" not in serialized
    assert "machine_fact_digest" not in serialized


def test_reviewed_candidate_is_preserved_when_machine_facts_change(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    original = yaml.safe_dump(_candidate(approved=True))
    path.write_text(original, encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        VISUAL_DIGEST,
        [],
        "d" * 64,
    )

    assert status == "stale_review_required"
    assert features == []
    assert path.read_text(encoding="utf-8") == original


def test_reviewed_candidate_is_preserved_when_selection_policy_changes(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    original = yaml.safe_dump(_candidate(approved=True))
    path.write_text(original, encoding="utf-8")

    status, features = landing._feature_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        "0" * 64,
        VISUAL_DIGEST,
        [],
        FACT_DIGEST,
    )

    assert status == "stale_review_required"
    assert features == []
    assert path.read_text(encoding="utf-8") == original


def test_summary_review_inputs_keep_all_machine_facts_and_one_published_pickup_row():
    observations = [
        {
            "type": "share_move",
            "archetype_id": f"deck-{index}",
            "display_name": f"Deck {index}",
            "current": {"count": 2, "denominator": 10, "share": 0.2},
            "previous_four_weeks": {"count": 1, "denominator": 10, "share": 0.1},
            "state": "increase",
            "direction": "up",
            "delta_pp": 10.0,
        }
        for index in range(6)
    ]
    inputs = landing._summary_review_inputs(observations, _published_pickup())

    assert len(inputs) == 7
    assert [item["type"] for item in inputs].count("share_move") == 6
    published = [
        item for item in inputs if item["input_source"] == "published_pickup"
    ]
    assert len(published) == 1
    assert published[0]["reason_types"] == ["return", "new_card"]
    assert published[0]["text_zh"] == "已经审核的中文 Pickup 内容"
    assert len({item["input_id"] for item in inputs}) == len(inputs)


def test_deck_link_catalog_keeps_every_top8_deck_independent_of_review_inputs():
    records = []
    for rank in range(1, 9):
        records.append(
            {
                "is_top8": True,
                "event_id": "100",
                "deck_id": f"deck-{rank}",
                "archetype_id": "example-parent",
                "archetype": "Example Parent",
                "player": f"Player {rank}",
                "final_rank": rank,
                "starttime": "2026-08-10 00:00:00.0",
                "main_deck": [{"name": f"Card {rank}", "qty": 60}],
                "side_deck": [],
            }
        )

    catalog = landing._deck_link_catalog(records)

    assert len(catalog) == 8
    assert [item["final_rank"] for item in catalog] == list(range(1, 9))
    assert catalog[0]["link_id"] == "deck:deck-1"


def test_published_pickup_must_match_the_current_landing_subject(tmp_path):
    path = tmp_path / f"{WEEK}.json"
    document = _published_pickup()
    document["classifier_digest"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(landing.MTGOLandingError, match="current Landing subject"):
        landing._load_published_pickup(
            path,
            format_id="standard",
            week=WEEK,
            source_event_ids=["100"],
            rules_digest=DIGEST,
            selection_policy_digest=POLICY_DIGEST,
        )


def test_missing_summary_review_is_written_as_pending_not_inferred_as_zero(tmp_path):
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(_candidate()), encoding="utf-8")
    inputs = landing._summary_review_inputs([], _published_pickup())

    status, items, digest = landing._summary_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        PICKUP_DIGEST,
        inputs,
        _link_catalog(),
    )

    updated = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert status == "summary_review_required"
    assert items == []
    assert updated["landing_summary"] == {
        "summary_fact_digest": digest,
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": False,
        "items": [],
    }


def test_explicitly_reviewed_zero_item_summary_is_current(tmp_path):
    candidate = _candidate()
    inputs = landing._summary_review_inputs([], _published_pickup())
    digest = landing._summary_digest(
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        PICKUP_DIGEST,
        inputs,
        _link_catalog(),
    )
    candidate["landing_summary"] = {
        "summary_fact_digest": digest,
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": True,
        "items": [],
    }
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    status, items, actual_digest = landing._summary_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        PICKUP_DIGEST,
        inputs,
        _link_catalog(),
    )

    assert status == "current"
    assert items == []
    assert actual_digest == digest
    assert landing.pickup._has_manual_review(candidate) is True


def test_unreviewed_empty_summary_is_not_mistaken_for_manual_content():
    candidate = _candidate()
    candidate["landing_summary"] = {
        "summary_fact_digest": FACT_DIGEST,
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": [],
        "deck_link_catalog": [],
        "reviewed": False,
        "items": [],
    }

    assert landing.pickup._has_manual_review(candidate) is False


def test_human_summary_can_merge_many_inputs_or_ignore_review_inputs(tmp_path):
    candidate = _candidate()
    inputs = landing._summary_review_inputs(
        [
            {"type": "exit", "archetype_id": "first", "value": 1},
            {"type": "exit", "archetype_id": "second", "value": 2},
        ],
        _published_pickup(),
    )
    digest = landing._summary_digest(
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        PICKUP_DIGEST,
        inputs,
        _link_catalog(),
    )
    candidate["landing_summary"] = {
        "summary_fact_digest": digest,
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": True,
        "items": [
            {
                "order": 2,
                "text_zh": "与机器候选无关的人工结论。",
                "text_en": "Independent human conclusion.",
                "source_input_ids": [],
            },
            {
                "order": 1,
                "text_zh": f"合并两项事实：deck:{'a' * 20}",
                "text_en": f"Two facts merged: deck:{'a' * 20}",
                "source_input_ids": [inputs[0]["input_id"], inputs[1]["input_id"]],
            },
        ],
    }
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    status, items, _digest = landing._summary_document(
        path,
        WEEK,
        ["100"],
        DIGEST,
        POLICY_DIGEST,
        PICKUP_DIGEST,
        inputs,
        _link_catalog(),
    )

    assert status == "current"
    assert [item["order"] for item in items] == [1, 2]
    assert "source_input_ids" not in json.dumps(items, ensure_ascii=False)
    assert "review_inputs" not in json.dumps(items, ensure_ascii=False)
    assert items[0]["deck_links"] == [
        {
            "order": 1,
            "token": f"deck:{'a' * 20}",
            "label": {
                "zh": "Example Parent · Example · 第1名",
                "en": "Example Parent · Example · Rank 1",
            },
            "deck": {
                key: _link_catalog()[0][key]
                for key in (
                    "archetype_id",
                    "display_name",
                    "event_id",
                    "deck_id",
                    "deck_fingerprint_sha256",
                    "player",
                    "final_rank",
                    "starttime",
                )
            },
        }
    ]


def test_summary_rejects_unknown_review_input_link(tmp_path):
    candidate = _candidate()
    inputs = landing._summary_review_inputs([], _published_pickup())
    candidate["landing_summary"] = {
        "summary_fact_digest": landing._summary_digest(
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        ),
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": True,
        "items": [
            {
                "order": 1,
                "text_zh": "人工结论",
                "text_en": "",
                "source_input_ids": ["unknown:0000000000000000"],
            }
        ],
    }
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    with pytest.raises(landing.MTGOLandingError, match="unknown review inputs"):
        landing._summary_document(
            path,
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        )


def test_summary_rejects_unknown_deck_link_token(tmp_path):
    candidate = _candidate()
    inputs = landing._summary_review_inputs([], _published_pickup())
    candidate["landing_summary"] = {
        "summary_fact_digest": landing._summary_digest(
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        ),
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": True,
        "items": [
            {
                "order": 1,
                "text_zh": f"人工结论：deck:{'b' * 20}",
                "text_en": f"Human conclusion: deck:{'b' * 20}",
                "source_input_ids": [],
            }
        ],
    }
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    with pytest.raises(landing.MTGOLandingError, match="unknown deck-link tokens"):
        landing._summary_document(
            path,
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        )


def test_summary_rejects_localized_deck_link_token_mismatch(tmp_path):
    candidate = _candidate()
    inputs = landing._summary_review_inputs([], _published_pickup())
    candidate["landing_summary"] = {
        "summary_fact_digest": landing._summary_digest(
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        ),
        "pickup_document_digest": PICKUP_DIGEST,
        "review_inputs": inputs,
        "deck_link_catalog": _link_catalog(),
        "reviewed": True,
        "items": [
            {
                "order": 1,
                "text_zh": f"人工结论：deck:{'a' * 20}",
                "text_en": "Human conclusion without the selected deck.",
            }
        ],
    }
    path = tmp_path / f"candidates_{WEEK}.yaml"
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")

    with pytest.raises(landing.MTGOLandingError, match="localized deck-link tokens"):
        landing._summary_document(
            path,
            WEEK,
            ["100"],
            DIGEST,
            POLICY_DIGEST,
            PICKUP_DIGEST,
            inputs,
            _link_catalog(),
        )


def test_pages_selection_excludes_private_pickup_review_files(tmp_path):
    from build_pages_artifact import publication_paths

    for relative in (
        "stats/standard/mtgo/landing/current.json",
        "stats/standard/mtgo/pickup/2026-W33.json",
        "stats/standard/mtgo/pickup/candidates_2026-W33.yaml",
        "stats/standard/mtgo/pickup/base_reference_2026-W33.yaml",
        "stats/standard/mtgo/pickup/known_archetypes.json",
        "stats/standard/mtgo/landing/review/2026-W33.yaml",
        "stats/standard/mtgo/landing/review/known_archetypes.json",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    config = {
        "site_files": ["index.html"],
        "site_directories": ["stats"],
        "excluded_patterns": [
                "stats/*/mtgo/pickup/base_reference_*.yaml",
                "stats/*/mtgo/pickup/candidates_*.yaml",
                "stats/*/mtgo/pickup/known_archetypes.json",
                "stats/*/mtgo/landing/review/*",
            ],
    }

    selected = publication_paths(tmp_path, config)

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W33.json" in selected
    assert not any("candidates_" in path for path in selected)
    assert not any("base_reference_" in path for path in selected)
    assert not any(path.endswith("known_archetypes.json") for path in selected)
    assert not any("/landing/review/" in path for path in selected)


def test_production_candidate_admits_only_latest_landing_document():
    from validate_production_candidate import _allowed_new_path

    formats = ("standard", "modern")
    assert _allowed_new_path(
        "stats/standard/mtgo/landing/current.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/2026-W33.json", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/candidates_2026-W33.yaml", formats, formats
    )
    assert not _allowed_new_path(
        "stats/standard/mtgo/landing/review/2026-W33.yaml", formats, formats
    )


def test_repository_pages_policy_admits_landing_but_excludes_private_pickup():
    from build_pages_artifact import load_config, publication_paths

    config_path = ROOT / "configs" / "pages_publication.json"
    selected = publication_paths(ROOT, load_config(ROOT, config_path))

    assert "stats/standard/mtgo/landing/current.json" in selected
    assert "stats/modern/mtgo/landing/current.json" in selected
    assert "stats/standard/mtgo/pickup/2026-W27.json" in selected
    assert not any("/pickup/candidates_" in path for path in selected)
    assert not any("/pickup/base_reference_" in path for path in selected)
    assert not any(path.endswith("/pickup/known_archetypes.json") for path in selected)
    assert not any("/landing/review/" in path for path in selected)


def test_landing_cli_requires_the_explicit_format_capability(monkeypatch, tmp_path):
    from mtgmeta.mtgo import __main__ as mtgo_cli

    calls = []

    def run(args, root, registry):
        calls.append((args.format_id, root, registry))
        return 0

    monkeypatch.setitem(mtgo_cli.RUNNERS, "build-landing", run)

    result = mtgo_cli.main(
        [
            "--root",
            str(tmp_path),
            "--registry",
            str(ROOT / "configs" / "formats.yaml"),
            "--format",
            "modern",
            "build-landing",
        ]
    )

    assert result == 0
    assert calls == [
        (
            "modern",
            tmp_path.resolve(),
            (ROOT / "configs" / "formats.yaml").resolve(),
        )
    ]


def test_landing_cli_reports_pending_summary_review_without_count_lookup(
    monkeypatch, tmp_path, capsys
):
    from mtgmeta.mtgo import __main__ as mtgo_cli

    monkeypatch.setattr(
        mtgo_cli.landing,
        "generate",
        lambda *args, **kwargs: {
            "status": "summary_review_required",
            "path": tmp_path / "current.json",
            "week": WEEK,
            "feature_count": 0,
            "summary_count": 0,
        },
    )

    result = mtgo_cli._run_landing(
        SimpleNamespace(format_id="standard"), tmp_path, tmp_path / "formats.yaml"
    )

    assert result == 0
    assert "preserved for explicit summary review" in capsys.readouterr().out


def test_existing_frontend_keeps_landing_in_the_accepted_product_order():
    source = (ROOT / "assets" / "js" / "phase8" / "app-core.js").read_text(
        encoding="utf-8"
    )

    assert "item.available && PRODUCT_ORDER.includes(item.id)" in source
    product_order = source.split("const PRODUCT_ORDER = [", 1)[1].split("];", 1)[0]
    assert '"mtgo-landing"' in product_order
