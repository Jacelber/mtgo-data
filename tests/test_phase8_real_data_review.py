"""P8-07 real-data review prototype contracts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "docs" / "prototypes" / "P8-07"
PHASE8_ASSETS = ROOT / "assets" / "js" / "phase8"
APP_FILES = ("app-core.js", "app-freshness.js", "app-mtgo.js", "app-tabletop.js", "app.js")


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


def test_review_entry_point_is_chinese_first_and_uses_candidate_assets() -> None:
    html = (PROTOTYPE / "index.html").read_text(encoding="utf-8")
    app = "\n".join(
        (PHASE8_ASSETS / name).read_text(encoding="utf-8")
        for name in APP_FILES
    )
    copy = app + (PHASE8_ASSETS / "i18n.js").read_text(encoding="utf-8")

    assert "P8-07 真实生产数据评审" in html
    assert "../../../assets/css/phase8-base.css" in html
    assert "../../../assets/css/phase8-candidate.css" in html
    assert "../../../assets/js/phase8/mtgo-controller.js" in html
    assert "../../../assets/js/phase8/tabletop-controller.js" in html
    assert "MTGO占比统计" in copy
    assert "MTGO官方数据统计" not in copy
    assert '"product.pickup": "每周精选套牌"' in copy
    assert '"format.pauper": "纯铁"' in copy
    assert "const RANGE_OPTIONS = [1, 4, 12];" in app
    assert "const DIFF_MIN = 1;" in app
    assert "const LOW_SAMPLE_THRESHOLD = 20;" in app
    assert 'class="pie-slice"' not in app
    assert "data-pie-detail" not in app
    assert 'const className = `composition-segment' in app
    assert '"chart.title": "高分牌表环境构成"' in copy
    assert "Number(item.high_score_share) >= 0.03" in app
    assert "composition-legend" not in app
    assert "data-tabletop-sort" in app
    assert "data-tabletop-detail" in app
    assert "MTGO 最近4周平均构筑与典型牌表" in copy
    assert "查看 Melee 原始牌表" not in app
    assert "近四周样本不足，暂无平均构筑与变化度数据。" in copy
    assert "最近一周样本不足，暂不显示近期构筑变化度。" in copy
    assert "activeMatchupDocument" in app
    assert "activeStatisticsSubtypes" in app
    assert "activeTabletopSubtypes" in app
    assert "合并赛事：" not in app
    assert "summary-grid" not in app
    assert 'Runtime.catalog.fetchJson("stats/catalog.json")' in app
    assert "modernTop8Events" not in app
    assert "prototype-cut" not in app


def test_catalog_and_real_review_payloads_have_expected_density() -> None:
    catalog = _json("stats/catalog.json")
    available = [
        (format_entry["id"], product["id"])
        for format_entry in catalog["formats"]
        for product in format_entry["products"]
        if product["available"]
    ]
    standard = _json("stats/standard/mtgo/top8/2026-W30.json")
    modern = _json("stats/modern/mtgo/top8/2026-W30.json")

    assert len(catalog["formats"]) == 6
    assert len(available) == 8
    assert len(standard["events"]) == 8
    assert sum(len(event["placements"]) for event in standard["events"]) == 64
    assert len(modern["events"]) == 13
    assert sum(len(event["placements"]) for event in modern["events"]) == 104


def test_top8_review_uses_immutable_bases_and_explicit_unavailable_states() -> None:
    for format_id, expected_available, expected_unavailable in (
        ("standard", 61, 3),
        ("modern", 100, 4),
    ):
        top8 = _json(f"stats/{format_id}/mtgo/top8/2026-W30.json")
        bases = _json(f"stats/{format_id}/mtgo/top8/2026-W30-bases.json")
        statuses = [
            placement["comparison"]["base_status"]
            for event in top8["events"]
            for placement in event["placements"]
        ]

        assert statuses.count("available") == expected_available
        assert statuses.count("unavailable") == expected_unavailable
        assert bases["base_period_end"] == top8["week"]["end"]
        assert all(
            placement["comparison"]["average_deck_ref"].startswith(
                "2026-W30-bases.json#identity/"
            )
            for event in top8["events"]
            for placement in event["placements"]
        )


def test_review_matrix_follows_parent_order_and_uses_literal_wins_over_matches() -> None:
    source = _json("stats/modern/mtgo/matchup_4w.json")
    script = r"""
const fs = require("fs");
const review = require("./assets/js/phase8/matchup-model.js");
const source = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const document = review.activeMatchupDocument(source, 20);
const collapsed = review.buildView(document, [], []);
const expandedParent = document.hierarchy.parents.find(parent =>
  parent.expandable && document.parent_order.includes(parent.id)
);
if (!expandedParent) throw new Error("Real matchup data has no expandable parent");
const expanded = review.buildView(
  document,
  [expandedParent.id],
  [expandedParent.id]
);
const subtypeId = expandedParent.subtype_ids[0];
const drawRecord = review.literalRecord({wins: 1, losses: 1, draws: 1});
process.stdout.write(JSON.stringify({
  collapsedRowIds: collapsed.rows.map(row => row.id),
  parentRetained: expanded.rows.some(row => row.id === expandedParent.id),
  subtypeIds: expanded.rows
    .filter(row => row.parentId === expandedParent.id && row.kind === "subtype")
    .map(row => row.id),
  activeSubtypeIds: expandedParent.subtype_ids,
  crossLevel: expanded.matrix[expandedParent.id][subtypeId],
  minSampleHint: document.min_sample_hint,
  drawRecord,
}));
"""
    result = _node(
        script,
        "stats/modern/mtgo/matchup_4w.json",
    )

    assert result["collapsedRowIds"] == source["parent_order"]
    assert result["parentRetained"] is True
    assert result["subtypeIds"] == result["activeSubtypeIds"]
    assert result["minSampleHint"] == 20
    cross_level = result["crossLevel"]
    assert cross_level["matches"] == (
        cross_level["wins"] + cross_level["losses"] + cross_level["draws"]
    )
    assert result["drawRecord"]["win_rate"] == 1 / 3


def test_tabletop_review_reads_literal_records_and_real_diagonal() -> None:
    overview = _json("stats/modern/melee/events/434455/overview.json")
    matchup = _json("stats/modern/melee/events/434455/matchup.json")
    scope = matchup["scopes"]["all_constructed"]
    first_parent = scope["parent_order"][0]
    diagonal = scope["parent_matrix"][first_parent][first_parent]["literal_record"]
    first_overview = overview["scopes"]["all_constructed"]["archetypes"][0]
    literal = first_overview["match_record"]["all_matches"]["literal_record"]

    assert matchup["rate_method"]["literal_win_rate_method"] == (
        "wins_over_valid_matches"
    )
    assert diagonal["matches"] > 0
    assert diagonal["win_rate"] == pytest.approx(
        diagonal["wins"] / diagonal["matches"], abs=1e-6
    )
    assert literal["win_rate"] == pytest.approx(
        literal["wins"] / literal["matches"], abs=1e-6
    )
    assert first_overview["match_record"]["all_matches"]["win_rate"] != (
        literal["win_rate"]
    )


def test_tabletop_deck_payload_supports_scope_specific_best_deck_review() -> None:
    decks = _json("stats/modern/melee/events/434455/decks.json")["decks"]
    eligible = [
        deck
        for deck in decks
        if deck["classification"]["archetype_id"] == "broodscale-combo"
        and deck["classification"]["subtype_id"] == "gruul"
        and deck["participant_status"] != "disqualified"
        and not deck["statistics_eligibility"]["played_match_metrics_excluded"]
        and deck["decklist"]["status"] == "submitted"
        and deck["scopes"]["all_constructed"]["participated"]
    ]

    assert eligible
    assert all(deck["decklist"]["cards"] for deck in eligible)
    assert all(
        deck["scopes"]["all_constructed"]["average_points_per_effective_round"]
        is not None
        for deck in eligible
    )
