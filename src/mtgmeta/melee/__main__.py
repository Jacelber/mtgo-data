"""Command-line entry point for the separately authorized Melee raw client."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import sys
from typing import Callable, Sequence

from .client import MeleeFetchError, MeleeRawFetchResult, fetch_complete_event, fetch_raw_event
from .config import MeleeConfigError, load_melee_event_registry
from .privacy import MINIMUM_HMAC_KEY_BYTES


PARTICIPANT_HMAC_KEY_ENV = "MELEE_PARTICIPANT_HMAC_KEY_BASE64"
PARTICIPANT_HMAC_KEY_ID_ENV = "MELEE_PARTICIPANT_HMAC_KEY_ID"


def _participant_hmac_settings() -> tuple[bytes, str]:
    encoded = os.environ.get(PARTICIPANT_HMAC_KEY_ENV, "")
    key_id = os.environ.get(PARTICIPANT_HMAC_KEY_ID_ENV, "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            f"{PARTICIPANT_HMAC_KEY_ENV} must be valid base64"
        ) from exc
    if len(key) < MINIMUM_HMAC_KEY_BYTES:
        raise ValueError(
            f"{PARTICIPANT_HMAC_KEY_ENV} must decode to at least "
            f"{MINIMUM_HMAC_KEY_BYTES} bytes"
        )
    if not key_id:
        raise ValueError(f"{PARTICIPANT_HMAC_KEY_ID_ENV} is required")
    return key, key_id


def _result_payload(result: MeleeRawFetchResult) -> dict[str, object]:
    return {
        "event_id": result.event_id,
        "mode": "dry-run" if result.dry_run else "execute",
        "archive_path": str(result.archive_path) if result.archive_path is not None else None,
        "planned_urls": list(result.planned_urls),
        "responses": len(result.responses),
        "planned_responses": result.planned_responses,
        "resumed_responses": result.resumed_responses,
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    fetch: Callable[..., MeleeRawFetchResult] = fetch_raw_event,
    complete_fetch: Callable[..., MeleeRawFetchResult] = fetch_complete_event,
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
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Discover and collect the complete public event; requires --execute",
    )
    args = parser.parse_args(argv)
    try:
        registry = load_melee_event_registry(args.registry)
        if args.complete and not args.execute:
            raise ValueError("--complete requires --execute because its request plan is discovered live")
        if args.complete:
            participant_hmac_key, participant_hmac_key_id = _participant_hmac_settings()

            def report_progress(payload: dict[str, object]) -> None:
                print(
                    "Melee raw collection progress: "
                    + json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    file=sys.stderr,
                )

            result = complete_fetch(
                args.event_id,
                registry,
                args.raw_root,
                progress=report_progress,
                participant_hmac_key=participant_hmac_key,
                participant_hmac_key_id=participant_hmac_key_id,
            )
        else:
            result = fetch(
                args.event_id,
                registry,
                args.raw_root,
                dry_run=not args.execute,
            )
    except (MeleeConfigError, MeleeFetchError, OSError, ValueError) as exc:
        print(f"Melee raw collection ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_result_payload(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
