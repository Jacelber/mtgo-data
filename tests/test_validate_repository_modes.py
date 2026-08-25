from pathlib import Path

from validate_repository import changed_validation_plan, validate_files


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
