"""Read changed paths without importing retired governance or choosing tests."""
from pathlib import Path
import subprocess
import re


class InfrastructureError(RuntimeError):
    pass


def preparation_source(root: Path, requested: str, deployed: str | None) -> str:
    """Fix one merged source which includes the requested and already delivered work."""
    current = subprocess.run(["git", "rev-parse", "refs/remotes/origin/master"], cwd=root,
                             check=True, capture_output=True, text=True).stdout.strip()
    for label, commit in (("requested", requested), ("deployed", deployed)):
        if commit is None:
            continue
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise InfrastructureError(f"Identify the actual {label} source before composing a whole-site candidate")
        result = subprocess.run(["git", "merge-base", "--is-ancestor", commit, current],
                                cwd=root, capture_output=True)
        if result.returncode:
            raise InfrastructureError(f"Current master does not include the {label} source; integrate that delivery first")
    return current


def changed_files(root: Path, base: str) -> list[str]:
    try:
        resolved = subprocess.run(["git", "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}"],
                                  cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        changed = subprocess.run(["git", "diff", "--name-only", "-z", "--no-renames", resolved, "--"],
                                 cwd=root, check=True, capture_output=True).stdout
        untracked = subprocess.run(["git", "ls-files", "-z", "--others", "--exclude-standard"],
                                   cwd=root, check=True, capture_output=True).stdout
        return sorted({name for name in (changed + untracked).decode("utf-8").split("\0") if name})
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as error:
        raise InfrastructureError(f"Cannot read changes from {base!r}: {error}") from error
