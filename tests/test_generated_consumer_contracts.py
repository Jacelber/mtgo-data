"""Dynamic consumer contracts for freshly generated MTGO candidates."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
RANGES = (1, 4, 12)


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _node(script: str, *args: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script, *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("format_id", ("standard", "modern"))
def test_current_matchup_consumer_follows_generated_parent_order(
    format_id: str,
) -> None:
    relative_path = f"stats/{format_id}/mtgo/matchup_4w.json"
    source = _json(relative_path)
    script = r"""
const fs = require("fs");
const review = require("./assets/js/phase8/matchup-model.js");
const source = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const document = review.activeMatchupDocument(source, 20);
const collapsed = review.buildView(document, [], []);
const expandedParent = document.hierarchy.parents.find(parent =>
  parent.expandable && document.parent_order.includes(parent.id)
);
const drawRecord = review.literalRecord({wins: 1, losses: 1, draws: 1});
process.stdout.write(JSON.stringify({
  collapsedRowIds: collapsed.rows.map(row => row.id),
  expansion: expandedParent ? (() => {
    const expanded = review.buildView(
      document,
      [expandedParent.id],
      [expandedParent.id]
    );
    const subtypeId = expandedParent.subtype_ids[0];
    return {
      parentRetained: expanded.rows.some(row => row.id === expandedParent.id),
      subtypeIds: expanded.rows
        .filter(row => row.parentId === expandedParent.id && row.kind === "subtype")
        .map(row => row.id),
      activeSubtypeIds: expandedParent.subtype_ids,
      crossLevel: expanded.matrix[expandedParent.id][subtypeId],
    };
  })() : null,
  minSampleHint: document.min_sample_hint,
  drawRecord,
}));
"""
    result = _node(script, relative_path)

    assert result["collapsedRowIds"] == source["parent_order"]
    assert result["minSampleHint"] == 20
    assert result["drawRecord"]["win_rate"] == 1 / 3
    if expansion := result["expansion"]:
        assert expansion["parentRetained"] is True
        assert expansion["subtypeIds"] == expansion["activeSubtypeIds"]
        cross_level = expansion["crossLevel"]
        assert cross_level["matches"] == (
            cross_level["wins"] + cross_level["losses"] + cross_level["draws"]
        )


@pytest.mark.parametrize("format_id", ("standard", "modern"))
@pytest.mark.parametrize("weeks", RANGES)
def test_current_freshness_inputs_are_internally_consistent(
    format_id: str,
    weeks: int,
) -> None:
    range_document = _json(f"stats/{format_id}/mtgo/range_{weeks}w.json")
    completeness = _json(f"stats/{format_id}/mtgo/completeness/{weeks}w.json")
    high_score = completeness["high_score_decklist_completeness"]
    coverage = completeness["matchup_coverage"]

    assert completeness["period"] == range_document["period"]
    assert high_score["period"] == {
        "start": range_document["period"]["start"],
        "end": range_document["period"]["end"],
    }
    assert high_score["observed_decklist_count"] == range_document["total_high_score"]
    assert coverage["expected_event_count"] == (
        coverage["available_event_count"]
        + coverage["deferred_event_count"]
        + coverage["missing_event_count"]
    )


@pytest.mark.parametrize("format_id", ("standard", "modern"))
def test_current_top8_freshness_inputs_follow_the_latest_generated_week(
    format_id: str,
) -> None:
    index = _json(f"stats/{format_id}/mtgo/top8/index.json")
    impact = index["classification_impact"]
    latest = index["weeks"][0]
    document = _json(f"stats/{format_id}/mtgo/top8/{latest['file']}")
    placements = [
        placement
        for event in document["events"]
        for placement in event.get("placements", [])
    ]

    assert latest["event_count"] == len(document["events"])
    assert document["week"]["start"] == latest["start"]
    assert document["week"]["end"] == latest["end"]
    assert impact["summary"]["retained_week_count"] == len(index["weeks"])
    for entry in index["weeks"]:
        week = _json(f"stats/{format_id}/mtgo/top8/{entry['file']}")
        bases = _json(
            f"stats/{format_id}/mtgo/top8/{entry['comparison_bases_file']}"
        )
        assert week["classifier_digest"] == index["classifier_digest"]
        assert bases["classifier_digest"] == index["classifier_digest"]
    assert all(
        placement["deck_status"] in {"available", "unavailable"}
        for placement in placements
    )


def test_current_pickup_freshness_inputs_follow_the_latest_generated_week() -> None:
    index = _json("stats/standard/mtgo/pickup/index.json")
    latest = index["weeks"][0]
    document = _json(f"stats/standard/mtgo/pickup/{latest['file']}")

    assert document["week"] == latest["week"]
    assert document["start"] == latest["start"]
    assert document["end"] == latest["end"]
    assert latest["existing_count"] == len(document["existing_changes"])
    assert latest["new_count"] == len(document["new_archetypes"])


@pytest.mark.parametrize("format_id", ("standard", "modern"))
def test_current_landing_follows_one_classifier_and_population_subject(
    format_id: str,
) -> None:
    document = _json(f"stats/{format_id}/mtgo/landing/current.json")
    environment = document["environment"]
    current = document["populations"]["current"]

    assert document["product"] == "mtgo-landing"
    assert document["source_event_ids"] == sorted(set(document["source_event_ids"]))
    assert document["source_event_ids"] == current["event_ids"]
    assert document["review_binding"]["source_event_ids"] == document["source_event_ids"]
    assert document["review_binding"]["classifier_digest"] == document["classifier"]["digest"]
    assert len(document["review_binding"]["visual_metadata_digest"]) == 64
    assert len(document["review_binding"]["machine_fact_digest"]) == 64
    if document["schema_version"] == "1.0.0":
        assert len(document["observations"]) <= 5
        assert "weekly_summary" not in document
    else:
        assert document["schema_version"] == "1.1.0"
        assert "observations" not in document
        assert len(document["review_binding"]["pickup_document_digest"]) == 64
        assert len(document["review_binding"]["summary_fact_digest"]) == 64
        assert document["weekly_summary"]["week"] == document["week"]["id"]
    assert all(
        row["current"]["share"] >= environment["threshold"]
        for row in environment["rows"]
    )
    assert all(len(row["key_cards"]) in {0, 2} for row in environment["rows"])
    assert all(
        item["category"] in {"new_deck", "new_technology"}
        and len(item["featured_cards"]) == 4
        for item in document["features"]["items"]
    )
