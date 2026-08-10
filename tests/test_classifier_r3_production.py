from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_features import (
    EQUIPMENT_MARKER,
    SemanticFeatureError,
    augment_semantic_counts,
    load_semantic_feature_manifest,
    mana_source_marker,
)
from mtgmeta.classifier_shadow import (
    classify_shadow_counts,
    load_shadow_feature_manifest,
)
from mtgmeta.classifier_shadow_audit import (
    _record_counts,
    diagnostic_flags,
    identity_signature,
    load_frozen_records,
    reordered_rule_set,
)
from mtgmeta.config import RuleConfigError, load_rule_set
from mtgmeta.melee.classification import build_classification_overlay_from_paths
from tools.build_classifier_r3_production_rules import build_production_rules


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "docs" / "audits" / "classifier-r2"
PRODUCTION_MANIFEST_PATH = ROOT / "configs" / "classifier_semantic_features.yaml"
PRODUCTION_MANIFEST = load_semantic_feature_manifest(PRODUCTION_MANIFEST_PATH)
SHADOW_MANIFEST = load_shadow_feature_manifest(
    AUDIT_ROOT / "semantic_card_features.yaml"
)
EXPECTED = {
    "modern": {
        "records": 5792,
        "classified": 5650,
        "unknown": 142,
        "parents": 70,
        "subtypes": 54,
        "rules": 119,
    },
    "standard": {
        "records": 3936,
        "classified": 3868,
        "unknown": 68,
        "parents": 72,
        "subtypes": 11,
        "rules": 82,
    },
}


def _corpus_path(format_id: str) -> Path:
    if format_id == "modern":
        return ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json"
    return ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"


@pytest.mark.parametrize("format_id", ["modern", "standard"])
def test_production_rules_are_the_accepted_r2_rules(format_id: str) -> None:
    rule_path = ROOT / "my_archetypes" / f"{format_id}.yaml"
    document = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
    assert document == build_production_rules(format_id)
    assert document["schema_version"] == "1.1.0"
    assert document["semantic_features"] == {
        "manifest_path": "configs/classifier_semantic_features.yaml",
        "manifest_sha256": sha256(PRODUCTION_MANIFEST_PATH.read_bytes()).hexdigest(),
    }
    rules = load_rule_set(rule_path)
    assert rules.semantic_features == PRODUCTION_MANIFEST
    assert (
        len(rules.archetypes),
        sum(len(item.subtypes) for item in rules.archetypes),
        sum(len(item.rules) for item in rules.archetypes),
    ) == (
        EXPECTED[format_id]["parents"],
        EXPECTED[format_id]["subtypes"],
        EXPECTED[format_id]["rules"],
    )


@pytest.mark.parametrize("format_id", ["modern", "standard"])
def test_production_matches_shadow_for_every_frozen_record(format_id: str) -> None:
    production = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
    reordered = reordered_rule_set(production)
    shadow = load_rule_set(AUDIT_ROOT / "shadow_rules" / f"{format_id}.yaml")
    statuses: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    records = load_frozen_records(_corpus_path(format_id))

    for record in records:
        main, side = _record_counts(record)
        actual = classify_counts(production, main, side)
        expected = classify_shadow_counts(shadow, main, side, SHADOW_MANIFEST)
        assert identity_signature(actual) == identity_signature(expected)
        assert identity_signature(actual) == identity_signature(
            classify_counts(reordered, main, side)
        )
        statuses[actual.status] += 1
        flags.update(
            name
            for name, enabled in diagnostic_flags(actual, production).items()
            if enabled
        )

    expected = EXPECTED[format_id]
    assert len(records) == expected["records"]
    assert statuses == Counter(
        classified=expected["classified"],
        unknown=expected["unknown"],
    )
    assert flags["conflict"] == 0
    assert flags["invalid_deck"] == 0
    assert flags["residual_subtype"] == 0


def test_production_manifest_is_schema_valid_explicit_and_fail_closed() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "classifier-semantic-features.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    document = yaml.safe_load(PRODUCTION_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(document)) == []

    main = {"Plains": 2, "Batterskull": 1, "Unreviewed Red Land": 4}
    augmented, _ = augment_semantic_counts(main, {}, PRODUCTION_MANIFEST)
    assert augmented[mana_source_marker("white")] == 2
    assert augmented[EQUIPMENT_MARKER] == 1
    assert mana_source_marker("red") not in augmented
    with pytest.raises(SemanticFeatureError, match="reserved"):
        augment_semantic_counts({mana_source_marker("white"): 1}, {}, PRODUCTION_MANIFEST)


def test_manifest_digest_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    rules = root / "my_archetypes" / "modern.yaml"
    manifest = root / "configs" / "classifier_semantic_features.yaml"
    rules.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    rules.write_bytes((ROOT / "my_archetypes" / "modern.yaml").read_bytes())
    manifest.write_bytes(PRODUCTION_MANIFEST_PATH.read_bytes() + b"\n")
    with pytest.raises(RuleConfigError, match="manifest_sha256"):
        load_rule_set(rules)


def test_event_434455_uses_production_rules_without_changing_source() -> None:
    event_path = ROOT / "data" / "modern" / "melee" / "events" / "434455.json"
    before = sha256(event_path.read_bytes()).hexdigest()
    overlay = build_classification_overlay_from_paths(
        event_path,
        ROOT / "my_archetypes" / "modern.yaml",
        ROOT,
    )
    assert overlay["summary"]["total_records"] == 362
    assert overlay["summary"]["classified"] == 351
    assert overlay["summary"]["unknown"] == 11
    assert overlay["summary"]["multiple_matches"] == 64
    assert overlay["summary"]["conflicts"] == 0
    assert overlay["summary"]["residual_subtype_violations"] == 0
    assert sha256(event_path.read_bytes()).hexdigest() == before
