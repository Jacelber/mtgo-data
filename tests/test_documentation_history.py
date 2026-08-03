from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
HISTORY_PATH = ROOT / "docs" / "history" / "STATUS-2026-08-04-pre-P11-13.yaml"
HISTORY_INDEX_PATH = ROOT / "docs" / "history" / "README.md"
EXPECTED_HISTORY_SHA256 = (
    "a8166a61b471b5140e4d67105fea02515e2dde3318429cd85fb6841cc0308c66"
)


def test_live_status_is_small_current_state_and_points_to_history():
    status_bytes = STATUS_PATH.read_bytes()
    status = yaml.safe_load(status_bytes)

    assert 8 * 1024 <= len(status_bytes) <= 16 * 1024
    assert status["status_document"]["live_state_only"] is True
    assert status["current_phase"]["id"] == 11
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

    historical_paths = {
        item["path"] for item in status["authoritative_documents"]["historical_documents"]
    }
    assert "docs/history/README.md" in historical_paths
    assert "docs/history/STATUS-2026-08-04-pre-P11-13.yaml" in historical_paths


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
