from __future__ import annotations

from copy import deepcopy
import json

import pytest

from tools.validate_p12_10_readiness import (
    DEFAULT_CONTRACT,
    ROOT,
    ReadinessValidationError,
    validate,
    validate_known_state,
)


def _contract() -> dict[str, object]:
    value = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_readiness_contract_validates_without_recomputing_shadow() -> None:
    result = validate()

    assert result["status"] == "valid"
    assert result["thresholds_recomputed"] is False
    assert result["known_state"] == {
        "standard": {
            "count": 91,
            "sha256": "8ee830827a1d554dc19b6b7e979ded056d0fb414fbf447fbb44619e917a3d006",
            "all_identities_resolve": True,
            "matches_accepted_r5_evidence": True,
        },
        "modern": {
            "count": 126,
            "sha256": "c589e26718fbac12bc164dd04dfc6dcb68c4a901df59ea1bf13242493a711235",
            "all_identities_resolve": True,
            "matches_accepted_r5_evidence": True,
        },
    }


def test_owner_approved_threshold_evidence_is_frozen() -> None:
    approval = _contract()["threshold_approval"]
    assert approval == {
        "source": "owner_provided_refreshed_shadow_summary",
        "accepted_on": "2026-08-15",
        "recomputed_by_task": False,
        "environment": {
            "threshold": 0.03,
            "standard": {"median_rows": 8, "coverage_percent": 88.04},
            "modern": {"median_rows": 11.5, "coverage_percent": 66.99},
        },
        "share_move": {
            "threshold_percentage_points": 5,
            "standard": {"weekly_min": 1, "weekly_max": 6},
            "modern": {"weekly_max": 2, "empty_weeks": 8},
        },
        "build_shift": {
            "threshold": 20,
            "standard": {"window_weeks": 12, "items": 1},
            "modern": {"weekly_min": 2, "weekly_max": 7, "median": 4.5},
            "comparison_at_15": {
                "modern_weekly_min": 3,
                "modern_weekly_max": 10,
            },
        },
    }


def test_known_state_mismatch_fails_closed_without_migration() -> None:
    contract = deepcopy(_contract())
    contract["known_state"]["formats"]["standard"]["sha256"] = "0" * 64

    with pytest.raises(ReadinessValidationError, match="digest changed"):
        validate_known_state(ROOT, contract)


def test_workbook_writeback_separates_machine_and_owner_fields() -> None:
    workbook = _contract()["workbook_writeback"]
    machine = set(workbook["machine_bound_columns"])
    editable = set(workbook["owner_editable_columns"])

    assert machine.isdisjoint(editable)
    assert workbook["structural_edit_action"] == "reject_without_write"
    assert workbook["binding_mismatch_action"] == "reject_without_write"
    assert workbook["repository_committed"] is False
