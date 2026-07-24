"""P6-10 cross-layer closeout contracts for the public MTGO products."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.mtgo.matchup import rollup_matchup_counts


PRODUCT_FORMATS = ("standard", "modern")
WINDOWS = [1, 4, 12, 36]
COMPLETE_CAPABILITIES = {
    "classification",
    "event_statistics",
    "range_statistics",
    "matchup_statistics",
    "weekly_pickup",
    "metadata_generation",
    "catalog_generation",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def wld(cell: dict) -> dict[str, int]:
    return {field: cell[field] for field in ("wins", "losses", "draws")}


def test_public_registry_workflow_and_generated_layers_are_aligned():
    registry = yaml.safe_load(
        (ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8")
    )
    complete = [
        item["id"]
        for item in registry["formats"]
        if item["state"] == "executable"
        and item["public"]
        and COMPLETE_CAPABILITIES <= set(item["mtgo"]["capabilities"])
    ]
    assert complete == list(PRODUCT_FORMATS)

    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    environment = workflow["jobs"]["update"]["env"]
    assert environment["MTGO_PRODUCT_FORMATS"].split() == list(PRODUCT_FORMATS)
    assert environment["MTGO_HIERARCHY_FORMATS"].split() == list(PRODUCT_FORMATS)

    for format_id in PRODUCT_FORMATS:
        base = ROOT / "stats" / format_id / "mtgo"
        metadata = load_json(base / "meta.json")
        statistics = load_json(base / metadata["statistics_catalog"])
        matchups = load_json(base / metadata["matchup_catalog"])
        hierarchy = load_json(base / metadata["hierarchy_catalog"])
        reports = load_json(ROOT / "reports" / format_id / "mtgo" / "index.json")

        assert {
            metadata["format"],
            statistics["format"],
            matchups["format"],
            hierarchy["format"],
            reports["format"],
        } == {format_id}
        assert {
            metadata["source"],
            statistics["source"],
            matchups["source"],
            hierarchy["source"],
            reports["source"],
        } == {"mtgo"}
        assert [entry["weeks"] for entry in statistics["ranges"]] == WINDOWS
        assert [entry["weeks"] for entry in matchups["ranges"]] == WINDOWS
        assert hierarchy["summary"] == {
            "parents": len(hierarchy["parents"]),
            "leaves": len(hierarchy["leaves"]),
            "expandable_parents": sum(
                parent["expandable"] for parent in hierarchy["parents"]
            ),
        }
        assert all(
            parent["expandable"] == (len(parent["subtype_ids"]) >= 2)
            for parent in hierarchy["parents"]
        )
        assert metadata["matchup_source"] == "Videre"
        assert set(metadata["matchup_coverage"]) == {
            "official_events",
            "events_with_archives",
            "events_without_archives",
            "stored_archives",
            "archives_outside_official_events",
        }


def test_every_public_matchup_window_conserves_hierarchical_counts():
    for format_id in PRODUCT_FORMATS:
        base = ROOT / "stats" / format_id / "mtgo"
        catalog = load_json(base / "matchup_index.json")
        maintained = load_json(base / "archetype_hierarchy.json")

        for entry in catalog["ranges"]:
            document = load_json(base / entry["file"])
            assert document["hierarchical"] is True
            assert document["canonical_level"] == "leaf"
            assert document["hierarchy"] == {
                "parents": maintained["parents"],
                "leaves": maintained["leaves"],
            }
            assert entry["leaves"] == len(document["leaf_order"])

            leaf_to_parent = {
                leaf["id"]: leaf["parent_id"]
                for leaf in document["hierarchy"]["leaves"]
            }
            leaf_counts = {
                row_id: {
                    column_id: wld(cell)
                    for column_id, cell in columns.items()
                }
                for row_id, columns in document["leaf_matrix"].items()
            }
            parent_counts = rollup_matchup_counts(leaf_counts, leaf_to_parent)
            emitted_parent_counts = {
                row_id: {
                    column_id: wld(cell)
                    for column_id, cell in columns.items()
                }
                for row_id, columns in document["parent_matrix"].items()
            }
            assert parent_counts == emitted_parent_counts
            assert sum(
                sum(cell.values())
                for columns in leaf_counts.values()
                for cell in columns.values()
            ) == entry["counted_matches"] * 2

            for parent_id in document["parent_order"]:
                expected = {"wins": 0, "losses": 0, "draws": 0}
                for opponent_id, cell in document["parent_matrix"][parent_id].items():
                    if opponent_id == parent_id:
                        continue
                    for field in expected:
                        expected[field] += cell[field]
                assert wld(document["parent_overall"][parent_id]) == expected

            if format_id == "standard":
                names = {
                    parent["id"]: parent["name"]
                    for parent in document["hierarchy"]["parents"]
                }
                assert document["archetype_order"] == [
                    names[parent_id] for parent_id in document["parent_order"]
                ]
                assert document["overall"] == {
                    names[parent_id]: document["parent_overall"][parent_id]
                    for parent_id in document["parent_order"]
                }
                assert document["matrix"] == {
                    names[row_id]: {
                        names[column_id]: cell
                        for column_id, cell in columns.items()
                    }
                    for row_id, columns in document["parent_matrix"].items()
                }
            else:
                assert "archetype_order" not in document
                assert "overall" not in document
                assert "matrix" not in document


def test_public_format_selector_uses_the_shared_hierarchical_renderer():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "assets" / "js" / "mtgo.js").read_text(encoding="utf-8")

    assert html.index('src="assets/js/matchup.js"') < html.index(
        'src="assets/js/mtgo.js"'
    )
    assert re.findall(
        r'\{\s*key:\s*"([^"]+)",\s*enabled:\s*true\s*\}',
        javascript,
    ) == list(PRODUCT_FORMATS)
    assert "MtgMatchup.buildView(" in javascript
    assert "mxExpandedRows" in javascript
    assert "mxExpandedColumns" in javascript
    assert "renderMxExpandControls(view)" in javascript
    assert "if (!node.showAxisToggle) return \"\";" in javascript
