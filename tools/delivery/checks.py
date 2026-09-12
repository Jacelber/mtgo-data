"""Explicit, finite check selection with content-based local result reuse."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ENTRY_FILES = ("AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md",
               "docs/GOVERNANCE.md", "docs/QUALITY.md", "docs/DELIVERY.md")
MECHANISMS = {
    "packages": ("test_packages.py", ("packages.py",)),
    "writer": ("test_state.py", ("state.py",)),
    "github": ("test_github.py", ("github.py", "state.py", "packages.py")),
    "platform": ("test_platform.py", ("platform.py", "github.py", "state.py", "packages.py", "commands.py")),
    "checks": ("test_checks.py", ("checks.py",)),
    "dispatch": ("test_commands.py", ("commands.py", "platform.py", "github.py", "state.py")),
}
NAMES = ("status", "entries", *MECHANISMS)


def status_advice(root: Path) -> dict:
    content = (root / "docs/STATUS.yaml").read_text(encoding="utf-8")
    lines = sum(bool(line.strip()) for line in content.splitlines())
    return {"state": "advisory" if lines > 120 or len(content) > 6000 else "passed",
            "nonempty_lines": lines, "characters": len(content),
            "note": "Size is a reminder only; preserve necessary live facts."}


def entries(root: Path) -> dict:
    missing = []
    for relative in ENTRY_FILES:
        source = root / relative
        if not source.is_file():
            missing.append(relative)
            continue
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", source.read_text(encoding="utf-8")):
            if "://" in target:
                continue
            if not (source.parent / target).is_file():
                missing.append(f"{relative}: {target}")
    if not (root / "tools/project.py").is_file():
        missing.append("tools/project.py")
    return {"state": "failed" if missing else "passed", "missing": missing}


def subjects(root: Path, name: str) -> list[Path]:
    if name == "status":
        return [root / "docs/STATUS.yaml"]
    if name == "entries":
        sources = [root / item for item in ENTRY_FILES]
        targets = [root / "tools/project.py"]
        for path in sources:
            if path.exists():
                targets.extend(path.parent / target for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")) if "://" not in target)
        return sources + targets
    if name in MECHANISMS:
        test, modules = MECHANISMS[name]
        sources = [root / "tools/delivery" / module for module in modules]
        if name in {"platform", "dispatch"}:
            sources.append(root / "tools/pages_writer.py")
        if name in {"checks", "platform"}:
            sources.append(root / "tools/project.py")
        return [*sources, root / "tests/delivery" / test]
    raise ValueError(f"Unknown check {name!r}; investigate actual impact, never fall back to full tests")


def identity(root: Path, name: str) -> str:
    digest = hashlib.sha256()
    paths = set(subjects(root, name)) | {root / "tools/delivery/checks.py"}
    for path in sorted(paths):
        digest.update(path.resolve().relative_to(root.resolve()).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"MISSING")
        digest.update(b"\0")
    # These mechanisms use only the standard library. Relevant runtime changes invalidate reuse.
    digest.update(str((sys.version_info[:3], sys.platform)).encode())
    return digest.hexdigest()


def run(root: Path, names: list[str], *, evidence: Path | None = None, expected: bool = False) -> dict:
    if not names:
        if expected:
            raise ValueError("A necessary check was expected but none was selected")
        return {"state": "not_needed", "checks": []}
    if len(set(names)) != len(names):
        raise ValueError("Duplicate check selection")
    cache = json.loads(evidence.read_text(encoding="utf-8")) if evidence and evidence.exists() else {}
    outcomes = []
    for name in names:
        subject = identity(root, name)
        previous = cache.get(name, {})
        if previous.get("subject") == subject and previous.get("state") in {"passed", "advisory"}:
            outcomes.append({"check": name, "state": "reused", "result": previous["state"]})
            continue
        if name == "status":
            result = status_advice(root)
        elif name == "entries":
            result = entries(root)
        else:
            command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/delivery", "-p", MECHANISMS[name][0], "-v"]
            execution = subprocess.run(command, cwd=root, text=True, capture_output=True)
            output = execution.stdout + execution.stderr
            count = re.search(r"Ran (\d+) tests?\b", output)
            outcome = "execution_failed" if not count or int(count[1]) == 0 or "_FailedTest" in output else "passed" if execution.returncode == 0 else "failed"
            result = {"state": outcome,
                      "command": command, "output": output, "exit_code": execution.returncode}
        cache[name] = {"subject": subject, **result}
        outcomes.append({"check": name, **result})
    if evidence:
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = "failed" if any(item["state"] == "failed" for item in outcomes) else "execution_failed" if any(item["state"] == "execution_failed" for item in outcomes) else "passed"
    return {"state": state, "checks": outcomes}
