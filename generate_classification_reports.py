"""Legacy-compatible entry point for MTGO classification diagnostic reports."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.classification_reports_cli import generate_reports
from mtgmeta.classification_reports_cli import main as _package_main


def main(argv: list[str] | None = None) -> int:
    """Retain the root-script default while delegating to the package command."""

    return _package_main(argv, default_root=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
