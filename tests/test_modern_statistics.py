"""P6-05 Modern event and rolling-range statistics contracts."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_deck
from mtgmeta.config import DisabledFormatError, load_rule_set
from mtgmeta.mtgo import stats


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "stats" / "modern" / "mtgo"
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
EXPECTED_TOTALS = {1: 416, 4: 1568, 12: 4480, 36: 5728}
EXPECTED_UNKNOWNS = {1: 14, 4: 32, 12: 103, 36: 127}


def committed_reference() -> tuple[datetime, dict]:
    index = json.loads((OUTPUT / "index.json").read_text(encoding="utf-8"))
    return datetime.fromisoformat(index["generated"]), index


def test_modern_event_input_is_complete_and_format_isolated():
    source_events = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "data" / "modern").glob("*.json"))
    ]
    events = stats.load_all_events(ROOT, "modern")
    assert len(events) == len(source_events)
    assert {event["format"] for _date, event in events} == {"CMODERN"}
    assert {event["event_id"] for _date, event in events} == {
        event["event_id"] for event in source_events
    }
    assert sum(len(event["players"]) for _date, event in events) == sum(
        len(event["players"]) for event in source_events
    )


def test_committed_modern_ranges_reconcile_parent_aggregates():
    generated, index = committed_reference()
    assert generated.isoformat(timespec="seconds") == index["generated"]
    assert index["format"] == "modern"
    assert index["source"] == "mtgo"
    assert index["latest_complete_week"] == "2026-07-13"
    assert [item["weeks"] for item in index["ranges"]] == [1, 4, 12, 36]

    for weeks in EXPECTED_TOTALS:
        document = json.loads(
            (OUTPUT / f"range_{weeks}w.json").read_text(encoding="utf-8")
        )
        assert document["format"] == "modern"
        assert document["source"] == "mtgo"
        assert document["total_decks"] == EXPECTED_TOTALS[weeks]
        assert document["unknown_count"] == EXPECTED_UNKNOWNS[weeks]
        assert all(item["id"] for item in document["archetypes"])
        assert len({item["id"] for item in document["archetypes"]}) == len(
            document["archetypes"]
        )
        assert sum(item["count"] for item in document["archetypes"]) == document["total_decks"]
        assert sum(item["high_score_count"] for item in document["archetypes"]) == document["total_high_score"]
        assert sum(item["top8_count"] for item in document["archetypes"]) == document["total_top8"]
        decks = json.loads(
            (OUTPUT / f"decks_{weeks}w.json").read_text(encoding="utf-8")
        )["decks"]
        assert all(entry["archetype_id"] for entry in decks.values())


@pytest.mark.committed_baseline
def test_fixed_reference_modern_regeneration_is_byte_identical(tmp_path):
    generated, _index = committed_reference()
    written = stats.build_all_stats(
        ROOT,
        "modern",
        today=generated.date(),
        generated_at=generated,
        output_directory=tmp_path,
    )
    assert set(written) == EXPECTED_FILES
    for filename in sorted(EXPECTED_FILES):
        assert written[filename].read_bytes() == (OUTPUT / filename).read_bytes(), filename


def test_statistics_aggregate_the_selected_parent_not_the_subtype():
    rules = load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    event = json.loads(
        (ROOT / "data" / "modern" / "Modern_Challenge_32_12837907.json").read_text(
            encoding="utf-8"
        )
    )
    player = next(
        player
        for player in event["players"]
        if classify_deck(rules, player).subtype_id is not None
    )
    classification = classify_deck(rules, player)
    processed = stats.process_event({**event, "players": [player]}, rules)
    assert classification.archetype_name is not None
    assert classification.subtype_name is not None
    assert processed["records"][0]["archetype"] == classification.archetype_name
    assert processed["records"][0]["archetype"] != classification.subtype_name
    assert processed["records"][0]["subtype_id"] == classification.subtype_id
    assert processed["records"][0]["subtype"] == classification.subtype_name


def test_cross_format_input_is_rejected_before_output(tmp_path):
    config_directory = tmp_path / "configs"
    rules_directory = tmp_path / "my_archetypes"
    event_directory = tmp_path / "data" / "modern"
    config_directory.mkdir()
    rules_directory.mkdir()
    event_directory.mkdir(parents=True)
    (config_directory / "formats.yaml").write_bytes(
        (ROOT / "configs" / "formats.yaml").read_bytes()
    )
    (rules_directory / "modern.yaml").write_bytes(
        (ROOT / "my_archetypes" / "modern.yaml").read_bytes()
    )
    (event_directory / "premodern.json").write_text(
        json.dumps({"format": "CPREMODERN", "starttime": "2026-07-01", "players": []}),
        encoding="utf-8",
    )
    with pytest.raises(stats.MTGOStatisticsError, match="cross-format event input rejected"):
        stats.build_all_stats(tmp_path, "modern")
    assert not (tmp_path / "stats" / "modern" / "mtgo").exists()


@pytest.mark.parametrize(
    "removed_capability", ["event_statistics", "range_statistics"]
)
def test_each_statistics_capability_is_required_before_output(tmp_path, removed_capability):
    registry = yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))
    modern = next(item for item in registry["formats"] if item["id"] == "modern")
    modern["mtgo"]["capabilities"].remove(removed_capability)
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    output = tmp_path / "output"
    with pytest.raises(DisabledFormatError, match=removed_capability):
        stats.build_all_stats(
            ROOT,
            "modern",
            registry_path=registry_path,
            output_directory=output,
        )
    assert not output.exists()
