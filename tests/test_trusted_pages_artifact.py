from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tools.select_trusted_pages_artifact import select_trusted_artifact


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)
REPOSITORY = "Jacelber/mtgo-data"
WORKFLOW_ID = 12
SHA = "a" * 40


def _artifact(**changes):
    artifact = {
        "id": 100,
        "name": "simple-card-localization-" + "b" * 64,
        "expired": False,
        "created_at": (NOW - timedelta(days=1)).isoformat(),
        "expires_at": (NOW + timedelta(days=30)).isoformat(),
        "workflow_run": {
            "id": 200,
            "head_branch": "master",
            "head_sha": SHA,
        },
    }
    artifact.update(changes)
    return artifact


def _run(**changes):
    run = {
        "id": 200,
        "workflow_id": WORKFLOW_ID,
        "path": ".github/workflows/pages.yml",
        "event": "push",
        "head_branch": "master",
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }
    run.update(changes)
    return run


def _select(artifact=None, run=None):
    return select_trusted_artifact(
        [_artifact() if artifact is None else artifact],
        repository=REPOSITORY,
        workflow_id=WORKFLOW_ID,
        get_run=lambda _run_id: _run() if run is None else run,
        name_matches=lambda name: name.startswith("simple-card-localization-"),
        now=NOW,
    )


def test_selects_only_a_completed_successful_exact_master_run():
    selected = _select()

    assert selected is not None
    assert selected.run_id == 200
    assert selected.run_attempt == 1
    assert selected.head_sha == SHA


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "in_progress", "conclusion": None},
        {"status": "completed", "conclusion": "failure"},
        {"status": "completed", "conclusion": "cancelled"},
        {"id": 201},
        {"workflow_id": 99},
        {"path": ".github/workflows/other.yml"},
        {"event": "pull_request"},
        {"head_branch": "feature"},
        {"head_sha": "not-a-commit"},
        {"repository": {"full_name": "other/repository"}},
        {"head_repository": {"full_name": "fork/repository"}},
    ],
)
def test_rejects_untrusted_run_provenance(changes):
    assert _select(run=_run(**changes)) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"expired": True},
        {"created_at": (NOW - timedelta(days=91)).isoformat()},
        {"created_at": (NOW + timedelta(seconds=1)).isoformat()},
        {"created_at": "unknown"},
        {"expires_at": (NOW - timedelta(seconds=1)).isoformat()},
        {"expires_at": "unknown"},
        {"workflow_run": {"id": 200, "head_branch": "other", "head_sha": SHA}},
        {"workflow_run": {"id": 200, "head_branch": "master", "head_sha": "b" * 40}},
    ],
)
def test_rejects_untrusted_artifact_metadata(changes):
    assert _select(artifact=_artifact(**changes)) is None


def test_skips_a_newer_failure_and_selects_an_older_success():
    failed = _artifact(id=101, workflow_run={"id": 201, "head_branch": "master", "head_sha": SHA})
    runs = {200: _run(), 201: _run(id=201, conclusion="failure")}

    selected = select_trusted_artifact(
        [_artifact(), failed],
        repository=REPOSITORY,
        workflow_id=WORKFLOW_ID,
        get_run=lambda run_id: runs[run_id],
        name_matches=lambda _name: True,
        now=NOW,
    )

    assert selected is not None
    assert selected.artifact_id == 100
