"""Legacy Standard entry point for format-aware MTGO statistics."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent
SHARED_SRC = REPOSITORY_ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from classify_standard import deck_to_counts, load_rules, match_archetype, normalize_name
from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo import stats as _shared


FORMAT_ID = "standard"
DATA_DIR = str(
    load_mtgo_context(REPOSITORY_ROOT, FORMAT_ID, "event_statistics").paths["events"]
)

AVG_FLOOR = _shared.AVG_FLOOR
MIN_SAMPLE = _shared.MIN_SAMPLE
BASE_WEEKS = _shared.BASE_WEEKS
CORE_RATE = _shared.CORE_RATE
DEV_PERCENTILE = _shared.DEV_PERCENTILE
RECENT_MIN = _shared.RECENT_MIN
PRIOR_WEEKS = _shared.PRIOR_WEEKS

to_int = _shared.to_int
rounds_from_player_count = _shared.rounds_from_player_count
high_score_threshold = _shared.high_score_threshold
parse_event_date = _shared.parse_event_date
week_monday = _shared.week_monday
latest_complete_week = _shared.latest_complete_week
aggregate = _shared.aggregate
deck_vector = _shared.deck_vector
mean_vector = _shared.mean_vector
appearance_rates = _shared.appearance_rates
split_core_flex = _shared.split_core_flex
weighted_l1 = _shared.weighted_l1
normalize_dev = _shared.normalize_dev
dev_denominator = _shared.dev_denominator
normalize_dev_abs = _shared.normalize_dev_abs
deck_diff = _shared.deck_diff
pick_medoid = _shared.pick_medoid
record_to_deck_display = _shared.record_to_deck_display
recent_change_for_arch = _shared.recent_change_for_arch
build_base_pack = _shared.build_base_pack
percentile = _shared.percentile
build_decks = _shared.build_decks
merge_cards = _shared.merge_cards
pick_best_deck = _shared.pick_best_deck
_neg_time_key = _shared._neg_time_key


def _legacy_classify_player(player, archetypes):
    main_counts, side_counts = deck_to_counts(player)
    return match_archetype(main_counts, side_counts, archetypes)


def process_event(event, archetypes):
    """Preserve the legacy classifier call path for existing consumers."""

    return _shared.process_event(
        event,
        archetypes,
        classifier=_legacy_classify_player,
    )


def load_all_events():
    return _shared.load_all_events(REPOSITORY_ROOT, FORMAT_ID)


def build_range(events, archetypes, end_monday, n_weeks, base_pack, d99):
    return _shared.build_range(
        events,
        archetypes,
        end_monday,
        n_weeks,
        base_pack,
        d99,
        format_id=FORMAT_ID,
    )


def build_all_stats(
    today: date | None = None,
    *,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
):
    return _shared.build_all_stats(
        REPOSITORY_ROOT,
        FORMAT_ID,
        today=today,
        generated_at=generated_at,
        output_directory=output_directory,
    )


def main():
    written = build_all_stats()
    if not written:
        print("No complete MTGO event week is available.")
        return
    index_path = written["index.json"]
    print(f"Standard MTGO statistics written to {index_path.parent}")


if __name__ == "__main__":
    main()
