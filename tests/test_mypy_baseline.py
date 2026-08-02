"""P11-03 mypy baseline contract."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_development_dependencies_pin_mypy_and_its_transitives() -> None:
    requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()

    for requirement in (
        "mypy==2.3.0",
        "ast-serialize==0.6.0",
        "librt==0.13.0",
        "mypy_extensions==1.1.0",
        "pathspec==1.1.1",
    ):
        assert requirement in requirements


def test_mypy_baseline_is_strict_and_limited_to_stable_shared_modules() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    mypy = project["tool"]["mypy"]

    assert mypy == {
        "files": [
            "src/mtgmeta/card_names.py",
            "src/mtgmeta/deck.py",
            "src/mtgmeta/rules.py",
            "src/mtgmeta/classifier.py",
        ],
        "follow_imports": "skip",
        "python_version": "3.12",
        "strict": True,
    }
