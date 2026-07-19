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
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}",
        "cancel-in-progress": "true",
    }


def test_job_is_bounded_and_uses_current_official_action_versions():
    job = load_workflow()["jobs"]["validate"]
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == "15"
    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@v7.0.0"
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"] == "actions/setup-python@v6.3.0"
    assert steps[1]["with"]["python-version"] == "3.12"


def test_all_required_checks_and_summary_are_present():
    steps = load_workflow()["jobs"]["validate"]["steps"]
    commands = [step.get("run", "") for step in steps]
    combined = "\n".join(commands)
    for expected in (
        "-r requirements-dev.txt",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
        "-m pytest",
        "GITHUB_STEP_SUMMARY",
    ):
        assert expected in combined
    assert steps[-1]["if"] == "always()"


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
    assert "github.token" not in text
