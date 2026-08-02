"""P11-02 Ruff baseline contract."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_development_dependencies_pin_ruff() -> None:
    requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "ruff==0.15.22" in requirements.splitlines()


def test_ruff_baseline_checks_maintained_package_f_rules() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ruff = project["tool"]["ruff"]

    assert ruff["target-version"] == "py312"
    assert ruff["lint"]["select"] == ["F"]
