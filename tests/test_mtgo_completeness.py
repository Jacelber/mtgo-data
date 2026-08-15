"""P8-06 MTGO range-completeness product contracts."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from mtgmeta.mtgo import completeness


ROOT = Path(__file__).resolve().parents[1]


def _event(
    event_id: int,
    event_date: str,
    player_count: int,
    swiss_scores: list[int],
) -> tuple[date, dict]:
    return (
        date.fromisoformat(event_date),
        {
            "event_id": event_id,
            "format": "standard",
            "starttime": f"{event_date}T00:00:00Z",
            "player_count": player_count,
            "players": [
                {
                    "loginid": str(index + 1),
                    "swiss_score": score,
                    "final_rank": index + 1,
                }
                for index, score in enumerate(swiss_scores)
            ],
        },
    )


def test_videre_coverage_uses_range_admission_and_explicit_status_buckets(
    tmp_path: Path,
) -> None:
    matches = tmp_path / "matches"
    matches.mkdir()
    for event_id in ("101", "102"):
        (matches / f"{event_id}.json").write_text(
            json.dumps({"event_id": int(event_id), "matches": [{"round": 1}]}),
            encoding="utf-8",
        )
    events = [
        _event(101, "2026-07-13", 8, [9]),
        _event(102, "2026-07-14", 8, [9]),
        _event(103, "2026-07-15", 8, [9]),
        _event(104, "2026-07-16", 8, [9]),
        _event(999, "2026-07-01", 8, [9]),
    ]

    result = completeness.build_videre_coverage(
        events,
        matches,
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
        deferred_event_ids={"103"},
    )

    assert result == {
        "formula_version": "videre-range-coverage-v1",
        "status": "available",
        "period": {"start": "2026-07-13", "end": "2026-07-19"},
        "expected_event_count": 4,
        "available_event_count": 2,
        "deferred_event_count": 1,
        "missing_event_count": 1,
        "excluded_event_count": 0,
        "available_event_ids": ["101", "102"],
        "deferred_event_ids": ["103"],
        "missing_event_ids": ["104"],
        "excluded_events": [],
        "completeness_rate": 0.5,
        "unavailable_reason": None,
    }


def test_videre_coverage_is_unavailable_instead_of_false_zero(
    tmp_path: Path,
) -> None:
    result = completeness.build_videre_coverage(
        [],
        tmp_path,
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
    )
    assert result["status"] == "unavailable"
    assert result["expected_event_count"] == 0
    assert result["completeness_rate"] is None
    assert result["unavailable_reason"] == "no_expected_events"


def test_high_score_completeness_matches_the_frozen_binomial_reference() -> None:
    event_specs = [
        (12847158, 50, 15),
        (12847168, 40, 13),
        (12847673, 38, 12),
        (12847680, 33, 12),
        (12847684, 39, 14),
        (12847697, 42, 15),
    ]
    events = [
        _event(
            event_id,
            "2026-07-13",
            player_count,
            [12] * observed,
        )
        for event_id, player_count, observed in event_specs
    ]
    events.append(_event(12847716, "2026-07-14", 32, [9] * 16))

    result = completeness.build_high_score_completeness(
        events,
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
    )

    assert result["formula_version"] == "mtgo-high-score-binomial-v1"
    assert result["status"] == "available"
    assert result["eligible_event_count"] == 7
    assert result["unsupported_event_count"] == 0
    assert result["observed_decklist_count"] == 97
    assert result["expected_decklist_count"] == 99.1875
    assert result["expected_decklist_count_display"] == 99
    assert result["completeness_rate"] == 0.977946
    assert result["exceeds_model"] is False
    assert result["unavailable_reason"] is None


@pytest.mark.parametrize(
    ("event", "reason"),
    [
        (
            {
                "event_id": 201,
                "format": "standard",
                "starttime": "2026-07-13T00:00:00Z",
                "players": [{"loginid": "1", "swiss_score": 9}],
            },
            "missing_player_count",
        ),
        (
            {
                "event_id": 202,
                "format": "standard",
                "starttime": "2026-07-13T00:00:00Z",
                "player_count": 8,
                "players": [{"loginid": "1", "swiss_score": None}],
            },
            "missing_swiss_scores",
        ),
    ],
)
def test_high_score_unsupported_events_are_reported_not_counted(
    event: dict,
    reason: str,
) -> None:
    result = completeness.build_high_score_completeness(
        [(date(2026, 7, 13), event)],
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
    )
    assert result["status"] == "unavailable"
    assert result["eligible_event_count"] == 0
    assert result["unsupported_event_count"] == 1
    assert result["events"] == []
    assert result["unsupported_events"][0]["reason"] == reason
    assert result["observed_decklist_count"] == 0
    assert result["expected_decklist_count"] == 0
    assert result["completeness_rate"] is None
    assert result["unavailable_reason"] == "no_eligible_events"


def test_high_score_observed_above_model_is_capped_but_disclosed() -> None:
    result = completeness.build_high_score_completeness(
        [_event(301, "2026-07-13", 8, [9] * 8)],
        period_start=date(2026, 7, 13),
        period_end=date(2026, 7, 19),
    )
    assert result["observed_decklist_count"] == 8
    assert result["expected_decklist_count"] == 4.0
    assert result["expected_decklist_count_display"] == 4
    assert result["completeness_rate"] == 1.0
    assert result["exceeds_model"] is True


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_committed_ranges_reconcile_lists_counts_and_periods(format_id: str) -> None:
    base = ROOT / "stats" / format_id / "mtgo" / "completeness"
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    assert [item["weeks"] for item in index["ranges"]] == [1, 4, 12, 36]
    for entry in index["ranges"]:
        document = json.loads((base / entry["file"]).read_text(encoding="utf-8"))
        coverage = document["matchup_coverage"]
        high_score = document["high_score_decklist_completeness"]
        assert coverage["period"] == {
            "start": document["period"]["start"],
            "end": document["period"]["end"],
        }
        assert high_score["period"] == coverage["period"]
        assert coverage["expected_event_count"] == (
            coverage["available_event_count"]
            + coverage["deferred_event_count"]
            + coverage["missing_event_count"]
        )
        assert coverage["available_event_count"] == len(
            coverage["available_event_ids"]
        )
        assert coverage["deferred_event_count"] == len(
            coverage["deferred_event_ids"]
        )
        assert coverage["missing_event_count"] == len(
            coverage["missing_event_ids"]
        )
        assert coverage["excluded_event_count"] == len(
            coverage["excluded_events"]
        )
        assert high_score["eligible_event_count"] == len(high_score["events"])
        assert high_score["unsupported_event_count"] == len(
            high_score["unsupported_events"]
        )
        assert high_score["observed_decklist_count"] == sum(
            event["observed_decklist_count"] for event in high_score["events"]
        )
