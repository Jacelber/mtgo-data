"""P3-04 tests for format-aware MTGO event and rolling-range statistics."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo import stats as mtgo_stats


def committed_statistics_reference() -> tuple[date, datetime]:
    index = json.loads(
        (ROOT / "stats" / "standard" / "mtgo" / "index.json").read_text(
            encoding="utf-8"
        )
    )
    generated = datetime.fromisoformat(index["generated"])
    return generated.date(), generated


def test_round_and_high_score_boundaries_remain_frozen():
    assert [mtgo_stats.rounds_from_player_count(value) for value in (8, 9, 16, 17, 32, 33)] == [
        3,
        4,
        4,
        5,
        5,
        6,
    ]
    assert [mtgo_stats.high_score_threshold(rounds) for rounds in (5, 6, 7, 8, 9)] == [
        9,
        12,
        12,
        15,
        15,
    ]


def test_process_event_rejects_missing_swiss_score_instead_of_counting_zero():
    event = {
        "event_id": "incomplete",
        "description": "Incomplete fixture",
        "player_count": 8,
        "players": [
            {
                "player": "Fixture",
                "swiss_score": None,
                "final_rank": 1,
                "main_deck": [],
                "sideboard": [],
            }
        ],
    }

    with pytest.raises(mtgo_stats.MTGOStatisticsError, match="swiss_score"):
        mtgo_stats.process_event(event, {})


def test_latest_complete_week_is_deterministic_at_the_reference_boundary():
    events = [
        (date(2026, 7, 12), {}),
        (date(2026, 7, 13), {}),
    ]
    assert mtgo_stats.latest_complete_week(events, today=date(2026, 7, 19)) == date(
        2026, 7, 6
    )
    assert mtgo_stats.latest_complete_week(events, today=date(2026, 7, 20)) == date(
        2026, 7, 13
    )


def test_disabled_format_fails_before_output_side_effects(tmp_path):
    reference_today, reference_generated = committed_statistics_reference()
    destination = tmp_path / "pauper-output"
    with pytest.raises(DisabledFormatError, match="not enabled"):
        mtgo_stats.build_all_stats(
            ROOT,
            "pauper",
            today=reference_today,
            generated_at=reference_generated,
            output_directory=destination,
        )
    assert not destination.exists()


def test_invalid_ranges_fail_before_output_side_effects(tmp_path):
    destination = tmp_path / "invalid-output"
    with pytest.raises(mtgo_stats.MTGOStatisticsError, match="positive integers"):
        mtgo_stats.build_all_stats(
            ROOT,
            "standard",
            output_directory=destination,
            ranges=(0,),
        )
    assert not destination.exists()


def test_shared_statistics_module_has_no_implicit_standard_paths():
    source = (SRC / "mtgmeta" / "mtgo" / "stats.py").read_text(encoding="utf-8")
    assert '"data/standard"' not in source
    assert '"stats/standard/mtgo"' not in source
    workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
    assert "src/mtgmeta/mtgo/stats.py" not in workflow
    assert "python -B stats_standard.py" not in workflow
    assert "build-statistics" in workflow


def test_legacy_public_card_alias_scope_is_preserved():
    assert mtgo_stats.normalize_legacy_card_name(" Kavaero, Mind-Bitten ") == (
        "Superior Spider-Man"
    )
    assert mtgo_stats.normalize_legacy_card_name("Leyline Weaver") == "Spider Manifestation"
    assert mtgo_stats.normalize_legacy_card_name("Unrelated Card") == "Unrelated Card"
