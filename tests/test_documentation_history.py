"""Minimum executable contract for live governance documents and their history."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
ROADMAP_PATH = ROOT / "docs" / "ROADMAP.md"
HISTORY_INDEX_PATH = ROOT / "docs" / "history" / "README.md"
PHASES_0_11_PATH = ROOT / "docs" / "history" / "ROADMAP-PHASES-0-11.md"
PHASE_12_PATH = ROOT / "docs" / "history" / "ROADMAP-PHASE-12-COMPLETED.md"

FORBIDDEN_STATUS_CACHES = {
    "approved_event_structures",
    "authoritative_documents",
    "delegated_local_execution_governance",
    "engineering_quality",
    "governance_baseline",
    "product_tracks",
    "publication_workflow_control",
    "recent_completion_handoff",
}


def live_status_policy_errors(status_bytes: bytes) -> list[str]:
    errors = []
    if len(status_bytes) > 10 * 1024:
        errors.append("STATUS exceeds 10 KiB")
    status = yaml.safe_load(status_bytes)
    stale_caches = FORBIDDEN_STATUS_CACHES & set(status)
    if stale_caches:
        errors.append("STATUS contains non-live caches: " + ", ".join(sorted(stale_caches)))
    status_document = status.get("status_document", {})
    if status_document.get("live_state_only") is not True:
        errors.append("live_state_only must be true")
    history_policy = status_document.get("history_policy")
    if not isinstance(history_policy, str) or not history_policy.strip():
        errors.append("history_policy must be non-empty")
    task = status.get("current_task", {})
    if not {"id", "name", "authorization", "stop_point"} <= set(task):
        errors.append("current_task is missing live contract fields")
    authorization = task.get("authorization", {})
    if set(authorization) != {
        "local_implementation",
        "commit",
        "remote_publication",
        "merge",
    } or not all(isinstance(value, bool) for value in authorization.values()):
        errors.append("current_task authorization must contain four booleans")
    return errors


def test_live_status_contract():
    assert live_status_policy_errors(STATUS_PATH.read_bytes()) == []


def test_live_roadmap_and_history_contract():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    history_index = HISTORY_INDEX_PATH.read_text(encoding="utf-8")
    phases_0_11 = PHASES_0_11_PATH.read_text(encoding="utf-8")
    phase_12 = PHASE_12_PATH.read_text(encoding="utf-8")

    assert len(roadmap.encode("utf-8")) <= 64 * 1024
    assert "# Phase 12 —" in roadmap
    assert "10. `P12-10`" in roadmap
    assert "# Phase 19 —" in roadmap
    assert "# Phase 0 —" not in roadmap
    assert "1. `P12-01`" not in roadmap
    assert "# Historical Phase" not in roadmap
    assert "ROADMAP-PHASES-0-11.md" in roadmap
    assert "ROADMAP-PHASES-0-11.md" in history_index
    assert "ROADMAP-PHASE-12-COMPLETED.md" in roadmap
    assert "ROADMAP-PHASE-12-COMPLETED.md" in history_index
    assert "# Phase 0 —" in phases_0_11 and "# Phase 11 —" in phases_0_11
    assert "1. `P12-01`" in phase_12 and "9. `P12-09`" in phase_12
    assert "non-authoritative" in phases_0_11 and "non-authoritative" in phase_12


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("oversize", "STATUS exceeds 10 KiB"),
        ("not-live", "live_state_only must be true"),
        ("empty-history", "history_policy must be non-empty"),
    ],
)
def test_live_status_contract_rejects_invalid_policy(mutation, expected):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    if mutation == "not-live":
        status["status_document"]["live_state_only"] = False
    elif mutation == "empty-history":
        status["status_document"]["history_policy"] = ""
    status_bytes = yaml.safe_dump(status).encode("utf-8")
    if mutation == "oversize":
        status_bytes += b"#" * (16 * 1024 + 1)

    assert expected in live_status_policy_errors(status_bytes)
