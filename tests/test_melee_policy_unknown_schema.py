"""The no-sideboard data policy does not pretend color analysis ran."""
from copy import deepcopy
from pathlib import Path

from mtgmeta.classifier import classify_deck
from mtgmeta.config import parse_rule_text
from mtgmeta.melee.classification import _classification_record
from validate_schemas import load_schemas, validate_instance

ROOT = Path(__file__).resolve().parents[1]


def test_no_sideboard_unknown_is_valid_without_inventing_color_diagnostics():
    rules = parse_rule_text('''schema_version: 1.0.0
format: standard
archetypes:
- id: fixture
  name: Fixture
  priority: 1
  rules:
  - id: fixture-rule
    priority: 1
    subtype_id: null
    conditions:
      all: [{card: Island, zone: main, min_count: 1}]
''')
    deck = {"main_deck": [{"name": "Island", "qty": 60}], "sideboard": []}
    result = classify_deck(rules, deck)
    assert result.status == "unknown" and result.errors == ('deck_data:60_main_without_sideboard',)
    record = _classification_record("participant-fixture", result, deck)
    schemas, registry = load_schemas(ROOT / "schemas", {"melee-classification.schema.json"})
    schema = schemas['melee-classification.schema.json']
    record_schema = {"$ref": schema['$id'] + schema['properties']['records']['items']['$ref']}
    assert not validate_instance(record, record_schema, registry)
    assert "color_diagnostics" not in record
    for errors in (["fixture: unresolved colors: blue"],
                   ["deck_data:60_main_without_sideboard", "fixture: missing card facts: X"]):
        changed = deepcopy(record)
        changed['errors'] = errors
        failures = validate_instance(changed, record_schema, registry)
        assert any("'color_diagnostics' is a required property" in f.message for f in failures)
