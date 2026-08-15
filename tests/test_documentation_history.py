"""Minimum executable contract for the live status document."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"


def live_status_policy_errors(status_bytes: bytes) -> list[str]:
    errors = []
    if len(status_bytes) > 16 * 1024:
        errors.append("STATUS exceeds 16 KiB")
    status = yaml.safe_load(status_bytes)
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


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("oversize", "STATUS exceeds 16 KiB"),
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
