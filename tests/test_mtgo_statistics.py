"""P3-04 tests for format-aware MTGO event and rolling-range statistics."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import stats_standard
from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo import stats as mtgo_stats


EXPECTED_FILES = {
    "index.json",
    "range_1w.json",
    "range_4w.json",
    "range_12w.json",
    "range_36w.json",
    "decks_1w.json",
    "decks_4w.json",
    "decks_12w.json",
    "decks_36w.json",
}
REFERENCE_TODAY = date(2026, 7, 19)
REFERENCE_GENERATED = datetime(2026, 7, 19, 21, 0, 4)


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


@pytest.mark.committed_baseline
def test_fixed_reference_regeneration_is_byte_identical(tmp_path):
    written = mtgo_stats.build_all_stats(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        generated_at=REFERENCE_GENERATED,
        output_directory=tmp_path,
    )
    assert set(written) == EXPECTED_FILES
    committed = ROOT / "stats" / "standard" / "mtgo"
    for filename in sorted(EXPECTED_FILES):
        assert written[filename].read_bytes() == (committed / filename).read_bytes(), filename


@pytest.mark.committed_baseline
def test_legacy_standard_wrapper_uses_the_same_fixed_output(tmp_path):
    written = stats_standard.build_all_stats(
        today=REFERENCE_TODAY,
        generated_at=REFERENCE_GENERATED,
        output_directory=tmp_path,
    )
    assert set(written) == EXPECTED_FILES
    assert stats_standard.deck_diff is mtgo_stats.deck_diff
    assert stats_standard.weighted_l1 is mtgo_stats.weighted_l1
    assert len(stats_standard.load_all_events()) == 123


def test_disabled_format_fails_before_output_side_effects(tmp_path):
    destination = tmp_path / "pauper-output"
    with pytest.raises(DisabledFormatError, match="not enabled"):
        mtgo_stats.build_all_stats(
            ROOT,
            "pauper",
            today=REFERENCE_TODAY,
            generated_at=REFERENCE_GENERATED,
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
