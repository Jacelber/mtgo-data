"""P7-08 cross-layer closeout contracts for the Phase 7 backend."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVENT_ID = "434455"
FORMAT = "modern"
DATA_ROOT = ROOT / "data" / FORMAT / "melee"
STATS_ROOT = ROOT / "stats" / FORMAT / "melee"
EVENT_STATS = STATS_ROOT / "events" / EVENT_ID
SCOPES = ("day1", "day2", "all_constructed")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_phase7_artifact_graph_is_complete_and_exact():
    event_path = DATA_ROOT / "events" / f"{EVENT_ID}.json"
    classification_path = DATA_ROOT / "classifications" / f"{EVENT_ID}.json"
    opportunity_path = DATA_ROOT / "opportunities" / f"{EVENT_ID}.json"
    event = load_json(event_path)
    classification = load_json(classification_path)
    opportunities = load_json(opportunity_path)
    documents = {
        name: load_json(EVENT_STATS / f"{name}.json")
        for name in ("overview", "decks", "matchup", "quality", "meta")
    }
    catalog = load_json(STATS_ROOT / "index.json")

    event_identity = {
        "event_id": event["metadata"]["event_id"],
        "source": event["metadata"]["source"],
        "format": event["metadata"]["constructed_format"],
    }
    assert event_identity == {
        "event_id": EVENT_ID,
        "source": "melee",
        "format": FORMAT,
    }
    for document in (classification, opportunities, *documents.values()):
        assert {
            "event_id": document["event_id"],
            "format": document["format"],
            "source": document["source"],
        } == {"event_id": EVENT_ID, "format": FORMAT, "source": "melee"}

    assert classification["input"]["event_sha256"] == digest(event_path)
    assert opportunities["input"]["event_sha256"] == digest(event_path)
    assert opportunities["input"]["classification_sha256"] == digest(
        classification_path
    )
    shared_input = documents["overview"]["input"]
    assert all(
        document["input"] == shared_input
        for document in documents.values()
    )
    assert shared_input["event_sha256"] == digest(event_path)
    assert shared_input["classification_sha256"] == digest(classification_path)
    assert shared_input["opportunity_sha256"] == digest(opportunity_path)

    meta = documents["meta"]
    for name in ("overview", "decks", "matchup", "quality"):
        path = EVENT_STATS / f"{name}.json"
        assert meta["outputs"][name]["path"] == f"{name}.json"
        assert meta["outputs"][name]["bytes"] == path.stat().st_size
        assert meta["outputs"][name]["sha256"] == digest(path)

    assert len(catalog["events"]) == 1
    entry = catalog["events"][0]
    assert catalog["default_event_id"] == EVENT_ID
    assert entry["event_id"] == EVENT_ID
    assert {
        entry[name]
        for name in ("meta", "overview", "decks", "matchup", "quality")
    } == {
        f"events/{EVENT_ID}/{name}.json"
        for name in ("meta", "overview", "decks", "matchup", "quality")
    }

    manifest = load_json(ROOT / "schemas" / "manifest.json")
    governed = {
        mapping["pattern"]
        for mapping in manifest["mappings"]
        if mapping["pattern"].startswith(f"stats/{FORMAT}/melee/")
    }
    assert governed == {
        f"stats/{FORMAT}/melee/events/{EVENT_ID}/{name}.json"
        for name in ("overview", "decks", "matchup", "quality", "meta")
    } | {f"stats/{FORMAT}/melee/index.json"}


def test_phase7_mixed_event_match_counts_reconcile_and_exclude_non_modern_rounds():
    event = load_json(DATA_ROOT / "events" / f"{EVENT_ID}.json")
    opportunities = load_json(DATA_ROOT / "opportunities" / f"{EVENT_ID}.json")
    overview = load_json(EVENT_STATS / "overview.json")
    matchup = load_json(EVENT_STATS / "matchup.json")
    quality = load_json(EVENT_STATS / "quality.json")

    constructed_rounds = {
        round_record["number"]
        for round_record in event["rounds"]
        if round_record["round_phase"] == "constructed"
        and round_record["game_format"] == FORMAT
        and round_record["swiss"]
    }
    assert constructed_rounds == {4, 5, 6, 7, 8, 12, 13, 14, 15, 16}

    for scope in SCOPES:
        ledger = opportunities["scope_summaries"][scope]
        event_overview = overview["scopes"][scope]
        matrix = matchup["scopes"][scope]
        assert (
            ledger["win_rate_match_count"]
            == ledger["matchup_match_count"]
            == event_overview["eligible_match_count"]
            == matrix["included_match_count"]
        )
        assert ledger["source_match_count"] == matrix["source_match_count"]
        assert matrix["directed_observation_count"] == 2 * matrix[
            "included_match_count"
        ]
        assert set(matrix["round_numbers"]) <= constructed_rounds
        assert matrix["excluded_match_count"] == sum(
            matrix["excluded_match_counts"].values()
        )

    day1 = matchup["scopes"]["day1"]
    day2 = matchup["scopes"]["day2"]
    combined = matchup["scopes"]["all_constructed"]
    for field in ("source_match_count", "included_match_count", "excluded_match_count"):
        assert combined[field] == day1[field] + day2[field]
    assert set(combined["round_numbers"]) == constructed_rounds
    assert combined["included_match_count"] == 1394
    assert combined["excluded_match_counts"] == {
        "bye": 7,
        "intentional_draw": 2,
        "no_show": 0,
        "awarded_win_top8_lock": 7,
        "administrative_result": 0,
        "disqualified_participant": 6,
        "unknown": 0,
    }
    assert quality["counts"]["eligible_constructed_matches"] == 1394
    assert quality["counts"]["disqualified_matches_excluded"] == 6
    assert next(
        check for check in quality["checks"] if check["id"] == "draft_and_playoff_excluded"
    )["passed"]


def test_phase7_workflows_and_public_roots_remain_source_separated():
    melee_workflow_path = ROOT / ".github" / "workflows" / "fetch_melee.yml"
    mtgo_workflow_path = ROOT / ".github" / "workflows" / "update.yml"
    melee_text = melee_workflow_path.read_text(encoding="utf-8")
    mtgo_text = mtgo_workflow_path.read_text(encoding="utf-8")
    melee_workflow = yaml.load(melee_text, Loader=yaml.BaseLoader)
    mtgo_workflow = yaml.load(mtgo_text, Loader=yaml.BaseLoader)

    assert set(melee_workflow["on"]) == {"workflow_dispatch"}
    assert "schedule" not in melee_workflow["on"]
    assert "schedule" in mtgo_workflow["on"]
    assert "mtgmeta.mtgo" not in melee_text
    assert "melee" not in mtgo_text.lower()
    assert (
        'git add -- "data_raw/melee/${EVENT_ID}/" "data/${FORMAT}/melee/" '
        '"stats/${FORMAT}/melee/"'
    ) in melee_text
    assert "HEAD:master" not in melee_text

    mtgo_meta = load_json(ROOT / "stats" / FORMAT / "mtgo" / "meta.json")
    melee_catalog = load_json(STATS_ROOT / "index.json")
    assert (mtgo_meta["source"], mtgo_meta["format"]) == ("mtgo", FORMAT)
    assert (melee_catalog["source"], melee_catalog["format"]) == ("melee", FORMAT)
