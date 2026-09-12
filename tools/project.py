"""One thin entry for environment, selected checks and existing candidate packages."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.delivery import checks, packages  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("env", help="Report runtime; install nothing and read no credentials")
    check = sub.add_parser("check", help="Explicit checks only; semantic/browser/classifier proof may use their direct tools")
    check.add_argument("--select", choices=checks.NAMES, action="append", default=[])
    check.add_argument("--expected", action="store_true", help="Reject accidental zero selection")
    check.add_argument("--evidence", type=Path, help="Optional reusable task-local results, never an authorization token")
    prepare = sub.add_parser("prepare", help="Package the already selected public site; no generation")
    prepare.add_argument("--site", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--target", default="Jacelber/mtgo-data")
    prepare.add_argument("--source", required=True)
    verify = sub.add_parser("verify", help="Verify an existing package without executing content")
    verify.add_argument("--candidate", type=Path, required=True)
    verify.add_argument("--target", default="Jacelber/mtgo-data")
    extract = sub.add_parser("extract", help="Safely retrieve existing package content for local review")
    extract.add_argument("--candidate", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)
    extract.add_argument("--target", default="Jacelber/mtgo-data")
    seal = sub.add_parser("seal", help="Encrypt an existing private candidate for a cloud handoff; no credentials")
    seal.add_argument("--candidate", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)
    seal.add_argument("--certificate", type=Path, required=True)
    seal.add_argument("--openssl", default="openssl", help="Existing OpenSSL executable; installs nothing")
    seal.add_argument("--target", default="Jacelber/mtgo-data")
    enable = sub.add_parser("enable-automatic", help="Release a recovery pause on Owner instruction; dispatch nothing")
    enable.add_argument("--target", default="Jacelber/mtgo-data",
                        choices=("Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"))
    enable.add_argument("--recovery", required=True, help="The specific recovery pause being released")
    enable.add_argument("--reason", required=True, help="Owner instruction or fulfilled prior authorization context")
    for name in ("deliver", "restore", "resume", "status"):
        operation = sub.add_parser(name, help=f"{name} an archived candidate or existing operation through the current writer")
        operation.add_argument("--target", default="Jacelber/mtgo-data",
                               choices=("Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"))
        operation.add_argument("--operation", required=name != "status", help="Stable ID retained across retries")
        if name in {"deliver", "restore"}:
            operation.add_argument("--package", required=True)
            operation.add_argument("--base", required=True, help="Actual preparation-base operation; empty only for first publication")
        if name == "restore":
            operation.add_argument("--reason", required=True)
        if name == "deliver":
            operation.add_argument("--automatic", action="store_true", help="Required for unattended automatic callers")
    args = parser.parse_args(argv)
    try:
        if args.command == "env":
            versions = {}
            for name in ("jsonschema", "PyYAML", "requests", "pytest"):
                try:
                    versions[name] = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    versions[name] = None
            result = {"python": sys.version, "executable": sys.executable, "packages": versions}
        elif args.command == "check":
            result = checks.run(ROOT, args.select, evidence=args.evidence, expected=args.expected)
        elif args.command == "prepare":
            result = packages.prepare(args.site, args.output, target=args.target, source=args.source)
        elif args.command == "seal":
            packages.seal_candidate(args.candidate, args.output, args.certificate, target=args.target, openssl=args.openssl)
            result = {"state": "encrypted", "path": str(args.output)}
        elif args.command in {"deliver", "restore", "resume", "status", "enable-automatic"}:
            from tools.delivery import commands
            if args.command == "status":
                result = commands.status(args.target, args.operation)
            elif args.command == "enable-automatic":
                result = commands.enable_automatic(args.target, args.recovery, args.reason)
            else:
                result = commands.dispatch(args.target, args.operation, getattr(args, "package", ""),
                    getattr(args, "base", None) or None,
                    {"deliver": "publish", "restore": "recovery", "resume": "resume"}[args.command],
                    getattr(args, "reason", ""), automatic=getattr(args, "automatic", False))
        else:
            manifest = json.loads((args.candidate / "manifest.json").read_text(encoding="utf-8"))
            package = args.candidate / "product.tar.gz"
            if args.command == "extract":
                packages.extract(package, manifest, args.output, target=args.target)
                result = {"state": "extracted", "id": manifest["id"], "path": str(args.output)}
            else:
                result = packages.verify(package, manifest, target=args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {"execution_failed": 2, "failed": 1, "unknown": 3, "unconfirmed": 3}.get(result.get("state"), 0)
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
