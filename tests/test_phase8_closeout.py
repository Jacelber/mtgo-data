"""Cross-product closeout contracts for the Phase 8 public front ends."""

from __future__ import annotations

import json
from pathlib import Path

from mtgmeta import consumer


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FORMATS = ("standard", "modern")
AVAILABLE_PRODUCTS = {
    "standard": {
        "mtgo-statistics": "stats/standard/mtgo/meta.json",
        "mtgo-matchups": "stats/standard/mtgo/matchup_index.json",
        "mtgo-top8": "stats/standard/mtgo/top8/index.json",
        "weekly-pickup": "stats/standard/mtgo/pickup/index.json",
    },
    "modern": {
        "mtgo-statistics": "stats/modern/mtgo/meta.json",
        "mtgo-matchups": "stats/modern/mtgo/matchup_index.json",
        "mtgo-top8": "stats/modern/mtgo/top8/index.json",
        "tabletop-major-events": "stats/modern/melee/index.json",
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_catalog_exposes_the_exact_accepted_cross_product_matrix() -> None:
    catalog = load_json(ROOT / "stats" / "catalog.json")
    formats = {item["id"]: item for item in catalog["formats"]}

    assert [item["id"] for item in catalog["formats"]] == [
        "standard",
        "pauper",
        "modern",
        "pioneer",
        "legacy",
        "vintage",
    ]
    for format_id, format_entry in formats.items():
        available = {
            item["id"]: item["path"]
            for item in format_entry["products"]
            if item["available"]
        }
        assert available == AVAILABLE_PRODUCTS.get(format_id, {})
        assert all(
            (item["path"] is not None) == item["available"]
            for item in format_entry["products"]
        )
        for product_id, relative_path in available.items():
            path = ROOT / relative_path
            document = load_json(path)
            expected_source = (
                "melee" if product_id == "tabletop-major-events" else "mtgo"
            )
            assert path.is_file()
            assert document["format"] == format_id
            assert document["source"] == expected_source


def test_public_catalogs_resolve_within_their_source_boundaries() -> None:
    for format_id in PUBLIC_FORMATS:
        root = ROOT / "stats" / format_id / "mtgo"
        metadata = load_json(root / "meta.json")
        for key in (
            "statistics_catalog",
            "matchup_catalog",
            "hierarchy_catalog",
            "top8_catalog",
            "completeness_catalog",
            "pickup_catalog",
        ):
            relative_path = metadata[key]
            if relative_path is not None:
                document = load_json(root / relative_path)
                assert document["format"] == format_id
                assert document["source"] == "mtgo"

    tabletop_root = ROOT / "stats" / "modern" / "melee"
    catalog = load_json(tabletop_root / "index.json")
    assert catalog["default_event_id"] == "434455"
    for entry in catalog["events"]:
        for key in ("meta", "overview", "decks", "matchup", "quality"):
            document = load_json(tabletop_root / entry[key])
            assert {
                document["event_id"],
                document["format"],
                document["source"],
            } == {entry["event_id"], "modern", "melee"}


def test_hierarchy_and_literal_matchup_contracts_hold_for_both_sources() -> None:
    for format_id in PUBLIC_FORMATS:
        root = ROOT / "stats" / format_id / "mtgo"
        hierarchy = load_json(root / "archetype_hierarchy.json")
        assert all(
            parent["expandable"] == (len(parent["subtype_ids"]) >= 2)
            for parent in hierarchy["parents"]
        )
        parent_names = {
            parent["id"]: parent["name"] for parent in hierarchy["parents"]
        }
        subtype_names_by_parent = {
            parent_id: tuple(
                leaf["name"]
                for leaf in hierarchy["leaves"]
                if leaf["kind"] == "subtype" and leaf["parent_id"] == parent_id
            )
            for parent_id in parent_names
        }
        assert all(
            leaf["display_name"]
            == consumer.identity_display_name(
                parent_names[leaf["parent_id"]],
                leaf["name"],
                maintained_subtype_names=subtype_names_by_parent[leaf["parent_id"]],
            )
            for leaf in hierarchy["leaves"]
            if leaf["kind"] == "subtype"
        )

        matchup = load_json(root / "matchup_4w.json")
        for parent_id in matchup["parent_order"]:
            mirror = matchup["parent_matrix"][parent_id].get(parent_id)
            if mirror is None:
                continue
            assert mirror["mirror"] is True
            assert mirror["literal_record"]["win_rate_method"] == (
                "wins_over_valid_matches"
            )

    tabletop = load_json(
        ROOT
        / "stats"
        / "modern"
        / "melee"
        / "events"
        / "434455"
        / "matchup.json"
    )
    for scope in tabletop["scopes"].values():
        for parent_id in scope["parent_order"]:
            mirror = scope["parent_matrix"][parent_id].get(parent_id)
            if mirror is None:
                continue
            assert mirror["mirror"] is True
            assert mirror["literal_record"]["win_rate_method"] == (
                "wins_over_valid_matches"
            )


def test_tabletop_event_selector_cannot_force_narrow_page_overflow() -> None:
    css = (
        ROOT / "assets" / "css" / "phase8-candidate.css"
    ).read_text(encoding="utf-8")

    assert ".select-row {\n    flex-wrap: wrap;\n  }" in css
    assert (
        ".select-row select {\n"
        "    min-width: 0;\n"
        "    max-width: 100%;\n"
        "  }"
    ) in css
