from __future__ import annotations

from datetime import date
import json

import pytest

from mtgmeta.mtgo import top8
from mtgmeta.rules import (
    ArchetypeDefinition,
    CardCondition,
    ClassificationRule,
    RuleSet,
)


MONDAY = date(2026, 1, 5)
SEALED_TODAY = date(2026, 1, 20)


def _rules(archetype_id: str, card: str) -> RuleSet:
    return RuleSet(
        schema_version="1.1.0",
        format="modern",
        archetypes=(
            ArchetypeDefinition(
                id=archetype_id,
                name=archetype_id.title(),
                priority=100,
                subtypes=(),
                rules=(
                    ClassificationRule(
                        id=f"{archetype_id}-rule",
                        priority=100,
                        subtype_id=None,
                        conditions=(CardCondition(card=card, zone="main"),),
                    ),
                ),
            ),
        ),
    )


def _events(card: str = "Signal Card"):
    return [
        (
            MONDAY,
            {
                "event_id": "1001",
                "description": "Modern Challenge 32",
                "starttime": "2026-01-05T12:00:00Z",
                "player_count": 8,
                "players": [
                    {
                        "player": f"Player {rank}",
                        "loginid": rank,
                        "swiss_score": 9,
                        "final_rank": rank,
                        "main_deck": [{"name": card, "qty": 60}],
                        "sideboard": [{"name": "Side Card", "qty": 15}],
                    }
                    for rank in range(1, 9)
                ],
            },
        )
    ]


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_sealed_history_restates_derived_identity_under_current_classifier(tmp_path):
    output = tmp_path / "top8"
    top8.write_latest_week(
        _events(),
        _rules("alpha", "Signal Card"),
        output,
        format_id="modern",
        today=SEALED_TODAY,
        generated_at="2026-01-20T00:00:00",
    )

    top8.write_latest_week(
        _events(),
        _rules("beta", "Signal Card"),
        output,
        format_id="modern",
        today=SEALED_TODAY,
        generated_at="2026-01-20T00:00:00",
    )

    week = _read(output / "2026-W02.json")
    bases = _read(output / "2026-W02-bases.json")
    index = _read(output / "index.json")
    impact = index["classification_impact"]
    assert {
        placement["identity"]["identity_id"]
        for placement in week["events"][0]["placements"]
    } == {"beta"}
    assert week["classifier_digest"] == bases["classifier_digest"]
    assert week["classifier_digest"] == index["classifier_digest"]
    assert impact["summary"]["classification_change_count"] == 8
    assert impact["weeks"][0]["classification_changes"][0] == {
        "event_id": "1001",
        "rank": 1,
        "before": "alpha",
        "after": "beta",
    }
    stable_bytes = {
        name: (output / name).read_bytes()
        for name in ("2026-W02.json", "2026-W02-bases.json")
    }
    top8.write_latest_week(
        _events(),
        _rules("beta", "Signal Card"),
        output,
        format_id="modern",
        today=SEALED_TODAY,
        generated_at="2026-01-20T00:00:00",
    )
    assert {
        name: (output / name).read_bytes()
        for name in ("2026-W02.json", "2026-W02-bases.json")
    } == stable_bytes
    assert _read(output / "index.json")["classification_impact"]["summary"][
        "classification_change_count"
    ] == 0


def test_retained_source_fact_change_still_fails_closed(tmp_path):
    output = tmp_path / "top8"
    top8.write_latest_week(
        _events(),
        _rules("alpha", "Signal Card"),
        output,
        format_id="modern",
        today=SEALED_TODAY,
        generated_at="2026-01-20T00:00:00",
    )

    with pytest.raises(
        top8.MTGOTop8Error,
        match="retained Top 8 source facts changed: event 1001",
    ):
        top8.write_latest_week(
            _events("Different Card"),
            _rules("beta", "Different Card"),
            output,
            format_id="modern",
            today=SEALED_TODAY,
            generated_at="2026-01-20T00:00:00",
        )


def test_unknown_is_an_explicit_restated_top8_identity(tmp_path):
    output = tmp_path / "top8"
    top8.write_latest_week(
        _events(),
        _rules("alpha", "Absent Card"),
        output,
        format_id="modern",
        today=SEALED_TODAY,
        generated_at="2026-01-20T00:00:00",
    )

    week = _read(output / "2026-W02.json")
    placement = week["events"][0]["placements"][0]
    assert placement["identity"] == {
        "identity_id": "unknown",
        "parent_id": "unknown",
        "subtype_id": None,
        "display_name": "Unknown",
        "detail_id": "unknown",
    }
    assert placement["comparison"]["identity_id"] == "unknown"
