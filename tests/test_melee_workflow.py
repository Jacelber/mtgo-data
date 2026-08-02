"""P7-07 manual, source-separated Melee workflow contract."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/fetch_melee.yml"


def _load():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _commands():
    return [step.get("run", "") for step in _load()["jobs"]["candidate"]["steps"]]


def test_workflow_is_manual_event_scoped_and_least_privilege():
    workflow = _load()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    event = workflow["on"]["workflow_dispatch"]["inputs"]["event_id"]
    assert event["required"] == "true"
    assert event["default"] == "434455"
    assert workflow["permissions"] == {"contents": "write"}
    assert workflow["concurrency"] == {
        "group": "melee-production-${{ inputs.event_id }}",
        "cancel-in-progress": "false",
    }


def test_workflow_is_master_dispatched_bounded_and_source_separated():
    job = _load()["jobs"]["candidate"]
    assert job["if"] == "github.ref == 'refs/heads/master'"
    assert job["timeout-minutes"] == "60"
    assert job["env"] == {
        "PYTHONPATH": "src",
        "EVENT_ID": "${{ inputs.event_id }}",
    }
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "mtgmeta.mtgo" not in text
    assert "update.yml" not in text
    assert "schedule:" not in text


def test_workflow_resolves_the_format_from_a_verified_whitelist_entry_first():
    workflow = _load()
    steps = workflow["jobs"]["candidate"]["steps"]
    resolve_index = next(
        index for index, step in enumerate(steps) if step["name"] == "Resolve verified whitelist format"
    )
    snapshot_index = next(
        index for index, step in enumerate(steps) if step["name"] == "Snapshot Melee candidate baseline"
    )
    source_index = next(
        index
        for index, step in enumerate(steps)
        if step["name"] == "Resolve retained snapshot or fetch a new whitelisted event"
    )
    resolve = steps[resolve_index]
    text = WORKFLOW.read_text(encoding="utf-8")

    assert resolve_index < snapshot_index < source_index
    assert resolve["id"] == "whitelist"
    assert resolve["env"] == {"EVENT_ID": "${{ inputs.event_id }}"}
    assert "load_melee_event_registry" in resolve["run"]
    assert "require_fetchable" in resolve["run"]
    assert 'echo "FORMAT=$EVENT_FORMAT" >> "$GITHUB_ENV"' in resolve["run"]
    assert 'echo "format=$EVENT_FORMAT" >> "$GITHUB_OUTPUT"' in resolve["run"]
    assert "FORMAT: modern" not in text


def test_pipeline_order_is_complete_and_fail_closed():
    required = [
        "-m pytest",
        "validate_melee_candidate.py snapshot",
        "-m mtgmeta.melee --event-id",
        "-m mtgmeta.melee.retention",
        "-m mtgmeta.melee.classification",
        "-m mtgmeta.melee.opportunities",
        "-m mtgmeta.melee.stats",
        "-m mtgmeta.melee.matchup",
        "-m mtgmeta.melee.publish",
        "-m mtgmeta.catalog",
        "validate_melee_candidate.py validate",
        "validate_repository.py",
        "validate_rules.py",
        "validate_schemas.py",
        "git add --",
        "git ls-remote",
    ]
    combined = _commands()
    indexes = [
        next(index for index, command in enumerate(combined) if fragment in command)
        for fragment in required
    ]
    assert indexes == sorted(indexes)


def test_existing_canonical_event_reuses_its_immutable_snapshot():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'if [ -f "$EVENT_PATH" ]' in text
    assert '["provenance"]["raw_artifacts"][0]["path"]' in text
    assert 'SOURCE_MODE="retained"' in text
    assert 'SOURCE_MODE="fetched"' in text
    assert "${{ steps.snapshot.outputs.snapshot }}" in text


def test_publication_uses_only_event_melee_paths_and_never_master_or_pr():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'git add -- "data_raw/melee/${EVENT_ID}/" "data/${FORMAT}/melee/" "stats/${FORMAT}/melee/"' in text
    assert '"stats/catalog.json"' in text
    assert 'BRANCH="data/melee-${EVENT_ID}"' in text
    assert 'git push origin "HEAD:refs/heads/${BRANCH}"' in text
    assert "HEAD:master" not in text
    assert "gh pr" not in text
    assert "pull-requests: write" not in text


def test_summary_and_workflow_contain_no_custom_secret():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "GITHUB_STEP_SUMMARY" in text
    assert "secrets." not in text.lower()
    assert "github.token" not in text.lower()
