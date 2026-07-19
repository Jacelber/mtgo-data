"""P2-03 tests for versioned shared rule models, loading, and schema."""

from __future__ import annotations

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

from mtgmeta.config import RuleConfigError, load_rule_set, parse_rule_text
from mtgmeta.rules import RULE_SCHEMA_VERSION, validate_rule_data


FIXTURES = ROOT / "tests" / "fixtures" / "rules"
VALID_PATH = FIXTURES / "valid_shared_rules.yaml"
SCHEMA_PATH = ROOT / "schemas" / "classification-rules.schema.json"


def valid_data():
    return yaml.safe_load(VALID_PATH.read_text(encoding="utf-8"))


def failure_paths(data):
    return {failure.path for failure in validate_rule_data(data)}


def test_valid_fixture_builds_immutable_models_and_preserves_equal_priorities():
    rule_set = load_rule_set(VALID_PATH)
    assert rule_set.schema_version == RULE_SCHEMA_VERSION
    assert rule_set.format == "standard"
    assert [item.id for item in rule_set.archetypes] == ["example-control", "example-aggro"]
    control = rule_set.archetypes[0]
    assert control.subtypes[0].parent_archetype_id == control.id
    assert [rule.priority for rule in control.rules] == [100, 100]
    assert control.rules[0].subtype_id == "artifact-build"
    bounded = control.rules[0].conditions[0]
    assert (bounded.zone, bounded.min_count, bounded.max_count, bounded.exact_count) == ("main", 2, 4, None)
    defaulted = rule_set.archetypes[1].rules[0].conditions[0]
    assert (defaulted.zone, defaulted.min_count) == ("any", 1)


def test_json_schema_accepts_fixture_and_rejects_shape_errors():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(valid_data())) == []
    bad = valid_data(); bad["unexpected"] = True
    assert list(validator.iter_errors(bad))
    bad = valid_data(); bad["archetypes"][0]["rules"][0]["conditions"]["all"][0]["exact_count"] = 3
    assert list(validator.iter_errors(bad))


def test_duplicate_yaml_keys_and_unknown_subtype_raise_stable_config_errors():
    with pytest.raises(RuleConfigError) as duplicate:
        parse_rule_text('schema_version: "1.0.0"\nformat: standard\nformat: modern\narchetypes: []\n')
    assert duplicate.value.failures[0].path == "YAML"
    with pytest.raises(RuleConfigError) as unknown:
        load_rule_set(FIXTURES / "invalid_unknown_subtype.yaml")
    assert unknown.value.failures[0].path == "archetypes[0].rules[0].subtype_id"
    assert "unknown subtype" in unknown.value.failures[0].message


@pytest.mark.parametrize(
    ("mutation", "expected_path"),
    [
        (lambda d: d.update(schema_version="2.0.0"), "schema_version"),
        (lambda d: d.update(format="Standard"), "format"),
        (lambda d: d["archetypes"][0].update(id="Bad_ID"), "archetypes[0].id"),
        (lambda d: d["archetypes"][0].update(priority=True), "archetypes[0].priority"),
        (lambda d: d["archetypes"][0]["rules"][0].update(priority="100"), "archetypes[0].rules[0].priority"),
        (lambda d: d["archetypes"][0]["rules"][0]["conditions"]["all"][0].update(zone="deck"), "archetypes[0].rules[0].conditions.all[0].zone"),
    ],
)
def test_scalar_and_identifier_failures_are_located(mutation, expected_path):
    data = valid_data(); mutation(data)
    assert expected_path in failure_paths(data)


def test_duplicate_ids_unknown_fields_empty_rules_and_bad_ranges_fail_semantically():
    data = valid_data()
    duplicate = dict(data["archetypes"][0]); duplicate["name"] = "Duplicate"
    data["archetypes"].append(duplicate)
    paths = failure_paths(data)
    assert "archetypes[2].id" in paths
    assert "archetypes[2].rules[0].id" in paths

    data = valid_data(); data["archetypes"][0]["subtypes"].append({"id": "artifact-build", "name": "Again"})
    assert "archetypes[0].subtypes[1].id" in failure_paths(data)
    data = valid_data(); data["archetypes"][0]["rules"] = []
    assert "archetypes[0].rules" in failure_paths(data)
    data = valid_data(); condition = data["archetypes"][0]["rules"][0]["conditions"]["all"][0]; condition.update(min_count=5, max_count=2)
    assert "archetypes[0].rules[0].conditions.all[0]" in failure_paths(data)
    data = valid_data(); data["archetypes"][0]["surprise"] = 1
    assert "archetypes[0].surprise" in failure_paths(data)
    data = valid_data(); data["archetypes"][0]["subtypes"].append({"id": "unused-build", "name": "Unused Build"})
    assert "archetypes[0].subtypes[1].id" in failure_paths(data)


def test_exact_count_is_mutually_exclusive_and_boolean_counts_are_invalid():
    data = valid_data(); condition = data["archetypes"][0]["rules"][0]["conditions"]["all"][0]; condition["exact_count"] = 3
    assert "archetypes[0].rules[0].conditions.all[0]" in failure_paths(data)
    data = valid_data(); data["archetypes"][1]["rules"][0]["conditions"]["all"][0]["min_count"] = False
    assert "archetypes[1].rules[0].conditions.all[0].min_count" in failure_paths(data)


def test_missing_and_unreadable_files_raise_config_errors(monkeypatch, tmp_path):
    with pytest.raises(RuleConfigError):
        load_rule_set(tmp_path / "missing.yaml")
    monkeypatch.setattr(Path, "read_text", lambda self, **_: (_ for _ in ()).throw(PermissionError("denied")))
    with pytest.raises(RuleConfigError):
        load_rule_set("denied.yaml")
