"""Minimum executable contract for live governance documents and their history."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
ROADMAP_PATH = ROOT / "docs" / "ROADMAP.md"
WEEKLY_MAINTENANCE_PATH = ROOT / "docs" / "WEEKLY_MAINTENANCE.md"
MELEE_ADMISSION_PATH = ROOT / "docs" / "MELEE_EVENT_ADMISSION_RUNBOOK.md"

FORBIDDEN_STATUS_CACHES = {
    "approved_event_structures",
    "authoritative_documents",
    "current_repository_state",
    "current_task",
    "delegated_local_execution_governance",
    "engineering_quality",
    "future_task_gates",
    "governance_baseline",
    "next_approved_task",
    "product_tracks",
    "prohibited_next_actions",
    "publication_workflow_control",
    "recent_completion_handoff",
    "weekly_classifier_review",
}

FORBIDDEN_TRANSIENT_KEYS = {
    "authorization",
    "base_commit",
    "branch",
    "local_acceptance",
    "merge_commit",
    "open_pull_request",
    "open_pull_request_head",
    "owner_acceptance",
    "pull_request",
    "workflow_run",
    "workspace",
}

EXPECTED_AUTHORITY_MODEL = {
    "owner_authorization": "active_owner_conversation",
    "repository_and_merge_facts": "git_and_github",
    "generated_subject_provenance": "artifacts",
    "durable_project_state": "this_document",
}


def _find_forbidden_transient_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(FORBIDDEN_TRANSIENT_KEYS & set(value))
        for child in value.values():
            found.update(_find_forbidden_transient_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_forbidden_transient_keys(child))
    return found


def live_status_policy_errors(status_bytes: bytes) -> list[str]:
    errors = []
    if len(status_bytes) > 10 * 1024:
        errors.append("STATUS exceeds 10 KiB")

    status = yaml.safe_load(status_bytes)
    if not isinstance(status, dict):
        return errors + ["STATUS must be a mapping"]

    stale_caches = FORBIDDEN_STATUS_CACHES & set(status)
    if stale_caches:
        errors.append("STATUS contains non-live caches: " + ", ".join(sorted(stale_caches)))

    transient_keys = _find_forbidden_transient_keys(status)
    if transient_keys:
        errors.append(
            "STATUS contains transient task facts: "
            + ", ".join(sorted(transient_keys))
        )

    status_document = status.get("status_document", {})
    if status_document.get("live_state_only") is not True:
        errors.append("live_state_only must be true")
    history_policy = status_document.get("history_policy")
    if not isinstance(history_policy, str) or not history_policy.strip():
        errors.append("history_policy must be non-empty")

    if status_document.get("authority_model") != EXPECTED_AUTHORITY_MODEL:
        errors.append("authority_model must name the four live authorities")

    project = status.get("project", {})
    if not {"name", "repository", "default_branch", "status"} <= set(project):
        errors.append("project is missing durable live fields")

    phase = status.get("current_phase", {})
    if not {"id", "name", "status", "objective"} <= set(phase):
        errors.append("current_phase is missing durable live fields")

    program = status.get("active_program", {})
    if not {"id", "name", "status", "governance_model"} <= set(program):
        errors.append("active_program is missing durable live fields")

    if not isinstance(status.get("known_blockers"), list):
        errors.append("known_blockers must be a list")

    paused = status.get("paused_activities")
    if not isinstance(paused, list):
        errors.append("paused_activities must be a list")
    elif any(
        not isinstance(item, dict) or not {"id", "name", "reason"} <= set(item)
        for item in paused
    ):
        errors.append("paused_activities entries must contain id, name, and reason")

    return errors


def test_live_status_contract():
    assert live_status_policy_errors(STATUS_PATH.read_bytes()) == []


def test_live_roadmap_history_pointers_exist():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    pointers = set(re.findall(r"`(docs/history/[^`]+)`", roadmap))

    assert pointers
    assert all((ROOT / pointer).is_file() for pointer in pointers)


def test_cross_source_unknown_review_runbooks_preserve_product_separation():
    weekly = " ".join(WEEKLY_MAINTENANCE_PATH.read_text(encoding="utf-8").split())
    melee = " ".join(MELEE_ADMISSION_PATH.read_text(encoding="utf-8").split())

    assert "The weekly readiness JSON and completion registry remain MTGO-only" in weekly
    assert "never written to `docs/STATUS.yaml`" in weekly
    assert "contains no authorization, progress, or workflow state" in weekly
    assert "Review-ready weekly supplement" in melee
    assert "The MTGO weekly readiness JSON and completion registry remain MTGO-only" in melee
    assert "contains no authorization, progress, or workflow state" in melee
    assert "The Owner decides in the active conversation" in melee
    assert "Public or live status is not part of this definition" in melee
    assert "An unavailable decklist is listed separately" in melee


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("oversize", "STATUS exceeds 10 KiB"),
        ("not-live", "live_state_only must be true"),
        ("empty-history", "history_policy must be non-empty"),
        ("wrong-authority", "authority_model must name the four live authorities"),
    ],
)
def test_live_status_contract_rejects_invalid_policy(mutation, expected):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    if mutation == "not-live":
        status["status_document"]["live_state_only"] = False
    elif mutation == "empty-history":
        status["status_document"]["history_policy"] = ""
    elif mutation == "wrong-authority":
        status["status_document"]["authority_model"]["owner_authorization"] = (
            "status_document"
        )
    status_bytes = yaml.safe_dump(status).encode("utf-8")
    if mutation == "oversize":
        status_bytes += b"#" * (16 * 1024 + 1)

    assert expected in live_status_policy_errors(status_bytes)


@pytest.mark.parametrize(
    "field",
    [
        "current_task",
        "next_approved_task",
        "current_repository_state",
        "weekly_classifier_review",
    ],
)
def test_live_status_contract_rejects_top_level_task_caches(field):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    status[field] = {}

    errors = live_status_policy_errors(yaml.safe_dump(status).encode("utf-8"))

    assert "STATUS contains non-live caches" in errors[0]
    assert field in errors[0]


@pytest.mark.parametrize("field", sorted(FORBIDDEN_TRANSIENT_KEYS))
def test_live_status_contract_rejects_nested_transient_task_facts(field):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    status["active_program"][field] = "cached"

    errors = live_status_policy_errors(yaml.safe_dump(status).encode("utf-8"))

    assert any(
        error.startswith("STATUS contains transient task facts:") and field in error
        for error in errors
    )
