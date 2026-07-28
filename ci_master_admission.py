"""Fail-safe admission decision for post-merge master validation.

Pull requests and manual runs always execute the full validation suite. A push
to master may use the lighter confirmation path only when GitHub metadata proves
that the exact two-parent merge was already validated by this workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


WORKFLOW_PATH = ".github/workflows/ci.yml"
AGGREGATE_JOB = "Repository validation (Python 3.12)"
REQUIRED_SUCCESSFUL_JOBS = {
    "Repository files, rules, and schemas",
    "Pytest shard (ordinary)",
    "Pytest shard (committed-baseline)",
    AGGREGATE_JOB,
}
SUBJECT_PREFIX = "Validated merge subject:"


@dataclass(frozen=True)
class AdmissionDecision:
    mode: str
    reason: str
    pull_request: int | None = None
    workflow_run: int | None = None


FetchJson = Callable[[str], object]


def validation_subject_step(
    pull_request: int, base_sha: str, head_sha: str
) -> str:
    return (
        f"{SUBJECT_PREFIX} pr={pull_request}; base={base_sha}; head={head_sha}"
    )


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _single_matching_pr(
    pull_requests: object, *, merge_sha: str, base_ref: str
) -> dict:
    if not isinstance(pull_requests, list):
        raise ValueError("pull request response was not a list")
    matches = [
        item
        for item in pull_requests
        if isinstance(item, dict)
        and item.get("merge_commit_sha") == merge_sha
        and item.get("merged_at")
        and item.get("base", {}).get("ref") == base_ref
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one merged pull request, found {len(matches)}")
    return matches[0]


def _merge_parents(commit: object) -> tuple[str, str]:
    if not isinstance(commit, dict):
        raise ValueError("commit response was not an object")
    parents = commit.get("parents")
    if not isinstance(parents, list) or len(parents) != 2:
        raise ValueError("master commit is not an exact two-parent merge")
    shas = tuple(parent.get("sha") for parent in parents if isinstance(parent, dict))
    if len(shas) != 2 or not all(isinstance(sha, str) for sha in shas):
        raise ValueError("merge parent metadata is incomplete")
    return shas[0], shas[1]


def _run_matches_subject(
    run: object,
    *,
    pull_request: int,
    base_sha: str,
    head_sha: str,
    merged_at: datetime,
    fetch_json: FetchJson,
    repository_api: str,
) -> bool:
    if not isinstance(run, dict):
        return False
    if (
        run.get("event") != "pull_request"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("head_sha") != head_sha
        or str(run.get("path", "")).split("@", 1)[0] != WORKFLOW_PATH
        or _parse_time(run.get("updated_at")) > merged_at
    ):
        return False

    run_id = run.get("id")
    attempt = run.get("run_attempt")
    if not isinstance(run_id, int) or not isinstance(attempt, int):
        return False
    jobs_payload = fetch_json(
        f"{repository_api}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100"
    )
    if not isinstance(jobs_payload, dict):
        return False
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        return False

    successful = {
        job.get("name")
        for job in jobs
        if isinstance(job, dict) and job.get("conclusion") == "success"
    }
    if not REQUIRED_SUCCESSFUL_JOBS.issubset(successful):
        return False

    aggregate_jobs = [
        job
        for job in jobs
        if isinstance(job, dict)
        and job.get("name") == AGGREGATE_JOB
        and job.get("conclusion") == "success"
    ]
    if len(aggregate_jobs) != 1:
        return False
    expected_step = validation_subject_step(pull_request, base_sha, head_sha)
    steps = aggregate_jobs[0].get("steps")
    if not isinstance(steps, list) or not any(
        isinstance(step, dict)
        and step.get("name") == expected_step
        and step.get("conclusion") == "success"
        for step in steps
    ):
        return False

    return True


def decide_master_push(
    *,
    repository: str,
    merge_sha: str,
    fetch_json: FetchJson,
    api_url: str = "https://api.github.com",
    base_ref: str = "master",
) -> AdmissionDecision:
    repository_api = f"{api_url.rstrip('/')}/repos/{repository}"
    try:
        commit = fetch_json(f"{repository_api}/commits/{quote(merge_sha)}")
        base_sha, head_sha = _merge_parents(commit)
        pull_requests = fetch_json(
            f"{repository_api}/commits/{quote(merge_sha)}/pulls?per_page=100"
        )
        pull_request = _single_matching_pr(
            pull_requests, merge_sha=merge_sha, base_ref=base_ref
        )
        if (
            pull_request.get("base", {}).get("sha") != base_sha
            or pull_request.get("head", {}).get("sha") != head_sha
        ):
            raise ValueError("pull request base/head do not match merge parents")

        number = pull_request.get("number")
        if not isinstance(number, int):
            raise ValueError("pull request number is missing")
        merged_at = _parse_time(pull_request.get("merged_at"))
        query = urlencode(
            {
                "event": "pull_request",
                "head_sha": head_sha,
                "status": "success",
                "per_page": 100,
            }
        )
        runs_payload = fetch_json(
            f"{repository_api}/actions/workflows/"
            f"{quote(Path(WORKFLOW_PATH).name, safe='')}/runs?{query}"
        )
        if not isinstance(runs_payload, dict):
            raise ValueError("workflow run response was not an object")
        runs = runs_payload.get("workflow_runs")
        if not isinstance(runs, list):
            raise ValueError("workflow run list is missing")
        runs = sorted(
            runs,
            key=lambda item: str(item.get("updated_at", ""))
            if isinstance(item, dict)
            else "",
            reverse=True,
        )
        for run in runs:
            if _run_matches_subject(
                run,
                pull_request=number,
                base_sha=base_sha,
                head_sha=head_sha,
                merged_at=merged_at,
                fetch_json=fetch_json,
                repository_api=repository_api,
            ):
                return AdmissionDecision(
                    mode="pr-confirmation",
                    reason="exact_validated_merge",
                    pull_request=number,
                    workflow_run=run["id"],
                )
        raise ValueError("no successful full validation matched the exact merge")
    except Exception as exc:
        detail = re.sub(
            r"[^A-Za-z0-9_.:-]+", "_", f"{type(exc).__name__}:{exc}"
        )[:160]
        return AdmissionDecision(
            mode="full",
            reason=f"fail_safe:{detail}",
        )


def github_fetcher(token: str) -> FetchJson:
    def fetch(url: str) -> object:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "mtgo-data-ci-master-admission",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(request, timeout=20) as response:
            return json.load(response)

    return fetch


def decide_from_environment() -> AdmissionDecision:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "push":
        return AdmissionDecision(mode="full", reason=f"event:{event_name or 'unknown'}")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    merge_sha = os.environ.get("GITHUB_SHA", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repository or not merge_sha or not token:
        return AdmissionDecision(mode="full", reason="missing_github_context")
    return decide_master_push(
        repository=repository,
        merge_sha=merge_sha,
        fetch_json=github_fetcher(token),
        api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    )


def _append_lines(path: str | None, lines: list[str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT"))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    args = parser.parse_args()

    decision = decide_from_environment()
    _append_lines(
        args.output,
        [
            f"mode={decision.mode}",
            f"reason={decision.reason}",
            f"pull_request={decision.pull_request or ''}",
            f"workflow_run={decision.workflow_run or ''}",
        ],
    )
    _append_lines(
        args.summary,
        [
            "## Master validation admission",
            "",
            f"- Mode: `{decision.mode}`",
            f"- Reason: `{decision.reason}`",
            f"- Pull request: `{decision.pull_request or 'not-applicable'}`",
            f"- Prior full-validation run: `{decision.workflow_run or 'not-applicable'}`",
            "- Ambiguous, missing, or unavailable evidence always selects full validation.",
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
