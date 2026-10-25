"""Archive-only fallback for a fixed private candidate sent in bounded parts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.delivery.github import APIError, GitHub  # noqa: E402
from tools.delivery.parts import archive_parts, split  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("split")
    local.add_argument("candidate", type=Path)
    local.add_argument("destination", type=Path)
    upload = sub.add_parser("upload")
    upload.add_argument("identifier")
    upload.add_argument("--token-env", required=True)
    args = parser.parse_args()
    try:
        target = "Jacelber/mtgo-data"
        if args.command == "split":
            result = split(args.candidate, args.destination, target=target)
        else:
            client = GitHub("Jacelber/mtgo-data-releases", token_env=args.token_env)
            result = archive_parts(client, args.identifier, target=target)
        print(json.dumps(result, indent=2))
        return 0
    except (APIError, OSError, ValueError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
