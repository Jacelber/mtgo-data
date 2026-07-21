import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema.exceptions import SchemaError

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]


def test_production_public_outputs_pass():
    checked, failures = schemas.validate_manifest(ROOT, ROOT / "schemas" / "manifest.json")
    assert checked == 23
    assert failures == []


def test_every_public_output_embeds_the_manifest_version():
    manifest = json.loads((ROOT / "schemas" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["output_schema_version_embedded"] is True
    matched = []
    for mapping in manifest["mappings"]:
        matched.extend(ROOT.glob(mapping["pattern"]))
    assert len(matched) == 23
    assert all(json.loads(path.read_text(encoding="utf-8"))["schema_version"] == manifest["schema_version"] for path in matched)


def test_all_declared_schemas_are_valid_and_versioned():
    loaded, _ = schemas.load_schemas(ROOT / "schemas")
    assert len(loaded) == 17
    assert "classification-rules.schema.json" in loaded
    assert "classification-report.schema.json" in loaded
    assert "classification-report-index.schema.json" in loaded
    assert "formats.schema.json" in loaded
    assert "melee-events.schema.json" in loaded
    assert "melee-event.schema.json" in loaded
    assert "melee-raw-archive.schema.json" in loaded
    assert all(schema["$schema"] == "https://json-schema.org/draft/2020-12/schema" for schema in loaded.values())
    assert loaded["formats.schema.json"]["x-schema-version"] == "1.1.0"
    assert loaded["melee-events.schema.json"]["x-schema-version"] == "3.0.0"
    assert loaded["melee-event.schema.json"]["x-schema-version"] == "2.1.0"
    assert loaded["melee-raw-archive.schema.json"]["x-schema-version"] == "2.0.0"
    assert all(
        schema["x-schema-version"] == "1.0.0"
        for name, schema in loaded.items()
        if name not in {
            "formats.schema.json", "melee-events.schema.json", "melee-event.schema.json",
            "melee-raw-archive.schema.json"
        }
    )


@pytest.mark.parametrize("filename", ["range_1w.json", "decks_1w.json", "index.json", "matchup_1w.json", "matchup_index.json", "meta.json"])
def test_required_top_level_field_removal_fails(filename):
    source = ROOT / "stats" / "standard" / "mtgo" / filename
    instance = json.loads(source.read_text(encoding="utf-8"))
    removed = next(iter(instance))
    instance.pop(removed)
    manifest = json.loads((ROOT / "schemas" / "manifest.json").read_text(encoding="utf-8"))
    mapping = next(item for item in manifest["mappings"] if source.match(item["pattern"]))
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    failures = schemas.validate_instance(instance, loaded[mapping["schema"]], registry)
    assert failures and "required property" in failures[0].message


def test_wrong_source_and_unknown_top_level_field_fail():
    instance = json.loads((ROOT / "stats/standard/mtgo/meta.json").read_text(encoding="utf-8"))
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    instance["source"] = "melee"
    assert schemas.validate_instance(instance, loaded["mtgo-meta.schema.json"], registry)


def test_missing_and_wrong_embedded_version_fail():
    instance = json.loads((ROOT / "stats/standard/mtgo/meta.json").read_text(encoding="utf-8"))
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    instance.pop("schema_version")
    failures = schemas.validate_instance(instance, loaded["mtgo-meta.schema.json"], registry)
    assert failures and "required property" in failures[0].message
    instance["schema_version"] = "1.0.1"
    failures = schemas.validate_instance(instance, loaded["mtgo-meta.schema.json"], registry)
    assert failures and "1.0.0" in failures[0].message
    instance["source"] = "mtgo"
    instance["unexpected"] = True
    assert schemas.validate_instance(instance, loaded["mtgo-meta.schema.json"], registry)


def test_manifest_rejects_missing_matches_and_schema(tmp_path):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    manifest = json.loads((ROOT / "schemas/manifest.json").read_text(encoding="utf-8"))
    manifest["mappings"] = [{"pattern": "missing/*.json", "schema": "mtgo-meta.schema.json"}]
    path = tmp_path / "schemas" / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SchemaError, match="matched no files"):
        schemas.validate_manifest(ROOT, path)
    manifest["mappings"] = [{"pattern": "stats/standard/mtgo/meta.json", "schema": "missing.schema.json"}]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SchemaError, match="missing schema"):
        schemas.validate_manifest(ROOT, path)


def test_cli_pass_help_usage_and_non_root_execution(tmp_path):
    script = ROOT / "validate_schemas.py"
    result = subprocess.run([sys.executable, "-B", str(script)], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0 and "PASS" in result.stdout and "checked=23" in result.stdout
    help_result = subprocess.run([sys.executable, "-B", str(script), "--help"], text=True, capture_output=True)
    assert help_result.returncode == 0 and "usage:" in help_result.stdout
    usage = subprocess.run([sys.executable, "-B", str(script), "--unknown"], text=True, capture_output=True)
    assert usage.returncode == 2 and "usage:" in usage.stderr


def test_cli_content_failure_and_infrastructure_error(tmp_path):
    root = tmp_path / "repo"
    schema_dir = root / "schemas"
    target_dir = root / "stats"
    schema_dir.mkdir(parents=True)
    target_dir.mkdir()
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://example.test/value.schema.json", "type": "object", "required": ["value"]}
    (schema_dir / "value.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    (schema_dir / "manifest.json").write_text(json.dumps({"schema_version": "1.0.0", "output_schema_version_embedded": True, "mappings": [{"pattern": "stats/value.json", "schema": "value.schema.json"}]}), encoding="utf-8")
    (target_dir / "value.json").write_text("{}", encoding="utf-8")
    script = ROOT / "validate_schemas.py"
    failed = subprocess.run([sys.executable, "-B", str(script), "--root", str(root), "--manifest", "schemas/manifest.json"], text=True, capture_output=True)
    assert failed.returncode == 1 and "FAIL" in failed.stdout and "Traceback" not in failed.stderr
    (schema_dir / "manifest.json").write_text("{", encoding="utf-8")
    error = subprocess.run([sys.executable, "-B", str(script), "--root", str(root), "--manifest", "schemas/manifest.json"], text=True, capture_output=True)
    assert error.returncode == 2 and "ERROR" in error.stdout and "Traceback" not in error.stderr


def test_validator_does_not_modify_repository():
    before = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    assert schemas.main([]) == 0
    after = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    assert after == before
