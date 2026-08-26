"""Minimum executable contract for live governance documents and their history."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
ROADMAP_PATH = ROOT / "docs" / "ROADMAP.md"

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


def test_live_roadmap_history_pointers_exist():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    pointers = set(re.findall(r"`(docs/history/[^`]+)`", roadmap))

    assert pointers
    assert all((ROOT / pointer).is_file() for pointer in pointers)


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
