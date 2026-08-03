"""P11-01 installable-package and console-script contract."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_declares_the_src_package_and_supported_runtime() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["build-system"] == {
        "requires": ["setuptools"],
        "build-backend": "setuptools.build_meta",
    }
    assert project["project"]["name"] == "mtgo-data"
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert project["tool"]["setuptools"]["package-data"] == {"mtgmeta": ["data/*.json"]}


def test_console_scripts_continue_to_use_existing_module_entry_points() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == {
        "mtgo-data-catalog": "mtgmeta.catalog:main",
        "mtgo-data-melee": "mtgmeta.melee.__main__:main",
        "mtgo-data-mtgo": "mtgmeta.mtgo.__main__:main",
    }


def test_classification_report_api_is_packaged() -> None:
    from mtgmeta.classification_reports_cli import generate_reports

    assert callable(generate_reports)
