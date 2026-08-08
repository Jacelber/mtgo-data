"""P9-06 structure-aware Tabletop consumer contracts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PHASE8_JS = ROOT / "assets" / "js" / "phase8"
APP_FILES = ("app-core.js", "app-freshness.js", "app-mtgo.js", "app-tabletop.js", "app.js")


def _controller_result(script: str) -> dict:
    bootstrap = r"""
global.P8Runtime = {
  createJsonClient: () => ({fetchJson: async () => ({})}),
  dirname: value => value,
  joinPath: (...parts) => parts.join("/"),
};
require("./assets/js/phase8/tabletop-controller.js");
"""
    result = subprocess.run(
        ["node", "-e", bootstrap + script],
        cwd=ROOT,
        check=True,
        encoding="utf-8",
        capture_output=True,
    )
    return json.loads(result.stdout)


def _i18n_result(script: str) -> dict:
    result = subprocess.run(
        [
            "node",
            "-e",
            'require("./assets/js/phase8/i18n.js");' + script,
        ],
        cwd=ROOT,
        check=True,
        encoding="utf-8",
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_controller_resolves_declared_scopes_and_multi_event_lock() -> None:
    result = _controller_result(
        r"""
const events = [
  {
    event_id: "day2-event",
    event_structure: "constructed_day2",
    scope_order: ["day1", "day2", "all_constructed"],
    default_scope: "all_constructed",
  },
  {
    event_id: "single-event",
    event_structure: "constructed_single_stage",
    scope_order: ["all_constructed"],
    default_scope: "all_constructed",
  },
];
const api = global.P8TabletopController;
process.stdout.write(JSON.stringify({
  day2Single: api.resolveScopeState({
    events,
    selectedEventIds: ["day2-event"],
    activeEventId: "day2-event",
    requestedScope: "day1",
    preferredSingleScope: "all_constructed",
  }),
  singleStage: api.resolveScopeState({
    events,
    selectedEventIds: ["single-event"],
    activeEventId: "single-event",
    requestedScope: "day2",
    preferredSingleScope: "day2",
  }),
  multi: api.resolveScopeState({
    events,
    selectedEventIds: ["day2-event", "single-event"],
    activeEventId: "single-event",
    requestedScope: "day2",
    preferredSingleScope: "day2",
  }),
  restoredDay2: api.resolveScopeState({
    events,
    selectedEventIds: ["day2-event"],
    activeEventId: "day2-event",
    requestedScope: "all_constructed",
    preferredSingleScope: "day1",
    restoreSingleScope: true,
  }),
}));
"""
    )

    assert result["day2Single"] == {
        "multi_event": False,
        "scope": "day1",
        "scope_order": ["day1", "day2", "all_constructed"],
        "disabled_scopes": [],
    }
    assert result["singleStage"] == {
        "multi_event": False,
        "scope": "all_constructed",
        "scope_order": ["all_constructed"],
        "disabled_scopes": [],
    }
    assert result["multi"] == {
        "multi_event": True,
        "scope": "all_constructed",
        "scope_order": ["day1", "day2", "all_constructed"],
        "disabled_scopes": ["day1", "day2"],
    }
    assert result["restoredDay2"]["scope"] == "day1"


def test_controller_requires_one_event_format_across_loaded_documents() -> None:
    result = _controller_result(
        r"""
const api = global.P8TabletopController;
const documents = {
  index: {format: "standard"},
  meta: {format: "standard"},
  overview: {format: "standard"},
  matchup: {format: "standard"},
  quality: {format: "standard"},
  tabletopDecks: {format: "standard"},
  mtgoDecks: {format: "standard"},
};
let mismatch;
try {
  api.resolveEventFormat({
    requestedFormat: "standard",
    ...documents,
    matchup: {format: "modern"},
  });
} catch (error) {
  mismatch = error.message;
}
process.stdout.write(JSON.stringify({
  format: api.resolveEventFormat({
    requestedFormat: "standard",
    ...documents,
  }),
  mismatch,
}));
"""
    )

    assert result == {
        "format": "standard",
        "mismatch": "实体大赛文档的赛制不一致。",
    }


def test_tabletop_scope_labels_are_format_dynamic_and_bilingual() -> None:
    result = _i18n_result(
        r"""
const api = global.P8I18n;
const scopes = ["day1", "day2", "all_constructed"];
api.setLanguage("zh");
const zh = {
  standard: scopes.map(scope => api.tabletopScopeLabel(scope, "standard")),
  modern: scopes.map(scope => api.tabletopScopeLabel(scope, "modern")),
};
api.setLanguage("en");
const en = {
  standard: scopes.map(scope => api.tabletopScopeLabel(scope, "standard")),
  modern: scopes.map(scope => api.tabletopScopeLabel(scope, "modern")),
};
process.stdout.write(JSON.stringify({zh, en}));
"""
    )

    assert result == {
        "zh": {
            "standard": ["第一日标准", "第二日标准", "全部标准瑞士轮"],
            "modern": ["第一日摩登", "第二日摩登", "全部摩登瑞士轮"],
        },
        "en": {
            "standard": [
                "Day 1 Standard",
                "Day 2 Standard",
                "All Standard Swiss Rounds",
            ],
            "modern": [
                "Day 1 Modern",
                "Day 2 Modern",
                "All Modern Swiss Rounds",
            ],
        },
    }


def test_structure_presentation_preserves_mixed_and_dispatches_pure_metrics() -> None:
    result = _controller_result(
        r"""
const api = global.P8TabletopController;
process.stdout.write(JSON.stringify({
  mixed: api.structurePresentation({event_structure: "mixed"}),
  day2: api.structurePresentation({
    event_structure: "constructed_day2",
    advancement_metric: "day2_conversion",
  }),
  single: api.structurePresentation({
    event_structure: "constructed_single_stage",
    advancement_metric: "high_score_conversion",
  }),
}));
"""
    )

    assert result == {
        "mixed": {
            "advancement_metric": "high_score",
            "show_mixed_selection_bias": True,
        },
        "day2": {
            "advancement_metric": "day2_conversion",
            "show_mixed_selection_bias": False,
        },
        "single": {
            "advancement_metric": "high_score",
            "show_mixed_selection_bias": False,
        },
    }


def test_renderer_exposes_bilingual_structure_states_without_aggregation() -> None:
    app = "\n".join(
        (PHASE8_JS / name).read_text(encoding="utf-8")
        for name in APP_FILES
    )
    i18n = (PHASE8_JS / "i18n.js").read_text(encoding="utf-8")

    for key in (
        "tabletop.day2_conversion",
        "tabletop.day2_conversion_tip",
        "tabletop.multi_scope_lock",
        "tabletop.multi_event_pending",
    ):
        assert i18n.count(f'"{key}"') == 2

    assert "TabletopController.resolveScopeState" in app
    assert "TabletopController.structurePresentation" in app
    assert "disabledScopes.has(scopeId)" in app
    assert "tabletop.multi_event_pending" in app
    assert "sum_raw_wld_then_recalculate" not in app
    assert "I18n.tabletopScopeLabel(scope, formatId)" in app
    assert "scopeLabel(scopeId, eventFormat)" in app
    assert "issueMessage(issue, eventFormat)" in app

    for fixed_label in (
        '"tabletop.scope.day1": "第一日摩登"',
        '"tabletop.scope.day2": "第二日摩登"',
        '"tabletop.scope.all_constructed": "全部摩登瑞士轮"',
        '"tabletop.scope.day1": "Day 1 Modern"',
        '"tabletop.scope.day2": "Day 2 Modern"',
        '"tabletop.scope.all_constructed": "All Modern Swiss Rounds"',
    ):
        assert fixed_label not in i18n


def test_current_mixed_event_remains_a_three_scope_high_score_surface() -> None:
    overview = json.loads(
        (
            ROOT
            / "stats"
            / "modern"
            / "melee"
            / "events"
            / "434455"
            / "overview.json"
        ).read_text(encoding="utf-8")
    )

    assert overview["event_structure"] == "mixed"
    assert overview["scope_order"] == ["day1", "day2", "all_constructed"]
    assert overview["scopes"]["day1"]["high_score_deck_count"] is not None
    assert overview["scopes"]["day2"]["high_score_deck_count"] is not None
