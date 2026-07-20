"""Legacy Standard command for format-aware MTGO metadata generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent
SHARED_SRC = REPOSITORY_ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo import pickup as _shared


FORMAT_ID = "standard"
_CONTEXT = load_mtgo_context(REPOSITORY_ROOT, FORMAT_ID, "metadata_generation")
RULES_FILE = str(_CONTEXT.paths["rules"])
OUT_DIR = str(_CONTEXT.paths["statistics"])
OUT_FILE = str(Path(OUT_DIR) / "meta.json")


def rules_last_commit_iso():
    return _shared.rules_last_commit_iso(REPOSITORY_ROOT, RULES_FILE)


def generate_metadata(
    *,
    data_updated: datetime | str | None = None,
    rules_updated: str | None = None,
    output_directory: str | Path | None = None,
):
    return _shared.generate_metadata(
        REPOSITORY_ROOT,
        FORMAT_ID,
        data_updated=data_updated,
        rules_updated=rules_updated,
        output_directory=output_directory,
    )


def main() -> None:
    destination = generate_metadata()
    print(f"写出 {destination}")


if __name__ == "__main__":
    main()
