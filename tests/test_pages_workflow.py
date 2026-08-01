"""P10-07 custom Pages workflow contract."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"


def _load():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_pages_workflow_builds_on_review_and_every_master_push() -> None:
    workflow = _load()
    assert set(workflow["on"]) == {"pull_request", "push", "workflow_dispatch"}
    assert workflow["on"]["push"] == {"branches": ["master"]}
    assert workflow["on"]["workflow_dispatch"] == {}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "pages",
        "cancel-in-progress": "false",
    }


def test_build_is_fresh_bounded_read_only_and_credential_free() -> None:
    job = _load()["jobs"]["build"]
    assert job["timeout-minutes"] == "10"
    assert job["permissions"] == {"contents": "read"}
    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@v7.0.0"
    assert steps[0]["with"] == {
        "fetch-depth": "0",
        "persist-credentials": "false",
    }
    assert steps[1]["uses"] == "actions/setup-python@v6.3.0"
    command = next(step["run"] for step in steps if "run" in step)
    assert "build_pages_artifact.py" in command
    assert '"$RUNNER_TEMP/pages-site"' in command
    assert '"$GITHUB_STEP_SUMMARY"' in command


def test_only_master_push_uploads_and_deploys() -> None:
    workflow = _load()
    condition = "github.event_name == 'push' && github.ref == 'refs/heads/master'"
    build_steps = workflow["jobs"]["build"]["steps"]
    configure = next(step for step in build_steps if "configure-pages" in step.get("uses", ""))
    upload = next(step for step in build_steps if "upload-pages-artifact" in step.get("uses", ""))
    assert configure == {
        "name": "Configure GitHub Pages",
        "if": condition,
        "uses": "actions/configure-pages@v5",
    }
    assert upload["if"] == condition
    assert upload["uses"] == "actions/upload-pages-artifact@v4"
    assert upload["with"] == {"path": "${{ runner.temp }}/pages-site"}

    deploy = workflow["jobs"]["deploy"]
    assert deploy["if"] == condition
    assert deploy["needs"] == "build"
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert deploy["environment"] == {
        "name": "github-pages",
        "url": "${{ steps.deployment.outputs.page_url }}",
    }
    assert deploy["steps"] == [
        {
            "name": "Deploy to GitHub Pages",
            "id": "deployment",
            "uses": "actions/deploy-pages@v4",
        }
    ]


def test_pages_workflow_has_no_secret_or_repository_write_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    assert "secrets." not in text
    assert "contents: write" not in text
    assert "git push" not in text
    assert "schedule:" not in text
