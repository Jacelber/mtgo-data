"""Legacy Standard entry point for format-aware Videre match fetching."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent
SHARED_SRC = REPOSITORY_ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.mtgo import matchup as _shared


FORMAT_ID = "standard"
FETCHED_FILE = str(REPOSITORY_ROOT / "fetched.txt")
NoResults = _shared.NoResults


def api_get(path, params):
    """Preserve the legacy path-based helper for existing imports."""

    format_id = str(path).rstrip("/").rsplit("/", 1)[-1]
    return _shared.api_get(format_id, params)


def fetch_all_matches(event_id):
    return _shared.fetch_all_matches(FORMAT_ID, event_id)


def event_ids_from_fetched():
    event_ids = _shared.event_ids_from_fetched(FETCHED_FILE, FORMAT_ID)
    if not Path(FETCHED_FILE).exists():
        print(f"Cannot find {FETCHED_FILE}")
    return event_ids


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in args
    explicit = [argument for argument in args if argument.isdigit()]
    event_ids = explicit if explicit else None
    summary = _shared.fetch_and_store_matches(
        REPOSITORY_ROOT,
        FORMAT_ID,
        event_ids=event_ids,
        force=force,
        fetched_file=FETCHED_FILE,
    )
    print(f"Events selected for Standard: {summary['requested']}")
    print(
        "Fetched: {fetched} | skipped: {skipped} | not found: {not_found} | failed: {failed}".format(
            **summary
        )
    )
    if summary["missing_event_ids"]:
        print(f"Videre has no records for: {summary['missing_event_ids']}")
    for event_id, message in summary["errors"]:
        print(f"ERROR {event_id}: {message}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
