from ci_master_admission import (
    AGGREGATE_JOB,
    AdmissionDecision,
    decide_master_push,
    validation_subject_step,
)


REPOSITORY_API = "https://api.github.test/repos/owner/repo"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
MERGE_SHA = "c" * 40


def valid_responses():
    run_id = 42
    return {
        f"{REPOSITORY_API}/commits/{MERGE_SHA}": {
            "sha": MERGE_SHA,
            "parents": [{"sha": BASE_SHA}, {"sha": HEAD_SHA}],
        },
        f"{REPOSITORY_API}/commits/{MERGE_SHA}/pulls?per_page=100": [
            {
                "number": 119,
                "merged_at": "2026-07-28T07:38:13Z",
                "merge_commit_sha": MERGE_SHA,
                "base": {"ref": "master", "sha": BASE_SHA},
                "head": {"sha": HEAD_SHA},
            }
        ],
        (
            f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
            f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
        ): {
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
            ]
        },
        f"{REPOSITORY_API}/actions/runs/{run_id}/attempts/1/jobs?per_page=100": {
            "jobs": [
                {
                    "name": "Repository files, rules, and schemas",
                    "conclusion": "success",
                },
                {"name": "Pytest shard (ordinary)", "conclusion": "success"},
                {
                    "name": "Pytest shard (committed-baseline)",
                    "conclusion": "success",
                },
                {
                    "name": AGGREGATE_JOB,
                    "conclusion": "success",
                    "steps": [
                        {
                            "name": validation_subject_step(
                                119, BASE_SHA, HEAD_SHA
                            ),
                            "conclusion": "success",
                        }
                    ],
                },
            ]
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


def test_exact_merge_with_complete_successful_pr_validation_is_confirmed():
    assert decide(valid_responses()) == AdmissionDecision(
        mode="pr-confirmation",
        reason="exact_validated_merge",
        pull_request=119,
        workflow_run=42,
    )


def test_direct_push_without_two_merge_parents_falls_back_to_full():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}"]["parents"] = [
        {"sha": BASE_SHA}
    ]
    decision = decide(responses)
    assert decision.mode == "full"
    assert "two-parent_merge" in decision.reason


def test_pr_base_must_equal_first_merge_parent():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}/pulls?per_page=100"][0][
        "base"
    ]["sha"] = "d" * 40
    decision = decide(responses)
    assert decision.mode == "full"
    assert "base_head" in decision.reason


def test_all_full_validation_jobs_are_required():
    responses = valid_responses()
    jobs_url = f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    responses[jobs_url]["jobs"] = [
        job
        for job in responses[jobs_url]["jobs"]
        if job["name"] != "Pytest shard (committed-baseline)"
    ]
    decision = decide(responses)
    assert decision.mode == "full"
    assert "no_successful_full_validation" in decision.reason


def test_subject_step_must_match_final_merge_parents():
    responses = valid_responses()
    jobs_url = f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    responses[jobs_url]["jobs"][-1]["steps"][0]["name"] = (
        validation_subject_step(119, "d" * 40, HEAD_SHA)
    )
    decision = decide(responses)
    assert decision.mode == "full"


def test_validation_must_finish_before_merge():
    responses = valid_responses()
    runs_url = (
        f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
        f"event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
    )
    responses[runs_url]["workflow_runs"][0]["updated_at"] = (
        "2026-07-28T07:39:00Z"
    )
    decision = decide(responses)
    assert decision.mode == "full"


def test_api_failure_is_fail_safe_full_validation():
    responses = valid_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}"] = RuntimeError(
        "temporary API failure"
    )
    decision = decide(responses)
    assert decision.mode == "full"
    assert "temporary_API_failure" in decision.reason
