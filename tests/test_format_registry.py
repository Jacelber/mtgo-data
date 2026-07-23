"""P3-02 tests for the MTGO format registry and safe path resolution."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import (
    DisabledFormatError,
    FormatConfigError,
    UnknownFormatError,
    load_format_registry,
    parse_format_text,
    resolve_repository_path,
)


REGISTRY_PATH = ROOT / "configs" / "formats.yaml"
SCHEMA_PATH = ROOT / "schemas" / "formats.schema.json"
CONTRACT_PATH = ROOT / "tests" / "fixtures" / "mtgo" / "format_pipeline_contract.json"


def registry_data():
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


def registry():
    return load_format_registry(REGISTRY_PATH)


def test_registry_preserves_the_p3_standard_contract_and_enables_modern_range_statistics():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    loaded = registry()

    assert loaded.schema_version == "1.1.0"
    assert [item.id for item in loaded.formats] == contract["format_state_model"]["known_format_ids"]
    assert [item.id for item in loaded.formats if item.state == "executable"] == [
        "standard",
        "modern",
    ]

    standard = loaded.require_mtgo("standard")
    assert standard.public is True
    assert standard.mtgo.capabilities == set(contract["required_capabilities"])
    assert standard.mtgo.paths.resolve(ROOT) == {
        key: ROOT / value
        for key, value in contract["standard_contract"]["paths"].items()
        if key in {"events", "matches", "rules", "statistics", "reports"}
    }
    assert [
        item.id for item in loaded.formats if item.mtgo.event_collection_enabled
    ] == ["standard", "pauper", "modern", "pioneer", "legacy", "vintage"]
    assert all(
        loaded.require_mtgo_event_collection(format_id).id == format_id
        for format_id in ("standard", "pauper", "modern", "pioneer", "legacy", "vintage")
    )
    modern = loaded.require_mtgo("modern")
    assert modern.public is False
    assert modern.mtgo.capabilities == {
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
    }


def test_known_disabled_and_unknown_formats_fail_without_a_standard_fallback():
    loaded = registry()
    for format_id in ("pauper", "pioneer", "legacy"):
        with pytest.raises(DisabledFormatError, match="not enabled"):
            loaded.require_mtgo(format_id)
    with pytest.raises(DisabledFormatError, match="decision-gated"):
        loaded.require_mtgo("vintage")
    with pytest.raises(UnknownFormatError, match="unknown format"):
        loaded.require_mtgo("alchemy")
    with pytest.raises(TypeError):
        loaded.require_mtgo()  # type: ignore[call-arg]
    assert loaded.require_mtgo("modern").id == "modern"


def test_schema_accepts_the_registry_and_rejects_extra_or_unsafe_shape_fields():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(registry_data())) == []

    invalid = copy.deepcopy(registry_data())
    invalid["formats"][0]["mtgo"]["paths"]["events"] = "../outside"
    assert list(validator.iter_errors(invalid))
    invalid = copy.deepcopy(registry_data())
    invalid["formats"][0]["unexpected"] = True
    assert list(validator.iter_errors(invalid))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda data: data["formats"][1].update(id="standard"), "duplicates"),
        (lambda data: data["formats"][0]["mtgo"].update(enabled=False), "must match executable state"),
        (lambda data: data["formats"][1]["mtgo"].update(capabilities=["classification"]), "must be empty"),
        (lambda data: data["formats"][1]["mtgo"].update(event_collection_enabled="yes"), "must be a boolean"),
        (lambda data: data["formats"][0]["mtgo"]["paths"].update(events="data\\standard"), "forward slashes"),
        (lambda data: data["formats"][0]["mtgo"]["paths"].update(events="data/../standard"), "safe repository-relative"),
        (lambda data: data["formats"][0]["mtgo"]["paths"].update(events="data/pauper"), "format-specific"),
    ],
)
def test_loader_rejects_semantically_unsafe_registry_entries(mutation, expected):
    data = registry_data()
    mutation(data)
    with pytest.raises(FormatConfigError, match=expected):
        parse_format_text(yaml.safe_dump(data, sort_keys=False))


def test_duplicate_yaml_keys_and_repository_escapes_fail_clearly(tmp_path):
    duplicate = REGISTRY_PATH.read_text(encoding="utf-8").replace(
        'schema_version: "1.1.0"', 'schema_version: "1.1.0"\nschema_version: "1.1.0"', 1
    )
    with pytest.raises(FormatConfigError, match="duplicate key"):
        parse_format_text(duplicate)
    with pytest.raises(FormatConfigError, match="safe repository-relative"):
        resolve_repository_path(tmp_path, "../outside")
    with pytest.raises(FormatConfigError, match="safe repository-relative"):
        resolve_repository_path(tmp_path, "C:/outside")
    assert resolve_repository_path(tmp_path, "data/standard") == tmp_path / "data" / "standard"
