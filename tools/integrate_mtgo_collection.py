"""Persist validated collected inputs without classifying or generating products.

The candidate is immutable. Integration can reuse it after unrelated deliveries;
conflicting input edits retain it for focused repair, never another collection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

import validate_production_candidate as validation
from tools.integrate_mtgo_candidate import git, text


def allowed(path: str, collection: tuple[str, ...], products: tuple[str, ...]) -> bool:
    parts = PurePosixPath(path).parts
    if path == "fetched.txt":
        return True
    if not parts or ".." in parts or "\\" in path:
        return False
    if len(parts) == 3 and parts[0] == "data" and parts[1] in collection:
        return bool(re.fullmatch(r"[A-Za-z0-9_-]+\.json", parts[2]))
    if len(parts) == 4 and parts[0] == "data" and parts[1] in collection:
        return parts[2:] == ("mtgo", "discovery.json")
    return (len(parts) == 5 and parts[0] == "data" and parts[1] in products
            and parts[2:4] == ("mtgo", "matches")
            and bool(re.fullmatch(r"[0-9]+\.json", parts[4])))


def validate(root: Path, baseline: dict, changes: list[validation.Change]) -> dict:
    collection, products = validation._configured_formats(root, require_public_products=False)
    for change in changes:
        if not allowed(change.path, collection, products):
            raise ValueError("Outside collection scope: " + change.path)
        if any((root / Path(*Path(change.path).parts[:i])).is_symlink()
               for i in range(1, len(Path(change.path).parts) + 1)):
            raise ValueError("Collection inputs cannot be symlinks: " + change.path)
    report, failures = validation.validate_candidate(root, baseline, changes, require_public_products=False)
    if failures:
        raise ValueError("Collection validation failed:\n" + "\n".join(failures))
    # Counts alone cannot detect replacement of an old ledger/discovery entry.
    for change in changes:
        previous = subprocess.run(["git", "show", "HEAD:" + change.path], cwd=root,
                                  capture_output=True)
        if previous.returncode:
            continue  # A newly collected source has no previous content.
        if change.path == "fetched.txt":
            before = set(previous.stdout.decode().splitlines()) - {""}
            after = set((root / change.path).read_text().splitlines()) - {""}
            if not before <= after:
                failures.append("Collection cannot discard fetched ledger entries")
        elif change.path.endswith("/discovery.json"):
            before = {e["link"] for e in json.loads(previous.stdout)["events"]}
            after = {e["link"] for e in json.loads((root / change.path).read_text())["events"]}
            if not before <= after:
                failures.append("Collection cannot discard discovered source entries")
    if failures:
        raise ValueError("Collection validation failed:\n" + "\n".join(failures))
    return report


def export(root: Path, artifact: Path, baseline: dict) -> dict:
    changes = validation.collect_changes(root)
    report = validate(root, baseline, changes)
    artifact.mkdir(parents=True, exist_ok=True)
    if changes:
        git(root, "add", "--", *[change.path for change in changes])
    patch = git(root, "diff", "--cached", "--no-renames", "--binary", "--full-index", "HEAD")
    (artifact / "collection.patch").write_bytes(patch)
    (artifact / "source.txt").write_text(text(root, "rev-parse", "HEAD") + "\n")
    (artifact / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return {"sha256": hashlib.sha256(patch).hexdigest(), "changed": bool(patch)}


def integrate(root: Path, artifact: Path, current: str, run: str) -> dict:
    if not run.isdigit():
        raise ValueError("Expected numeric collection run identity")
    if text(root, "status", "--porcelain"):
        raise ValueError("Integration checkout contains unexplained changes")
    source = (artifact / "source.txt").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Candidate source is not an exact commit")
    current = text(root, "rev-parse", "--verify", current + "^{commit}")
    git(root, "merge-base", "--is-ancestor", source, current)
    patch = artifact / "collection.patch"
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    for commit in text(root, "log", current, "--format=%H", "--fixed-strings",
                       "--grep", f"Collection-Run: {run}").splitlines():
        message = text(root, "show", "-s", "--format=%B", commit).splitlines()
        if f"Collection-Run: {run}" in message:
            if f"Collected-Inputs-SHA256: {digest}" not in message:
                raise ValueError("This run already retained different collected inputs")
            return {"status": "retained", "changed": True, "commit": commit, "reused": True}
    git(root, "checkout", "--detach", current)
    if patch.stat().st_size == 0:
        return {"status": "unchanged", "changed": False, "commit": current}
    collection, products = validation._configured_formats(root, require_public_products=False)
    for record in git(root, "apply", "--numstat", "-z", str(patch.resolve())).decode().split("\0"):
        if record and not allowed(record.split("\t", 2)[-1], collection, products):
            raise ValueError("Transferred patch escaped collection scope")
    summary = text(root, "apply", "--summary", str(patch.resolve()))
    if "120000" in summary or "160000" in summary:
        raise ValueError("Links and submodules are not collected inputs")
    baseline = validation.snapshot_state(root, require_public_products=False)
    # Exact application fails without altering files when a later collector has
    # edited the same source. Preserve the artifact, not guessed merge results.
    git(root, "apply", "--check", "--index", str(patch.resolve()))
    git(root, "apply", "--index", str(patch.resolve()))
    try:
        validate(root, baseline, validation.collect_changes(root))
        git(root, "commit", "-m", "chore: retain MTGO collected inputs",
            "-m", f"Collection-Run: {run}\nCollection-Source: {source}\nCollected-Inputs-SHA256: {digest}")
    except Exception:
        git(root, "apply", "--reverse", "--index", str(patch.resolve()))
        raise
    return {"status": "prepared", "changed": True, "commit": text(root, "rev-parse", "HEAD")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "integrate"))
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--current", default="refs/remotes/origin/master")
    parser.add_argument("--run")
    args = parser.parse_args()
    if args.action == "export":
        if args.baseline is None:
            parser.error("export requires --baseline")
        result = export(Path.cwd(), args.artifact, json.loads(args.baseline.read_text()))
    else:
        result = integrate(Path.cwd(), args.artifact, args.current, args.run or "")
    print(json.dumps(result))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key, value in result.items():
                output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


if __name__ == "__main__":
    main()
