from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from validate_production_candidate import (
    Change,
    collect_changes,
    snapshot_state,
    validate_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
FORMATS = ("standard", "legacy", "pioneer", "pauper", "vintage", "modern")


def make_candidate_root(tmp_path: Path) -> Path:
    (tmp_path / "configs").mkdir()
    shutil.copyfile(ROOT / "configs" / "formats.yaml", tmp_path / "configs" / "formats.yaml")
    for format_id in FORMATS:
        (tmp_path / "data" / format_id).mkdir(parents=True)
    for format_id in ("standard", "modern"):
        (tmp_path / "data" / format_id / "mtgo" / "matches").mkdir(parents=True)
        (tmp_path / "stats" / format_id / "mtgo").mkdir(parents=True)
        (tmp_path / "reports" / format_id / "mtgo").mkdir(parents=True)
    (tmp_path / "fetched.txt").write_text("/decklist/standard-existing\n", encoding="utf-8")
    return tmp_path


def event_document(format_id: str = "standard"):
    return {
        "event_id": "123",
        "description": f"{format_id.title()} Challenge 32",
        "format": format_id.upper(),
        "starttime": "2026-07-20 00:00:00.0",
        "player_count": 1,
        "inplayoffs": "1",
        "players": [{"player": "Fixture"}],
    }


def test_snapshot_records_collection_counts_without_historical_constants(tmp_path):
    root = make_candidate_root(tmp_path)
    (root / "data" / "standard" / "event.json").write_text(
        json.dumps(event_document()), encoding="utf-8"
    )
    state = snapshot_state(root)
    assert state["schema_version"] == "2.0.0"
    assert state["event_files"] == {
        "standard": 1,
        "pauper": 0,
        "modern": 0,
        "pioneer": 0,
        "legacy": 0,
        "vintage": 0,
    }
    assert state["match_files"] == {"standard": 0, "modern": 0}
    assert state["fetched_entries"] == 1


def test_pre_p6_08_baseline_shape_fails_closed(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    baseline["schema_version"] = "1.0.0"
    baseline["standard_match_files"] = baseline.pop("match_files")["standard"]
    _report, failures = validate_candidate(root, baseline, [])
    assert "baseline snapshot has an unsupported schema_version" in failures
    assert "baseline snapshot does not match the configured product formats" in failures


def test_valid_candidate_reports_dynamic_deltas_and_source_separation(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    event = root / "data" / "modern" / "Modern_Challenge_32_123.json"
    event.write_text(json.dumps(event_document("modern")), encoding="utf-8")
    statistic = root / "stats" / "standard" / "mtgo" / "index.json"
    statistic.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    modern_match = root / "data" / "modern" / "mtgo" / "matches" / "123.json"
    modern_match.write_text(
        json.dumps({"event_id": "123", "matches": []}),
        encoding="utf-8",
    )
    modern_report = root / "reports" / "modern" / "mtgo" / "index.json"
    modern_report.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    (root / "fetched.txt").write_text(
        "/decklist/standard-existing\n/decklist/modern-new\n", encoding="utf-8"
    )
    report, failures = validate_candidate(
        root,
        baseline,
        [
            Change("??", "data/modern/Modern_Challenge_32_123.json"),
            Change("??", "data/modern/mtgo/matches/123.json"),
            Change(" M", "stats/standard/mtgo/index.json"),
            Change(" M", "reports/modern/mtgo/index.json"),
            Change(" M", "fetched.txt"),
        ],
    )
    assert failures == []
    assert report["event_file_deltas"]["modern"] == 1
    assert report["match_file_deltas"] == {"standard": 0, "modern": 1}
    assert report["fetched_entry_delta"] == 1
    assert report["changes_by_area"] == {
        "events_modern": 1,
        "ledger": 1,
        "matches_modern": 1,
        "reports_modern": 1,
        "statistics_standard": 1,
    }


def test_candidate_blocks_deletion_cross_source_write_and_malformed_json(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    melee = root / "data" / "melee" / "event.json"
    melee.parent.mkdir()
    melee.write_text("{}", encoding="utf-8")
    broken = root / "data" / "standard" / "broken.json"
    broken.write_text("{", encoding="utf-8")
    cross_format = root / "data" / "modern" / "cross-format.json"
    cross_format.write_text(json.dumps(event_document("standard")), encoding="utf-8")
    broken_match = root / "data" / "modern" / "mtgo" / "matches" / "broken.json"
    broken_match.write_text(json.dumps({"matches": {}}), encoding="utf-8")
    planned = root / "stats" / "pioneer" / "mtgo" / "index.json"
    planned.parent.mkdir(parents=True)
    planned.write_text("{}", encoding="utf-8")
    _report, failures = validate_candidate(
        root,
        baseline,
        [
            Change(" D", "data/legacy/old.json"),
            Change("??", "data/melee/event.json"),
            Change("??", "data/standard/broken.json"),
            Change("??", "data/modern/cross-format.json"),
            Change("??", "data/modern/mtgo/matches/broken.json"),
            Change("??", "stats/pioneer/mtgo/index.json"),
        ],
    )
    assert any("deletion is not allowed" in failure for failure in failures)
    assert any("outside the production publication scope" in failure for failure in failures)
    assert any("cannot parse candidate file" in failure for failure in failures)
    assert any("embedded format" in failure for failure in failures)
    assert any("match JSON is missing event_id" in failure for failure in failures)
    assert any("matches must be a list" in failure for failure in failures)


def test_candidate_blocks_count_regression_duplicate_ledger_and_code_changes(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    baseline["event_files"]["standard"] = 1
    baseline["match_files"]["modern"] = 1
    (root / "fetched.txt").write_text(
        "/decklist/standard-existing\n/decklist/standard-existing\n", encoding="utf-8"
    )
    source = root / "src" / "unexpected.py"
    source.parent.mkdir()
    source.write_text("pass\n", encoding="utf-8")
    _report, failures = validate_candidate(
        root,
        baseline,
        [Change("??", "src/unexpected.py"), Change(" M", "fetched.txt")],
    )
    assert any("event file count decreased for standard" in failure for failure in failures)
    assert any("match file count decreased for modern" in failure for failure in failures)
    assert any("duplicate entries" in failure for failure in failures)
    assert any("outside the production publication scope" in failure for failure in failures)


def test_candidate_blocks_unapproved_new_generated_paths(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    unexpected = root / "stats" / "standard" / "mtgo" / "unexpected.json"
    unexpected.write_text("{}", encoding="utf-8")
    unexpected_modern = root / "stats" / "modern" / "mtgo" / "unexpected.json"
    unexpected_modern.write_text("{}", encoding="utf-8")
    approved = (
        root
        / "stats"
        / "standard"
        / "mtgo"
        / "pickup"
        / "candidates_2026-W29.yaml"
    )
    approved.parent.mkdir(parents=True)
    approved.write_text(yaml.safe_dump({"approved": False}), encoding="utf-8")
    _report, failures = validate_candidate(
        root,
        baseline,
        [
            Change("??", "stats/standard/mtgo/unexpected.json"),
            Change("??", "stats/modern/mtgo/unexpected.json"),
            Change("??", "stats/standard/mtgo/pickup/candidates_2026-W29.yaml"),
        ],
    )
    assert failures == [
        "stats/modern/mtgo/unexpected.json: new generated path is not in the approved creation scope",
        "stats/standard/mtgo/unexpected.json: new generated path is not in the approved creation scope",
    ]


def test_candidate_accepts_valid_changed_yaml_and_rejects_renames(tmp_path):
    root = make_candidate_root(tmp_path)
    baseline = snapshot_state(root)
    candidates = []
    for format_id in ("standard", "modern"):
        candidate = (
            root
            / "stats"
            / format_id
            / "mtgo"
            / "pickup"
            / "candidates_2026-W29.yaml"
        )
        candidate.parent.mkdir(parents=True)
        candidate.write_text(yaml.safe_dump({"approved": False}), encoding="utf-8")
        candidates.append(candidate)
    _report, failures = validate_candidate(
        root,
        baseline,
        [
            Change("??", "stats/standard/mtgo/pickup/candidates_2026-W29.yaml"),
            Change("??", "stats/modern/mtgo/pickup/candidates_2026-W29.yaml"),
            Change("R ", "data/standard/new.json", "data/standard/old.json"),
        ],
    )
    assert len(failures) == 1
    assert "rename/copy is not allowed" in failures[0]


def test_git_change_collection_drives_an_end_to_end_candidate_check(tmp_path):
    root = make_candidate_root(tmp_path)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    baseline = snapshot_state(root)

    event = root / "data" / "standard" / "Standard_Challenge_32_123.json"
    event.write_text(json.dumps(event_document()), encoding="utf-8")
    (root / "fetched.txt").write_text(
        "/decklist/standard-existing\n/decklist/standard-new\n", encoding="utf-8"
    )
    changes = collect_changes(root)
    assert {(change.status, change.path) for change in changes} == {
        (" M", "fetched.txt"),
        ("??", "data/standard/Standard_Challenge_32_123.json"),
    }
    report, failures = validate_candidate(root, baseline, changes)
    assert failures == []
    assert report["event_file_deltas"]["standard"] == 1


def test_snapshot_cli_requires_a_clean_checkout(tmp_path):
    root = make_candidate_root(tmp_path)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    output = tmp_path.parent / f"{tmp_path.name}-baseline.json"
    command = [
        sys.executable,
        "-B",
        str(ROOT / "validate_production_candidate.py"),
        "--root",
        str(root),
        "snapshot",
        "--output",
        str(output),
    ]
    clean = subprocess.run(command, text=True, capture_output=True)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    (root / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
    dirty = subprocess.run(command, text=True, capture_output=True)
    assert dirty.returncode == 2
    assert "requires a clean checkout" in dirty.stdout
