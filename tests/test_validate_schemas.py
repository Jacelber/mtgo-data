import json
from pathlib import Path

from validate_schemas import main, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_melee_manifests_are_dynamic_and_cover_internal_and_public_documents():
    public = json.loads((ROOT / "schemas/manifest.json").read_text(encoding="utf-8"))
    internal = json.loads(
        (ROOT / "schemas/melee-data-manifest.json").read_text(encoding="utf-8")
    )
    public_patterns = {item["pattern"] for item in public["mappings"]}
    internal_patterns = {item["pattern"] for item in internal["mappings"]}

    assert not any("434455" in pattern for pattern in public_patterns)
    assert {
        "stats/*/melee/index.json",
        "stats/*/melee/events/*/overview.json",
        "stats/*/melee/events/*/decks.json",
        "stats/*/melee/events/*/matchup.json",
        "stats/*/melee/events/*/quality.json",
        "stats/*/melee/events/*/meta.json",
    } <= public_patterns
    assert internal_patterns == {
        "data/*/melee/events/*.json",
        "data/*/melee/classifications/*.json",
        "data/*/melee/opportunities/*.json",
    }


def test_current_melee_documents_pass_both_complete_manifests():
    for relative in ("schemas/manifest.json", "schemas/melee-data-manifest.json"):
        checked, failures = validate_manifest(ROOT, ROOT / relative)
        assert checked > 0
        assert failures == []


def test_explicit_schema_path_fails_when_manifest_does_not_map_it(capsys):
    assert main(["--root", str(ROOT), "--path", "README.md"]) == 2
    assert "not mapped by the selected manifest" in capsys.readouterr().out


def test_selected_output_loads_only_its_schema_and_checks_referenced_values(tmp_path):
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    def write(name, value):
        (schemas / name).write_text(json.dumps(value), encoding="utf-8")
    write("manifest.json", {"schema_version": "1.0.0", "output_schema_version_embedded": True,
        "mappings": [{"pattern": "selected.json", "schema": "selected.schema.json"},
                     {"pattern": "other.json", "schema": "broken.schema.json"}]})
    write("selected.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.test/selected.schema.json", "$ref": "count.schema.json"})
    write("count.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.test/count.schema.json", "type": "integer", "minimum": 0})
    (schemas / "broken.schema.json").write_text("malformed unrelated schema")
    (tmp_path / "other.json").write_text("malformed unrelated output")
    for value, valid in ((3, True), (5, True), (-1, False)):
        (tmp_path / "selected.json").write_text(json.dumps(value))
        checked, failures = validate_manifest(tmp_path, schemas / "manifest.json", {"selected.json"})
        assert checked == 1
        assert (not failures) == valid
