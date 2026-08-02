from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def load_workflow():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def all_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif value is not None:
        yield str(value)


def test_triggers_are_review_and_validation_only():
    workflow = load_workflow()
    triggers = workflow["on"]
    assert set(triggers) == {"pull_request", "push", "workflow_dispatch"}
    assert triggers["push"] == {"branches": ["master"]}
    assert triggers["pull_request"] == {}
    assert triggers["workflow_dispatch"] == {}


def test_permissions_and_concurrency_are_least_privilege():
    workflow = load_workflow()
    assert workflow["permissions"] == {
        "actions": "read",
        "contents": "read",
        "pull-requests": "read",
    }
    assert workflow["concurrency"] == {
        "group": "ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}",
        "cancel-in-progress": "true",
    }


def test_execution_jobs_are_bounded_and_use_current_official_actions():
    jobs = load_workflow()["jobs"]
    assert jobs["admission"]["timeout-minutes"] == "5"
    assert jobs["static-validation"]["timeout-minutes"] == "10"
    assert jobs["pytest"]["timeout-minutes"] == "30"
    assert jobs["post-merge-confirmation"]["timeout-minutes"] == "5"
    assert jobs["validate"]["timeout-minutes"] == "5"

    for job_name in ("admission", "static-validation", "pytest"):
        job = jobs[job_name]
        assert job["runs-on"] == "ubuntu-latest"
        steps = job["steps"]
        assert steps[0]["uses"] == "actions/checkout@v7.0.0"
        assert steps[0]["with"]["persist-credentials"] == "false"
        assert steps[1]["uses"] == "actions/setup-python@v6.3.0"
        assert steps[1]["with"]["python-version"] == "3.12"

    for job_name in ("static-validation", "pytest"):
        subject_step = jobs[job_name]["steps"][2]
        assert subject_step["name"] == "Verify checked-out PR merge subject"
        assert subject_step["if"] == "github.event_name == 'pull_request'"
        assert "git cat-file -p HEAD" in subject_step["run"]
        assert "github.event.pull_request.base.sha" in subject_step["run"]
        assert "github.event.pull_request.head.sha" in subject_step["run"]
        assert "exit 1" in subject_step["run"]


def test_pytest_shards_are_exact_marker_complements():
    pytest_job = load_workflow()["jobs"]["pytest"]
    assert pytest_job["strategy"]["fail-fast"] == "false"
    assert pytest_job["strategy"]["matrix"]["include"] == [
        {
            "shard": "ordinary",
            "marker_expression": "not committed_baseline",
        },
        {
            "shard": "committed-baseline",
            "marker_expression": "committed_baseline",
        },
    ]
    combined = "\n".join(
        step.get("run", "") for step in pytest_job["steps"]
    )
    assert '-m "${{ matrix.marker_expression }}"' in combined
    assert "-p ci_timing" in combined
    assert "ci_timing.py --summary" in combined
    assert "GITHUB_STEP_SUMMARY" in combined


def test_static_validation_and_aggregate_check_are_complete():
    jobs = load_workflow()["jobs"]
    static_commands = "\n".join(
        step.get("run", "") for step in jobs["static-validation"]["steps"]
    )
    for expected in (
        "-r requirements-dev.txt",
        "python -B -m ruff check src",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
    ):
        assert expected in static_commands

    aggregate = jobs["validate"]
    assert aggregate["name"] == "Repository validation (Python 3.12)"
    assert aggregate["if"] == "always()"
    assert aggregate["needs"] == [
        "admission",
        "static-validation",
        "pytest",
        "post-merge-confirmation",
    ]
    assert aggregate["steps"][0]["if"] == "github.event_name == 'pull_request'"
    assert "Validated merge subject:" in aggregate["steps"][0]["name"]
    command = aggregate["steps"][1]["run"]
    assert "needs.admission.result" in command
    assert "needs.admission.outputs.mode" in command
    assert "needs.static-validation.result" in command
    assert "needs.pytest.result" in command
    assert "needs.post-merge-confirmation.result" in command
    assert "exit 1" in command


def test_master_admission_is_fail_safe_and_full_suite_is_default():
    jobs = load_workflow()["jobs"]
    admission = jobs["admission"]
    assert admission["outputs"]["mode"] == "${{ steps.classify.outputs.mode }}"
    classify = admission["steps"][2]
    assert classify["run"] == "python -B ci_master_admission.py"
    assert classify["env"] == {"GITHUB_TOKEN": "${{ github.token }}"}

    assert jobs["static-validation"]["needs"] == "admission"
    assert jobs["pytest"]["needs"] == "admission"
    assert jobs["static-validation"]["if"] == (
        "needs.admission.outputs.mode == 'full'"
    )
    assert jobs["pytest"]["if"] == "needs.admission.outputs.mode == 'full'"
    assert jobs["post-merge-confirmation"]["if"] == (
        "needs.admission.outputs.mode == 'pr-confirmation'"
    )


def test_ci_cannot_fetch_production_data_or_write_repository():
    text = "\n".join(all_strings(load_workflow())).lower()
    forbidden = (
        "contents: write",
        "batch_mtgo.py",
        "fetch_videre_matches.py",
        "stats_standard.py",
        "stats_matchup.py",
        "weekly_pickup.py",
        "git push",
        "git commit",
        "pull_request_target",
        "schedule",
    )
    assert all(value not in text for value in forbidden)


def test_workflow_contains_no_secret_or_token_expression():
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    assert "secrets." not in text
    assert text.count("github.token") == 1
