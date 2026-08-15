"""Output-gated admission decisions for pull requests and master validation.

Pull-request maturity is not a validation input. Artifact declarations, changed
paths, file statuses, and complete GitHub evidence select the smallest targeted
validation. Unknown evidence stops immediately for owner classification instead
of spending minutes on an unrelated catch-all suite. A push to master may use
the confirmation path only when the exact two-parent merge was already checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


WORKFLOW_PATH = ".github/workflows/ci.yml"
AGGREGATE_JOB = "Repository validation (Python 3.12)"
ADMISSION_JOB = "Select PR validation class or exact-merge confirmation"
TARGETED_JOB = "Targeted PR validation"
TARGETED_CATEGORIES = frozenset({"code", "data", "docs", "governance", "ui"})
SUBJECT_PREFIX = "Validated merge subject:"
CLASS_PREFIX = "Validated PR class:"
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
FILE_OPERATION_PATTERN = re.compile(
    r"<!--\s*file-operation:\s*([^<>]+?)\s*-->", re.IGNORECASE
)
OWNER_UI_ACCEPTANCE_PATTERN = re.compile(
    r"<!--\s*owner-ui-accepted:\s*([^<>]+?)\s*-->", re.IGNORECASE
)
VALIDATING_ACTIONS = frozenset({"opened", "synchronize", "reopened", "edited"})
FILES_PER_PAGE = 100
MAX_PULL_REQUEST_FILES = 3000


@dataclass(frozen=True)
class AdmissionDecision:
    mode: str
    reason: str
    pull_request: int | None = None
    workflow_run: int | None = None
    validation_class: str | None = None


@dataclass(frozen=True)
class FileOperation:
    kind: str
    category: str
    path: str
    previous_path: str | None = None


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


def _declared_path(value: str) -> str:
    path = value.strip()
    if (
        not path
        or "\\" in path
        or path.startswith("/")
        or "|" in path
        or ".." in path.split("/")
    ):
        raise ValueError("file_operation_path_invalid")
    return path


def _parse_file_operations(body: object) -> frozenset[FileOperation]:
    if not isinstance(body, str):
        raise ValueError("missing_artifact_impact_declaration")
    operations: list[FileOperation] = []
    for declaration in FILE_OPERATION_PATTERN.findall(body):
        fields = [field.strip() for field in declaration.split("|")]
        kind = fields[0].lower() if fields else ""
        expected_fields = 4 if kind == "rename" else 3
        if kind not in {"add", "delete", "rename"} or len(fields) != expected_fields:
            raise ValueError("file_operation_declaration_invalid")
        category = fields[1].lower()
        if category not in TARGETED_CATEGORIES:
            raise ValueError(f"file_operation_category_invalid:{category}")
        operations.append(
            FileOperation(
                kind=kind,
                category=category,
                path=_declared_path(fields[-1]),
                previous_path=(
                    _declared_path(fields[2]) if kind == "rename" else None
                ),
            )
        )
    if len(operations) != len(set(operations)):
        raise ValueError("duplicate_file_operation_declaration")
    return frozenset(operations)


def _owner_ui_acceptance(body: object) -> str | None:
    if not isinstance(body, str):
        return None
    declarations = OWNER_UI_ACCEPTANCE_PATTERN.findall(body)
    if len(declarations) > 1:
        raise ValueError("expected_at_most_one_owner_ui_acceptance")
    if not declarations:
        return None
    value = declarations[0].strip().lower()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("owner_ui_acceptance_invalid")
    return value.removeprefix("sha256:")


def _pull_request_files(
    *, repository_api: str, pull_request: int, fetch_json: FetchJson
) -> list[dict]:
    files: list[dict] = []
    page = 1
    while True:
        payload = fetch_json(
            f"{repository_api}/pulls/{pull_request}/files"
            f"?per_page={FILES_PER_PAGE}&page={page}"
        )
        if not isinstance(payload, list):
            raise ValueError("pull_request_files_missing")
        if len(payload) > FILES_PER_PAGE:
            raise ValueError("pull_request_files_page_too_large")
        if not payload:
            if not files:
                raise ValueError("pull_request_files_missing")
            return files
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("pull_request_file_entry_invalid")
        if len(files) + len(payload) > MAX_PULL_REQUEST_FILES:
            raise ValueError("pull_request_files_exceed_supported_limit")
        files.extend(payload)
        if len(payload) < FILES_PER_PAGE:
            return files
        page += 1


def _validated_path(path: object) -> str:
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        raise ValueError("pull_request_path_invalid")
    if ".." in path.split("/"):
        raise ValueError("pull_request_path_invalid")
    return path


def _operation_for(
    declarations: frozenset[FileOperation],
    *,
    kind: str,
    path: str,
    previous_path: str | None = None,
) -> FileOperation | None:
    matches = [
        operation
        for operation in declarations
        if operation.kind == kind
        and operation.path == path
        and operation.previous_path == previous_path
    ]
    if len(matches) > 1:
        raise ValueError("conflicting_file_operation_declaration")
    return matches[0] if matches else None


def _validated_change(
    item: dict,
    declarations: frozenset[FileOperation],
) -> tuple[str, FileOperation | None]:
    path = _validated_path(item.get("filename"))
    status = item.get("status")
    if status == "modified" and not item.get("previous_filename"):
        return path, None
    if status == "added" and not item.get("previous_filename"):
        return path, _operation_for(declarations, kind="add", path=path)
    if status == "removed" and not item.get("previous_filename"):
        operation = _operation_for(declarations, kind="delete", path=path)
        if operation is None:
            raise ValueError(f"undeclared_file_operation:delete:{path}")
        return path, operation
    if status == "renamed":
        previous_path = _validated_path(item.get("previous_filename"))
        operation = _operation_for(
            declarations,
            kind="rename",
            path=path,
            previous_path=previous_path,
        )
        if operation is None:
            raise ValueError(
                f"undeclared_file_operation:rename:{previous_path}:{path}"
            )
        return path, operation
    raise ValueError(f"pull_request_file_status:{status or 'missing'}")


def _path_category(path: str) -> str | None:
    """Return the one minimal check category for a known repository path."""

    if path.startswith("docs/") or path in {
        "AGENTS.md",
        "CLAUDE.md",
        "NOTICE.md",
        "README.md",
        "PROJECT_NOTES.md",
        ".github/copilot-instructions.md",
    }:
        return "docs"
    if (
        path.startswith(("assets/", "melee/", "tests/browser/", "tests/js/"))
        or path in {"index.html", "package.json", "package-lock.json"}
    ):
        return "ui"
    if path.startswith(("schemas/", "stats/", "configs/", "rules/")):
        return "data"
    if path.startswith("src/") or path.endswith(".py"):
        return "code"
    if path.startswith(".github/") or path in {
        ".gitignore",
        "mypy.ini",
        "pyproject.toml",
        "pytest.ini",
        "requirements.txt",
        "requirements-dev.txt",
    }:
        return "governance"
    return None


def _is_user_visible_path(path: str) -> bool:
    return path == "index.html" or path.startswith(("assets/", "melee/"))


def owner_ui_subject_digest(files: list[dict]) -> str | None:
    """Hash only changed files that can alter the published browser UI."""

    records: list[str] = []
    for item in files:
        path = _validated_path(item.get("filename"))
        status = item.get("status")
        previous = item.get("previous_filename")
        previous_path = _validated_path(previous) if previous is not None else None
        if not (
            _is_user_visible_path(path)
            or (previous_path is not None and _is_user_visible_path(previous_path))
        ):
            continue
        if status not in {"added", "modified", "removed", "renamed"}:
            raise ValueError(f"pull_request_file_status:{status or 'missing'}")
        blob_sha = item.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(
            r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", blob_sha
        ):
            raise ValueError(f"owner_ui_blob_sha_missing:{path}")
        records.append(
            json.dumps(
                [status, previous_path or "", path, blob_sha.lower()],
                ensure_ascii=True,
                separators=(",", ":"),
            )
        )
    if not records:
        return None
    canonical = "\n".join(sorted(records)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _classify_pull_request_evidence(
    *, pull_request: dict, files: list[dict]
) -> AdmissionDecision:
    body = pull_request.get("body")
    impacts = _parse_artifact_impacts(body)
    declarations = _parse_file_operations(body)
    used_declarations: set[FileOperation] = set()
    categories: set[str] = set()
    for item in files:
        path, operation = _validated_change(item, declarations)
        inferred = _path_category(path)
        if operation is not None:
            if inferred is not None and inferred != operation.category:
                raise ValueError(
                    f"file_operation_category_mismatch:{path}:"
                    f"{operation.category}:{inferred}"
                )
            if operation.previous_path:
                previous_category = _path_category(operation.previous_path)
                if previous_category is not None and previous_category != operation.category:
                    raise ValueError(
                        f"file_operation_category_mismatch:{operation.previous_path}:"
                        f"{operation.category}:{previous_category}"
                    )
            used_declarations.add(operation)
            categories.add(operation.category)
        elif inferred is not None:
            categories.add(inferred)
        else:
            raise ValueError(f"undeclared_file_operation:add:{path}")
    if declarations != used_declarations:
        raise ValueError("file_operation_declaration_does_not_match_diff")
    expected_ui_digest = owner_ui_subject_digest(files)
    accepted_ui_digest = _owner_ui_acceptance(body)
    if expected_ui_digest is None:
        if "user_visible_ui" in impacts or accepted_ui_digest is not None:
            raise ValueError("owner_ui_acceptance_without_user_visible_change")
    else:
        if "user_visible_ui" not in impacts:
            raise ValueError("user_visible_ui_impact_missing")
        if accepted_ui_digest is None:
            raise ValueError("owner_ui_acceptance_missing")
        if accepted_ui_digest != expected_ui_digest:
            raise ValueError("owner_ui_acceptance_stale")
    ordered = "+".join(sorted(categories))
    return AdmissionDecision(
        mode="targeted",
        reason=(
            f"known_paths:{ordered};declared:{'+'.join(sorted(impacts))};"
            f"file_operations:{len(used_declarations)}"
        ),
        validation_class=f"targeted:{ordered}",
    )


def decide_pull_request(
    *,
    event_payload: object,
    repository: str,
    fetch_json: FetchJson,
    api_url: str = "https://api.github.com",
) -> AdmissionDecision:
    """Classify a PR independently of its Draft or Ready state."""

    try:
        if not isinstance(event_payload, dict):
            raise ValueError("pull_request_event_missing")
        pull_request = event_payload.get("pull_request")
        if not isinstance(pull_request, dict):
            raise ValueError("pull_request_payload_missing")
        action = event_payload.get("action")
        if not isinstance(action, str) or not action:
            raise ValueError("pull_request_action_missing")
        if action not in VALIDATING_ACTIONS:
            raise ValueError(f"pull_request_action_not_supported:{action}")
        if action == "edited":
            changes = event_payload.get("changes")
            if not isinstance(changes, dict):
                raise ValueError("edited_changes_missing")
            if not ({"body", "base"} & set(changes)):
                return AdmissionDecision(
                    mode="metadata-only",
                    reason="edited_metadata_does_not_change_validation_subject",
                    validation_class="metadata-only",
                )

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
        decision = _classify_pull_request_evidence(
            pull_request=pull_request, files=files
        )
        if decision.mode == "unclassified":
            return AdmissionDecision(
                mode=decision.mode,
                reason=f"{decision.reason}:{action}",
                validation_class=decision.validation_class,
            )
        return decision
    except Exception as exc:
        return AdmissionDecision(
            mode="unclassified",
            reason=_fail_safe_reason(exc),
            validation_class="unclassified",
        )


def validation_subject_step(
    pull_request: int, base_sha: str, head_sha: str
) -> str:
    return (
        f"{SUBJECT_PREFIX} pr={pull_request}; base={base_sha}; head={head_sha}"
    )


def validation_class_step(validation_class: str) -> str:
    return f"{CLASS_PREFIX} {validation_class}"


def expected_successful_jobs(validation_class: str) -> frozenset[str] | None:
    if validation_class.startswith("targeted:"):
        categories = frozenset(validation_class.removeprefix("targeted:").split("+"))
        if categories and categories <= TARGETED_CATEGORIES:
            return frozenset({ADMISSION_JOB, TARGETED_JOB, AGGREGATE_JOB})
    return None


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
    validation_class: str,
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
    total_count = jobs_payload.get("total_count")
    if (
        not isinstance(jobs, list)
        or not isinstance(total_count, int)
        or total_count != len(jobs)
        or total_count >= 100
    ):
        return False

    successful_names = [
        job.get("name")
        for job in jobs
        if isinstance(job, dict) and job.get("conclusion") == "success"
    ]
    expected_successful = expected_successful_jobs(validation_class)
    if (
        expected_successful is None
        or len(successful_names) != len(set(successful_names))
        or set(successful_names) != expected_successful
    ):
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
    expected_class_step = validation_class_step(validation_class)
    steps = aggregate_jobs[0].get("steps")
    if not isinstance(steps, list):
        return False
    successful_steps = {
        step.get("name")
        for step in steps
        if isinstance(step, dict) and step.get("conclusion") == "success"
    }
    if not {expected_step, expected_class_step}.issubset(successful_steps):
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
        current_pull_request = fetch_json(f"{repository_api}/pulls/{number}")
        if not isinstance(current_pull_request, dict):
            raise ValueError("current pull request response was not an object")
        if (
            current_pull_request.get("number") != number
            or current_pull_request.get("base", {}).get("ref") != base_ref
            or current_pull_request.get("base", {}).get("sha") != base_sha
            or current_pull_request.get("head", {}).get("sha") != head_sha
            or current_pull_request.get("merge_commit_sha") != merge_sha
            or _parse_time(current_pull_request.get("merged_at")) != merged_at
        ):
            raise ValueError("current pull request metadata changed")
        files = _pull_request_files(
            repository_api=repository_api,
            pull_request=number,
            fetch_json=fetch_json,
        )
        required = _classify_pull_request_evidence(
            pull_request=current_pull_request, files=files
        )
        validation_class = required.validation_class
        if expected_successful_jobs(validation_class) is None:
            raise ValueError("merged pull request validation class is unsupported")
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
        total_count = runs_payload.get("total_count")
        if (
            not isinstance(runs, list)
            or not isinstance(total_count, int)
            or total_count != len(runs)
            or total_count >= 100
        ):
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
                validation_class=validation_class,
                fetch_json=fetch_json,
                repository_api=repository_api,
            ):
                return AdmissionDecision(
                    mode="pr-confirmation",
                    reason=f"exact_validated_merge:{validation_class}",
                    pull_request=number,
                    workflow_run=run["id"],
                    validation_class=validation_class,
                )
        raise ValueError(
            f"no successful {validation_class} validation matched the exact merge"
        )
    except Exception as exc:
        return AdmissionDecision(
            mode="unclassified",
            reason=_fail_safe_reason(exc),
            validation_class="unclassified",
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
                mode="unclassified",
                reason="missing_pull_request_context",
                validation_class="unclassified",
            )
        try:
            with Path(event_path).open(encoding="utf-8") as handle:
                event_payload = json.load(handle)
        except Exception as exc:
            return AdmissionDecision(
                mode="unclassified",
                reason=_fail_safe_reason(exc),
                validation_class="unclassified",
            )
        return decide_pull_request(
            event_payload=event_payload,
            repository=repository,
            fetch_json=github_fetcher(token),
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
    if event_name != "push":
        return AdmissionDecision(
            mode="unclassified",
            reason=f"event:{event_name or 'unknown'}",
            validation_class="unclassified",
        )
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    merge_sha = os.environ.get("GITHUB_SHA", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repository or not merge_sha or not token:
        return AdmissionDecision(
            mode="unclassified",
            reason="missing_github_context",
            validation_class="unclassified",
        )
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


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def owner_ui_marker_from_git(base: str) -> str:
    """Build the PR marker after Owner review and the local commit exist."""

    files: list[dict] = []
    for line in _git("diff", "--name-status", "--find-renames", f"{base}...HEAD").splitlines():
        fields = line.split("\t")
        code = fields[0]
        if code.startswith("R") and len(fields) == 3:
            previous, path = fields[1:]
            status = "renamed"
        elif code in {"A", "M", "D"} and len(fields) == 2:
            path = fields[1]
            previous = None
            status = {"A": "added", "M": "modified", "D": "removed"}[code]
        else:
            raise ValueError(f"unsupported_git_change:{line}")
        if not (
            _is_user_visible_path(path)
            or (previous is not None and _is_user_visible_path(previous))
        ):
            continue
        revision = base if status == "removed" else "HEAD"
        blob_path = previous if status == "removed" else path
        item = {
            "filename": path,
            "status": status,
            "sha": _git("rev-parse", f"{revision}:{blob_path}"),
        }
        if previous is not None:
            item["previous_filename"] = previous
        files.append(item)
    digest = owner_ui_subject_digest(files)
    if digest is None:
        raise ValueError("no_user_visible_change")
    return f"<!-- owner-ui-accepted: sha256:{digest} -->"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT"))
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument(
        "--owner-ui-marker-from",
        metavar="BASE",
        help="print the Owner-accepted UI subject marker for BASE...HEAD",
    )
    args = parser.parse_args()

    if args.owner_ui_marker_from:
        print(owner_ui_marker_from_git(args.owner_ui_marker_from))
        return 0

    decision = decide_from_environment()
    _append_lines(
        args.output,
        [
            f"mode={decision.mode}",
            f"reason={decision.reason}",
            f"pull_request={decision.pull_request or ''}",
            f"workflow_run={decision.workflow_run or ''}",
            f"validation_class={decision.validation_class or ''}",
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
            f"- Validation class: `{decision.validation_class or 'not-applicable'}`",
            f"- Prior validation run: `{decision.workflow_run or 'not-applicable'}`",
            "- Ambiguous, missing, unavailable, or undeclared file-operation evidence stops for owner classification without running a catch-all suite.",
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
