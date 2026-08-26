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


def test_targeted_commands_map_directly_to_named_changed_contracts():
    steps = _workflow()["jobs"]["targeted-validation"]["steps"]
    by_name = {step["name"]: step for step in steps}
    assert "docs-history" in by_name["Validate live documentation policy"]["if"]
    assert "code" in by_name["Check maintained Python package"]["if"]
    assert "rules-standard" in by_name["Validate changed archetype rules"]["if"]
    assert "rules-modern" in by_name["Validate changed archetype rules"]["if"]
    assert "schema-contract" in by_name["Validate changed public JSON contracts"]["if"]
    assert "schema-documents" in by_name["Validate changed public JSON contracts"]["if"]
    assert "top8-restatement" in by_name["Validate Top 8 restatement"]["if"]
    assert "ci-admission" in by_name["Validate changed governance contracts"]["if"]
    assert "ci-workflow" in by_name["Validate changed governance contracts"]["if"]
    package_install = by_name["Install maintained package for code and data checks"]
    assert "code" in package_install["if"]
    assert "data" in package_install["if"]
    commands = "\n".join(step.get("run", "") for step in steps)
    for required in (
        "validate_repository.py",
        "pip install --disable-pip-version-check --no-deps .",
        "test_documentation_history.py",
        "ruff check src",
        "-m mypy",
        "validate_rules.py",
        "validate_schemas.py",
        "--changed-from",
        "test_mtgo_top8_restatement.py",
        "test_ci_master_admission.py",
        "test_ci_workflow.py",
        "test_github_publication_preflight.py",
        "test_validate_repository_modes.py",
    ):
        assert required in commands
    assert "node --test" not in commands
    checkout = by_name["Check out repository without persisted credentials"]
    assert checkout["with"]["fetch-depth"] == "0"
    repository_validation = by_name["Validate repository files and references"]["run"]
    assert "--changed-from" in repository_validation
    assert "github.event.pull_request.base.sha" in repository_validation


def test_production_repository_validation_is_explicitly_full():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    step = next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step["name"] == "Validate repository files and references"
    )
    assert step["run"] == "python -B validate_repository.py --full"


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
    assert "Admission reason: ${{ needs.admission.outputs.reason }}" in command
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
    build = workflow["jobs"]["build"]
    publish = workflow["jobs"]["publish"]
    assert "baseline" not in workflow["jobs"]
    assert publish["outputs"] == {
        "published-commit": "${{ steps.verify.outputs.commit }}"
    }
    assert "generation-needed" in fetch["outputs"]
    assert "generation-needed" in build["if"]
    assert build["needs"] == "fetch"
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


def test_production_build_orders_landing_screening_before_landing_and_catalog():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    steps = workflow["jobs"]["build"]["steps"]
    names = [step["name"] for step in steps]

    screening_index = names.index("Prepare Landing screening candidates when absent")
    landing_index = names.index("Build latest MTGO Landing documents")
    metadata_index = names.index("Generate product metadata")
    catalog_index = names.index("Generate format-first consumer catalog")

    assert screening_index < landing_index < metadata_index < catalog_index
    assert "landing-review prepare --if-absent" in steps[screening_index]["run"]
    assert "build-landing" in steps[landing_index]["run"]


def test_mtgo_fetch_retries_only_explicit_transient_source_failures():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    fetch = workflow["jobs"]["fetch"]
    assert fetch["timeout-minutes"] == "45"
    assert fetch["permissions"] == {"actions": "read", "contents": "read"}
    assert fetch["env"]["MTGO_TRANSIENT_EXIT_CODE"] == "75"

    step = next(
        step
        for step in fetch["steps"]
        if step["name"] == "Fetch every pending MTGO input operation"
    )
    command = step["run"]
    for required in (
        "RECOVERY_DELAYS=(120 300)",
        "fetch_events_with_recovery",
        "for attempt in 1 2 3",
        'if [ "$attempt" -eq 3 ]',
        '"$MTGO_TRANSIENT_EXIT_CODE"',
        'return "$status"',
        'sleep "$delay"',
        "mtgo_fetch_checkpoint.py complete",
    ):
        assert required in command


def test_weekly_readiness_uses_the_verified_publication_and_private_handoff():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert workflow["on"]["schedule"] == [{"cron": "0 9 * * *"}]
    readiness = workflow["jobs"]["weekly-readiness"]
    assert readiness["permissions"] == {"contents": "read"}
    assert readiness["env"] == {"PYTHONPATH": "src"}
    assert readiness["needs"] == ["fetch", "publish"]
    assert "generation-needed == 'true'" in readiness["if"]
    assert "generation-needed == 'false'" in readiness["if"]
    checkout = next(
        step
        for step in readiness["steps"]
        if step["name"] == "Check out the verified production publication"
    )
    assert checkout["with"]["ref"] == (
        "${{ needs.publish.outputs.published-commit || github.sha }}"
    )
    commands = "\n".join(step.get("run", "") for step in readiness["steps"])
    for required in (
        "generate_weekly_maintenance_readiness.py",
        "--publication-sha",
        "--production-run-id",
        "--github-output",
        "No Codex scheduled task",
    ):
        assert required in commands
    upload = next(
        step
        for step in readiness["steps"]
        if step["name"] == "Upload the private weekly handoff"
    )
    assert upload["with"]["retention-days"] == "21"
    assert upload["with"]["name"] == "${{ steps.generate.outputs.artifact-name }}"
    assert "weekly-maintenance-readiness-${WEEK}" in commands

    notify = workflow["jobs"]["weekly-readiness-notify"]
    assert notify["permissions"] == {"actions": "read", "issues": "write"}
    assert not any("checkout" in step.get("uses", "") for step in notify["steps"])
    script = next(
        step["with"]["script"]
        for step in notify["steps"]
        if step["name"] == "Create or update the deduplicated readiness issue"
    )
    for required in (
        "weekly-maintenance:${week}",
        "readiness-digest:",
        "const presentations = {",
        "Weekly MTGO maintenance is blocked",
        "Weekly MTGO maintenance is completed",
        "Weekly MTGO maintenance requires revalidation",
        "revalidation_required",
        'state: "closed"',
        "existing.state === presentation.state",
        "existing.body?.includes(digestMarker)",
        "unresolved_unknown_count",
        "outside_review_week_unresolved_unknown_count",
        "outside the review week in the retained-corpus queue",
        "accepted_intentional_unknown_count",
        "complete main deck and sideboard",
        "random card piles",
        "readiness.landing.status",
        "optional_draft_status",
        "human final copy may be edited, replaced, omitted",
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
    checkout = next(
        step
        for step in build["steps"]
        if step["name"] == "Check out full history without persisted credentials"
    )
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    commands = "\n".join(step.get("run", "") for step in build["steps"])
    for required in (
        "--verify-production-evidence",
        "diff --recursive --brief --no-dereference",
        "Published commit content does not match the validated output",
        "Validated output contains a path outside the production boundary",
        "Production evidence is accepted only for a master workflow dispatch",
    ):
        assert required in commands
    evidence = next(
        step
        for step in build["steps"]
        if step["name"] == "Admit exact production publication evidence"
    )
    assert evidence["env"]["PAGES_SUBJECT_COMMIT"] == "${{ github.sha }}"
    assert "published-output.tar" not in commands
    assert all(token not in commands for token in ("pytest", "playwright", "node --test"))
    deploy_commands = "\n".join(
        step.get("run", "") for step in workflow["jobs"]["deploy"]["steps"]
    )
    for resource in ("index.html", "melee/index.html", "stats/catalog.json"):
        assert resource in deploy_commands
