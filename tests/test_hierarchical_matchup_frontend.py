"""P6-09 shared hierarchical matchup front-end contracts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def run_view(expanded_rows=(), expanded_columns=()):
    document = {
        "hierarchical": True,
        "min_sample_hint": 2,
        "parent_order": ["alpha", "beta", "gamma"],
        "hierarchy": {
            "parents": [
                {
                    "id": "alpha",
                    "name": "Alpha",
                    "expandable": True,
                    "subtype_ids": ["alpha/one", "alpha/two"],
                },
                {
                    "id": "beta",
                    "name": "Beta",
                    "expandable": False,
                    "subtype_ids": [],
                },
                {
                    "id": "gamma",
                    "name": "Gamma",
                    "expandable": False,
                    "subtype_ids": ["gamma/only"],
                },
            ],
            "leaves": [
                {
                    "id": "alpha/one",
                    "kind": "subtype",
                    "name": "One",
                    "parent_id": "alpha",
                    "subtype_id": "one",
                },
                {
                    "id": "alpha/two",
                    "kind": "subtype",
                    "name": "Two",
                    "parent_id": "alpha",
                    "subtype_id": "two",
                },
                {
                    "id": "beta",
                    "kind": "archetype",
                    "name": "Beta",
                    "parent_id": "beta",
                    "subtype_id": None,
                },
                {
                    "id": "gamma/only",
                    "kind": "subtype",
                    "name": "Only",
                    "parent_id": "gamma",
                    "subtype_id": "only",
                },
            ],
        },
        "leaf_matrix": {
            "alpha/one": {
                "alpha/two": {"wins": 1, "losses": 0, "draws": 0},
                "beta": {"wins": 1, "losses": 0, "draws": 0},
            },
            "alpha/two": {
                "alpha/one": {"wins": 0, "losses": 1, "draws": 0},
                "beta": {"wins": 0, "losses": 1, "draws": 0},
            },
            "beta": {
                "alpha/one": {"wins": 0, "losses": 1, "draws": 0},
                "alpha/two": {"wins": 1, "losses": 0, "draws": 0},
                "gamma/only": {"wins": 0, "losses": 0, "draws": 1},
            },
            "gamma/only": {
                "beta": {"wins": 0, "losses": 0, "draws": 1},
            },
        },
    }
    script = """
const api = require("./assets/js/matchup.js");
const document = JSON.parse(process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const columns = JSON.parse(process.argv[3]);
process.stdout.write(JSON.stringify(api.buildView(document, rows, columns)));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            json.dumps(document),
            json.dumps(list(expanded_rows)),
            json.dumps(list(expanded_columns)),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_collapsed_view_recalculates_parent_cells_from_canonical_counts():
    view = run_view()

    assert [item["id"] for item in view["rows"]] == ["alpha", "beta", "gamma"]
    assert [item["id"] for item in view["columns"]] == ["alpha", "beta", "gamma"]
    assert [item["showAxisToggle"] for item in view["rows"]] == [
        True,
        False,
        False,
    ]
    assert view["expandableParentIds"] == ["alpha"]
    assert view["matrix"]["alpha"]["beta"] == {
        "wins": 1,
        "losses": 1,
        "draws": 0,
        "matches": 2,
        "win_rate": 0.5,
        "ci_half": view["matrix"]["alpha"]["beta"]["ci_half"],
        "low_sample": False,
        "mirror": False,
    }
    assert view["matrix"]["alpha"]["alpha"]["matches"] == 2
    assert view["overall"]["alpha"]["matches"] == 2
    assert view["overall"]["alpha"]["win_rate"] == 0.5


def test_row_and_column_expansion_are_independent_and_exclude_parent_mirrors_from_overall():
    row_view = run_view(["alpha"], [])
    assert [item["id"] for item in row_view["rows"]] == [
        "alpha/one",
        "alpha/two",
        "beta",
        "gamma",
    ]
    assert [item["showAxisToggle"] for item in row_view["rows"]] == [
        True,
        False,
        False,
        False,
    ]
    assert [item["id"] for item in row_view["columns"]] == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert row_view["overall"]["alpha/one"]["matches"] == 1
    assert row_view["overall"]["alpha/one"]["wins"] == 1

    column_view = run_view([], ["alpha"])
    assert [item["id"] for item in column_view["rows"]] == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert [item["id"] for item in column_view["columns"]] == [
        "alpha/one",
        "alpha/two",
        "beta",
        "gamma",
    ]
    assert column_view["matrix"]["beta"]["alpha/one"]["losses"] == 1
    assert column_view["matrix"]["beta"]["alpha/two"]["wins"] == 1


def test_expanding_both_axes_exposes_subtype_matchups_but_single_subtype_parent_stays_collapsed():
    view = run_view(["alpha", "gamma"], ["alpha", "gamma"])

    assert [item["id"] for item in view["rows"]] == [
        "alpha/one",
        "alpha/two",
        "beta",
        "gamma",
    ]
    assert view["matrix"]["alpha/one"]["alpha/two"]["wins"] == 1
    assert view["matrix"]["alpha/two"]["alpha/one"]["losses"] == 1
