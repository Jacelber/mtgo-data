from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
HISTORY_PATH = ROOT / "docs" / "history" / "STATUS-2026-08-04-pre-P11-13.yaml"
HISTORY_INDEX_PATH = ROOT / "docs" / "history" / "README.md"
EXPECTED_HISTORY_SHA256 = (
    "a8166a61b471b5140e4d67105fea02515e2dde3318429cd85fb6841cc0308c66"
)


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
    return errors


def test_live_status_is_small_current_state_and_points_to_history():
    status_bytes = STATUS_PATH.read_bytes()
    status = yaml.safe_load(status_bytes)

    assert 8 * 1024 <= len(status_bytes) <= 16 * 1024
    assert live_status_policy_errors(status_bytes) == []
    assert status["status_document"]["live_state_only"] is True
    assert status["status_document"]["history_policy"].strip()
    assert status["current_phase"]["id"] == 12
    assert {"id", "name", "authorization", "stop_point"} <= set(status["current_task"])
    assert set(status["current_task"]["authorization"]) == {
        "local_implementation",
        "commit",
        "remote_publication",
        "merge",
    }
    assert all(
        isinstance(value, bool)
        for value in status["current_task"]["authorization"].values()
    )
    assert status["known_blockers"] == []
    assert status["next_approved_task"]["local_execution_authorized"] is False
    assert status["current_task"]["id"] == "P12-03B"
    assert status["current_task"]["status"] == (
        "local_contract_complete_ready_pr_publication_authorized"
    )
    assert status["current_task"]["base_commit"] == (
        "ec00f59c8a260bf0975af9fffa0badfabac430d3"
    )
    assert status["current_task"]["authorization"] == {
        "local_implementation": True,
        "commit": True,
        "remote_publication": True,
        "merge": False,
    }
    assert status["recent_completion_handoff"] == {
        "id": "GOV-03-READY-IMPACT-CI",
        "name": "Impact-classified pull-request validation",
        "status": "completed_and_merged",
        "pull_request": 188,
        "merge_commit": "ec00f59c8a260bf0975af9fffa0badfabac430d3",
        "note": (
            "GitHub and Git history retain the detailed validation, publication, "
            "and Pages evidence."
        ),
    }
    assert status["next_approved_task"]["id"] == "P12-04"
    assert status["next_approved_task"]["status"] == "planned_not_authorized"
    assert status["next_approved_task"]["requires_user_confirmation"] is True
    assert status["next_approved_task"]["remote_publication_authorized"] is False
    assert status["future_task_gates"][0]["task"] == "P12-10"
    assert status["future_task_gates"][0]["status"] == (
        "blocked_pending_separate_authorization_and_evidence"
    )

    historical_paths = {
        item["path"] for item in status["authoritative_documents"]["historical_documents"]
    }
    assert "docs/history/README.md" in historical_paths
    assert "docs/history/STATUS-2026-08-04-pre-P11-13.yaml" in historical_paths


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("oversize", "STATUS exceeds 16 KiB"),
        ("not-live", "live_state_only must be true"),
        ("empty-history", "history_policy must be non-empty"),
    ],
)
def test_live_status_policy_rejects_regressions(mutation, expected):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    if mutation == "not-live":
        status["status_document"]["live_state_only"] = False
    elif mutation == "empty-history":
        status["status_document"]["history_policy"] = ""
    status_bytes = yaml.safe_dump(status).encode("utf-8")
    if mutation == "oversize":
        status_bytes += b"#" * (16 * 1024 + 1)

    assert expected in live_status_policy_errors(status_bytes)


def test_pre_split_status_history_is_complete_and_non_authoritative():
    history_bytes = HISTORY_PATH.read_bytes()
    history = yaml.safe_load(history_bytes)
    index = HISTORY_INDEX_PATH.read_text(encoding="utf-8")

    assert hashlib.sha256(history_bytes).hexdigest() == EXPECTED_HISTORY_SHA256
    assert history["current_task"]["id"] == "P11-12"
    assert "phase_0_tasks" in history
    assert "phase_8_plan" in history
    assert "phase_9_plan" in history
    assert "phase_5_tasks" in history
    assert "phase_6_tasks" in history
    assert "non-authoritative" in index
    assert "must not be used to authorize work" in index
    assert EXPECTED_HISTORY_SHA256 in index
    assert "83a54fe0907e1c8775b643295fd9e15327e0daf5" in index


def test_agent_adapters_are_thin_and_have_no_phase_snapshot():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(
        encoding="utf-8"
    )

    assert len(agents.encode("utf-8")) <= 8 * 1024
    assert len(claude.encode("utf-8")) <= 2 * 1024
    assert len(copilot.encode("utf-8")) <= 2 * 1024
    for adapter in (claude, copilot):
        assert "`AGENTS.md` is the mandatory entry point" in adapter
        assert "At the time this file was created" not in adapter
        assert "When the project is in Phase 0" not in adapter


def test_readme_keeps_supported_operations_without_phase_narrative():
    readme_bytes = (ROOT / "README.md").read_bytes()
    readme = readme_bytes.decode("utf-8")

    assert len(readme_bytes) <= 20 * 1024
    assert "Phase 9 is complete" not in readme
    assert "P7-02" not in readme
    assert "P7-03" not in readme
    assert "mtgo-data-mtgo.exe --root . --format standard build-statistics" in readme
    assert "mtgo-data-melee.exe --event-id 434455" in readme
    assert "-m mtgmeta.melee.retention" in readme
    assert "Melee production candidate" in readme
    assert "docs/STATUS.yaml" in readme


def test_pr_maturity_and_validation_class_policy_is_consistent():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    admission = (
        ROOT / "docs" / "audits" / "CI-MASTER-ADMISSION.md"
    ).read_text(encoding="utf-8")

    assert "Pull-request maturity and validation scope are separate" in agents
    assert "Pull-request maturity is not an input to validation strength" in workflow
    assert "pull-request maturity and validation class are separated" in roadmap
    assert "# DEC-085 - Separate pull-request maturity from validation class" in decisions
    assert "Draft and Ready\npull requests use the same" in admission
    assert "every Ready pull request retains the complete" not in roadmap


def test_p12_03_landing_contract_is_consistent():
    scope = (ROOT / "docs" / "PROJECT_SCOPE.md").read_text(encoding="utf-8")
    statistics = (ROOT / "docs" / "STATISTICS_SPEC.md").read_text(
        encoding="utf-8"
    )
    architecture = (ROOT / "docs" / "DATA_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "audits" / "P12-03.md").read_text(
        encoding="utf-8"
    )

    for document in (statistics, roadmap, decisions, audit):
        assert "five percentage points" in document
        assert "Weekly Pickup" in document

    assert "five-percentage-point movement" in architecture
    assert "Weekly Pickup" in architecture

    assert "at least `0.03`" in statistics
    assert "construction-deviation score of at least `20`" in statistics
    assert "There is no separate public `notable`" in statistics
    assert "does not derive a statistical `new_entry`" in statistics
    assert "product ID `mtgo-landing`" in architecture
    assert "Standard and Modern are the explicit migration exceptions" in architecture
    assert "P12-10 is blocked" in architecture
    assert "future formats to admit Landing" in roadmap
    assert "# DEC-086 - Freeze the reviewed MTGO Landing contract" in decisions
    assert "products predate Landing" in scope
