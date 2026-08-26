import json
from pathlib import Path

from validate_repository import changed_validation_plan, validate_files
from validate_schemas import validate_manifest


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
