import json
from pathlib import Path

from validate_repository import (
    changed_validation_plan,
    validate_files,
    validate_public_product_facts,
)
from validate_schemas import validate_manifest


def write_public_product_fixture(
    root: Path,
    *,
    whitelist_event_ids: tuple[str, ...],
    public_event_ids: tuple[str, ...],
) -> tuple[list[str], dict]:
    (root / "configs").mkdir()
    (root / "stats" / "modern" / "melee").mkdir(parents=True)
    (root / "README.md").write_text(
        "| MTGO Environment Trends | Modern | `/index.html` |\n"
        "| Tabletop Major Events | Modern (event `434455`) | `/melee/index.html` |\n",
        encoding="utf-8",
    )
    (root / "stats" / "catalog.json").write_text(
        json.dumps(
            {
                "formats": [
                    {
                        "id": "modern",
                        "display_name": "Modern",
                        "products": [
                            {"id": "mtgo-statistics", "available": True},
                            {
                                "id": "tabletop-major-events",
                                "available": True,
                                "path": "stats/modern/melee/index.json",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "configs" / "melee_events.yaml").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": event_id,
                        "format": "modern",
                        "enabled": True,
                        "review_status": "verified",
                        "tabletop": True,
                    }
                    for event_id in whitelist_event_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "stats" / "modern" / "melee" / "index.json").write_text(
        json.dumps(
            {
                "format": "modern",
                "events": [
                    {"event_id": event_id} for event_id in public_event_ids
                ],
            }
        ),
        encoding="utf-8",
    )
    names = [
        "README.md",
        "configs/melee_events.yaml",
        "stats/catalog.json",
        "stats/modern/melee/index.json",
    ]
    status = {
        "current_repository_state": {
            "public_entries": {
                "mtgo": "/index.html",
                "tabletop": "/melee/index.html",
            }
        }
    }
    return names, status


def test_changed_plan_includes_directly_changed_maintained_files():
    tracked = [
        "src/mtgmeta/example.py",
        "assets/js/phase8/runtime.js",
        "data/unrelated/broken.json",
    ]

    plan = changed_validation_plan(
        ["src/mtgmeta/example.py", "assets/js/phase8/runtime.js"], tracked
    )

    assert plan.candidates == (
        "assets/js/phase8/runtime.js",
        "src/mtgmeta/example.py",
    )
    assert plan.javascript == ("assets/js/phase8/runtime.js",)
    assert "data/unrelated/broken.json" not in plan.candidates


def test_changed_plan_adds_only_the_triggered_coupled_contracts():
    tracked = ["README.md", "docs/STATUS.yaml", "index.html"]

    readme_plan = changed_validation_plan(["README.md"], tracked)
    entry_plan = changed_validation_plan(["index.html"], tracked)

    assert readme_plan.public_product_facts is True
    assert readme_plan.candidates == ("README.md", "docs/STATUS.yaml")
    assert readme_plan.reference_groups == frozenset()
    assert entry_plan.public_product_facts is False
    assert entry_plan.reference_groups == frozenset(
        {"frontend-templates", "phase8-entries"}
    )


def test_changed_plan_treats_tabletop_event_catalog_as_public_product_facts():
    catalog_path = "stats/modern/melee/index.json"

    plan = changed_validation_plan([catalog_path], [catalog_path, "docs/STATUS.yaml"])

    assert plan.public_product_facts is True
    assert plan.candidates == ("docs/STATUS.yaml", catalog_path)


def test_enabled_unpublished_event_does_not_change_public_product_facts(tmp_path):
    names, status = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455", "441441"),
        public_event_ids=("434455",),
    )

    _, failures = validate_public_product_facts(tmp_path, names, status)

    assert failures == []


def test_public_event_requires_matching_whitelist_entry(tmp_path):
    names, status = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455",),
        public_event_ids=("434455", "441441"),
    )
    (tmp_path / "README.md").write_text(
        "| MTGO Environment Trends | Modern | `/index.html` |\n"
        "| Tabletop Major Events | Modern (events `434455`, `441441`) | `/melee/index.html` |\n",
        encoding="utf-8",
    )

    _, failures = validate_public_product_facts(tmp_path, names, status)

    assert [failure.message for failure in failures] == [
        "public event '441441' requires an enabled, verified Tabletop whitelist entry"
    ]


def test_readme_event_ids_follow_public_catalog(tmp_path):
    names, status = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455", "441441"),
        public_event_ids=("434455", "441441"),
    )

    _, failures = validate_public_product_facts(tmp_path, names, status)

    assert [failure.message for failure in failures] == [
        "missing or inconsistent row '| Tabletop Major Events | Modern (events `434455`, `441441`) | `/melee/index.html` |'"
    ]


def test_changed_file_validation_does_not_parse_an_unrelated_area(tmp_path: Path):
    changed = tmp_path / "changed.py"
    unrelated = tmp_path / "unrelated.json"
    changed.write_text("VALUE = 1\n", encoding="utf-8")
    unrelated.write_text("{not valid json", encoding="utf-8")

    counts, failures, _ = validate_files(tmp_path, ["changed.py"], ())

    assert counts == {"Python": 1, "JavaScript": 0, "JSON": 0, "YAML": 0}
    assert failures == []


def test_changed_schema_mode_excludes_unrelated_documents_but_full_mode_keeps_them(
    tmp_path,
):
    schema_dir = tmp_path / "schemas"
    stats_dir = tmp_path / "stats"
    schema_dir.mkdir()
    stats_dir.mkdir()
    (schema_dir / "value.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.test/value",
                "required": ["value"],
            }
        ),
        encoding="utf-8",
    )
    manifest = schema_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "output_schema_version_embedded": True,
                "mappings": [{"pattern": "stats/*.json", "schema": "value.schema.json"}],
            }
        ),
        encoding="utf-8",
    )
    (stats_dir / "changed.json").write_text('{"value": 1}', encoding="utf-8")
    (stats_dir / "unrelated.json").write_text("{}", encoding="utf-8")

    changed_checked, changed_failures = validate_manifest(
        tmp_path,
        manifest,
        {"stats/changed.json"},
    )
    full_checked, full_failures = validate_manifest(tmp_path, manifest)

    assert (changed_checked, changed_failures) == (1, [])
    assert full_checked == 2
    assert [failure.path for failure in full_failures] == ["stats/unrelated.json"]
