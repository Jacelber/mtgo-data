from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
UPDATE = WORKFLOWS / "update.yml"


def load_update():
    return yaml.load(UPDATE.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def run_commands():
    return [step.get("run", "") for step in load_update()["jobs"]["update"]["steps"]]


def command_index(fragment):
    commands = run_commands()
    return next(index for index, command in enumerate(commands) if fragment in command)


def test_only_one_production_workflow_remains():
    assert not (WORKFLOWS / "scrape.yml").exists()
    assert UPDATE.exists()
    assert (ROOT / "batch_mtgo.py").exists()
    assert sorted(path.name for path in WORKFLOWS.glob("*.yml")) == ["ci.yml", "update.yml"]


def test_update_is_the_only_scheduled_production_pipeline():
    workflow = load_update()
    assert set(workflow["on"]) == {"workflow_dispatch", "schedule"}
    assert workflow["on"]["workflow_dispatch"] == {}
    assert workflow["on"]["schedule"] == [{"cron": "0 20 * * *"}]
    assert workflow["permissions"] == {"contents": "write"}
    assert workflow["concurrency"] == {"group": "production-data-update", "cancel-in-progress": "false"}


def test_job_is_master_only_bounded_and_uses_official_actions():
    job = load_update()["jobs"]["update"]
    assert job["if"] == "github.ref == 'refs/heads/master'"
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == "45"
    assert job["env"] == {
        "PYTHONPATH": "src",
        "MTGO_EVENT_FORMATS": "standard legacy pioneer pauper vintage modern",
        "MTGO_PRODUCT_FORMATS": "standard modern",
        "MTGO_HIERARCHY_FORMATS": "modern",
    }
    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@v7.0.0"
    assert steps[0]["with"] == {"fetch-depth": "0", "persist-credentials": "true"}
    assert steps[1]["uses"] == "actions/setup-python@v6.3.0"
    assert steps[1]["with"]["python-version"] == "3.11"


def test_complete_pipeline_order_preserves_mtgo_and_videre():
    ordered = [
        "-r requirements-dev.txt",
        "-m pytest",
        "validate_production_candidate.py snapshot",
        "fetch-events",
        "fetch-matches",
        "build-statistics",
        "build-matchups",
        "pickup candidates --if-absent",
        "generate-hierarchy",
        "generate-metadata",
        "classification-reports --strict",
        "validate_production_candidate.py validate",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
        "git add --",
        "git ls-remote origin refs/heads/master",
    ]
    indexes = [command_index(fragment) for fragment in ordered]
    assert indexes == sorted(indexes)


def test_clean_baseline_and_dynamic_candidate_checks_are_not_conflated():
    steps = load_update()["jobs"]["update"]["steps"]
    commands = [step.get("run", "") for step in steps]
    pytest_indexes = [index for index, command in enumerate(commands) if "-m pytest" in command]
    assert len(pytest_indexes) == 1
    assert pytest_indexes[0] < command_index("fetch-events")
    snapshot_index = command_index("validate_production_candidate.py snapshot")
    candidate_index = command_index("validate_production_candidate.py validate")
    assert pytest_indexes[0] < snapshot_index < command_index("fetch-events")
    assert command_index("classification-reports --strict") < candidate_index
    assert candidate_index < command_index("git add --")


def test_only_candidate_generation_may_continue_on_error():
    steps = load_update()["jobs"]["update"]["steps"]
    allowed = {"Generate Weekly Pickup candidates when absent"}
    actual = {step["name"] for step in steps if step.get("continue-on-error") == "true"}
    assert actual == allowed
    candidate = next(step for step in steps if step["name"] in allowed)
    assert "STATUS=0" in candidate["run"]
    assert '|| STATUS=$?' in candidate["run"]
    assert 'exit "$STATUS"' in candidate["run"]


def test_publication_scope_covers_replaced_scraper_and_generated_outputs():
    publish = next(step for step in load_update()["jobs"]["update"]["steps"] if step.get("id") == "publish")
    command = publish["run"]
    assert "git add -- data/ stats/ reports/ fetched.txt" in command
    assert "unknown_highperf.txt" not in command
    assert "unknown_clusters.txt" not in command
    assert "git push origin HEAD:master" in command
    assert "git pull" not in command
    assert "rebase" not in command
    assert command.count("git add") == 1
    assert 'echo "commit=$(git rev-parse HEAD)"' in command


def test_publication_is_confirmed_against_remote_master():
    steps = load_update()["jobs"]["update"]["steps"]
    verify = next(step for step in steps if step.get("id") == "verify")
    assert "git status --porcelain" in verify["run"]
    assert "git ls-remote origin refs/heads/master" in verify["run"]
    assert 'if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]' in verify["run"]
    assert command_index("git add --") < command_index("git ls-remote origin refs/heads/master")


def test_summary_is_always_written_without_secrets():
    steps = load_update()["jobs"]["update"]["steps"]
    summary = steps[-1]
    assert summary["if"] == "always()"
    assert "GITHUB_STEP_SUMMARY" in summary["run"]
    text = UPDATE.read_text(encoding="utf-8").lower()
    assert "secrets." not in text
    assert "github.token" not in text
    assert "Validation layers: clean-checkout regression" in summary["run"]
    assert "Product formats: ${MTGO_PRODUCT_FORMATS}" in summary["run"]
    assert "Hierarchy formats: ${MTGO_HIERARCHY_FORMATS}" in summary["run"]


def test_format_aware_loops_replace_every_standard_production_wrapper():
    workflow = UPDATE.read_text(encoding="utf-8")
    assert "$MTGO_FORMAT" not in workflow
    assert "python -B -m mtgmeta.mtgo --format \"$FORMAT\" fetch-events" in workflow
    for command in (
        "fetch-matches",
        "build-statistics",
        "build-matchups",
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


def test_event_archive_formats_match_the_registry_collection_allowlist():
    configured = [
        item["id"]
        for item in yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))["formats"]
        if item["mtgo"]["event_collection_enabled"]
    ]
    workflow_formats = load_update()["jobs"]["update"]["env"]["MTGO_EVENT_FORMATS"].split()
    assert set(workflow_formats) == set(configured)
    assert workflow_formats == ["standard", "legacy", "pioneer", "pauper", "vintage", "modern"]


def test_product_formats_match_complete_executable_registry_products():
    required = {
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
        "weekly_pickup",
        "metadata_generation",
        "catalog_generation",
    }
    configured = [
        item["id"]
        for item in yaml.safe_load(
            (ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8")
        )["formats"]
        if item["mtgo"]["enabled"]
        and required <= set(item["mtgo"]["capabilities"])
    ]
    env = load_update()["jobs"]["update"]["env"]
    assert env["MTGO_PRODUCT_FORMATS"].split() == configured == ["standard", "modern"]
    assert env["MTGO_HIERARCHY_FORMATS"].split() == ["modern"]


def test_every_product_rule_file_is_validated_before_schema_validation():
    rules = command_index('validate_rules.py "my_archetypes/${FORMAT}.yaml"')
    schemas = command_index("validate_schemas.py")
    assert rules < schemas
    command = run_commands()[rules]
    assert "for FORMAT in $MTGO_PRODUCT_FORMATS" in command
