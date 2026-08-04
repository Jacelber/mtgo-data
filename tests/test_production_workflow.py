from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
UPDATE = WORKFLOWS / "update.yml"


def load_update():
    return yaml.load(UPDATE.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def job(name):
    return load_update()["jobs"][name]


def steps(name):
    return job(name)["steps"]


def run_commands(name):
    return [step.get("run", "") for step in steps(name)]


def command_index(name, fragment):
    commands = run_commands(name)
    return next(index for index, command in enumerate(commands) if fragment in command)


def test_mtgo_remains_the_only_scheduled_production_workflow():
    assert not (WORKFLOWS / "scrape.yml").exists()
    assert UPDATE.exists()
    assert (ROOT / "src" / "mtgmeta" / "mtgo" / "__main__.py").exists()
    assert sorted(path.name for path in WORKFLOWS.glob("*.yml")) == [
        "ci.yml",
        "fetch_melee.yml",
        "pages.yml",
        "update.yml",
    ]


def test_update_keeps_its_schedule_master_boundary_and_concurrency():
    workflow = load_update()
    assert set(workflow["on"]) == {"workflow_dispatch", "schedule"}
    assert workflow["on"]["workflow_dispatch"] == {}
    assert workflow["on"]["schedule"] == [{"cron": "0 20 * * *"}]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "production-data-update",
        "cancel-in-progress": "false",
    }
    assert set(workflow["jobs"]) == {"fetch", "build", "publish", "notify"}
    assert all(job(name)["if"] == "github.ref == 'refs/heads/master'" for name in ("fetch", "build", "publish"))


def test_fetch_build_and_publish_have_separate_minimum_permissions():
    assert job("fetch")["permissions"] == {"actions": "read", "contents": "read"}
    assert job("build")["permissions"] == {"contents": "read"}
    assert job("publish")["permissions"] == {"contents": "write"}
    assert job("notify")["permissions"] == {"issues": "write"}
    assert job("build")["needs"] == "fetch"
    assert job("publish")["needs"] == "build"
    assert job("notify")["needs"] == ["fetch", "build", "publish"]


def test_every_job_is_bounded_and_uses_the_same_immutable_trigger_commit():
    for name in ("fetch", "build", "publish"):
        assert job(name)["runs-on"] == "ubuntu-latest"
        assert int(job(name)["timeout-minutes"]) > 0
        checkout = next(step for step in steps(name) if step.get("uses") == "actions/checkout@v7.0.0")
        assert checkout["with"]["fetch-depth"] == "0"
        assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert next(step for step in steps("fetch") if step.get("uses") == "actions/checkout@v7.0.0")["with"][
        "persist-credentials"
    ] == "false"
    assert next(step for step in steps("build") if step.get("uses") == "actions/checkout@v7.0.0")["with"][
        "persist-credentials"
    ] == "false"
    assert next(step for step in steps("publish") if step.get("uses") == "actions/checkout@v7.0.0")["with"][
        "persist-credentials"
    ] == "true"


def test_all_project_workflows_use_only_python_3_12():
    for path in WORKFLOWS.glob("*.yml"):
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        for workflow_job in workflow["jobs"].values():
            for step in workflow_job.get("steps", []):
                if step.get("uses") == "actions/setup-python@v6.3.0":
                    assert step["with"]["python-version"] == "3.12", path


def test_fetch_runs_clean_regression_then_snapshots_and_collects_only_inputs():
    ordered = [
        "-r requirements-dev.txt",
        "-m pytest",
        "validate_production_candidate.py snapshot",
        "fetch-events",
        "fetch-matches",
    ]
    indexes = [command_index("fetch", fragment) for fragment in ordered]
    assert indexes == sorted(indexes)
    assert command_index("fetch", "-m pytest") < command_index("fetch", "fetch-events")
    assert command_index("fetch", "validate_production_candidate.py snapshot") < command_index(
        "fetch", "fetch-events"
    )
    candidate_package = next(
        step["run"] for step in steps("fetch") if step["name"] == "Package fetched candidate for the build job"
    )
    assert "tar -cf" in candidate_package
    assert "sha256sum" in candidate_package
    fetch_text = UPDATE.read_text(encoding="utf-8")
    assert "mtgo-fetch-candidate" in fetch_text
    assert "actions/upload-artifact@v4.6.2" in fetch_text
    assert "retention-days: 1" in fetch_text
    assert "if-no-files-found: error" in fetch_text


def test_workflow_summary_backticks_are_literal_shell_text():
    workflow = UPDATE.read_text(encoding="utf-8")
    assert "\\\\`" not in workflow
    assert 'echo "- Candidate transfer: immutable \\`mtgo-fetch-candidate\\` artifact"' in workflow
    assert (
        'echo "- Candidate transfer: verified \\`mtgo-fetch-candidate\\` input and '
        'immutable \\`mtgo-build-candidate\\` output"'
    ) in workflow
    assert 'echo "- Candidate transfer: verified immutable \\`mtgo-build-candidate\\` artifact"' in workflow


def test_fetch_resumes_only_a_verified_same_commit_checkpoint_and_never_builds_it():
    fetch_text = UPDATE.read_text(encoding="utf-8")
    assert "actions/github-script@v7.0.1" in fetch_text
    assert "mtgo-fetch-checkpoint" in fetch_text
    assert "artifact.workflow_run?.head_sha === context.sha" in fetch_text
    assert "actions/download-artifact@v4.3.0" in fetch_text
    assert "github-token: ${{ github.token }}" in fetch_text
    assert "mtgo_fetch_checkpoint.py validate" in fetch_text
    assert "cmp \"$ARTIFACT_DIR/production-baseline.json\" \"$RUNNER_TEMP/production-baseline.json\"" in fetch_text
    assert "tar -tf" in fetch_text
    assert "mtgo_fetch_checkpoint.py is-complete" in fetch_text
    assert "mtgo_fetch_checkpoint.py complete" in fetch_text
    assert "retention-days: 7" in fetch_text
    assert "Package resumable fetch checkpoint" in fetch_text
    assert "if: failure() && steps.checkpoint.outcome == 'success'" in fetch_text
    assert "mtgo-fetch-checkpoint" not in "\n".join(
        step.get("uses", "") + "\n" + step.get("run", "") for step in steps("build")
    )
    assert "mtgo-fetch-checkpoint" not in "\n".join(
        step.get("uses", "") + "\n" + step.get("run", "") for step in steps("publish")
    )


def test_build_verifies_and_consumes_fetch_artifact_before_generation_and_validation():
    ordered = [
        "actions/download-artifact@v4.3.0",
        "sha256sum --check",
        "tar -xf",
        "build-statistics",
        "build-matchups",
        "build-completeness",
        "build-top8",
        "pickup candidates --if-absent",
        "generate-hierarchy",
        "generate-metadata",
        "-m mtgmeta.catalog",
        "classification-reports --strict",
        "validate_production_candidate.py validate",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
        "tar -cf",
        "sha256sum",
    ]
    flattened = "\n".join(
        step.get("uses", "") + "\n" + step.get("run", "") for step in steps("build")
    )
    indexes = []
    cursor = 0
    for fragment in ordered:
        cursor = flattened.index(fragment, cursor)
        indexes.append(cursor)
        cursor += len(fragment)
    assert indexes == sorted(indexes)
    assert "mtgo-build-candidate" in flattened
    assert "actions/upload-artifact@v4.6.2" in flattened


def test_publish_verifies_the_validated_output_and_is_the_only_commit_writer():
    publish_text = "\n".join(step.get("uses", "") + "\n" + step.get("run", "") for step in steps("publish"))
    assert "actions/download-artifact@v4.3.0" in publish_text
    assert "sha256sum --check" in publish_text
    assert "tar -tf" in publish_text
    assert "git status --porcelain" in publish_text
    assert "git add -- data/ stats/ reports/ fetched.txt" in publish_text
    assert "git push origin HEAD:master" in publish_text
    assert "git pull" not in publish_text
    assert "rebase" not in publish_text
    for name in ("fetch", "build"):
        text = "\n".join(run_commands(name))
        assert "git commit" not in text
        assert "git push" not in text


def test_notification_job_creates_or_updates_only_deduplicated_failed_stage_issues():
    notify = job("notify")
    text = "\n".join(
        step.get("uses", "") + "\n" + step.get("run", "") + "\n" + step.get("with", {}).get("script", "")
        for step in steps("notify")
    )
    assert notify["if"] == (
        "always() && github.ref == 'refs/heads/master' && "
        "(needs.fetch.result == 'failure' || needs.build.result == 'failure' || needs.publish.result == 'failure')"
    )
    assert notify["runs-on"] == "ubuntu-latest"
    assert notify["timeout-minutes"] == "5"
    assert "actions/checkout" not in text
    assert "actions/github-script@v7.0.1" in text
    assert "github.paginate(github.rest.issues.listForRepo" in text
    assert "<!-- mtgo-production-failure:${stage} -->" in text
    assert "!issue.pull_request" in text
    assert "github.rest.issues.create" in text
    assert "github.rest.issues.createComment" in text
    stage = next(step for step in steps("notify") if step["name"] == "Identify the failed production stage")
    assert stage["env"] == {
        "FETCH_RESULT": "${{ needs.fetch.result }}",
        "BUILD_RESULT": "${{ needs.build.result }}",
        "PUBLISH_RESULT": "${{ needs.publish.result }}",
    }
    assert "core.summary.write" in text
    assert "error.message" not in text
    assert "github.token" not in text
    assert "secrets." not in text.lower()


def test_only_the_dedicated_notification_job_may_write_issues():
    workflow = load_update()
    assert {name for name, value in workflow["jobs"].items() if "issues" in value.get("permissions", {})} == {
        "notify"
    }
    for name in ("fetch", "build", "publish"):
        assert "issues" not in job(name)["permissions"]


def test_clean_baseline_and_dynamic_candidate_checks_are_not_conflated():
    assert command_index("fetch", "-m pytest") < command_index(
        "fetch", "validate_production_candidate.py snapshot"
    )
    assert command_index("build", "classification-reports --strict") < command_index(
        "build", "validate_production_candidate.py validate"
    )


def test_only_candidate_generation_may_continue_on_error():
    allowed = {"Generate Weekly Pickup candidates when absent"}
    actual = {step["name"] for step in steps("build") if step.get("continue-on-error") == "true"}
    assert actual == allowed
    candidate = next(step for step in steps("build") if step["name"] in allowed)
    assert "STATUS=0" in candidate["run"]
    assert '|| STATUS=$?' in candidate["run"]
    assert 'exit "$STATUS"' in candidate["run"]


def test_format_aware_loops_and_registry_boundaries_remain_intact():
    workflow = UPDATE.read_text(encoding="utf-8")
    assert "python -B -m mtgmeta.catalog --root ." in workflow
    assert "$MTGO_FORMAT" not in workflow
    assert 'python -B -m mtgmeta.mtgo --format "$FORMAT" fetch-events' in workflow
    for command in (
        "fetch-matches",
        "build-statistics",
        "build-matchups",
        "build-completeness",
        "build-top8",
        "pickup candidates --if-absent",
        "generate-hierarchy",
        "generate-metadata",
        "classification-reports --strict",
    ):
        assert f'python -B -m mtgmeta.mtgo --format "$FORMAT" {command}' in workflow
    for legacy in (
        "batch_mtgo.py",
        "fetch_videre_matches.py",
        "stats_standard.py",
        "stats_matchup.py",
        "weekly_pickup.py",
        "gen_meta.py",
        "generate_classification_reports.py",
        "dump_unknown_highperf.py",
        "cluster_unknown.py",
    ):
        assert legacy not in workflow


def test_event_archive_and_product_formats_still_match_the_registry():
    configured = [
        item["id"]
        for item in yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))["formats"]
        if item["mtgo"]["event_collection_enabled"]
    ]
    workflow_formats = job("fetch")["env"]["MTGO_EVENT_FORMATS"].split()
    assert set(workflow_formats) == set(configured)
    assert workflow_formats == ["standard", "legacy", "pioneer", "pauper", "vintage", "modern"]

    required = {
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
        "weekly_top8",
        "completeness_reporting",
        "weekly_pickup",
        "metadata_generation",
        "catalog_generation",
    }
    products = [
        item["id"]
        for item in yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))["formats"]
        if item["mtgo"]["enabled"] and required <= set(item["mtgo"]["capabilities"])
    ]
    assert job("build")["env"]["MTGO_PRODUCT_FORMATS"].split() == products == ["standard", "modern"]
    assert job("build")["env"]["MTGO_HIERARCHY_FORMATS"].split() == ["standard", "modern"]


def test_every_product_rule_file_is_validated_before_schema_validation():
    rules = command_index("build", 'validate_rules.py "my_archetypes/${FORMAT}.yaml"')
    schemas = command_index("build", "validate_schemas.py")
    assert rules < schemas
    assert "for FORMAT in $MTGO_PRODUCT_FORMATS" in run_commands("build")[rules]
