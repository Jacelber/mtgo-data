"""Range-specific MTGO source-completeness products."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path
from typing import Any, Iterable

from public_contract import versioned

from . import load_mtgo_context
from .stats import (
    DEFAULT_RANGES,
    high_score_threshold,
    latest_complete_week,
    load_events_from_directory,
    rounds_from_player_count,
)


SOURCE_ID = "mtgo"
VIDERE_FORMULA_VERSION = "videre-range-coverage-v1"
HIGH_SCORE_FORMULA_VERSION = "mtgo-high-score-binomial-v1"


class MTGOCompletenessError(RuntimeError):
    """Raised when completeness input or output cannot be trusted."""


def _event_id(event: dict[str, Any]) -> str:
    value = event.get("event_id")
    if isinstance(value, bool) or not str(value or "").isdigit():
        raise MTGOCompletenessError("MTGO completeness event_id must contain digits only")
    return str(value)


def _events_in_period(
    events: Iterable[tuple[date, dict[str, Any]]],
    period_start: date,
    period_end: date,
) -> list[tuple[date, dict[str, Any]]]:
    if period_end < period_start:
        raise MTGOCompletenessError("completeness period end precedes its start")
    selected = [
        (event_date, event)
        for event_date, event in events
        if period_start <= event_date <= period_end
    ]
    selected.sort(key=lambda item: (item[0], _event_id(item[1])))
    ids = [_event_id(event) for _event_date, event in selected]
    if len(ids) != len(set(ids)):
        raise MTGOCompletenessError("completeness period contains duplicate event IDs")
    return selected


def _has_usable_match_archive(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    rows = value.get("matches") if isinstance(value, dict) else value
    return isinstance(rows, list) and bool(rows)


def build_videre_coverage(
    events: Iterable[tuple[date, dict[str, Any]]],
    matches_directory: str | Path,
    *,
    period_start: date,
    period_end: date,
    deferred_event_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Classify admitted events as available, explicitly deferred, or missing."""

    selected = _events_in_period(events, period_start, period_end)
    admitted_ids = {_event_id(event) for _event_date, event in selected}
    deferred = {str(event_id) for event_id in deferred_event_ids}
    if any(not event_id.isdigit() for event_id in deferred):
        raise MTGOCompletenessError("deferred Videre event IDs must contain digits only")
    unknown_deferred = deferred - admitted_ids
    if unknown_deferred:
        raise MTGOCompletenessError(
            "deferred Videre events are outside the admitted period: "
            + ", ".join(sorted(unknown_deferred))
        )

    matches_path = Path(matches_directory)
    available = {
        event_id
        for event_id in admitted_ids
        if _has_usable_match_archive(matches_path / f"{event_id}.json")
    }
    deferred -= available
    missing = admitted_ids - available - deferred
    expected = len(admitted_ids)
    status = "available" if expected else "unavailable"
    return {
        "formula_version": VIDERE_FORMULA_VERSION,
        "status": status,
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "expected_event_count": expected,
        "available_event_count": len(available),
        "deferred_event_count": len(deferred),
        "missing_event_count": len(missing),
        "excluded_event_count": 0,
        "available_event_ids": sorted(available, key=int),
        "deferred_event_ids": sorted(deferred, key=int),
        "missing_event_ids": sorted(missing, key=int),
        "excluded_events": [],
        "completeness_rate": (
            round(len(available) / expected, 6) if expected else None
        ),
        "unavailable_reason": None if expected else "no_expected_events",
    }


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _valid_swiss_scores(event: dict[str, Any]) -> list[int] | None:
    players = event.get("players")
    if not isinstance(players, list) or not players:
        return None
    scores: list[int] = []
    for player in players:
        if not isinstance(player, dict):
            return None
        value = player.get("swiss_score")
        if isinstance(value, bool):
            return None
        try:
            score = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        if score < 0:
            return None
        scores.append(score)
    return scores


def _unsupported_event(event_id: str, reason: str) -> dict[str, str]:
    return {
        "event_id": event_id,
        "reason": reason,
        "note": {
            "missing_player_count": "The retained event has no usable positive player count.",
            "unsupported_round_model": "The existing MTGO player-count round model cannot represent this event.",
            "missing_high_score_threshold": "The existing MTGO round model has no high-score threshold.",
            "missing_swiss_scores": "One or more retained decklists lack usable Swiss-score evidence.",
        }[reason],
    }


def build_high_score_completeness(
    events: Iterable[tuple[date, dict[str, Any]]],
    *,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """Build the reviewed observed-versus-binomial high-score estimate."""

    selected = _events_in_period(events, period_start, period_end)
    eligible: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []
    for _event_date, event in selected:
        event_id = _event_id(event)
        player_count = _positive_int(event.get("player_count"))
        if player_count is None:
            unsupported.append(_unsupported_event(event_id, "missing_player_count"))
            continue
        rounds = rounds_from_player_count(player_count)
        if not isinstance(rounds, int) or rounds < 1:
            unsupported.append(_unsupported_event(event_id, "unsupported_round_model"))
            continue
        threshold = high_score_threshold(rounds)
        if not isinstance(threshold, int) or threshold < 3:
            unsupported.append(
                _unsupported_event(event_id, "missing_high_score_threshold")
            )
            continue
        scores = _valid_swiss_scores(event)
        if scores is None:
            unsupported.append(_unsupported_event(event_id, "missing_swiss_scores"))
            continue
        minimum_wins = math.ceil(threshold / 3)
        probability = sum(
            math.comb(rounds, wins) / (2**rounds)
            for wins in range(minimum_wins, rounds + 1)
        )
        eligible.append(
            {
                "event_id": event_id,
                "player_count": player_count,
                "round_count": rounds,
                "high_score_threshold": threshold,
                "minimum_decisive_wins": minimum_wins,
                "observed_decklist_count": sum(
                    score >= threshold for score in scores
                ),
                "expected_decklist_count": player_count * probability,
            }
        )

    observed = sum(event["observed_decklist_count"] for event in eligible)
    expected = sum(event["expected_decklist_count"] for event in eligible)
    available = bool(eligible)
    return {
        "formula_version": HIGH_SCORE_FORMULA_VERSION,
        "status": "available" if available else "unavailable",
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "eligible_event_count": len(eligible),
        "unsupported_event_count": len(unsupported),
        "events": eligible,
        "unsupported_events": unsupported,
        "observed_decklist_count": observed,
        "expected_decklist_count": expected,
        "expected_decklist_count_display": int(
            Decimal(str(expected)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        ),
        "completeness_rate": (
            round(min(observed / expected, 1.0), 6)
            if available and expected > 0
            else None
        ),
        "exceeds_model": observed > expected,
        "unavailable_reason": None if available else "no_eligible_events",
    }


def _generated_value(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now().isoformat(timespec="seconds")
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def build_all_completeness(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
    registry_path: str | Path | None = None,
    ranges: Iterable[int] = DEFAULT_RANGES,
) -> dict[str, Path]:
    """Generate every configured MTGO completeness range and its catalog."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "completeness_reporting",
        registry_path=registry_path,
    )
    normalized_ranges = tuple(ranges)
    if not normalized_ranges or any(
        not isinstance(weeks, int) or isinstance(weeks, bool) or weeks <= 0
        for weeks in normalized_ranges
    ):
        raise MTGOCompletenessError("completeness ranges must be positive integers")
    if len(normalized_ranges) != len(set(normalized_ranges)):
        raise MTGOCompletenessError("completeness ranges must be unique")

    events = load_events_from_directory(
        context.paths["events"],
        repository_root=context.repository_root,
        format_id=format_id,
    )
    end_monday = latest_complete_week(events, today=today)
    if end_monday is None:
        return {}
    end_sunday = end_monday + timedelta(days=6)
    output = (
        Path(output_directory)
        if output_directory is not None
        else context.paths["statistics"] / "completeness"
    )
    documents: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    for weeks in normalized_ranges:
        period_start = end_monday - timedelta(weeks=weeks - 1)
        matchup_coverage = build_videre_coverage(
            events,
            context.paths["matches"],
            period_start=period_start,
            period_end=end_sunday,
        )
        high_score = build_high_score_completeness(
            events,
            period_start=period_start,
            period_end=end_sunday,
        )
        filename = f"{weeks}w.json"
        documents[filename] = versioned(
            {
                "document_type": "mtgo_completeness_range",
                "format": format_id,
                "source": SOURCE_ID,
                "period": {
                    "type": f"{weeks}w",
                    "start": period_start.isoformat(),
                    "end": end_sunday.isoformat(),
                    "weeks": weeks,
                },
                "matchup_coverage": matchup_coverage,
                "high_score_decklist_completeness": high_score,
            }
        )
        entries.append(
            {
                "file": filename,
                "type": f"{weeks}w",
                "start": period_start.isoformat(),
                "end": end_sunday.isoformat(),
                "weeks": weeks,
                "matchup_status": matchup_coverage["status"],
                "high_score_status": high_score["status"],
            }
        )
    documents["index.json"] = versioned(
        {
            "document_type": "mtgo_completeness_index",
            "format": format_id,
            "source": SOURCE_ID,
            "generated": _generated_value(generated_at),
            "latest_complete_week": end_monday.isoformat(),
            "ranges": entries,
        }
    )

    output.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for filename, document in documents.items():
        destination = output / filename
        destination.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        written[filename] = destination
    return written


__all__ = [
    "HIGH_SCORE_FORMULA_VERSION",
    "MTGOCompletenessError",
    "VIDERE_FORMULA_VERSION",
    "build_all_completeness",
    "build_high_score_completeness",
    "build_videre_coverage",
]
