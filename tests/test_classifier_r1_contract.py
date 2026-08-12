from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "docs" / "audits" / "classifier-r1"
IDENTITY_PATH = CONTRACT_ROOT / "identity_dictionary.yaml"
TRANSITION_PATH = CONTRACT_ROOT / "transition_map.yaml"
VALIDATION_PATH = CONTRACT_ROOT / "validation_matrix.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"{path} must contain one mapping"
    return document


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _rules(format_id: str) -> dict[str, Any]:
    return _load_yaml(
        ROOT
        / "docs"
        / "audits"
        / "classifier-r2"
        / "baseline_rules"
        / f"{format_id}.yaml"
    )


def _parent_ids(rule_document: dict[str, Any]) -> set[str]:
    return {parent["id"] for parent in rule_document["archetypes"]}


def _target_projection(
    identity: dict[str, Any], format_id: str
) -> dict[str, tuple[str, ...]]:
    projection = {
        parent["id"]: tuple(subtype["id"] for subtype in parent.get("subtypes", []))
        for parent in _rules(format_id)["archetypes"]
    }
    for overlay in identity["target_overlays"][format_id]:
        for retired_id in overlay["retire_parent_ids"]:
            projection.pop(retired_id)
        for target in overlay["targets"]:
            assert "subtypes" in target, (
                f"{format_id}/{target['id']} must explicitly declare its target subtypes"
            )
            projection[target["id"]] = tuple(target["subtypes"])
    return projection


def _parent_part(identity: str) -> str:
    return identity.split("/", maxsplit=1)[0]


def test_r1_contract_uses_the_exact_reviewed_rule_baseline() -> None:
    identity = _load_yaml(IDENTITY_PATH)

    assert identity["schema_version"] == "1.0.0"
    assert identity["status"] == "owner_reviewed_target_contract_not_production"
    assert identity["artifact_impact"] == "internal_diagnostics"

    for format_id in ("modern", "standard"):
        source = identity["base"]["rule_sources"][format_id]
        source_path = ROOT / source["frozen_path"]
        rules = _rules(format_id)
        assert _sha256(source_path) == source["sha256"]
        assert len(rules["archetypes"]) == source["parent_count"]
        assert sum(len(parent.get("subtypes", [])) for parent in rules["archetypes"]) == source[
            "subtype_count"
        ]
        assert sum(len(parent["rules"]) for parent in rules["archetypes"]) == source[
            "rule_count"
        ]


def test_all_129_owner_review_rows_are_represented_once() -> None:
    identity = _load_yaml(IDENTITY_PATH)
    inventory = identity["review_inventory"]

    accepted = inventory["accepted_current"]
    modified = inventory["needs_modification"]
    resolved = inventory["previously_unreviewed_resolved"]

    assert sum(len(values) for values in accepted.values()) == 104
    assert sum(len(values) for values in modified.values()) == 24
    assert sum(len(values) for values in resolved.values()) == 1

    for format_id in ("modern", "standard"):
        reviewed = accepted[format_id] + modified[format_id] + resolved.get(format_id, [])
        assert len(reviewed) == len(set(reviewed))
        assert set(reviewed) == _parent_ids(_rules(format_id))

        dependent = {
            item["parent_id"]
            for item in inventory["dependent_amendments_to_accepted_current"][format_id]
        }
        assert dependent <= set(accepted[format_id])

    assert inventory["unresolved_owner_decisions"] == 0
    assert inventory["total_parent_rows"] == 129


def test_target_projection_has_unique_ids_and_declared_counts() -> None:
    identity = _load_yaml(IDENTITY_PATH)

    for format_id in ("modern", "standard"):
        overlays = identity["target_overlays"][format_id]
        family_ids = [overlay["family"] for overlay in overlays]
        assert len(family_ids) == len(set(family_ids))

        target_ids = [
            target["id"] for overlay in overlays for target in overlay["targets"]
        ]
        assert len(target_ids) == len(set(target_ids))

        projection = _target_projection(identity, format_id)
        expected = identity["target_summary"][format_id]
        assert len(projection) == expected["parent_count"]
        assert sum(len(subtypes) for subtypes in projection.values()) == expected[
            "subtype_count"
        ]

        for parent_id, subtypes in projection.items():
            assert parent_id == parent_id.lower()
            assert parent_id.isascii()
            assert len(subtypes) == len(set(subtypes))
            for subtype_id in subtypes:
                assert subtype_id == subtype_id.lower()
                assert subtype_id.isascii()


def test_every_retired_parent_has_a_valid_transition() -> None:
    identity = _load_yaml(IDENTITY_PATH)
    transitions = _load_yaml(TRANSITION_PATH)

    for format_id in ("modern", "standard"):
        baseline_ids = _parent_ids(_rules(format_id))
        projection = _target_projection(identity, format_id)
        entries = transitions["parent_transitions"][format_id]
        transition_sources = {entry["source"] for entry in entries}

        assert len(entries) == len(transition_sources)
        assert transition_sources <= baseline_ids

        retired = {
            retired_id
            for overlay in identity["target_overlays"][format_id]
            for retired_id in overlay["retire_parent_ids"]
        }
        assert retired <= transition_sources

        for entry in entries:
            assert entry["targets"]
            for target in entry["targets"]:
                assert _parent_part(target) in projection


def test_pickup_plan_matches_the_exact_known_state_sources() -> None:
    transitions = _load_yaml(TRANSITION_PATH)
    sources = transitions["base"]["pickup_known_state"]

    modern_path = ROOT / sources["modern"]["frozen_path"]
    standard_path = ROOT / sources["standard"]["frozen_path"]
    modern_known = set(json.loads(modern_path.read_text(encoding="utf-8"))["known_ids"])
    standard_known = set(json.loads(standard_path.read_text(encoding="utf-8"))["known"])

    assert _sha256(modern_path) == sources["modern"]["sha256"]
    assert _sha256(standard_path) == sources["standard"]["sha256"]
    assert len(modern_known) == sources["modern"]["entry_count"]
    assert len(standard_known) == sources["standard"]["entry_count"]

    plan = transitions["pickup_target_plan"]
    modern_remove = set(plan["modern"]["known_parent_ids_remove"])
    modern_add = set(plan["modern"]["known_parent_ids_add"])
    assert modern_remove <= modern_known
    assert not modern_add & modern_known
    migrated_modern = modern_known - modern_remove | modern_add
    assert not modern_remove & migrated_modern
    assert modern_add <= migrated_modern

    standard_remove = set(plan["standard"]["known_display_names_remove"])
    standard_add = set(plan["standard"]["known_display_names_add"])
    assert standard_remove <= standard_known
    assert not standard_add & standard_known
    migrated_standard = standard_known - standard_remove | standard_add
    assert not standard_remove & migrated_standard
    assert standard_add <= migrated_standard


def test_validation_matrix_covers_every_target_overlay_family() -> None:
    identity = _load_yaml(IDENTITY_PATH)
    validation = _load_yaml(VALIDATION_PATH)

    assert validation["status"] == "specified_for_r2_not_executed"
    assert {gate["id"] for gate in validation["global_gates"]} == {
        f"G{number:02d}" for number in range(1, 11)
    }

    for format_id in ("modern", "standard"):
        overlay_families = {
            overlay["family"] for overlay in identity["target_overlays"][format_id]
        }
        matrix_families = {
            entry["family"] for entry in validation["family_matrix"][format_id]
        }
        assert matrix_families == overlay_families


def test_r1_contract_keeps_its_reviewed_inputs_frozen() -> None:
    identity = _load_yaml(IDENTITY_PATH)
    transitions = _load_yaml(TRANSITION_PATH)
    validation = _load_yaml(VALIDATION_PATH)

    assert identity["inheritance_policy"]["numeric_priority_status"] == (
        "deferred_to_r2_complete_shadow"
    )
    assert transitions["status"] == "migration_plan_not_applied"
    assert validation["status"] == "specified_for_r2_not_executed"
    for format_id in ("modern", "standard"):
        source = identity["base"]["rule_sources"][format_id]
        assert _sha256(ROOT / source["frozen_path"]) == source["sha256"]
