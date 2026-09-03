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


def _melee_workflow():
    return yaml.load(
        PRODUCTION_WORKFLOWS[1].read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


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
    classifier = by_name["Validate classifier rule contracts"]
    assert "classifier-contract" in classifier["if"]
    assert "classifier-adapter" in classifier["if"]
    assert "rules-standard" in classifier["if"]
    assert "rules-modern" in classifier["if"]
    assert "tests/test_classifier_rule_contracts.py" in classifier["run"]
    assert "pytest-classifier-contract" in classifier["run"]
    assert "::test_standard_owner_rule_contracts" in classifier["run"]
    assert "::test_modern_owner_rule_contracts" in classifier["run"]
    assert "::test_melee_split_card_adapter_contract" in classifier["run"]
    assert classifier["run"].count("python -B -m pytest") == 1
    assert "schema-contract" in by_name["Validate changed public JSON contracts"]["if"]
    assert "schema-documents" in by_name["Validate changed public JSON contracts"]["if"]
    assert "top8-restatement" in by_name["Validate Top 8 restatement"]["if"]
    cache = by_name["Validate Landing card-image cache contract"]
    assert "landing-card-image-cache" in cache["if"]
    assert "tests/test_landing_card_image_cache.py" in cache["run"]
    localization = by_name["Validate card-localization contract"]
    assert "card-localization" in localization["if"]
    assert "tests/test_card_names.py" in localization["run"]
    assert "tests/test_simple_card_localization.py" in localization["run"]
    browser_localization = by_name["Validate card-localization browser selection"]
    assert "card-localization" in browser_localization["if"]
    assert "tests/js/phase8-card-localization.test.js" in browser_localization["run"]
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
        "test_classifier_rule_contracts.py",
        "validate_schemas.py",
        "--changed-from",
        "test_mtgo_top8_restatement.py",
        "test_ci_master_admission.py",
        "test_ci_workflow.py",
        "test_github_publication_preflight.py",
        "test_validate_repository_modes.py",
    ):
        assert required in commands
    assert commands.count("node --test") == 1
    checkout = by_name["Check out repository without persisted credentials"]
    assert checkout["with"]["fetch-depth"] == "0"
    repository_validation = by_name["Validate repository files and references"]["run"]
    assert "--changed-from" in repository_validation
    assert "github.event.pull_request.base.sha" in repository_validation


def test_production_repository_validation_is_explicitly_full():
    expected_by_path = {
        UPDATE_WORKFLOW: "python -B validate_repository.py --full",
        PRODUCTION_WORKFLOWS[1]: "python -B validate_repository.py --full-candidate",
    }
    for path, expected in expected_by_path.items():
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        commands = [
            line.strip()
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            for line in step.get("run", "").splitlines()
            if "validate_repository.py" in line
        ]
        assert commands == [expected], path


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


def test_melee_candidate_checkpoints_retained_evidence_before_derived_work() -> None:
    workflow = _melee_workflow()
    job = workflow["jobs"]["candidate"]
    by_name = {step["name"]: step for step in job["steps"]}
    names = list(by_name)

    assert names.index("Snapshot Melee candidate baseline") < names.index(
        "Resolve exact event review branch"
    )
    assert names.index("Retain normalized event") < names.index(
        "Checkpoint immutable source and normalized event"
    ) < names.index("Classify submitted decks strictly")

    resume = by_name["Resolve exact event review branch"]["run"]
    assert "read -r STATUS CHANGED_PATH REST" in resume
    assert 'case "$CHANGED_PATH" in' in resume
    assert "${CHANGED_PATH}" in resume
    assert "read -r STATUS PATH REST" not in resume
    for required in (
        'git ls-remote --exit-code --heads origin "refs/heads/${BRANCH}"',
        "git fetch --no-tags origin",
        'git diff --name-status "$MERGE_BASE" "$REMOTE_REF"',
        '"data_raw/melee/${EVENT_ID}/"*',
        '"data/${FORMAT}/melee/events/${EVENT_ID}.json"',
        '"stats/${FORMAT}/melee/events/${EVENT_ID}/"*',
        '"stats/catalog.json"',
        'git checkout -B "$BRANCH"',
        'git merge-base --is-ancestor "$GITHUB_SHA" HEAD',
        'git merge --no-edit "$GITHUB_SHA"',
    ):
        assert required in resume
    assert resume.index("git diff --name-status") < resume.index("git checkout -B")
    assert "outside the event boundary" in resume
    for prohibited in ("--force", "git pull", "git rebase"):
        assert prohibited not in resume

    checkpoint = by_name["Checkpoint immutable source and normalized event"]
    assert checkpoint["if"] == (
        "steps.snapshot.outputs.source_mode == 'fetched' || "
        "steps.review-branch.outputs.resumed == 'true'"
    )
    command = checkpoint["run"]
    for required in (
        'git add -- "data_raw/melee/${EVENT_ID}/"',
        '"data/${FORMAT}/melee/events/${EVENT_ID}.json"',
        "chore: checkpoint Melee event ${EVENT_ID} source",
        'git push origin "HEAD:refs/heads/${BRANCH}"',
    ):
        assert required in command
    for prohibited in ("classifications", "opportunities", "stats/", "--force"):
        assert prohibited not in command

    verify = by_name["Verify immutable checkpoint"]
    assert verify["if"] == "steps.checkpoint.outputs.commit != ''"
    assert "git ls-remote origin" in verify["run"]


def test_melee_candidate_requires_a_closed_operation_and_exact_recovery_checkpoint():
    workflow = _melee_workflow()
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"event_id", "operation", "retained_checkpoint"}
    assert "default" not in inputs["event_id"]
    assert inputs["operation"]["required"] == "true"
    assert inputs["retained_checkpoint"]["default"] == ""

    by_name = {step["name"]: step for step in workflow["jobs"]["candidate"]["steps"]}
    preflight = by_name["Validate candidate operation contract"]["run"]
    assert "collect-new|resume-retained" in preflight
    assert "^[0-9a-f]{40}$" in preflight
    resume = by_name["Resolve exact event review branch"]["run"]
    assert 'REMOTE_SHA="$EXPECTED_CHECKPOINT"' not in resume
    assert 'test "$REMOTE_SHA" = "$EXPECTED_CHECKPOINT"' in resume
    assert 'test "$(git rev-parse "$REMOTE_REF")" = "$EXPECTED_CHECKPOINT"' in resume
    source = by_name["Resolve explicitly selected event source"]["run"]
    assert 'case "$OPERATION" in' in source
    assert "resume-retained)" in source
    assert "collect-new)" in source


def test_melee_candidate_stages_exact_scope_before_complete_validation():
    workflow = _melee_workflow()
    steps = workflow["jobs"]["candidate"]["steps"]
    by_name = {step["name"]: step for step in steps}
    names = list(by_name)
    assert names.index("Validate Melee candidate scope") < names.index(
        "Stage validated candidate scope"
    ) < names.index("Validate repository, rules, and Schemas")
    stage = by_name["Stage validated candidate scope"]["run"]
    assert 'git add -- "data_raw/melee/${EVENT_ID}/"' in stage
    assert "git diff --quiet" in stage
    validation = by_name["Validate repository, rules, and Schemas"]["run"]
    assert "validate_repository.py --full-candidate" in validation
    assert "schemas/melee-data-manifest.json" in validation
    publish = by_name["Commit and push review branch"]["run"]
    assert "git add" not in publish


def test_melee_candidate_binds_browser_smoke_to_exact_staged_tree():
    workflow = _melee_workflow()
    steps = workflow["jobs"]["candidate"]["steps"]
    by_name = {step["name"]: step for step in steps}
    names = list(by_name)
    ordered = (
        "Checkpoint immutable source and normalized event",
        "Classify submitted decks strictly",
        "Stage validated candidate scope",
        "Validate repository, rules, and Schemas",
        "Set up Node.js 24 for candidate consumer smoke",
        "Install pinned browser-test package",
        "Install Chromium with runner dependencies",
        "Bind exact staged candidate tree",
        "Render exact Melee candidate in Chromium",
        "Confirm browser-validated candidate tree",
        "Commit and push review branch",
    )
    assert [names.index(name) for name in ordered] == sorted(
        names.index(name) for name in ordered
    )

    bind = by_name["Bind exact staged candidate tree"]
    assert bind["id"] == "candidate-tree"
    assert "git diff --quiet" in bind["run"]
    assert "git write-tree" in bind["run"]
    assert 'echo "tree=$CANDIDATE_TREE" >> "$GITHUB_OUTPUT"' in bind["run"]

    smoke = by_name["Render exact Melee candidate in Chromium"]
    assert smoke["env"] == {
        "TABLETOP_CANDIDATE_FORMAT": "${{ steps.whitelist.outputs.format }}",
        "TABLETOP_CANDIDATE_EVENT_ID": "${{ inputs.event_id }}",
    }
    assert "tests/browser/production-pages.spec.js" in smoke["run"]
    assert "--grep" in smoke["run"]
    assert "Tabletop entry renders candidate-derived data" in smoke["run"]

    confirm = by_name["Confirm browser-validated candidate tree"]["run"]
    assert "git diff --quiet" in confirm
    assert "git write-tree" in confirm
    assert "${{ steps.candidate-tree.outputs.tree }}" in confirm

    publish = by_name["Commit and push review branch"]["run"]
    assert "git add" not in publish
    assert "git write-tree" in publish
    assert "git rev-parse 'HEAD^{tree}'" in publish
    assert "${{ steps.candidate-tree.outputs.tree }}" in publish
    assert publish.index("git commit") < publish.rindex("git rev-parse 'HEAD^{tree}'")

    after_smoke = steps[names.index("Render exact Melee candidate in Chromium") + 1 :]
    commands = "\n".join(step.get("run", "") for step in after_smoke)
    for prohibited in ("git add", "mtgmeta.", "validate_schemas.py", "ruff", "prettier"):
        assert prohibited not in commands


def test_production_candidate_is_built_once_and_published_with_immutable_evidence():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    fetch = workflow["jobs"]["fetch"]
    build = workflow["jobs"]["build"]
    publish = workflow["jobs"]["publish"]
    assert "baseline" not in workflow["jobs"]
    assert set(publish["outputs"]) == {
        "failure-kind",
        "observed-master",
        "published-commit",
        "recovery-dispatched",
        "source-commit",
    }
    assert publish["outputs"]["source-commit"] == "${{ github.sha }}"
    assert "stale-base" in publish["outputs"]["failure-kind"]
    assert "publication-base" in publish["outputs"]["observed-master"]
    assert "stale-base-recovery" in publish["outputs"]["recovery-dispatched"]
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


def test_stale_production_base_restarts_once_without_reusing_candidate():
    workflow = yaml.load(
        UPDATE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    dispatch_inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(dispatch_inputs) == {"stale_base_retry_of"}
    assert dispatch_inputs["stale_base_retry_of"] == {
        "description": "Internal parent run ID for one bounded stale-base recovery",
        "required": "false",
        "default": "",
        "type": "string",
    }

    publish = workflow["jobs"]["publish"]
    assert publish["permissions"] == {"actions": "write", "contents": "write"}
    by_name = {step["name"]: step for step in publish["steps"]}
    names = list(by_name)
    assert names.index("Check publication base is current") < names.index(
        "Download immutable validated output"
    )

    base = by_name["Check publication base is current"]
    assert base["id"] == "publication-base"
    for required in (
        "git ls-remote origin refs/heads/master",
        'if [ "$REMOTE_MASTER" != "$GITHUB_SHA" ]',
        'echo "stale=true"',
        'echo "stale=false"',
        'echo "observed-master=$REMOTE_MASTER"',
    ):
        assert required in base["run"]

    current_base = "steps.publication-base.outputs.stale == 'false'"
    assert current_base in by_name["Download immutable validated output"]["if"]
    assert current_base in by_name["Verify and restore validated output"]["if"]

    publish_step = by_name["Commit and push production evidence"]
    assert current_base in publish_step["if"]
    for required in (
        "git push origin HEAD:master",
        'if [ "$PUSH_STATUS" -ne 0 ]',
        "git ls-remote origin refs/heads/master",
        'if [ "$REMOTE_MASTER" != "$GITHUB_SHA" ]',
        'echo "status=stale"',
        'echo "status=published"',
    ):
        assert required in publish_step["run"]
    for prohibited in ("git pull", "git rebase", "--force", "validated-output-sha256"):
        assert prohibited not in by_name["Request one stale-base recovery"]["with"][
            "script"
        ]

    recovery = by_name["Request one stale-base recovery"]
    assert recovery["id"] == "stale-base-recovery"
    assert "always()" in recovery["if"]
    assert "inputs.stale_base_retry_of == ''" in recovery["if"]
    script = recovery["with"]["script"]
    for required in (
        'workflow_id: "update.yml"',
        'ref: "master"',
        "stale_base_retry_of: String(context.runId)",
        'core.setOutput("dispatched", "true")',
    ):
        assert required in script

    stop = by_name["Stop stale publication"]
    assert "always()" in stop["if"]
    assert 'exit 1' in stop["run"]
    assert "stale-base-recovery" in stop["run"]

    verify = by_name["Verify published master commit and clean workspace"]
    assert "steps.publish.outputs.status == 'published'" in verify["if"]
    for required in (
        "git fetch --no-tags origin master",
        'git merge-base --is-ancestor "$LOCAL_SHA" "$REMOTE_SHA"',
        "remains an ancestor of current master",
    ):
        assert required in verify["run"]

    notify = workflow["jobs"]["notify"]
    failed_stage = {step["name"]: step for step in notify["steps"]}[
        "Identify the failed production stage"
    ]
    assert failed_stage["env"]["PUBLISH_FAILURE_KIND"] == (
        "${{ needs.publish.outputs.failure-kind }}"
    )
    issue_script = next(
        step["with"]["script"]
        for step in notify["steps"]
        if step["name"] == "Create or update the stage failure issue"
    )
    for required in (
        "Failure kind",
        "Started from",
        "Observed master",
        "Bounded recovery dispatched",
    ):
        assert required in issue_script


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
    localization_cache = workflow["jobs"]["localization-cache"]
    assert localization_cache["timeout-minutes"] == "30"
    assert localization_cache["permissions"] == {
        "actions": "read",
        "contents": "read",
    }
    localization_steps = {
        step["name"]: step for step in localization_cache["steps"]
    }
    assert "head_branch === \"master\"" in localization_steps[
        "Find exact trusted simple card localization cache"
    ]["with"]["script"]
    assert localization_steps[
        "Build missing simple card localization cache"
    ]["if"] == "steps.localization-cache-artifact.outputs.cache-hit != 'true'"
    localization_commands = "\n".join(
        step.get("run", "") for step in localization_cache["steps"]
    )
    assert "tools/build_simple_card_localization.py subject" in localization_commands
    assert "tools/build_simple_card_localization.py verify" in localization_commands
    assert workflow["jobs"]["build"]["timeout-minutes"] == "20"
    push_paths = set(workflow["on"]["push"]["paths"])
    assert {"index.html", "melee/**", "stats/**", "data/**"} <= push_paths
    assert {
        "schemas/landing-card-image-cache.schema.json",
        "src/mtgmeta/card_names.py",
        "src/mtgmeta/data/om1_spm_aliases.json",
        "tools/build_landing_card_image_cache.py",
        "tools/build_simple_card_localization.py",
    } <= push_paths
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
    assert build["needs"] == "localization-cache"
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
    for required in (
        "tools/build_landing_card_image_cache.py subject",
        "tools/build_landing_card_image_cache.py build",
        "tools/build_landing_card_image_cache.py verify",
        "tools/build_simple_card_localization.py verify",
        '--overlay "landing_card_images=$RUNNER_TEMP/landing-card-image-cache"',
        '--overlay "card_localization=$RUNNER_TEMP/card-localization"',
    ):
        assert required in commands
    assert "tools/build_simple_card_localization.py build" not in commands
    localization_handoff = next(
        step
        for step in build["steps"]
        if step["name"] == "Download verified simple card localization handoff"
    )
    assert localization_handoff["with"]["name"] == (
        "simple-card-localization-handoff-${{ github.run_attempt }}"
    )
    cache_upload = next(
        step
        for step in build["steps"]
        if step["name"] == "Retain new Landing card-image cache"
    )
    assert cache_upload["uses"] == "actions/upload-artifact@v4.6.2"
    assert cache_upload["with"]["retention-days"] == "90"
    assert "refs/heads/master" in cache_upload["if"]
    deploy_commands = "\n".join(
        step.get("run", "") for step in workflow["jobs"]["deploy"]["steps"]
    )
    for resource in ("index.html", "melee/index.html", "stats/catalog.json"):
        assert resource in deploy_commands
