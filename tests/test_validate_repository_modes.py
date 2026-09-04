import json
import subprocess
from pathlib import Path

import pytest

from mtgmeta.mtgo.landing_editorial import build_public_name_contract

from validate_repository import (
    changed_validation_plan,
    validate_files,
    validate_public_product_facts,
    validate_test_inventory,
    tracked_files,
)
from validate_schemas import validate_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def write_public_product_fixture(
    root: Path,
    *,
    whitelist_event_ids: tuple[str, ...],
    public_event_ids: tuple[str, ...],
) -> list[str]:
    (root / "configs").mkdir()
    (root / "my_archetypes").mkdir()
    (root / "schemas").mkdir()
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
    rule_template = (
        "schema_version: 1.0.0\n"
        "format: {format_id}\n"
        "archetypes:\n"
        "- id: {identity}\n"
        "  name: {english}\n"
        "  priority: 1\n"
        "  rules:\n"
        "  - id: {identity}-rule\n"
        "    priority: 1\n"
        "    subtype_id: null\n"
        "    conditions:\n"
        "      all:\n"
        "      - card: Synthetic Card\n"
        "        min_count: 1\n"
    )
    (root / "my_archetypes" / "modern.yaml").write_text(
        rule_template.format(
            format_id="modern",
            identity="synthetic-control",
            english="Synthetic Control",
        ),
        encoding="utf-8",
    )
    (root / "my_archetypes" / "standard.yaml").write_text(
        rule_template.format(
            format_id="standard",
            identity="synthetic-standard",
            english="Synthetic Standard",
        ),
        encoding="utf-8",
    )
    (root / "schemas" / "mtgo-archetype-names.schema.json").write_text(
        (REPOSITORY_ROOT / "schemas" / "mtgo-archetype-names.schema.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (root / "configs" / "formats.yaml").write_text(
        (REPOSITORY_ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (root / "configs" / "mtgo_archetype_names.yaml").write_text(
        "schema_version: 1.0.0\n"
        "names:\n"
        "- format: modern\n"
        "  parent_id: synthetic-control\n"
        "  subtype_id: null\n"
        "  english: Synthetic Control\n"
        "  chinese: 合成控制\n"
        "  review_status: approved\n"
        "  identity_key: modern|synthetic-control|none\n"
        "- format: standard\n"
        "  parent_id: synthetic-standard\n"
        "  subtype_id: null\n"
        "  english: Synthetic Standard\n"
        "  chinese: 合成标准\n"
        "  review_status: approved\n"
        "  identity_key: standard|synthetic-standard|none\n",
        encoding="utf-8",
    )
    (root / "stats" / "modern" / "archetype_names.json").write_text(
        json.dumps(build_public_name_contract(root, "modern")),
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
        "configs/mtgo_archetype_names.yaml",
        "stats/catalog.json",
        "stats/modern/archetype_names.json",
        "stats/modern/melee/index.json",
    ]
    return names


def write_test_inventory_fixture(
    root: Path,
    *,
    rows: tuple[tuple[str, str], ...],
    files: dict[str, str],
) -> list[str]:
    matrix = root / "docs" / "TEST_TRIGGER_MATRIX.md"
    matrix.parent.mkdir(parents=True)
    body = [
        "## Retained Python tests",
        "",
        "| File | Trigger | Purpose | Minimum subject | Independent oracle |",
        "| --- | --- | --- | --- | --- |",
    ]
    body.extend(
        f"| `{path}` | trigger | purpose | subject | `{oracle}` |"
        for path, oracle in rows
    )
    body.extend(("", "## Next section", ""))
    matrix.write_text("\n".join(body), encoding="utf-8")
    for path, source in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    return sorted(["docs/TEST_TRIGGER_MATRIX.md", *files])


def test_registered_synthetic_test_inventory_passes(tmp_path: Path) -> None:
    names = write_test_inventory_fixture(
        tmp_path,
        rows=(("tests/test_alpha.py", "synthetic"),),
        files={"tests/test_alpha.py": "def test_alpha():\n    assert True\n"},
    )

    checked, failures = validate_test_inventory(tmp_path, names)

    assert checked == 2
    assert failures == []


@pytest.mark.parametrize(
    ("rows", "files", "expected"),
    (
        (
            (),
            {"tests/unit/test_alpha.py": "def test_alpha():\n    assert True\n"},
            "unregistered Python test",
        ),
        (
            (("tests/test_alpha.py", "result-looked-right"),),
            {"tests/test_alpha.py": "def test_alpha():\n    assert True\n"},
            "invalid independent oracle",
        ),
        (
            (("tests/test_alpha.py", "synthetic"),),
            {},
            "stale Python test registration",
        ),
        (
            (("tests/test_w35_alpha.py", "synthetic"),),
            {"tests/test_w35_alpha.py": "def test_alpha():\n    assert True\n"},
            "week- or event-specific Python test files are prohibited",
        ),
        (
            (("tests/test_alpha.py", "owner-rule-contract"),),
            {
                "tests/test_alpha.py": (
                    "from pathlib import Path\n"
                    "ROOT = Path(__file__).parents[1]\n"
                    "VALUE = ROOT / 'data/modern/event.json'\n"
                )
            },
            "tests must not read repository-live data or reports as an oracle",
        ),
        (
            (
                ("tests/test_alpha.py", "synthetic"),
                ("tests/test_alpha.py", "synthetic"),
            ),
            {"tests/test_alpha.py": "def test_alpha():\n    assert True\n"},
            "duplicate test registration",
        ),
        (
            (("tests/test_alpha.py", "synthetic"),),
            {
                "tests/test_alpha.py": (
                    "from pathlib import Path\n"
                    "ROOT = Path(__file__).parents[1]\n"
                    "VALUE = ROOT / 'stats/example.json'\n"
                )
            },
            "repository-live statistics require",
        ),
    ),
)
def test_test_inventory_failures_are_closed_and_specific(
    tmp_path: Path,
    rows: tuple[tuple[str, str], ...],
    files: dict[str, str],
    expected: str,
) -> None:
    names = write_test_inventory_fixture(tmp_path, rows=rows, files=files)

    _checked, failures = validate_test_inventory(tmp_path, names)

    assert any(expected in failure.message for failure in failures)


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
    tracked = [
        "README.md",
        "docs/STATUS.yaml",
        "docs/TEST_TRIGGER_MATRIX.md",
        "index.html",
        "tests/test_alpha.py",
    ]

    readme_plan = changed_validation_plan(["README.md"], tracked)
    entry_plan = changed_validation_plan(["index.html"], tracked)

    assert readme_plan.public_product_facts is True
    assert readme_plan.candidates == ("README.md",)
    assert readme_plan.reference_groups == frozenset()
    assert entry_plan.public_product_facts is False
    assert entry_plan.reference_groups == frozenset(
        {"frontend-templates", "phase8-entries"}
    )
    test_plan = changed_validation_plan(["tests/test_alpha.py"], tracked)
    assert test_plan.reference_groups == frozenset({"test-inventory"})
    matrix_plan = changed_validation_plan(["docs/TEST_TRIGGER_MATRIX.md"], tracked)
    assert matrix_plan.reference_groups == frozenset({"test-inventory"})


@pytest.mark.parametrize("path", ["configs/mtgo_weekly_review_completions.yaml",
    "src/mtgmeta/mtgo/publication.py", "src/mtgmeta/mtgo/stats.py", "data/standard/synthetic.json"])
def test_reviewed_publication_changes_select_only_read_only_closure(path):
    plan = changed_validation_plan([path], [path])
    assert plan.reference_groups == frozenset({"classifier-closure"})


@pytest.mark.parametrize(
    "changed_path",
    (
        "configs/mtgo_archetype_names.yaml",
        "stats/modern/archetype_names.json",
        "stats/modern/melee/index.json",
        "stats/modern/melee/events/441441/overview.json",
    ),
)
def test_changed_plan_treats_public_name_and_tabletop_outputs_as_public_product_facts(
    changed_path: str,
):
    plan = changed_validation_plan(
        [changed_path],
        [changed_path, "docs/STATUS.yaml"],
    )

    assert plan.public_product_facts is True
    assert plan.candidates == (changed_path,)


def test_status_change_does_not_select_public_product_fact_validation():
    plan = changed_validation_plan(
        ["docs/STATUS.yaml"],
        ["README.md", "docs/STATUS.yaml", "stats/catalog.json"],
    )

    assert plan.public_product_facts is False
    assert plan.candidates == ("docs/STATUS.yaml",)


def test_enabled_unpublished_event_does_not_change_public_product_facts(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455", "441441"),
        public_event_ids=("434455",),
    )

    _, failures = validate_public_product_facts(tmp_path, names)

    assert failures == []


def test_stale_public_classifier_name_contract_fails_closed(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455",),
        public_event_ids=("434455",),
    )
    public_contract = tmp_path / "stats" / "modern" / "archetype_names.json"
    document = json.loads(public_contract.read_text(encoding="utf-8"))
    document["names"][0]["display"]["zh"] = "陈旧名称"
    public_contract.write_text(json.dumps(document), encoding="utf-8")

    _, failures = validate_public_product_facts(tmp_path, names)

    assert any(
        failure.path == "stats/modern/archetype_names.json"
        and "does not match the approved bilingual name catalog" in failure.message
        for failure in failures
    )


def test_public_event_requires_matching_whitelist_entry(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455",),
        public_event_ids=("434455", "441441"),
    )
    (tmp_path / "README.md").write_text(
        "| MTGO Environment Trends | Modern | `/index.html` |\n"
        "| Tabletop Major Events | Modern (events `434455`, `441441`) | `/melee/index.html` |\n",
        encoding="utf-8",
    )

    _, failures = validate_public_product_facts(tmp_path, names)

    assert [failure.message for failure in failures] == [
        "public event '441441' requires an enabled, verified Tabletop whitelist entry"
    ]


def test_readme_event_ids_follow_public_catalog(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455", "441441"),
        public_event_ids=("434455", "441441"),
    )

    _, failures = validate_public_product_facts(tmp_path, names)

    assert [failure.message for failure in failures] == [
        "missing or inconsistent row '| Tabletop Major Events | Modern (events `434455`, `441441`) | `/melee/index.html` |'"
    ]


def test_candidate_mode_defers_only_tabletop_readme_synchronization(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455", "441441"),
        public_event_ids=("434455", "441441"),
    )

    _, failures = validate_public_product_facts(
        tmp_path, names, defer_tabletop_readme=True
    )

    assert failures == []


def test_candidate_mode_keeps_whitelist_and_mtgo_readme_checks(tmp_path):
    names = write_public_product_fixture(
        tmp_path,
        whitelist_event_ids=("434455",),
        public_event_ids=("434455", "441441"),
    )
    (tmp_path / "README.md").write_text(
        "| Tabletop Major Events | Modern (events `434455`, `441441`) | `/melee/index.html` |\n",
        encoding="utf-8",
    )

    _, failures = validate_public_product_facts(
        tmp_path, names, defer_tabletop_readme=True
    )

    assert {failure.message for failure in failures} == {
        "public event '441441' requires an enabled, verified Tabletop whitelist entry",
        "missing or inconsistent row '| MTGO Environment Trends | Modern | `/index.html` |'",
    }


def test_candidate_file_discovery_is_stable_before_and_after_bounded_staging(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
    candidate = repository / "stats" / "modern" / "melee" / "events" / "441441"
    candidate.mkdir(parents=True)
    (candidate / "overview.json").write_text("{}\n", encoding="utf-8")

    expected = ["stats/modern/melee/events/441441/overview.json"]
    assert tracked_files(repository) == expected
    subprocess.run(
        ["git", "add", "--", "stats/modern/melee/events/441441/overview.json"],
        cwd=repository,
        check=True,
    )

    assert tracked_files(repository) == expected


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
