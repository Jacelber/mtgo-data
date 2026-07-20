"""Legacy Standard entry point for format-aware MTGO matchup statistics."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent
SHARED_SRC = REPOSITORY_ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from classify_standard import deck_to_counts, load_rules, match_archetype
from mtgmeta.legacy_rules import LegacyArchetypeRules
from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo import matchup as _shared


FORMAT_ID = "standard"
_CONTEXT = load_mtgo_context(REPOSITORY_ROOT, FORMAT_ID, "matchup_statistics")
OFFICIAL_DIR = str(_CONTEXT.paths["events"])
MATCHES_DIR = str(_CONTEXT.paths["matches"])
OUT_DIR = str(_CONTEXT.paths["statistics"])

RANGES = list(_shared.DEFAULT_RANGES)
MIN_MATCHUP_SAMPLE = _shared.MIN_MATCHUP_SAMPLE
WILSON_Z = _shared.WILSON_Z
wilson_half_width = _shared.wilson_half_width
_blank_cell = _shared._blank_cell
_win_rate = _shared._win_rate
_emit_cell = _shared._emit_cell
build_window_output = _shared.build_window_output


def _legacy_rule_set(archetypes):
    return archetypes.rule_set if isinstance(archetypes, LegacyArchetypeRules) else archetypes


def load_official_events(archetypes):
    return _shared.load_official_events_from_directory(
        OFFICIAL_DIR,
        _legacy_rule_set(archetypes),
        classifier=lambda player, _rules: match_archetype(
            *deck_to_counts(player),
            archetypes,
        ),
    )


def accumulate_event(
    event_id,
    player_arch,
    official_names,
    matrix,
    mirror,
    overall,
    seen_keys,
    stats,
):
    return _shared.accumulate_event(
        MATCHES_DIR,
        event_id,
        player_arch,
        official_names,
        matrix,
        mirror,
        overall,
        seen_keys,
        stats,
    )


def build_window(events, end_monday, n_weeks):
    return _shared.build_window(
        events,
        end_monday,
        n_weeks,
        matches_directory=MATCHES_DIR,
        format_id=FORMAT_ID,
    )


def build_all_matchups(
    today: date | None = None,
    *,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
):
    return _shared.build_all_matchups(
        REPOSITORY_ROOT,
        FORMAT_ID,
        today=today,
        generated_at=generated_at,
        output_directory=output_directory,
    )


def main() -> int:
    written, statistics = build_all_matchups()
    if not written:
        print("No complete MTGO event week is available.")
        return 0
    for weeks in RANGES:
        values = statistics[weeks]
        print(
            f"[{weeks:>2}w] counted={values['counted']} "
            f"cross={values['cross_matches']} mirror={values['mirror_matches']} "
            f"dropped={values['dropped_unmapped']}"
        )
    print(f"Standard matchup statistics written to {Path(OUT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
