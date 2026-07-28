"""P8-05 contracts for weekly MTGO Top 8 presentation data."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.config import DisabledFormatError
from mtgmeta.mtgo import top8
from mtgmeta.rules import build_rule_set
import validate_schemas


ROOT = Path(__file__).resolve().parents[1]


def rules():
    return build_rule_set(
        {
            "schema_version": "1.0.0",
            "format": "modern",
            "archetypes": [
                {
                    "id": "prowess",
                    "name": "Prowess",
                    "priority": 100,
                    "subtypes": [
                        {"id": "grixis", "name": "Grixis"},
                        {"id": "izzet", "name": "Izzet"},
                    ],
                    "rules": [
                        {
                            "id": "prowess-grixis",
                            "priority": 102,
                            "subtype_id": "grixis",
                            "conditions": {"all": [{"card": "Grixis Card"}]},
                        },
                        {
                            "id": "prowess-izzet",
                            "priority": 101,
                            "subtype_id": "izzet",
                            "conditions": {"all": [{"card": "Izzet Card"}]},
                        },
                    ],
                },
                {
                    "id": "energy",
                    "name": "Energy",
                    "priority": 50,
                    "subtypes": [],
                    "rules": [
                        {
                            "id": "energy-core",
                            "priority": 50,
                            "subtype_id": None,
                            "conditions": {"all": [{"card": "Energy Card"}]},
                        }
                    ],
                },
            ],
        }
    )


def player(rank: int, card: str, *, player_name: str | None = None):
    return {
        "player": player_name or f"Player {rank}",
        "loginid": str(1000 + rank),
        "swiss_score": "12",
        "final_rank": str(rank),
        "main_deck": [{"name": card, "qty": 4}],
        "sideboard": [{"name": "Sideboard Card", "qty": 2}],
    }


def event(
    event_id: str,
    description: str,
    event_date: str,
    players: list[dict],
):
    return {
        "event_id": event_id,
        "description": description,
        "format": "CMODERN",
        "starttime": f"{event_date} 15:00:00.0",
        "player_count": 32,
        "inplayoffs": 1,
        "players": players,
    }


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Modern Challenge 32", "C32"),
        ("Modern Challenge 64", "C64"),
        ("Modern Showcase Challenge", "SC"),
        ("Modern Showcase Qualifier", "SCQ"),
        ("Modern RC Qualifier", "RCQ"),
        ("Modern RC Super Qualifier", "RCSQ"),
    ],
)
def test_display_name_uses_approved_compact_labels(name, expected):
    assert top8.event_display_name(name, "modern") == expected


def test_week_document_keeps_exact_ranks_missing_states_and_full_identity_labels():
    document = top8.build_week_document(
        [
            (
                date(2026, 7, 20),
                event(
                    "200",
                    "Modern Challenge 32",
                    "2026-07-20",
                    [
                        player(1, "Grixis Card", player_name="Winner"),
                        player(2, "Energy Card"),
                        player(4, "Izzet Card"),
                    ],
                ),
            )
        ],
        rules(),
        date(2026, 7, 20),
        format_id="modern",
    )

    assert document["week"] == {"start": "2026-07-20", "end": "2026-07-26"}
    assert len(document["events"]) == 1
    output_event = document["events"][0]
    assert output_event["display_name"] == "C32"
    assert [item["rank"] for item in output_event["placements"]] == list(range(1, 9))

    winner = output_event["placements"][0]
    assert winner["deck_status"] == "available"
    assert winner["identity"] == {
        "identity_id": "prowess/grixis",
        "parent_id": "prowess",
        "subtype_id": "grixis",
        "display_name": "Grixis Prowess",
        "detail_id": "prowess/grixis",
    }
    assert winner["exact_deck"] == {
        "player": "Winner",
        "main_deck": [{"name": "Grixis Card", "qty": 4}],
        "sideboard": [{"name": "Sideboard Card", "qty": 2}],
        "deviation": None,
        "deviation_diff": None,
    }
    assert winner["comparison"] == {
        "identity_id": "prowess/grixis",
        "base_period": "4w",
        "base_period_end": "2026-07-26",
        "base_status": "unavailable",
        "average_deck_ref": "2026-W30-bases.json#identity/prowess/grixis",
    }

    parent = output_event["placements"][1]
    assert parent["identity"]["identity_id"] == "energy"
    assert parent["identity"]["display_name"] == "Energy"
    assert parent["comparison"]["average_deck_ref"].endswith("#identity/energy")

    missing = output_event["placements"][2]
    assert missing == {
        "rank": 3,
        "deck_status": "missing",
        "identity": None,
        "exact_deck": None,
        "comparison": None,
    }


def test_duplicate_top8_rank_fails_closed():
    source = event(
        "201",
        "Modern Challenge 32",
        "2026-07-20",
        [player(1, "Grixis Card"), player(1, "Izzet Card")],
    )
    with pytest.raises(top8.MTGOTop8Error, match="duplicate final rank 1"):
        top8.build_week_document(
            [(date(2026, 7, 20), source)],
            rules(),
            date(2026, 7, 20),
            format_id="modern",
        )


def test_duplicate_event_identity_fails_closed():
    first = event(
        "201",
        "Modern Challenge 32",
        "2026-07-20",
        [player(1, "Grixis Card")],
    )
    second = event(
        "201",
        "Modern Challenge 64",
        "2026-07-21",
        [player(1, "Izzet Card")],
    )
    with pytest.raises(top8.MTGOTop8Error, match="duplicate event_id"):
        top8.build_week_document(
            [(date(2026, 7, 20), first), (date(2026, 7, 21), second)],
            rules(),
            date(2026, 7, 20),
            format_id="modern",
        )


def test_missing_complete_week_fails_before_output(tmp_path):
    with pytest.raises(top8.MTGOTop8Error, match="no complete MTGO event week"):
        top8.write_latest_week(
            [],
            rules(),
            tmp_path / "output",
            format_id="modern",
            today=date(2026, 7, 28),
        )
    assert not (tmp_path / "output").exists()


def test_build_latest_week_is_deterministic_and_writes_week_catalog(tmp_path):
    source_events = [
        (
            date(2026, 7, 20),
            event(
                "202",
                "Modern Showcase Qualifier",
                "2026-07-20",
                [player(rank, "Grixis Card") for rank in range(1, 9)],
            ),
        )
    ]
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_written = top8.write_latest_week(
        source_events,
        rules(),
        first,
        format_id="modern",
        today=date(2026, 7, 28),
        generated_at="2026-07-28T12:00:00",
    )
    second_written = top8.write_latest_week(
        source_events,
        rules(),
        second,
        format_id="modern",
        today=date(2026, 7, 28),
        generated_at="2026-07-28T12:00:00",
    )

    assert set(first_written) == {
        "2026-W30.json",
        "2026-W30-bases.json",
        "index.json",
    }
    assert {
        name: path.read_bytes() for name, path in first_written.items()
    } == {
        name: path.read_bytes() for name, path in second_written.items()
    }
    catalog = json.loads((first / "index.json").read_text(encoding="utf-8"))
    assert catalog["latest_complete_week"] == "2026-07-20"
    assert catalog["history_policy"] == "immutable_weekly_comparison_bases"
    assert catalog["weeks"] == [
        {
            "file": "2026-W30.json",
            "comparison_bases_file": "2026-W30-bases.json",
            "start": "2026-07-20",
            "end": "2026-07-26",
            "event_count": 1,
        }
    ]


@pytest.mark.parametrize(("format_id", "event_count"), [("standard", 8), ("modern", 13)])
def test_committed_real_week_has_all_events_and_exact_rank_slots(format_id, event_count):
    output = ROOT / "stats" / format_id / "mtgo" / "top8"
    catalog = json.loads((output / "index.json").read_text(encoding="utf-8"))
    assert catalog["latest_complete_week"] == "2026-07-20"
    assert len(catalog["weeks"]) == 1
    week = json.loads(
        (output / catalog["weeks"][0]["file"]).read_text(encoding="utf-8")
    )
    assert len(week["events"]) == event_count
    for item in week["events"]:
        assert [placement["rank"] for placement in item["placements"]] == list(
            range(1, 9)
        )
        assert all(
            placement["deck_status"] == "available"
            for placement in item["placements"]
        )
        assert all(
            placement["comparison"]["base_period_end"] == week["week"]["end"]
            for placement in item["placements"]
        )


@pytest.mark.parametrize("format_id", ["standard", "modern"])
@pytest.mark.committed_baseline
def test_committed_latest_week_rebuild_is_byte_identical(format_id, tmp_path):
    committed = ROOT / "stats" / format_id / "mtgo" / "top8"
    index = json.loads((committed / "index.json").read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(index["generated"])
    written = top8.build_all_top8(
        ROOT,
        format_id,
        today=generated.date(),
        generated_at=generated,
        output_directory=tmp_path / format_id,
    )
    assert set(written) == {
        index["weeks"][0]["file"],
        index["weeks"][0]["comparison_bases_file"],
        "index.json",
    }
    for name, path in written.items():
        assert path.read_bytes() == (committed / name).read_bytes()


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_committed_top8_documents_match_formal_schemas(format_id):
    loaded, registry = validate_schemas.load_schemas(ROOT / "schemas")
    output = ROOT / "stats" / format_id / "mtgo" / "top8"
    catalog = json.loads((output / "index.json").read_text(encoding="utf-8"))
    assert validate_schemas.validate_instance(
        catalog,
        loaded["mtgo-top8-index.schema.json"],
        registry,
    ) == []
    week = json.loads(
        (output / catalog["weeks"][0]["file"]).read_text(encoding="utf-8")
    )
    assert validate_schemas.validate_instance(
        week,
        loaded["mtgo-top8-week.schema.json"],
        registry,
    ) == []
    bases = json.loads(
        (output / catalog["weeks"][0]["comparison_bases_file"]).read_text(
            encoding="utf-8"
        )
    )
    assert validate_schemas.validate_instance(
        bases,
        loaded["mtgo-top8-comparison-bases.schema.json"],
        registry,
    ) == []


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_committed_comparison_identities_resolve_in_same_period_deck_data(format_id):
    output = ROOT / "stats" / format_id / "mtgo"
    decks = json.loads((output / "decks_4w.json").read_text(encoding="utf-8"))[
        "decks"
    ]
    available_identities = set()
    for parent in decks.values():
        parent_id = parent.get("archetype_id")
        if parent_id:
            available_identities.add(parent_id)
        available_identities.update(
            f"{subtype['parent_id']}/{subtype['id']}"
            for subtype in parent.get("subtypes", [])
        )

    catalog = json.loads(
        (output / "top8" / "index.json").read_text(encoding="utf-8")
    )
    week = json.loads(
        (output / "top8" / catalog["weeks"][0]["file"]).read_text(encoding="utf-8")
    )
    referenced = {
        placement["comparison"]["identity_id"]
        for event_item in week["events"]
        for placement in event_item["placements"]
        if placement["comparison"] is not None
    }
    assert referenced <= available_identities


def test_top8_capability_is_required_before_output(tmp_path):
    registry = yaml.safe_load(
        (ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8")
    )
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    modern["mtgo"]["capabilities"].remove("weekly_top8")
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(
        yaml.safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    with pytest.raises(DisabledFormatError, match="weekly_top8"):
        top8.build_all_top8(
            ROOT,
            "modern",
            registry_path=registry_path,
            output_directory=output,
        )
    assert not output.exists()
