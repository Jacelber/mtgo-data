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

COMPLETION_ACTION_COMMANDS = {
    "commit": {"commit", "commit this task", "commit the current task"},
    "remote_publication": {
        "push",
        "push this branch",
        "push the current branch",
        "create a pull request",
        "publish",
        "publish this task",
        "publish the current task",
    },
    "merge": {"merge", "merge this task", "merge the current task"},
}


def _prohibited_completion_actions(status: dict) -> set[str]:
    task = status.get("current_task", {})
    prohibitions = task.get("prohibited_changes", []) + status.get(
        "prohibited_next_actions", []
    )
    commands = set()
    for prohibition in prohibitions:
        if not isinstance(prohibition, str):
            continue
        normalized = " ".join(prohibition.lower().split())
        if not normalized.startswith("do not "):
            continue
        commands.update(
            command.strip(" .")
            for command in re.split(r",|\band\b|\bor\b", normalized[7:])
            if command.strip(" .")
        )
    return {
        action
        for action, action_commands in COMPLETION_ACTION_COMMANDS.items()
        if commands & action_commands
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
    completion_actions = ("commit", "remote_publication", "merge")
    owner_acceptance = task.get("owner_acceptance", {})
    if owner_acceptance.get("status") == "accepted" and not all(
        authorization.get(action) is True for action in completion_actions
    ):
        errors.append(
            "accepted current_task must authorize commit, remote_publication, and merge"
        )
    prohibited_completion_actions = _prohibited_completion_actions(status)
    for action in completion_actions:
        if authorization.get(action) is True and action in prohibited_completion_actions:
            errors.append(
                f"authorized current_task {action} conflicts with a prohibited action"
            )
    next_task = status.get("next_approved_task", {})
    if next_task.get("id") == task.get("id"):
        next_authorization_keys = {
            "commit": "commit_authorized",
            "remote_publication": "publication_authorized",
            "merge": "merge_authorized",
        }
        for action, next_action in next_authorization_keys.items():
            if authorization.get(action) is not next_task.get(next_action):
                errors.append(
                    "current_task and next_approved_task completion authorization "
                    f"must agree: {action}"
                )
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


@pytest.mark.parametrize("authorization_key", ["commit", "remote_publication", "merge"])
def test_live_status_contract_rejects_accepted_task_without_completion_authority(
    authorization_key,
):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    status["current_task"]["owner_acceptance"]["status"] = "accepted"
    status["current_task"]["authorization"].update(
        commit=True,
        remote_publication=True,
        merge=True,
    )
    status["current_task"]["authorization"][authorization_key] = False

    errors = live_status_policy_errors(yaml.safe_dump(status).encode("utf-8"))

    assert (
        "accepted current_task must authorize commit, remote_publication, and merge"
        in errors
    )


@pytest.mark.parametrize("prohibition_location", ["current_task", "status"])
def test_live_status_contract_rejects_authorized_actions_in_prohibited_lists(
    prohibition_location,
):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    status["current_task"]["owner_acceptance"]["status"] = "accepted"
    status["current_task"]["authorization"].update(
        commit=True,
        remote_publication=True,
        merge=True,
    )
    prohibition = (
        "Do not commit, push, create a pull request, merge, or begin another task."
    )
    status["current_task"]["prohibited_changes"] = (
        [prohibition] if prohibition_location == "current_task" else []
    )
    status["prohibited_next_actions"] = (
        [prohibition] if prohibition_location == "status" else []
    )

    errors = live_status_policy_errors(yaml.safe_dump(status).encode("utf-8"))

    assert {
        "authorized current_task commit conflicts with a prohibited action",
        "authorized current_task remote_publication conflicts with a prohibited action",
        "authorized current_task merge conflicts with a prohibited action",
    } <= set(errors)


@pytest.mark.parametrize(
    ("authorization_key", "next_authorization_key"),
    [
        ("commit", "commit_authorized"),
        ("remote_publication", "publication_authorized"),
        ("merge", "merge_authorized"),
    ],
)
def test_live_status_contract_rejects_mismatched_duplicate_completion_authority(
    authorization_key,
    next_authorization_key,
):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    status["current_task"]["owner_acceptance"]["status"] = "accepted"
    status["current_task"]["authorization"].update(
        commit=True,
        remote_publication=True,
        merge=True,
    )
    status["current_task"]["prohibited_changes"] = []
    status["prohibited_next_actions"] = []
    status["next_approved_task"].update(
        commit_authorized=True,
        publication_authorized=True,
        merge_authorized=True,
    )
    status["next_approved_task"][next_authorization_key] = False

    errors = live_status_policy_errors(yaml.safe_dump(status).encode("utf-8"))

    assert (
        "current_task and next_approved_task completion authorization must agree: "
        f"{authorization_key}"
    ) in errors
