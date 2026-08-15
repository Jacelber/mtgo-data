from __future__ import annotations

from pathlib import Path

import pytest

from ci_master_admission import (
    ADMISSION_JOB,
    AGGREGATE_JOB,
    TARGETED_JOB,
    AdmissionDecision,
    decide_from_environment,
    decide_master_push,
    decide_pull_request,
    expected_successful_jobs,
    validation_class_step,
    validation_subject_step,
)


REPOSITORY_API = "https://api.github.test/repos/owner/repo"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
MERGE_SHA = "c" * 40


def _event(body="<!-- artifact-impact: none -->", action="synchronize", changes=None):
    payload = {
        "action": action,
        "pull_request": {"number": 184, "body": body, "draft": True},
    }
    if changes is not None:
        payload["changes"] = changes
    return payload


def _decide_pr(files, **event_overrides):
    pages = [files[index : index + 100] for index in range(0, len(files), 100)]
    if len(files) % 100 == 0:
        pages.append([])

    def fetch(url):
        prefix = f"{REPOSITORY_API}/pulls/184/files?per_page=100&page="
        return pages[int(url.removeprefix(prefix)) - 1]

    return decide_pull_request(
        event_payload=_event(**event_overrides),
        repository="owner/repo",
        fetch_json=fetch,
        api_url="https://api.github.test",
    )


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/STATUS.yaml"], "targeted:docs"),
        (["assets/js/app.js"], "targeted:ui"),
        (["src/mtgmeta/deck.py"], "targeted:code"),
        (["schemas/range.schema.json"], "targeted:data"),
        ([".github/workflows/ci.yml"], "targeted:governance"),
        (
            ["docs/STATUS.yaml", "src/mtgmeta/deck.py", "stats/catalog.json"],
            "targeted:code+data+docs",
        ),
    ],
)
def test_known_paths_select_only_their_targeted_categories(paths, expected):
    files = [{"filename": path, "status": "modified"} for path in paths]
    decision = _decide_pr(files)
    assert decision.mode == "targeted"
    assert decision.validation_class == expected


def test_known_added_path_needs_no_operation_declaration():
    decision = _decide_pr(
        [{"filename": "docs/reviews/Owner-Review.md", "status": "added"}]
    )
    assert decision.validation_class == "targeted:docs"


@pytest.mark.parametrize(
    ("file", "declaration", "expected"),
    [
        (
            {"filename": "review-output/Owner-Review.md", "status": "added"},
            "add|docs|review-output/Owner-Review.md",
            "targeted:docs",
        ),
        (
            {"filename": "docs/old.md", "status": "removed"},
            "delete|docs|docs/old.md",
            "targeted:docs",
        ),
        (
            {
                "filename": "docs/history/old.md",
                "previous_filename": "docs/old.md",
                "status": "renamed",
            },
            "rename|docs|docs/old.md|docs/history/old.md",
            "targeted:docs",
        ),
    ],
)
def test_exact_declared_file_operations_select_the_minimal_category(
    file, declaration, expected
):
    body = (
        "<!-- artifact-impact: internal_diagnostics -->\n"
        f"<!-- file-operation: {declaration} -->"
    )
    decision = _decide_pr([file], body=body)
    assert decision.mode == "targeted"
    assert decision.validation_class == expected


@pytest.mark.parametrize(
    "files",
    [
        [{"filename": "new_kind/file.xyz", "status": "added"}],
        [{"filename": "README.md", "status": "removed"}],
        [
            {
                "filename": "README.md",
                "previous_filename": "OLD.md",
                "status": "renamed",
            }
        ],
    ],
)
def test_unknown_deleted_or_renamed_paths_stop_without_catch_all(files):
    decision = _decide_pr(files)
    assert decision.mode == "unclassified"
    assert decision.validation_class == "unclassified"


@pytest.mark.parametrize(
    "body",
    [
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->\n"
            "<!-- file-operation: add|ui|review-output/result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/another.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|../result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: copy|docs|review-output/result.md -->"
        ),
    ],
)
def test_wrong_stale_or_invalid_operation_declaration_stops_without_tests(body):
    decision = _decide_pr(
        [{"filename": "review-output/result.md", "status": "added"}],
        body=body,
    )
    assert decision.mode == "unclassified"


def test_declared_category_cannot_override_a_known_path_category():
    body = (
        "<!-- artifact-impact: internal_diagnostics -->\n"
        "<!-- file-operation: add|ui|docs/reviews/result.md -->"
    )
    decision = _decide_pr(
        [{"filename": "docs/reviews/result.md", "status": "added"}],
        body=body,
    )
    assert decision.mode == "unclassified"


def test_pull_request_template_examples_are_not_active_declarations():
    template = (
        Path(__file__).resolve().parents[1] / ".github" / "pull_request_template.md"
    ).read_text(encoding="utf-8")
    assert "<!-- file-operation:" not in template
    assert template.count("<!-- EXAMPLE-file-operation:") == 3


def test_missing_or_invalid_impact_declaration_stops_without_tests():
    for body in ("", "<!-- artifact-impact: mystery -->"):
        assert _decide_pr(
            [{"filename": "README.md", "status": "modified"}], body=body
        ).mode == "unclassified"


def test_metadata_edit_without_body_or_base_change_runs_nothing():
    decision = _decide_pr(
        [{"filename": "README.md", "status": "modified"}],
        action="edited",
        changes={"title": {"from": "old"}},
    )
    assert decision.mode == "metadata-only"


def test_file_pagination_is_complete_before_classification():
    files = [
        {"filename": f"docs/history/item-{index}.md", "status": "modified"}
        for index in range(101)
    ]
    assert _decide_pr(files).validation_class == "targeted:docs"


def _valid_merge_responses(validation_class="targeted:governance"):
    pull_request = {
        "number": 119,
        "body": "<!-- artifact-impact: none -->",
        "merged_at": "2026-07-28T07:38:13Z",
        "merge_commit_sha": MERGE_SHA,
        "base": {"ref": "master", "sha": BASE_SHA},
        "head": {"sha": HEAD_SHA},
    }
    jobs = []
    for name in sorted(expected_successful_jobs(validation_class) or ()):
        job = {"name": name, "conclusion": "success"}
        if name == AGGREGATE_JOB:
            job["steps"] = [
                {
                    "name": validation_subject_step(119, BASE_SHA, HEAD_SHA),
                    "conclusion": "success",
                },
                {
                    "name": validation_class_step(validation_class),
                    "conclusion": "success",
                },
            ]
        jobs.append(job)
    return {
        f"{REPOSITORY_API}/commits/{MERGE_SHA}": {
            "parents": [{"sha": BASE_SHA}, {"sha": HEAD_SHA}]
        },
        f"{REPOSITORY_API}/commits/{MERGE_SHA}/pulls?per_page=100": [pull_request],
        f"{REPOSITORY_API}/pulls/119": pull_request,
        f"{REPOSITORY_API}/pulls/119/files?per_page=100&page=1": [
            {"filename": ".github/workflows/ci.yml", "status": "modified"}
        ],
        (
            f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
            f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
        ): {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 42,
                    "run_attempt": 1,
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                    "head_sha": HEAD_SHA,
                    "path": ".github/workflows/ci.yml",
                    "updated_at": "2026-07-28T07:37:50Z",
                }
            ],
        },
        f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100": {
            "total_count": len(jobs),
            "jobs": jobs,
        },
    }


def _decide_merge(responses):
    return decide_master_push(
        repository="owner/repo",
        merge_sha=MERGE_SHA,
        fetch_json=lambda url: responses[url],
        api_url="https://api.github.test",
    )


def test_exact_merge_reuses_only_the_exact_targeted_evidence():
    decision = _decide_merge(_valid_merge_responses())
    assert decision == AdmissionDecision(
        mode="pr-confirmation",
        reason="exact_validated_merge:targeted:governance",
        pull_request=119,
        workflow_run=42,
        validation_class="targeted:governance",
    )


def test_incomplete_merge_evidence_stops_without_full_suite():
    responses = _valid_merge_responses()
    jobs_url = f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    responses[jobs_url]["jobs"].pop()
    responses[jobs_url]["total_count"] -= 1
    assert _decide_merge(responses).mode == "unclassified"


def test_direct_push_stops_without_full_suite():
    responses = {f"{REPOSITORY_API}/commits/{MERGE_SHA}": {"parents": [{"sha": BASE_SHA}]}}
    assert _decide_merge(responses).mode == "unclassified"


def test_targeted_job_matrix_has_no_heavy_baseline_jobs():
    assert expected_successful_jobs("targeted:code+docs") == frozenset(
        {ADMISSION_JOB, TARGETED_JOB, AGGREGATE_JOB}
    )
    assert expected_successful_jobs("unclassified") is None


def test_workflow_dispatch_stops_for_explicit_classification(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    decision = decide_from_environment()
    assert decision.mode == "unclassified"
