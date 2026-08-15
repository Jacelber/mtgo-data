"""Validate the frozen P12-10 Pickup readiness contract without changing data."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    ROOT
    / "docs"
    / "audits"
    / "p12-10-readiness"
    / "pickup_review_contract.json"
)
R5_SUMMARY = (
    ROOT
    / "docs"
    / "audits"
    / "classifier-r5"
    / "production_promotion_summary.json"
)


class ReadinessValidationError(ValueError):
    """Raised when a readiness binding no longer matches the repository."""


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
        else:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ReadinessValidationError(f"{path}: cannot load mapping") from exc
    if not isinstance(value, dict):
        raise ReadinessValidationError(f"{path}: expected an object")
    return value


def _relative_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ReadinessValidationError(f"{field}: expected a repository path")
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ReadinessValidationError(f"{field}: path escapes repository") from exc
    return path


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ReadinessValidationError(f"{field}: expected non-empty strings")
    if len(value) != len(set(value)):
        raise ReadinessValidationError(f"{field}: duplicate entries")
    return value


def _validate_threshold_approval(contract: Mapping[str, Any]) -> None:
    approval = contract.get("threshold_approval")
    if not isinstance(approval, Mapping):
        raise ReadinessValidationError("threshold_approval: expected an object")
    expected = {
        "source": "owner_provided_refreshed_shadow_summary",
        "accepted_on": "2026-08-15",
        "recomputed_by_task": False,
    }
    for field, value in expected.items():
        if approval.get(field) != value:
            raise ReadinessValidationError(
                f"threshold_approval.{field}: expected {value!r}"
            )
    environment = approval.get("environment")
    movement = approval.get("share_move")
    build_shift = approval.get("build_shift")
    if not all(isinstance(item, Mapping) for item in (environment, movement, build_shift)):
        raise ReadinessValidationError("threshold_approval: missing threshold evidence")
    if environment.get("threshold") != 0.03:
        raise ReadinessValidationError("environment threshold must remain 0.03")
    if movement.get("threshold_percentage_points") != 5:
        raise ReadinessValidationError("share_move threshold must remain 5pp")
    if build_shift.get("threshold") != 20:
        raise ReadinessValidationError("build_shift threshold must remain 20")


def _parent_identities(rules_path: Path, representation: object) -> set[str]:
    rules = _load_mapping(rules_path)
    archetypes = rules.get("archetypes")
    if not isinstance(archetypes, list):
        raise ReadinessValidationError(f"{rules_path}: missing archetypes")
    key = "id" if representation == "parent_id" else "name"
    values = {
        item.get(key)
        for item in archetypes
        if isinstance(item, Mapping) and isinstance(item.get(key), str)
    }
    if len(values) != len(archetypes):
        raise ReadinessValidationError(
            f"{rules_path}: duplicate or invalid parent {key}"
        )
    return values


def validate_known_state(
    root: Path, contract: Mapping[str, Any]
) -> dict[str, dict[str, object]]:
    known_contract = contract.get("known_state")
    if not isinstance(known_contract, Mapping):
        raise ReadinessValidationError("known_state: expected an object")
    if known_contract.get("mismatch_action") != "stop_without_migration":
        raise ReadinessValidationError("known_state must fail closed without migration")
    formats = known_contract.get("formats")
    if not isinstance(formats, Mapping) or set(formats) != {"standard", "modern"}:
        raise ReadinessValidationError("known_state.formats must cover Standard and Modern")

    r5 = _load_mapping(root / R5_SUMMARY.relative_to(ROOT))
    r5_states = r5.get("pickup_known_state")
    if not isinstance(r5_states, Mapping):
        raise ReadinessValidationError("R5 summary lacks Pickup known-state evidence")

    result: dict[str, dict[str, object]] = {}
    for format_id in ("standard", "modern"):
        item = formats.get(format_id)
        if not isinstance(item, Mapping):
            raise ReadinessValidationError(f"known_state.{format_id}: expected an object")
        state_path = _relative_path(root, item.get("path"), f"{format_id}.path")
        rules_path = _relative_path(
            root, item.get("rules_path"), f"{format_id}.rules_path"
        )
        digest = sha256(state_path.read_bytes()).hexdigest()
        expected_digest = item.get("sha256")
        if digest != expected_digest:
            raise ReadinessValidationError(f"{format_id} known-state digest changed")

        document = _load_mapping(state_path)
        identity_key = item.get("identity_key")
        if set(document) != {identity_key}:
            raise ReadinessValidationError(
                f"{format_id} known state has unexpected fields"
            )
        identities = _string_list(document.get(identity_key), f"{format_id}.{identity_key}")
        if identities != sorted(identities):
            raise ReadinessValidationError(f"{format_id} known state is not sorted")
        if len(identities) != item.get("expected_count"):
            raise ReadinessValidationError(f"{format_id} known-state count changed")

        r5_item = r5_states.get(format_id)
        if not isinstance(r5_item, Mapping):
            raise ReadinessValidationError(f"R5 summary lacks {format_id} state")
        if r5_item.get("sha256") != digest or r5_item.get("after") != len(identities):
            raise ReadinessValidationError(
                f"{format_id} known state no longer matches accepted R5 evidence"
            )

        parents = _parent_identities(rules_path, item.get("identity_representation"))
        missing = sorted(set(identities) - parents)
        if missing:
            raise ReadinessValidationError(
                f"{format_id} known state references absent parents: {missing}"
            )
        result[format_id] = {
            "count": len(identities),
            "sha256": digest,
            "all_identities_resolve": True,
            "matches_accepted_r5_evidence": True,
        }
    return result


def _validate_review_contract(contract: Mapping[str, Any]) -> None:
    candidate = contract.get("pickup_candidate_extension")
    manifest = contract.get("review_manifest")
    workbook = contract.get("workbook_writeback")
    if not all(isinstance(item, Mapping) for item in (candidate, manifest, workbook)):
        raise ReadinessValidationError("review contract sections must be objects")
    if candidate.get("parallel_root_candidate_configuration") is not False:
        raise ReadinessValidationError("parallel candidate configuration is prohibited")
    if candidate.get("category_by_collection") != {
        "existing_changes": "new_technology",
        "new_archetypes": "new_deck",
    }:
        raise ReadinessValidationError("Pickup category mapping changed")
    landing = candidate.get("landing_object")
    if not isinstance(landing, Mapping) or landing.get("featured_card_count") != 4:
        raise ReadinessValidationError("Landing review must select exactly four cards")

    manifest_fields = set(
        _string_list(manifest.get("required_fields"), "review_manifest.required_fields")
    )
    required_bindings = {
        "master_sha",
        "source_event_ids",
        "classifier_digest",
        "pickup_candidate_digest",
        "known_state_digest",
        "visual_metadata_digest",
        "machine_fact_digest",
        "workbook_baseline_digest",
    }
    if not required_bindings <= manifest_fields:
        raise ReadinessValidationError("review manifest is missing immutable bindings")

    machine = set(
        _string_list(
            workbook.get("machine_bound_columns"),
            "workbook_writeback.machine_bound_columns",
        )
    )
    editable = set(
        _string_list(
            workbook.get("owner_editable_columns"),
            "workbook_writeback.owner_editable_columns",
        )
    )
    if machine & editable:
        raise ReadinessValidationError("workbook machine and editable columns overlap")
    required_editable = {
        "approved",
        "landing_order",
        "headline_zh",
        "headline_en",
        "positioning_zh",
        "positioning_en",
        "featured_card_1",
        "featured_card_2",
        "featured_card_3",
        "featured_card_4",
    }
    if not required_editable <= editable:
        raise ReadinessValidationError("workbook omits required Owner fields")
    if workbook.get("structural_edit_action") != "reject_without_write":
        raise ReadinessValidationError("workbook structural edits must fail closed")


def validate(
    repository_root: Path = ROOT, contract_path: Path = DEFAULT_CONTRACT
) -> dict[str, object]:
    root = repository_root.resolve()
    contract = _load_mapping(contract_path)
    if contract.get("task_id") != "P12-10-READINESS-PICKUP-CONTRACT":
        raise ReadinessValidationError("unexpected readiness task ID")
    if contract.get("artifact_impact") != "internal_diagnostics":
        raise ReadinessValidationError("readiness contract must remain internal")
    _validate_threshold_approval(contract)
    known_state = validate_known_state(root, contract)
    _validate_review_contract(contract)
    if contract.get("remaining_gates") != [
        "one_no_publication_tuesday_rehearsal",
        "separate_p12_10_implementation_authorization",
    ]:
        raise ReadinessValidationError("remaining P12-10 gates changed")
    return {
        "status": "valid",
        "thresholds_recomputed": False,
        "known_state": known_state,
        "review_contract": "valid",
        "remaining_gates": contract["remaining_gates"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.repository_root, args.contract),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
