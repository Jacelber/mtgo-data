"""Command-line entry point for the separately authorized Melee raw client."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable, Sequence

from .client import MeleeFetchError, MeleeRawFetchResult, fetch_raw_event
from .config import MeleeConfigError, load_melee_event_registry


def _result_payload(result: MeleeRawFetchResult) -> dict[str, object]:
    return {
        "event_id": result.event_id,
        "mode": "dry-run" if result.dry_run else "execute",
        "archive_path": str(result.archive_path) if result.archive_path is not None else None,
        "planned_urls": list(result.planned_urls),
        "responses": len(result.responses),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    fetch: Callable[..., MeleeRawFetchResult] = fetch_raw_event,
) -> int:
    parser = argparse.ArgumentParser(description="Validate or execute one whitelisted Melee raw-response plan.")
    parser.add_argument("--event-id", required=True, help="Whitelisted Melee tournament ID")
    parser.add_argument("--registry", type=Path, default=Path("configs/melee_events.yaml"))
    parser.add_argument("--raw-root", type=Path, default=Path("data_raw"))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform approved requests; without this flag the command is a zero-side-effect dry run",
    )
    args = parser.parse_args(argv)
    try:
        registry = load_melee_event_registry(args.registry)
        result = fetch(args.event_id, registry, args.raw_root, dry_run=not args.execute)
    except (MeleeConfigError, MeleeFetchError, OSError, ValueError) as exc:
        print(f"Melee raw collection ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_result_payload(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
