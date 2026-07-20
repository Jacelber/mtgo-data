import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "standard" / "public_contract" / "contract.json"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def contract():
    return load_json(CONTRACT_PATH)


def assert_identity(document, expected):
    assert document["schema_version"] == expected["schema_version"]
    assert document["format"] == expected["format"]
    assert document["source"] == expected["source"]


def test_frontend_public_paths_are_frozen_and_exist():
    expected = contract()
    frontend_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            REPO_ROOT / "index.html",
            REPO_ROOT / "assets" / "js" / "common.js",
            REPO_ROOT / "assets" / "js" / "mtgo.js",
        )
    )

    for template in expected["frontend_templates"]:
        assert template in frontend_source

    base = REPO_ROOT / "stats" / expected["format"] / expected["source"]
    assert (base / "meta.json").is_file()
    assert (base / "pickup" / "index.json").is_file()
    for weeks in expected["ranges"]:
        assert (base / f"range_{weeks}w.json").is_file()
        assert (base / f"decks_{weeks}w.json").is_file()
        assert (base / f"matchup_{weeks}w.json").is_file()


def test_statistics_catalog_targets_and_periods_reconcile():
    expected = contract()
    catalog_path = REPO_ROOT / expected["catalogs"]["statistics"]
    catalog = load_json(catalog_path)
    assert_identity(catalog, expected)
    assert [entry["weeks"] for entry in catalog["ranges"]] == expected["ranges"]

    for entry in catalog["ranges"]:
        range_document = load_json(catalog_path.parent / entry["file"])
        decks_document = load_json(catalog_path.parent / entry["decks_file"])
        assert_identity(range_document, expected)
        assert_identity(decks_document, expected)
        assert range_document["period"] == decks_document["period"]
        assert range_document["period"] == {
            "type": entry["type"],
            "start": entry["start"],
            "end": entry["end"],
            "weeks": entry["weeks"],
        }
        assert range_document["total_decks"] == entry["total_decks"]
        assert sum(item["count"] for item in range_document["archetypes"]) == entry["total_decks"]


def test_matchup_catalog_targets_periods_and_counts_reconcile():
    expected = contract()
    catalog_path = REPO_ROOT / expected["catalogs"]["matchups"]
    catalog = load_json(catalog_path)
    assert_identity(catalog, expected)
    assert [entry["weeks"] for entry in catalog["ranges"]] == expected["ranges"]

    for entry in catalog["ranges"]:
        document = load_json(catalog_path.parent / entry["file"])
        assert_identity(document, expected)
        assert document["period"] == {
            "type": entry["type"],
            "start": entry["start"],
            "end": entry["end"],
            "weeks": entry["weeks"],
        }
        assert document["min_sample_hint"] == catalog["min_sample_hint"]
        assert len(document["archetype_order"]) == entry["archetypes"]

        counted_matches = 0
        counted_pairs = set()
        for archetype, opponents in document["matrix"].items():
            for opponent, cell in opponents.items():
                assert cell["matches"] == cell["wins"] + cell["losses"] + cell["draws"]
                reverse = document["matrix"][opponent][archetype]
                assert (cell["wins"], cell["losses"], cell["draws"]) == (
                    reverse["losses"], reverse["wins"], reverse["draws"]
                )
                pair = tuple(sorted((archetype, opponent)))
                if pair not in counted_pairs:
                    counted_pairs.add(pair)
                    divisor = 2 if archetype == opponent else 1
                    assert cell["matches"] % divisor == 0
                    counted_matches += cell["matches"] // divisor
        assert counted_matches == entry["counted_matches"]


def test_pickup_catalog_targets_and_metadata_reconcile():
    expected = contract()
    catalog_path = REPO_ROOT / expected["catalogs"]["pickup"]
    catalog = load_json(catalog_path)
    assert_identity(catalog, expected)

    for entry in catalog["weeks"]:
        document = load_json(catalog_path.parent / entry["file"])
        assert_identity(document, expected)
        assert document["week"] == entry["week"]
        assert document["start"] == entry["start"]
        assert document["end"] == entry["end"]
        assert len(document["existing_changes"]) == entry["existing_count"]
        assert len(document["new_archetypes"]) == entry["new_count"]
