"""Trusted archive-only entry: accepts packages, never candidate Python or workflows."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.delivery.github import APIError, GitHub  # noqa: E402
from tools.delivery.state import end_candidate
from tools.delivery.packages import open_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="Jacelber/mtgo-data-releases")
    parser.add_argument("--target", default="Jacelber/mtgo-data")
    parser.add_argument("--token-env", help="Explicit narrow credential in Actions; omitted only in trusted local gh context")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize empty archive control state, never reset existing state")
    upload = sub.add_parser("upload")
    upload.add_argument("candidate", type=Path)
    upload.add_argument("--encrypted", action="store_true")
    upload.add_argument("--key-env", default="ARCHIVE_HANDOFF_KEY")
    fetch = sub.add_parser("download")
    fetch.add_argument("identifier")
    fetch.add_argument("destination", type=Path)
    finish = sub.add_parser("finish", help="Mark a candidate no longer needed for active review or diagnosis")
    finish.add_argument("identifier")
    finish.add_argument("--reason", required=True)
    prune = sub.add_parser("prune", help="Preview expired packages, or remove only currently unreferenced expired packages")
    prune.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.target not in {"Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"}:
            raise ValueError("Unsupported archive target")
        state_path = "state/pages.json" if args.target == "Jacelber/mtgo-data" else "state/verification-pages.json"
        client = GitHub(args.repository, token_env=args.token_env, state_path=state_path)
        client.private()
        if args.command == "init":
            state, sha = client.load_state()
            result = {"state": "already_initialized"} if sha else {"state": "initialized", "sha": client.save_state(state, sha)}
        elif args.command == "upload":
            if args.encrypted:
                key = os.environ.get(args.key_env)
                if not key:
                    raise ValueError("Trusted uploader has no handoff decryption key")
                with tempfile.TemporaryDirectory(prefix="trusted-handoff-") as temporary:
                    root = Path(temporary)
                    private = root / "key.pem"
                    private.write_text(key, encoding="ascii")
                    private.chmod(0o600)
                    open_candidate(args.candidate, root / "candidate", private, target=args.target)
                    result = client.archive(root / "candidate", target=args.target)
            else:
                result = client.archive(args.candidate, target=args.target)
        elif args.command == "finish":
            state, sha = client.load_state()
            state = end_candidate(state, args.identifier, reason=args.reason)
            client.save_state(state, sha)
            result = {"state": "ended", "package": args.identifier, "reason": args.reason}
        elif args.command == "prune":
            result = client.prune(execute=args.execute)
        else:
            result = client.retrieve(args.identifier, args.destination, target=args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (APIError, OSError, ValueError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
