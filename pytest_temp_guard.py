"""Keep pytest basetemp outside the repository under test."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import pytest


ROOT = Path(__file__).resolve().parent
BASE_TEMP_KEY = pytest.StashKey[Path]()


def is_within(path: Path, root: Path) -> bool:
    path = path.resolve()
    root = root.resolve()
    return path == root or root in path.parents


def select_basetemp(
    requested: str | Path | None,
    *,
    repository: Path = ROOT,
    environment: Mapping[str, str] = os.environ,
    process_id: int | None = None,
) -> Path:
    if requested is not None:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
    else:
        external_root = environment.get("RUNNER_TEMP") or environment.get(
            "PYTEST_EXTERNAL_TEMP_ROOT"
        )
        parent = (
            Path(external_root)
            if external_root
            else repository.parent / ".pytest-temp"
        )
        candidate = parent / f"pytest-{repository.name}-{process_id or os.getpid()}"

    candidate = candidate.resolve()
    if is_within(candidate, repository):
        raise ValueError(
            f"pytest basetemp must be outside the repository: {candidate}"
        )
    return candidate


def pytest_configure(config: pytest.Config) -> None:
    try:
        basetemp = select_basetemp(config.option.basetemp)
        basetemp.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise pytest.UsageError(str(exc)) from exc
    config.option.basetemp = str(basetemp)
    config.stash[BASE_TEMP_KEY] = basetemp


def pytest_report_header(config: pytest.Config) -> str:
    return f"external basetemp: {config.stash[BASE_TEMP_KEY]}"
