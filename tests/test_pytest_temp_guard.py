"""Regression contracts for repository-external pytest temporary files."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from pytest_temp_guard import is_within, select_basetemp


ROOT = Path(__file__).resolve().parents[1]


def test_default_basetemp_is_a_unique_repository_sibling(tmp_path):
    repository = tmp_path / "checkout"
    repository.mkdir()

    selected = select_basetemp(
        None,
        repository=repository,
        environment={},
        process_id=1234,
    )

    assert selected == tmp_path / ".pytest-temp" / "pytest-checkout-1234"
    assert not is_within(selected, repository)


def test_non_utf8_artifact_under_ci_runner_temp_stays_external(tmp_path):
    repository = tmp_path / "checkout"
    runner_temp = tmp_path / "runner-temp"

    selected = select_basetemp(
        None,
        repository=repository,
        environment={"RUNNER_TEMP": str(runner_temp)},
        process_id=7,
    )
    selected.mkdir(parents=True)
    artifact = selected / "generated.py"
    artifact.write_bytes(b"\xff\xfe")

    assert selected == runner_temp / "pytest-checkout-7"
    assert not is_within(selected, repository)
    assert not is_within(artifact, repository)


def test_repository_internal_basetemp_is_rejected(tmp_path):
    repository = tmp_path / "checkout"

    with pytest.raises(ValueError, match="must be outside the repository"):
        select_basetemp(repository / "test-temp", repository=repository)


def test_internal_basetemp_stops_pytest_before_collection():
    forbidden = ROOT / ".forbidden-pytest-temp"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            f"--basetemp={forbidden}",
            "tests/test_ci_timing.py",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "pytest basetemp must be outside the repository" in (
        result.stdout + result.stderr
    )
    assert not forbidden.exists()
