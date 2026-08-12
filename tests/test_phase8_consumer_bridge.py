"""P8-07 backend contracts required by the frozen Phase 8 consumers."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from mtgmeta import catalog
from mtgmeta.consumer import identity_display_name
from mtgmeta.config import load_rule_set
from mtgmeta.mtgo import top8
import validate_schemas


ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_global_catalog_is_deterministic_schema_valid_and_format_first():
    generated = "2026-07-28T12:00:00+00:00"
    first = catalog.build_catalog(ROOT, generated_at=generated)
    second = catalog.build_catalog(ROOT, generated_at=generated)
    assert first == second
    assert [item["id"] for item in first["formats"]] == [
        "standard",
        "pauper",
        "modern",
        "pioneer",
        "legacy",
        "vintage",
    ]
    by_format = {item["id"]: item for item in first["formats"]}
    standard = {item["id"]: item for item in by_format["standard"]["products"]}
    modern = {item["id"]: item for item in by_format["modern"]["products"]}
    assert standard["tabletop-major-events"]["available"] is False
    assert standard["weekly-pickup"]["available"] is True
    assert modern["tabletop-major-events"]["available"] is True
    assert modern["weekly-pickup"]["available"] is False
    assert all(
        item["default_product_id"] is None
        for key, item in by_format.items()
        if key not in {"standard", "modern"}
    )
    loaded, registry = validate_schemas.load_schemas(ROOT / "schemas")
    assert validate_schemas.validate_instance(
        first,
        loaded["consumer-catalog.schema.json"],
        registry,
    ) == []


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_mtgo_outputs_publish_self_contained_subtype_labels(format_id):
    root = ROOT / "stats" / format_id / "mtgo"
    for range_file in root.glob("range_*w.json"):
        for parent in _json(range_file)["archetypes"]:
            subtype_names = tuple(
                subtype["name"] for subtype in parent.get("subtypes", [])
            )
            for subtype in parent.get("subtypes", []):
                assert subtype["display_name"] == identity_display_name(
                    parent["name"],
                    subtype["name"],
                    maintained_subtype_names=subtype_names,
                )
    hierarchy = _json(root / "archetype_hierarchy.json")
    assert all(leaf["display_name"] for leaf in hierarchy["leaves"])
    matchup = _json(root / "matchup_4w.json")
    assert all(leaf["display_name"] for leaf in matchup["hierarchy"]["leaves"])


@pytest.mark.parametrize(
    ("parent_name", "subtype_name", "maintained_subtype_names", "expected"),
    [
        (
            "Boros Manufacturing",
            "Jeskai",
            ("Jeskai", "Mardu", "Boros"),
            "Jeskai Manufacturing",
        ),
        (
            "Boros Manufacturing",
            "Mardu",
            ("Jeskai", "Mardu", "Boros"),
            "Mardu Manufacturing",
        ),
        (
            "Boros Manufacturing",
            "Boros",
            ("Jeskai", "Mardu", "Boros"),
            "Boros Manufacturing",
        ),
        (
            "Izzet Steel-Cutter",
            "Izzet",
            ("Izzet",),
            "Izzet Steel-Cutter",
        ),
        (
            "Dimir Tempo",
            "Dimir",
            ("Dimir", "Dimir Red Splash", "Dimir White Splash"),
            "Dimir Tempo",
        ),
        (
            "Dimir Tempo",
            "Dimir Red Splash",
            ("Dimir", "Dimir Red Splash", "Dimir White Splash"),
            "Dimir Red Splash Tempo",
        ),
        (
            "Dimir Tempo",
            "Dimir White Splash",
            ("Dimir", "Dimir Red Splash", "Dimir White Splash"),
            "Dimir White Splash Tempo",
        ),
        (
            "Rakdos Hollow One",
            "Rakdos",
            ("Rakdos", "Mardu"),
            "Rakdos Hollow One",
        ),
        (
            "Rakdos Hollow One",
            "Mardu",
            ("Rakdos", "Mardu"),
            "Mardu Hollow One",
        ),
        (
            "Prowess",
            "Grixis",
            ("Izzet", "Temur", "Grixis"),
            "Grixis Prowess",
        ),
    ],
)
def test_identity_display_name_replaces_only_a_maintained_parent_prefix(
    parent_name,
    subtype_name,
    maintained_subtype_names,
    expected,
):
    assert identity_display_name(
        parent_name,
        subtype_name,
        maintained_subtype_names=maintained_subtype_names,
    ) == expected


def test_current_taxonomies_change_exactly_the_nine_accepted_labels():
    expected = {
        ("standard", "boros-manufacturing", "jeskai", "Jeskai Manufacturing"),
        ("standard", "boros-manufacturing", "mardu", "Mardu Manufacturing"),
        ("standard", "boros-manufacturing", "boros", "Boros Manufacturing"),
        ("modern", "steel-cutter", "izzet", "Izzet Steel-Cutter"),
        ("modern", "dimir-tempo", "dimir", "Dimir Tempo"),
        ("modern", "dimir-tempo", "grixis", "Dimir Red Splash Tempo"),
        ("modern", "dimir-tempo", "esper", "Dimir White Splash Tempo"),
        ("modern", "rakdos-hollow-one", "rakdos", "Rakdos Hollow One"),
        ("modern", "rakdos-hollow-one", "mardu", "Mardu Hollow One"),
    }
    changed = set()
    total = 0
    for format_id in ("standard", "modern"):
        rules = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
        for parent in rules.archetypes:
            subtype_names = tuple(item.name for item in parent.subtypes)
            for subtype in parent.subtypes:
                total += 1
                legacy = (
                    subtype.name
                    if parent.name.casefold() in subtype.name.casefold()
                    else f"{subtype.name} {parent.name}"
                )
                current = identity_display_name(
                    parent.name,
                    subtype.name,
                    maintained_subtype_names=subtype_names,
                )
                if current != legacy:
                    changed.add((format_id, parent.id, subtype.id, current))
    assert total == 81
    assert changed == expected
    assert total - len(changed) == 72


def test_tabletop_preserves_legacy_rate_and_adds_literal_rate_and_labels():
    event = ROOT / "stats" / "modern" / "melee" / "events" / "434455"
    overview = _json(event / "overview.json")
    record = next(
        row["match_record"]["all_matches"]
        for row in overview["scopes"]["all_constructed"]["archetypes"]
        if row["match_record"]["all_matches"]["draws"] > 0
    )
    assert record["win_rate"] == round(
        (record["wins"] + 0.5 * record["draws"]) / record["matches"],
        6,
    )
    assert record["literal_record"]["win_rate"] == round(
        record["wins"] / record["matches"],
        6,
    )
    assert record["literal_record"]["win_rate_method"] == "wins_over_valid_matches"
    assert all(
        subtype["display_name"]
        for row in overview["scopes"]["all_constructed"]["archetypes"]
        for subtype in row["subtypes"]
    )
    matchup = _json(event / "matchup.json")
    assert matchup["rate_method"]["literal_win_rate_method"] == (
        "wins_over_valid_matches"
    )
    assert all(leaf["display_name"] for leaf in matchup["hierarchy"]["leaves"])
    assert all(
        "literal_record" in cell
        for row in matchup["scopes"]["all_constructed"]["leaf_matrix"].values()
        for cell in row.values()
    )


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_top8_uses_immutable_week_base_and_publishes_deviation(format_id):
    root = ROOT / "stats" / format_id / "mtgo" / "top8"
    index = _json(root / "index.json")
    assert index["history_policy"] == "one_week_provisional_then_immutable"
    entry = index["weeks"][0]
    week = _json(root / entry["file"])
    bases = _json(root / entry["comparison_bases_file"])
    available = [
        placement
        for event in week["events"]
        for placement in event["placements"]
        if placement["deck_status"] == "available"
    ]
    assert available
    for placement in available:
        comparison = placement["comparison"]
        identity_id = comparison["identity_id"]
        assert comparison["average_deck_ref"] == (
            f"{entry['comparison_bases_file']}#identity/{identity_id}"
        )
        assert identity_id in bases["identities"]
        if comparison["base_status"] == "available":
            assert placement["exact_deck"]["deviation"] is not None
            assert placement["exact_deck"]["deviation_diff"] is not None
        else:
            assert placement["exact_deck"]["deviation"] is None
            assert placement["exact_deck"]["deviation_diff"] is None


def test_existing_provisional_event_cannot_be_rewritten(tmp_path):
    committed = _json(ROOT / "stats" / "modern" / "mtgo" / "top8" / "index.json")
    generated = datetime.fromisoformat(committed["generated"])
    output = tmp_path / "top8"
    top8.build_all_top8(
        ROOT,
        "modern",
        today=generated.date(),
        generated_at=generated,
        output_directory=output,
    )
    week_path = output / committed["weeks"][0]["file"]
    week = _json(week_path)
    week["events"][0]["name"] = "mutated"
    week_path.write_text(json.dumps(week, indent=2), encoding="utf-8")
    with pytest.raises(
        top8.MTGOTop8Error,
        match="provisional Top 8 existing event changed",
    ):
        top8.build_all_top8(
            ROOT,
            "modern",
            today=generated.date(),
            generated_at=generated,
            output_directory=output,
        )
