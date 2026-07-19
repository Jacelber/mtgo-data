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
    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@v7.0.0"
    assert steps[0]["with"] == {"fetch-depth": "0", "persist-credentials": "true"}
    assert steps[1]["uses"] == "actions/setup-python@v6.3.0"
    assert steps[1]["with"]["python-version"] == "3.11"


def test_complete_pipeline_order_preserves_mtgo_and_videre():
    ordered = [
        "-r requirements-dev.txt",
        "batch_mtgo.py",
        "fetch_videre_matches.py",
        "stats_standard.py",
        "stats_matchup.py",
        "gen_meta.py",
        "generate_classification_reports.py --strict",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
        "-m pytest",
        "git add --",
    ]
    indexes = [command_index(fragment) for fragment in ordered]
    assert indexes == sorted(indexes)


def test_only_diagnostics_and_candidate_generation_may_continue_on_error():
    steps = load_update()["jobs"]["update"]["steps"]
    allowed = {
        "Dump unknown high-performing decks",
        "Cluster unknown decks",
        "Generate Weekly Pickup candidates when absent",
    }
    actual = {step["name"] for step in steps if step.get("continue-on-error") == "true"}
    assert actual == allowed


def test_publication_scope_covers_replaced_scraper_and_generated_outputs():
    publish = next(step for step in load_update()["jobs"]["update"]["steps"] if step.get("id") == "publish")
    command = publish["run"]
    assert "git add -- data/ stats/ reports/ fetched.txt unknown_highperf.txt unknown_clusters.txt" in command
    assert "git push origin HEAD:master" in command
    assert "git pull" not in command
    assert "rebase" not in command
    assert command.count("git add") == 1


def test_summary_is_always_written_without_secrets():
    steps = load_update()["jobs"]["update"]["steps"]
    summary = steps[-1]
    assert summary["if"] == "always()"
    assert "GITHUB_STEP_SUMMARY" in summary["run"]
    text = UPDATE.read_text(encoding="utf-8").lower()
    assert "secrets." not in text
    assert "github.token" not in text
