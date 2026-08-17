from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "tools" / "github_publication_preflight.ps1"


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.fail("PowerShell is required to validate the publication preflight")
    return executable


def _write_fake_gh(tmp_path: Path) -> Path:
    fake = tmp_path / "fake_gh.py"
    fake.write_text(
        """
import json
import os
import sys

scenario = os.environ["FAKE_GH_SCENARIO"]
arguments = sys.argv[1:]

if arguments[:2] == ["auth", "status"]:
    state = "failure" if scenario == "auth_rejected" else "success"
    scopes = "gist, read:org, repo" if scenario == "workflow_missing" else "gist, read:org, repo, workflow"
    print(json.dumps({"hosts": {"github.com": [{
        "active": True,
        "host": "github.com",
        "login": "Jacelber",
        "scopes": scopes,
        "state": state,
        "tokenSource": "keyring",
    }]}}))
    raise SystemExit(0)

if arguments[:2] == ["api", "user"]:
    print("the redundant authenticated-user endpoint must not be called", file=sys.stderr)
    raise SystemExit(98)

if arguments[:2] == ["api", "repos/Jacelber/mtgo-data"]:
    if scenario == "http_503":
        print("gh: service unavailable (HTTP 503)", file=sys.stderr)
        raise SystemExit(1)
    print("false" if scenario == "push_missing" else "true")
    raise SystemExit(0)

print("unexpected gh arguments", file=sys.stderr)
raise SystemExit(99)
""".lstrip(),
        encoding="utf-8",
    )

    if os.name == "nt":
        wrapper = tmp_path / "gh.cmd"
        wrapper.write_text(
            f'@"{sys.executable}" "{fake}" %*\n',
            encoding="utf-8",
        )
    else:
        wrapper = tmp_path / "gh"
        wrapper.write_text(
            "#!/bin/sh\n"
            f"exec {shlex.quote(sys.executable)} {shlex.quote(str(fake))} \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return wrapper


def _run_preflight(
    tmp_path: Path,
    scenario: str,
    *arguments: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    _write_fake_gh(tmp_path)
    environment = os.environ.copy()
    environment["FAKE_GH_SCENARIO"] = scenario
    environment["PATH"] = f"{tmp_path}{os.pathsep}{environment['PATH']}"
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PREFLIGHT),
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(result.stdout.strip())
    return result, payload


def test_ordinary_context_cannot_issue_credential_verdict(tmp_path: Path) -> None:
    result, payload = _run_preflight(tmp_path, "ready")

    assert result.returncode == 2
    assert payload["state"] == "RETRY_ACTUAL_CONTEXT"


def test_structured_active_account_can_return_ready(tmp_path: Path) -> None:
    result, payload = _run_preflight(
        tmp_path,
        "ready",
        "-ActualPublicationContext",
        "-RequireWorkflowScope",
    )

    assert result.returncode == 0
    assert payload == {
        "state": "READY",
        "login": "Jacelber",
        "push_permission": True,
        "workflow_scope": True,
        "next_action": (
            "Continue with the repository-specific command-scoped publication path."
        ),
    }


def test_structured_authentication_failure_is_rejected(tmp_path: Path) -> None:
    result, payload = _run_preflight(
        tmp_path,
        "auth_rejected",
        "-ActualPublicationContext",
    )

    assert result.returncode == 3
    assert payload["state"] == "AUTH_REJECTED"


def test_missing_workflow_scope_is_permission_failure(tmp_path: Path) -> None:
    result, payload = _run_preflight(
        tmp_path,
        "workflow_missing",
        "-ActualPublicationContext",
        "-RequireWorkflowScope",
    )

    assert result.returncode == 4
    assert payload["state"] == "PERMISSION_MISSING"
    assert payload["workflow_scope"] is False


def test_missing_repository_push_permission_is_permission_failure(
    tmp_path: Path,
) -> None:
    result, payload = _run_preflight(
        tmp_path,
        "push_missing",
        "-ActualPublicationContext",
    )

    assert result.returncode == 4
    assert payload["state"] == "PERMISSION_MISSING"
    assert payload["push_permission"] is False


def test_github_http_5xx_is_network_error(tmp_path: Path) -> None:
    result, payload = _run_preflight(
        tmp_path,
        "http_503",
        "-ActualPublicationContext",
    )

    assert result.returncode == 5
    assert payload["state"] == "NETWORK_ERROR"
