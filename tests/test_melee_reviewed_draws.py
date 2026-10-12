"""Keep three-draw notation and Owner-reviewed exclusions distinct from played draws."""

from dataclasses import replace
from pathlib import Path

import pytest

from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.normalize import MeleeNormalizationError, _override_result, _source_result
from mtgmeta.melee.parser import SourceCompetitor, SourceMatch


ROOT = Path(__file__).resolve().parents[1]


def _event():
    return load_melee_event_registry(ROOT / "configs/melee_events.yaml").get("405591")


def _draw(text, *, outcome=None, points=None):
    ids = ("4367375", "4367233")
    return SourceMatch(
        source_match_id="7cfd7a2f-6119-4cbf-bf3d-b4e0016f89f9",
        source_round_id="1425508",
        competitor_source_ids=ids,
        competitor_results=tuple(SourceCompetitor(pid, outcome, points) for pid in ids),
        result_text=text,
        status_text=None,
        table_number=9,
    )


@pytest.mark.parametrize("text", ["0-0-3", "0-0-3 Draw", " 0-0-3 DRAW "])
def test_three_draw_text_resolves_missing_structured_results(text):
    played, results = _source_result(_draw(text), _event())
    assert played is False
    assert [r["result_type"] for r in results] == ["intentional_draw"] * 2
    assert [r["match_points"] for r in results] == [1, 1]


def test_three_draw_text_does_not_override_contradictory_points():
    assert _source_result(_draw("0-0-3 Draw", points=3), _event()) is None


@pytest.mark.parametrize("text", ["0-0-1 Draw", "1-1-1 Draw"])
def test_other_draw_scores_remain_played_without_reviewed_override(text):
    played, results = _source_result(_draw(text, outcome="Draw", points=1), _event())
    assert played is True
    assert [r["result_type"] for r in results] == ["played_draw"] * 2


def test_round15_exclusion_is_bound_to_one_match_and_both_participants():
    (override,) = _event().reviewed_overrides
    source = _draw("0-0-1 Draw", outcome="Draw", points=1)
    assert override.source_match_id == source.source_match_id
    played, results = _override_result(source, override)
    assert played is False
    assert [r["result_type"] for r in results] == ["intentional_draw"] * 2
    assert [r["match_points"] for r in results] == [1, 1]
    assert "2026-10-12" in override.reason
    assert "not an official ID flag" in override.reason
    with pytest.raises(MeleeNormalizationError, match="competitor identities"):
        _override_result(replace(source, competitor_source_ids=("4367375", "9999999")), override)
