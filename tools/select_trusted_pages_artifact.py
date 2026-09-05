"""Select an artifact from a completed successful Pages run on master."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


PAGES_WORKFLOW_PATH = ".github/workflows/pages.yml"
ALLOWED_EVENTS = frozenset({"push", "workflow_dispatch"})
MAX_ARTIFACT_PAGES = 10
MAX_TRUSTED_AGE_DAYS = 90


class ArtifactSelectionError(ValueError):
    """Indicate that GitHub artifact evidence could not be inspected safely."""


@dataclass(frozen=True)
class TrustedArtifact:
    artifact_id: int
    artifact_name: str
    run_id: int
    run_attempt: int
    head_sha: str


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def select_trusted_artifact(
    artifacts: Iterable[dict[str, Any]],
    *,
    repository: str,
    workflow_id: int,
    get_run: Callable[[int], dict[str, Any]],
    name_matches: Callable[[str], bool],
    now: datetime | None = None,
) -> TrustedArtifact | None:
    """Return the newest artifact whose complete run provenance is trusted."""

    current_time = now or datetime.now(timezone.utc)

    def artifact_id_key(item: dict[str, Any]) -> int:
        value = item.get("id")
        return value if isinstance(value, int) else -1

    candidates = sorted(
        (item for item in artifacts if isinstance(item, dict)),
        key=artifact_id_key,
        reverse=True,
    )
    for artifact in candidates:
        artifact_id = artifact.get("id")
        name = artifact.get("name")
        created_at = _timestamp(artifact.get("created_at"))
        expires_at = _timestamp(artifact.get("expires_at"))
        artifact_run = artifact.get("workflow_run")
        if (
            not isinstance(artifact_id, int)
            or not isinstance(name, str)
            or not name_matches(name)
            or artifact.get("expired") is not False
            or created_at is None
            or created_at > current_time
            or current_time - created_at > timedelta(days=MAX_TRUSTED_AGE_DAYS)
            or expires_at is None
            or expires_at <= current_time
            or not isinstance(artifact_run, dict)
        ):
            continue
        run_id = artifact_run.get("id")
        if not isinstance(run_id, int):
            continue
        run = get_run(run_id)
        run_repository = run.get("repository")
        head_repository = run.get("head_repository")
        head_sha = run.get("head_sha")
        run_attempt = run.get("run_attempt")
        if (
            run.get("id") != run_id
            or run.get("workflow_id") != workflow_id
            or run.get("path") != PAGES_WORKFLOW_PATH
            or run.get("event") not in ALLOWED_EVENTS
            or run.get("head_branch") != "master"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or not isinstance(run_repository, dict)
            or run_repository.get("full_name") != repository
            or not isinstance(head_repository, dict)
            or head_repository.get("full_name") != repository
            or not isinstance(head_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", head_sha) is None
            or artifact_run.get("head_sha") != head_sha
            or artifact_run.get("head_branch") != "master"
            or not isinstance(run_attempt, int)
            or run_attempt < 1
        ):
            continue
        return TrustedArtifact(
            artifact_id=artifact_id,
            artifact_name=name,
            run_id=run_id,
            run_attempt=run_attempt,
            head_sha=head_sha,
        )
    return None


class GitHubClient:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "mtgo-data-pages-artifact-selector/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                value = json.load(response)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ArtifactSelectionError(f"GitHub API request failed: {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ArtifactSelectionError(f"GitHub API response is not an object: {path}")
        return value


def _artifacts(
    client: GitHubClient,
    repository: str,
    exact_name: str | None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for page in range(1, MAX_ARTIFACT_PAGES + 1):
        query = {"per_page": "100", "page": str(page)}
        if exact_name:
            query["name"] = exact_name
        value = client.get(f"/repos/{repository}/actions/artifacts", query)
        items = value.get("artifacts")
        if not isinstance(items, list):
            raise ArtifactSelectionError("GitHub artifact list is malformed")
        found.extend(item for item in items if isinstance(item, dict))
        if len(items) < 100:
            return found
    return found


def _write_outputs(path: Path, artifact: TrustedArtifact | None) -> None:
    values = {
        "found": "true" if artifact else "false",
        "artifact-id": str(artifact.artifact_id) if artifact else "",
        "artifact-name": artifact.artifact_name if artifact else "",
        "run-id": str(artifact.run_id) if artifact else "",
        "run-attempt": str(artifact.run_attempt) if artifact else "",
        "head-sha": artifact.head_sha if artifact else "",
    }
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", default=PAGES_WORKFLOW_PATH)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artifact-name")
    group.add_argument("--artifact-name-regex")
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    if not token:
        parser.error("GITHUB_TOKEN is required")
    client = GitHubClient(api_url, token)
    workflow_path = urllib.parse.quote(args.workflow, safe="")
    try:
        workflow = client.get(
            f"/repos/{args.repository}/actions/workflows/{workflow_path}"
        )
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise ArtifactSelectionError("Pages workflow identity is unavailable")
        exact_name: str | None = args.artifact_name
        regex: str | None = args.artifact_name_regex
        if exact_name is not None:
            name_matches = lambda name: name == exact_name
        else:
            if regex is None:
                raise ArtifactSelectionError("artifact name matcher is unavailable")
            pattern = re.compile(regex)
            name_matches = lambda name: pattern.fullmatch(name) is not None
        artifact = select_trusted_artifact(
            _artifacts(client, args.repository, exact_name),
            repository=args.repository,
            workflow_id=workflow_id,
            get_run=lambda run_id: client.get(
                f"/repos/{args.repository}/actions/runs/{run_id}"
            ),
            name_matches=name_matches,
        )
        _write_outputs(args.github_output, artifact)
    except (ArtifactSelectionError, re.error) as exc:
        parser.error(str(exc))
    print(
        "Trusted Pages artifact: "
        + (f"{artifact.artifact_name} run={artifact.run_id}" if artifact else "none")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
