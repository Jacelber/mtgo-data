from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
UPDATE_WORKFLOW = ROOT / ".github" / "workflows" / "update.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PRODUCTION_WORKFLOWS = (
    ROOT / ".github" / "workflows" / "update.yml",
    ROOT / ".github" / "workflows" / "fetch_melee.yml",
)


def _workflow():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif value is not None:
        yield str(value)


def test_triggers_permissions_and_concurrency_remain_bounded():
    workflow = _workflow()
    assert workflow["on"] == {
        "pull_request": {"types": ["opened", "synchronize", "reopened", "edited"]},
        "push": {"branches": ["master"]},
        "workflow_dispatch": {},
    }
    assert workflow["permissions"] == {
        "actions": "read",
        "contents": "read",
        "pull-requests": "read",
    }
    assert workflow["concurrency"]["cancel-in-progress"] == "true"


def test_pr_path_contains_only_admission_targeted_and_aggregate_jobs():
    jobs = _workflow()["jobs"]
    assert set(jobs) == {
        "admission",
        "targeted-validation",
        "post-merge-confirmation",
        "validate",
    }
    assert jobs["targeted-validation"]["name"] == "Targeted PR validation"
    assert jobs["targeted-validation"]["if"] == (
        "needs.admission.outputs.mode == 'targeted'"
    )
    assert jobs["targeted-validation"]["timeout-minutes"] == "5"
    assert jobs["validate"]["needs"] == [
        "admission",
        "targeted-validation",
        "post-merge-confirmation",
    ]


def test_targeted_commands_map_directly_to_changed_artifact_categories():
    steps = _workflow()["jobs"]["targeted-validation"]["steps"]
    by_name = {step["name"]: step for step in steps}
    assert "docs" in by_name["Validate live documentation policy"]["if"]
    assert "code" in by_name["Check maintained Python package"]["if"]
    assert "data" in by_name["Validate rules and public JSON schemas"]["if"]
    assert "governance" in by_name["Validate CI control contracts"]["if"]
    commands = "\n".join(step.get("run", "") for step in steps)
    for required in (
        "validate_repository.py",
        "test_documentation_history.py",
        "ruff check src",
        "-m mypy",
        "validate_rules.py",
        "validate_schemas.py",
        "test_ci_master_admission.py",
        "test_ci_workflow.py",
    ):
        assert required in commands
    assert "node --test" not in commands


def test_pr_workflow_contains_no_long_or_repeated_validation():
    text = "\n".join(_strings(_workflow())).lower()
    for retired in (
        "committed_baseline",
        "npm run test:browser",
        "playwright install",
        "pytest shard",
        "complete validation",
        "batch_mtgo.py",
        "git push",
        "git commit",
        "contents: write",
    ):
        assert retired not in text


def test_unknown_paths_fail_fast_in_aggregate_without_running_targeted_job():
    jobs = _workflow()["jobs"]
    command = jobs["validate"]["steps"][2]["run"]
    assert '= "unclassified"' in command
    assert "owner classification" in command
    assert "catch-all tests were run" in command
    assert "exit 1" in command


def test_exact_merge_confirmation_remains_evidence_bound():
    job = _workflow()["jobs"]["post-merge-confirmation"]
    assert job["if"] == "needs.admission.outputs.mode == 'pr-confirmation'"
    command = job["steps"][0]["run"]
    for required in (
        "github.event_name",
        "refs/heads/master",
        "pull_request",
        "workflow_run",
        "validation_class",
        "exact_validated_merge:",
    ):
        assert required in command


def test_workflow_contains_no_secret_expression():
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    assert "secrets." not in text
    assert text.count("github.token") == 1


def test_production_pytest_commands_are_explicit_and_external_temped():
    commands = []
    for path in PRODUCTION_WORKFLOWS:
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        commands.extend(
            step["run"]
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if "-m pytest" in step.get("run", "")
        )

    assert commands
    assert all("tests/" in command for command in commands)
    assert all("--basetemp=" in command for command in commands)
    assert not any(command.strip() in {"python -m pytest", "python -B -m pytest"} for command in commands)


def test_production_candidate_is_built_once_and_published_with_immutable_evidence():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    fetch = workflow["jobs"]["fetch"]
    baseline = workflow["jobs"]["baseline"]
    build = workflow["jobs"]["build"]
    publish = workflow["jobs"]["publish"]
    assert "generation-needed" in fetch["outputs"]
    assert baseline["needs"] == "fetch"
    assert "generation-needed" in baseline["if"]
    assert "generation-needed" in build["if"]
    assert set(build["outputs"]) == {
        "generation-subject-sha256",
        "validated-output-sha256",
    }
    commands = "\n".join(
        step.get("run", "")
        for job in (fetch, build, publish)
        for step in job["steps"]
    )
    for required in (
        "Generation-Subject-SHA256",
        "Validated-Output-SHA256",
        "Production-Run",
        "Production-Attempt",
        "Production-Source",
        "--allow-empty",
        "--sort=name",
        "generation-subject.txt",
    ):
        assert required in commands
    dispatch = next(
        step
        for step in publish["steps"]
        if step["name"] == "Dispatch Pages deployment for published data"
    )
    script = dispatch["with"]["script"]
    for required in (
        "publication_commit",
        "producer_run_id",
        "producer_run_attempt",
        "source_commit",
        "generation_subject_sha256",
        "validated_output_sha256",
    ):
        assert required in script


def test_pages_runs_only_for_site_inputs_and_reuses_exact_production_evidence():
    workflow = yaml.load(
        PAGES_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    push_paths = set(workflow["on"]["push"]["paths"])
    assert {"index.html", "melee/**", "stats/**", "data/**"} <= push_paths
    assert not ({"docs/**", "tests/**", ".github/workflows/ci.yml"} & push_paths)
    assert set(workflow["on"]["workflow_dispatch"]["inputs"]) == {
        "publication_commit",
        "producer_run_id",
        "producer_run_attempt",
        "source_commit",
        "generation_subject_sha256",
        "validated_output_sha256",
    }
    build = workflow["jobs"]["build"]
    assert build["permissions"] == {"actions": "read", "contents": "read"}
    commands = "\n".join(step.get("run", "") for step in build["steps"])
    for required in (
        "--verify-production-evidence",
        "diff --recursive --brief --no-dereference",
        "Published commit content does not match the validated output",
        "Validated output contains a path outside the production boundary",
    ):
        assert required in commands
    assert "published-output.tar" not in commands
    assert all(token not in commands for token in ("pytest", "playwright", "node --test"))
    deploy_commands = "\n".join(
        step.get("run", "") for step in workflow["jobs"]["deploy"]["steps"]
    )
    for resource in ("index.html", "melee/index.html", "stats/catalog.json"):
        assert resource in deploy_commands
