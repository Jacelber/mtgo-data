from __future__ import annotations

import pytest

from ci_master_admission import (
    ADMISSION_JOB,
    AGGREGATE_JOB,
    BROWSER_JOB,
    COMMITTED_BASELINE_JOB,
    EXPECTED_SUCCESSFUL_JOBS,
    FOCUSED_JOB,
    ORDINARY_JOB,
    STATIC_JOB,
    AdmissionDecision,
    decide_from_environment,
    decide_master_push,
    decide_pull_request,
    validation_class_step,
    validation_subject_step,
)


REPOSITORY_API = "https://api.github.test/repos/owner/repo"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
MERGE_SHA = "c" * 40


def pull_request_event(
    *,
    body="<!-- artifact-impact: user_visible_ui -->",
    draft=True,
    action="synchronize",
    changes=None,
):
    event = {
        "action": action,
        "pull_request": {
            "number": 184,
            "body": body,
            "draft": draft,
        },
    }
    if changes is not None:
        event["changes"] = changes
    return event


def decide_pr(files, **event_overrides):
    event = pull_request_event(**event_overrides)
    files_url = f"{REPOSITORY_API}/pulls/184/files?per_page=100&page=1"

    def fetch(url):
        assert url == files_url
        if isinstance(files, Exception):
            raise files
        return files

    return decide_pull_request(
        event_payload=event,
        repository="owner/repo",
        fetch_json=fetch,
        api_url="https://api.github.test",
    )


def class_evidence(validation_class):
    if validation_class == "focused-docs":
        return (
            "<!-- artifact-impact: internal_diagnostics -->",
            [{"filename": "docs/audits/example.md", "status": "modified"}],
        )
    if validation_class == "focused-ui":
        return (
            "<!-- artifact-impact: user_visible_ui -->",
            [
                {
                    "filename": "assets/css/phase8-candidate.css",
                    "status": "modified",
                },
                {
                    "filename": "tests/browser/production-pages.spec.js",
                    "status": "modified",
                },
            ],
        )
    return (
        "<!-- artifact-impact: none -->",
        [{"filename": ".github/workflows/ci.yml", "status": "modified"}],
    )


def valid_responses(validation_class="full"):
    run_id = 42
    body, files = class_evidence(validation_class)
    pull_request = {
        "number": 119,
        "body": body,
        "merged_at": "2026-07-28T07:38:13Z",
        "merge_commit_sha": MERGE_SHA,
        "base": {"ref": "master", "sha": BASE_SHA},
        "head": {"sha": HEAD_SHA},
    }
    successful_jobs = []
    for name in sorted(EXPECTED_SUCCESSFUL_JOBS[validation_class]):
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
        successful_jobs.append(job)

    return {
        f"{REPOSITORY_API}/commits/{MERGE_SHA}": {
            "sha": MERGE_SHA,
            "parents": [{"sha": BASE_SHA}, {"sha": HEAD_SHA}],
        },
        f"{REPOSITORY_API}/commits/{MERGE_SHA}/pulls?per_page=100": [
            dict(pull_request)
        ],
        f"{REPOSITORY_API}/pulls/119": dict(pull_request),
        f"{REPOSITORY_API}/pulls/119/files?per_page=100&page=1": files,
        (
            f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
            f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
        ): {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": run_id,
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
        f"{REPOSITORY_API}/actions/runs/{run_id}/attempts/1/jobs?per_page=100": {
            "total_count": len(successful_jobs),
            "jobs": successful_jobs,
        },
    }


def decide(responses):
    def fetch(url):
        value = responses[url]
        if isinstance(value, Exception):
            raise value
        return value

    return decide_master_push(
        repository="owner/repo",
        merge_sha=MERGE_SHA,
        fetch_json=fetch,
        api_url="https://api.github.test",
    )


@pytest.mark.parametrize("validation_class", ["focused-docs", "focused-ui", "full"])
def test_exact_merge_reuses_the_still_required_validation_class(validation_class):
    assert decide(valid_responses(validation_class)) == AdmissionDecision(
        mode="pr-confirmation",
        reason=f"exact_validated_merge:{validation_class}",
        pull_request=119,
        workflow_run=42,
        validation_class=validation_class,
    )


def test_direct_push_without_two_merge_parents_falls_back_to_full():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}"]["parents"] = [
        {"sha": BASE_SHA}
    ]
    decision = decide(responses)
    assert decision.mode == "full"
    assert decision.validation_class == "full"
    assert "two-parent_merge" in decision.reason


def test_pr_base_must_equal_first_merge_parent():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}/pulls?per_page=100"][0][
        "base"
    ]["sha"] = "d" * 40
    decision = decide(responses)
    assert decision.mode == "full"
    assert "base_head" in decision.reason


@pytest.mark.parametrize(
    "mutation",
    ["missing-job", "extra-job", "wrong-class-step", "wrong-subject-step"],
)
def test_exact_job_and_subject_matrix_is_required(mutation):
    responses = valid_responses("focused-ui")
    jobs_payload = responses[
        f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    ]
    if mutation == "missing-job":
        jobs_payload["jobs"] = [
            job for job in jobs_payload["jobs"] if job["name"] != BROWSER_JOB
        ]
        jobs_payload["total_count"] -= 1
    elif mutation == "extra-job":
        jobs_payload["jobs"].append(
            {"name": STATIC_JOB, "conclusion": "success"}
        )
        jobs_payload["total_count"] += 1
    else:
        aggregate = next(
            job for job in jobs_payload["jobs"] if job["name"] == AGGREGATE_JOB
        )
        index = 1 if mutation == "wrong-class-step" else 0
        aggregate["steps"][index]["name"] = "wrong successful subject"
    assert decide(responses).mode == "full"


def test_incomplete_job_or_run_pagination_is_fail_safe():
    jobs = valid_responses()
    jobs_payload = jobs[
        f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    ]
    jobs_payload["total_count"] += 1
    assert decide(jobs).mode == "full"

    runs = valid_responses()
    runs_url = (
        f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
        f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
    )
    runs[runs_url]["total_count"] = 2
    assert decide(runs).mode == "full"


def test_validation_must_finish_before_merge():
    responses = valid_responses()
    runs_url = (
        f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
        f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
    )
    responses[runs_url]["workflow_runs"][0]["updated_at"] = (
        "2026-07-28T07:39:00Z"
    )
    assert decide(responses).mode == "full"


def test_changed_current_declaration_or_file_class_falls_back_to_full():
    changed_declaration = valid_responses("focused-docs")
    changed_declaration[f"{REPOSITORY_API}/pulls/119"]["body"] = (
        "<!-- artifact-impact: none -->"
    )
    assert decide(changed_declaration).mode == "full"

    changed_files = valid_responses("focused-ui")
    changed_files[f"{REPOSITORY_API}/pulls/119/files?per_page=100&page=1"] = [
        {"filename": "assets/js/phase8/runtime.js", "status": "modified"}
    ]
    assert decide(changed_files).mode == "full"


def test_api_failure_is_fail_safe_full_validation():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}"] = RuntimeError(
        "temporary API failure"
    )
    decision = decide(responses)
    assert decision.mode == "full"
    assert "temporary_API_failure" in decision.reason


@pytest.mark.parametrize("draft", [True, False])
def test_safe_docs_classification_is_independent_of_pr_maturity(draft):
    decision = decide_pr(
        [{"filename": "docs/history/example.md", "status": "added"}],
        body="<!-- artifact-impact: internal_diagnostics -->",
        draft=draft,
    )
    assert decision == AdmissionDecision(
        mode="focused-docs",
        reason="safe_internal_documentation",
        validation_class="focused-docs",
    )


@pytest.mark.parametrize("draft", [True, False])
def test_safe_ui_classification_is_independent_of_pr_maturity(draft):
    decision = decide_pr(
        [
            {"filename": "assets/css/phase8-base.css", "status": "modified"},
            {
                "filename": "tests/browser/url-state.spec.js",
                "status": "modified",
            },
        ],
        draft=draft,
    )
    assert decision.mode == "focused-ui"
    assert decision.validation_class == "focused-ui"


@pytest.mark.parametrize(
    "path",
    [
        "assets/js/phase8/app.js",
        "assets/js/phase8/app-core.js",
        "assets/js/phase8/i18n.js",
        "assets/js/phase8/matchup-model.js",
        "assets/js/phase8/mtgo-controller.js",
        "assets/js/phase8/runtime.js",
        "assets/js/phase8/tabletop-controller.js",
        "assets/css/site.css",
    ],
)
def test_shared_runtime_and_non_allowlisted_ui_paths_require_full(path):
    decision = decide_pr([{"filename": path, "status": "modified"}])
    assert decision.mode == "full"
    assert "path_or_impact_not_focused" in decision.reason


@pytest.mark.parametrize(
    ("path", "impact"),
    [
        ("src/mtgmeta/statistics.py", "none"),
        (".github/workflows/ci.yml", "none"),
        ("docs/STATISTICS_SPEC.md", "internal_diagnostics"),
        ("docs/audits/CI-MASTER-ADMISSION.md", "internal_diagnostics"),
        ("schemas/mtgo-range.schema.json", "statistical_json_structure"),
        ("index.html", "public_path"),
    ],
)
def test_backend_workflow_authority_schema_and_public_paths_require_full(
    path, impact
):
    decision = decide_pr(
        [{"filename": path, "status": "modified"}],
        body=f"<!-- artifact-impact: {impact} -->",
    )
    assert decision.mode == "full"


def test_delete_and_rename_fall_back_to_full():
    removed = decide_pr(
        [{"filename": "assets/css/phase8-base.css", "status": "removed"}]
    )
    renamed = decide_pr(
        [
            {
                "filename": "assets/css/phase8-new.css",
                "previous_filename": "assets/css/phase8-base.css",
                "status": "renamed",
            }
        ]
    )
    assert removed.mode == "full"
    assert "removed" in removed.reason
    assert renamed.mode == "full"
    assert "renamed" in renamed.reason


def test_missing_invalid_or_conflicting_declaration_is_fail_safe_full():
    files = [{"filename": "assets/css/phase8-base.css", "status": "modified"}]
    missing = decide_pr(files, body="No declaration")
    invalid = decide_pr(files, body="<!-- artifact-impact: cosmetic -->")
    conflicting = decide_pr(
        files,
        body=(
            "<!-- artifact-impact: user_visible_ui -->\n"
            "<!-- artifact-impact: internal_diagnostics -->"
        ),
    )
    assert missing.mode == "full"
    assert "artifact_impact_declaration" in missing.reason
    assert invalid.mode == "full"
    assert "unknown_artifact_impact" in invalid.reason
    assert conflicting.mode == "full"
    assert "artifact_impact_declaration" in conflicting.reason


def test_classification_api_failure_and_unsupported_pagination_are_full():
    failed = decide_pr(RuntimeError("files API unavailable"))
    assert failed.mode == "full"
    assert "files_API_unavailable" in failed.reason

    paginated = decide_pr(
        [
            {"filename": f"docs/history/{index}.md", "status": "modified"}
            for index in range(100)
        ],
        body="<!-- artifact-impact: internal_diagnostics -->",
    )
    assert paginated.mode == "full"
    assert "require_pagination" in paginated.reason


def test_title_only_edit_uses_metadata_only_without_file_api():
    decision = decide_pr(
        RuntimeError("must not fetch files"),
        action="edited",
        changes={"title": {"from": "old"}},
    )
    assert decision == AdmissionDecision(
        mode="metadata-only",
        reason="edited_metadata_does_not_change_validation_subject",
        validation_class="metadata-only",
    )


@pytest.mark.parametrize("changed_field", ["body", "base"])
def test_body_or_base_edit_reclassifies_the_current_subject(changed_field):
    decision = decide_pr(
        [{"filename": "assets/css/phase8-base.css", "status": "modified"}],
        action="edited",
        changes={changed_field: {"from": "old"}},
    )
    assert decision.mode == "focused-ui"


def test_edited_event_without_change_evidence_is_fail_safe_full():
    decision = decide_pr(
        RuntimeError("must not fetch files"), action="edited", changes=None
    )
    assert decision.mode == "full"
    assert "edited_changes_missing" in decision.reason


def test_state_only_actions_are_not_supported_validation_events():
    for action in ("ready_for_review", "converted_to_draft"):
        decision = decide_pr(RuntimeError("must not fetch files"), action=action)
        assert decision.mode == "full"
        assert "action_not_supported" in decision.reason


def test_workflow_dispatch_remains_full_validation(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    assert decide_from_environment() == AdmissionDecision(
        mode="full",
        reason="event:workflow_dispatch",
        validation_class="full",
    )


def test_job_matrix_names_cover_every_validation_class():
    assert EXPECTED_SUCCESSFUL_JOBS == {
        "focused-docs": frozenset({ADMISSION_JOB, FOCUSED_JOB, AGGREGATE_JOB}),
        "focused-ui": frozenset(
            {ADMISSION_JOB, FOCUSED_JOB, BROWSER_JOB, AGGREGATE_JOB}
        ),
        "full": frozenset(
            {
                ADMISSION_JOB,
                STATIC_JOB,
                ORDINARY_JOB,
                COMMITTED_BASELINE_JOB,
                BROWSER_JOB,
                AGGREGATE_JOB,
            }
        ),
    }
