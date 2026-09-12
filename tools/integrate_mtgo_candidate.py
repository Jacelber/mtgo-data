"""Transfer an existing MTGO output delta; never collect, generate or retest it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


OUTPUTS = ("data", "stats", "reports", "fetched.txt")
# Finite inputs used by the existing MTGO job, not an inferred dependency graph.
# A change here needs focused applicability review, not a whole-workflow restart.
INPUTS = ("src", "data", "configs", "my_archetypes", "schemas", "rules",
          "fetched.txt", "pyproject.toml", "requirements.txt")


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def text(root: Path, *args: str) -> str:
    return git(root, *args).decode("utf-8").strip()


def allowed(path: str) -> bool:
    return path == "fetched.txt" or path.startswith(("data/", "stats/", "reports/"))


def export(root: Path, artifact: Path) -> None:
    artifact.mkdir(parents=True, exist_ok=True)
    source = text(root, "rev-parse", "HEAD")
    git(root, "add", "--", *[p for p in OUTPUTS if (root / p).exists()])
    paths = git(root, "diff", "--cached", "--name-only", "-z").decode("utf-8").split("\0")
    if any(path and not allowed(path) for path in paths):
        raise ValueError("Candidate index includes a path outside MTGO output transfer")
    (artifact / "output.patch").write_bytes(git(root, "diff", "--cached", "--no-renames", "--binary", "--full-index", "HEAD"))
    (artifact / "source.txt").write_text(source + "\n", encoding="utf-8")


def integrate(root: Path, artifact: Path, current: str, run: str) -> dict:
    if not run.isdigit():
        raise ValueError("Expected numeric GitHub run identity")
    if text(root, "status", "--porcelain"):
        raise ValueError("Integration checkout contains unexplained changes")
    source = (artifact / "source.txt").read_text(encoding="utf-8").strip()
    if len(source) != 40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("Candidate source is not an exact commit")
    current = text(root, "rev-parse", "--verify", current + "^{commit}")
    git(root, "merge-base", "--is-ancestor", source, current)
    patch = artifact / "output.patch"
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    subject = (artifact / "generation-subject.txt").read_text(encoding="utf-8").strip()
    if len(subject) != 64 or any(c not in "0123456789abcdef" for c in subject):
        raise ValueError("Missing candidate generation subject")
    # A push response may have been lost. Read existing history before another write.
    for commit in text(root, "log", current, "--format=%H", "--fixed-strings",
                       "--grep", f"Production-Run: {run}").splitlines():
        message = text(root, "show", "-s", "--format=%B", commit).splitlines()
        if f"Production-Run: {run}" in message:
            if f"Validated-Output-SHA256: {digest}" not in message:
                raise ValueError("This run already published a different candidate")
            return {"status": "published", "changed": True, "commit": commit, "reused": True}
    changed_inputs = text(root, "diff", "--name-only", source, current, "--", *INPUTS)
    if changed_inputs:
        raise ValueError("Candidate retained; review these changed inputs and update only affected results:\n"
                         + changed_inputs)
    git(root, "checkout", "--detach", current)
    if patch.stat().st_size == 0:
        return {"status": "unchanged", "changed": False, "commit": current}
    # Exact application preserves other delivered files; conflicts need composition,
    # not silently regenerated output or guessed expected values.
    git(root, "apply", "--check", "--index", str(patch.resolve()))
    git(root, "apply", "--index", str(patch.resolve()))
    paths = git(root, "diff", "--cached", "--name-only", "-z").decode("utf-8").split("\0")
    if any(path and not allowed(path) for path in paths):
        raise ValueError("Transferred patch escaped the output boundary; do not publish")
    git(root, "commit", "-m", "chore: update MTGO production data",
        "-m", f"Production-Run: {run}\nProduction-Source: {source}\nGeneration-Subject-SHA256: {subject}\nValidated-Output-SHA256: {digest}")
    return {"status": "prepared", "changed": True, "commit": text(root, "rev-parse", "HEAD")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "integrate"))
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--current", default="refs/remotes/origin/master")
    parser.add_argument("--run")
    args = parser.parse_args()
    if args.action == "export":
        export(Path.cwd(), args.artifact)
        return
    result = integrate(Path.cwd(), args.artifact, args.current, args.run or "")
    print(json.dumps(result))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            for key, value in result.items():
                output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


if __name__ == "__main__":
    main()
