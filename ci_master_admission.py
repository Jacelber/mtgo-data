"""Fail-safe admission decisions for pull requests and master validation.

Ready pull requests and ambiguous Draft pull requests execute the full suite.
Strictly allowlisted Draft changes may use focused feedback. A push to master
may use the lighter confirmation path only when GitHub metadata proves that the
exact two-parent merge was already validated by this workflow.
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
ARTIFACT_IMPACTS = frozenset(
    {
        "none",
        "internal_diagnostics",
        "user_visible_ui",
        "statistical_json_structure",
        "public_path",
    }
)
ARTIFACT_IMPACT_PATTERN = re.compile(
    r"<!--\s*artifact-impact:\s*([^<>]+?)\s*-->", re.IGNORECASE
)
SAFE_DOC_PREFIXES = ("docs/audits/", "docs/history/")
SAFE_UI_SUFFIXES = {
    "assets/js/": ".js",
    "assets/css/": ".css",
    "tests/browser/": ".js",
}


@dataclass(frozen=True)
class AdmissionDecision:
    mode: str
    reason: str
    pull_request: int | None = None
    workflow_run: int | None = None


FetchJson = Callable[[str], object]


def _fail_safe_reason(exc: Exception) -> str:
    detail = re.sub(
        r"[^A-Za-z0-9_.:-]+", "_", f"{type(exc).__name__}:{exc}"
    )[:160]
    return f"fail_safe:{detail}"


def _parse_artifact_impacts(body: object) -> frozenset[str]:
    if not isinstance(body, str):
        raise ValueError("missing_artifact_impact_declaration")
    declarations = ARTIFACT_IMPACT_PATTERN.findall(body)
    if len(declarations) != 1:
        raise ValueError("expected_one_artifact_impact_declaration")
    values = [value.strip().lower() for value in declarations[0].split(",")]
    if not values or any(not value for value in values) or len(values) != len(set(values)):
        raise ValueError("invalid_artifact_impact_declaration")
    unknown = sorted(set(values) - ARTIFACT_IMPACTS)
    if unknown:
        raise ValueError(f"unknown_artifact_impact:{','.join(unknown)}")
    return frozenset(values)


def _pull_request_files(
    *, repository_api: str, pull_request: int, fetch_json: FetchJson
) -> list[dict]:
    payload = fetch_json(
        f"{repository_api}/pulls/{pull_request}/files?per_page=100&page=1"
    )
    if not isinstance(payload, list) or not payload:
        raise ValueError("pull_request_files_missing")
    if len(payload) >= 100:
        raise ValueError("pull_request_files_require_pagination")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("pull_request_file_entry_invalid")
    return payload


def _validated_path(item: dict) -> str:
    path = item.get("filename")
    status = item.get("status")
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        raise ValueError("pull_request_path_invalid")
    if ".." in path.split("/"):
        raise ValueError("pull_request_path_invalid")
    if item.get("previous_filename") or status not in {"added", "modified"}:
        raise ValueError(f"pull_request_file_status:{status or 'missing'}")
    return path


def _is_safe_doc_path(path: str) -> bool:
    return path.endswith(".md") and path.startswith(SAFE_DOC_PREFIXES)


def _is_safe_ui_path(path: str) -> bool:
    return any(
        path.startswith(prefix) and path.endswith(suffix)
        for prefix, suffix in SAFE_UI_SUFFIXES.items()
    )


def decide_pull_request(
    *,
    event_payload: object,
    repository: str,
    fetch_json: FetchJson,
    api_url: str = "https://api.github.com",
) -> AdmissionDecision:
    """Classify Draft feedback without weakening Ready pull-request validation."""

    try:
        if not isinstance(event_payload, dict):
            raise ValueError("pull_request_event_missing")
        pull_request = event_payload.get("pull_request")
        if not isinstance(pull_request, dict):
            raise ValueError("pull_request_payload_missing")
        action = event_payload.get("action")
        if not isinstance(action, str) or not action:
            raise ValueError("pull_request_action_missing")
        draft = pull_request.get("draft")
        if not isinstance(draft, bool):
            raise ValueError("pull_request_draft_state_missing")
        if not draft:
            return AdmissionDecision(
                mode="full", reason=f"ready_pull_request:{action}"
            )

        impacts = _parse_artifact_impacts(pull_request.get("body"))
        number = pull_request.get("number", event_payload.get("number"))
        if not isinstance(number, int):
            raise ValueError("pull_request_number_missing")
        if not repository:
            raise ValueError("repository_missing")
        repository_api = f"{api_url.rstrip('/')}/repos/{repository}"
        files = _pull_request_files(
            repository_api=repository_api,
            pull_request=number,
            fetch_json=fetch_json,
        )
        paths = [_validated_path(item) for item in files]

        if impacts == {"internal_diagnostics"} and all(
            _is_safe_doc_path(path) for path in paths
        ):
            return AdmissionDecision(
                mode="draft-docs", reason="draft_safe_docs"
            )
        if impacts == {"user_visible_ui"} and all(
            _is_safe_ui_path(path) for path in paths
        ):
            return AdmissionDecision(
                mode="draft-ui", reason="draft_safe_user_visible_ui"
            )
        return AdmissionDecision(
            mode="full", reason="draft_requires_full:path_not_fast_allowlisted"
        )
    except Exception as exc:
        return AdmissionDecision(mode="full", reason=_fail_safe_reason(exc))


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
        return AdmissionDecision(
            mode="full",
            reason=_fail_safe_reason(exc),
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
    if event_name == "pull_request":
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        token = os.environ.get("GITHUB_TOKEN", "")
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if not repository or not token or not event_path:
            return AdmissionDecision(
                mode="full", reason="missing_pull_request_context"
            )
        try:
            with Path(event_path).open(encoding="utf-8") as handle:
                event_payload = json.load(handle)
        except Exception as exc:
            return AdmissionDecision(mode="full", reason=_fail_safe_reason(exc))
        return decide_pull_request(
            event_payload=event_payload,
            repository=repository,
            fetch_json=github_fetcher(token),
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
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
            "## CI validation admission",
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
