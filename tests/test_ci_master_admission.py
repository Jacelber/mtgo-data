from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ci_master_admission import (
    ADMISSION_JOB,
    AGGREGATE_JOB,
    TARGETED_JOB,
    AdmissionDecision,
    decide_accepted_refresh,
    decide_from_environment,
    decide_local_pull_request,
    decide_master_push,
    decide_pull_request,
    expected_successful_jobs,
    owner_ui_subject_digest,
    validation_class_step,
    validation_subject_step,
    verify_production_evidence,
)


REPOSITORY_API = "https://api.github.test/repos/owner/repo"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
MERGE_SHA = "c" * 40
PRODUCTION_SOURCE_SHA = "d" * 40
PRODUCTION_COMMIT_SHA = "e" * 40
PAGES_SUBJECT_SHA = "f" * 40
GENERATION_SUBJECT_SHA256 = "a" * 64
VALIDATED_OUTPUT_SHA256 = "b" * 64
PRODUCTION_RUN_ID = 4321
PRODUCTION_RUN_ATTEMPT = 2


def _event(body="<!-- artifact-impact: none -->", action="synchronize", changes=None):
    payload = {
        "action": action,
        "pull_request": {"number": 184, "body": body, "draft": True},
    }
    if changes is not None:
        payload["changes"] = changes
    return payload


def _decide_pr(files, **event_overrides):
    pages = [files[index : index + 100] for index in range(0, len(files), 100)]
    if len(files) % 100 == 0:
        pages.append([])

    def fetch(url):
        prefix = f"{REPOSITORY_API}/pulls/184/files?per_page=100&page="
        return pages[int(url.removeprefix(prefix)) - 1]

    return decide_pull_request(
        event_payload=_event(**event_overrides),
        repository="owner/repo",
        fetch_json=fetch,
        api_url="https://api.github.test",
    )


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/STATUS.yaml"], "targeted:docs"),
        (["assets/js/app.js"], "targeted:ui"),
        (["src/mtgmeta/deck.py"], "targeted:code"),
        (["schemas/range.schema.json"], "targeted:data"),
        (["data/modern/melee/classifications/434455.json"], "targeted:data"),
        (["my_archetypes/standard.yaml"], "targeted:data"),
        (["reports/standard/mtgo/index.json"], "targeted:data"),
        (
            ["tests/fixtures/melee/434455_compatibility_manifest.json"],
            "targeted:data",
        ),
        ([".github/workflows/ci.yml"], "targeted:governance"),
        (["tools/github_publication_preflight.ps1"], "targeted:governance"),
        (
            ["docs/STATUS.yaml", "src/mtgmeta/deck.py", "stats/catalog.json"],
            "targeted:code+data+docs",
        ),
    ],
)
def test_known_paths_select_only_their_targeted_categories(paths, expected):
    files = [
        {
            "filename": path,
            "status": "modified",
            **({"sha": "d" * 40} if path.startswith("assets/") else {}),
        }
        for path in paths
    ]
    digest = owner_ui_subject_digest(files)
    body = "<!-- artifact-impact: none -->"
    if digest:
        body = (
            "<!-- artifact-impact: user_visible_ui -->\n"
            f"<!-- owner-ui-accepted: sha256:{digest} -->"
        )
    decision = _decide_pr(files, body=body)
    assert decision.mode == "targeted"
    assert decision.validation_class == expected


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/reviews/Owner-Review.md"], ()),
        (["docs/STATUS.yaml"], ("docs-history",)),
        (["docs/ROADMAP.md"], ("docs-history",)),
        (["configs/mtgo_formats.yaml"], ()),
        (["stats/standard/mtgo/landing/review/candidates_2099-W02.yaml"], ()),
        (["stats/standard/mtgo/meta.json"], ("schema-documents",)),
        (["schemas/mtgo-meta.schema.json"], ("schema-contract",)),
        (["validate_schemas.py"], ("repository-modes", "schema-contract")),
        (
            ["data/modern/melee/classifications/434455.json"],
            ("melee-data-schema",),
        ),
        (
            ["my_archetypes/standard.yaml"],
            ("rules-standard", "top8-restatement"),
        ),
        (
            ["my_archetypes/modern.yaml"],
            ("rules-modern", "top8-restatement"),
        ),
        (
            ["tests/test_classifier_rule_contracts.py"],
            ("classifier-contract",),
        ),
        (
            ["src/mtgmeta/melee/classification.py"],
            ("classifier-adapter",),
        ),
        (["src/mtgmeta/mtgo/top8.py"], ("top8-restatement",)),
        (
            ["tools/build_landing_card_image_cache.py"],
            ("landing-card-image-cache",),
        ),
        (
            ["tools/build_simple_card_localization.py"],
            ("card-localization",),
        ),
        (
            ["src/mtgmeta/data/om1_spm_aliases.json"],
            ("card-localization",),
        ),
        (
            ["tests/test_card_names.py"],
            ("card-localization",),
        ),
        (
            [".github/workflows/pages.yml"],
            (
                "card-localization",
                "ci-admission",
                "ci-workflow",
                "landing-card-image-cache",
            ),
        ),
    ],
)
def test_named_triggers_select_only_the_changed_contract(paths, expected):
    decision = _decide_pr(
        [{"filename": path, "status": "modified"} for path in paths]
    )

    assert decision.validation_triggers == expected


def test_known_added_path_needs_no_operation_declaration():
    decision = _decide_pr(
        [{"filename": "docs/reviews/Owner-Review.md", "status": "added"}]
    )
    assert decision.validation_class == "targeted:docs"


def _melee_publication_files(event_id="441441"):
    paths = [
        f"data_raw/melee/{event_id}/snapshot/manifest.json",
        f"data/modern/melee/events/{event_id}.json",
        f"data/modern/melee/classifications/{event_id}.json",
        f"data/modern/melee/opportunities/{event_id}.json",
        "stats/modern/melee/index.json",
        "stats/catalog.json",
        "README.md",
        "docs/STATUS.yaml",
    ] + [
        f"stats/modern/melee/events/{event_id}/{name}.json"
        for name in ("overview", "decks", "matchup", "quality", "meta")
    ]
    return [
        {
            "filename": path,
            "status": "added" if event_id in path else "modified",
        }
        for path in paths
    ]


def test_new_melee_event_publication_requires_and_accepts_complete_bundle():
    complete = _decide_pr(_melee_publication_files())
    assert complete.mode == "targeted"
    assert "melee-data-schema" in complete.validation_triggers

    incomplete = _decide_pr(
        [item for item in _melee_publication_files() if item["filename"] != "README.md"]
    )
    assert incomplete.mode == "unclassified"
    assert "incomplete_melee_event_publication_bundle" in incomplete.reason
    assert "README.md" in incomplete.reason


def test_stage_c_runner_is_a_known_ui_diagnostic_path():
    decision = _decide_pr(
        [{
            "filename": "scripts/run_card_localization_stage_c_trial.mjs",
            "status": "modified",
        }]
    )
    assert decision.validation_class == "targeted:ui"


@pytest.mark.parametrize(
    ("file", "declaration", "expected"),
    [
        (
            {"filename": "review-output/Owner-Review.md", "status": "added"},
            "add|docs|review-output/Owner-Review.md",
            "targeted:docs",
        ),
        (
            {"filename": "docs/old.md", "status": "removed"},
            "delete|docs|docs/old.md",
            "targeted:docs",
        ),
        (
            {
                "filename": "docs/history/old.md",
                "previous_filename": "docs/old.md",
                "status": "renamed",
            },
            "rename|docs|docs/old.md|docs/history/old.md",
            "targeted:docs",
        ),
    ],
)
def test_exact_declared_file_operations_select_the_minimal_category(
    file, declaration, expected
):
    body = (
        "<!-- artifact-impact: internal_diagnostics -->\n"
        f"<!-- file-operation: {declaration} -->"
    )
    decision = _decide_pr([file], body=body)
    assert decision.mode == "targeted"
    assert decision.validation_class == expected


@pytest.mark.parametrize(
    "files",
    [
        [{"filename": "new_kind/file.xyz", "status": "added"}],
        [{"filename": "README.md", "status": "removed"}],
        [
            {
                "filename": "README.md",
                "previous_filename": "OLD.md",
                "status": "renamed",
            }
        ],
    ],
)
def test_unknown_deleted_or_renamed_paths_stop_without_catch_all(files):
    decision = _decide_pr(files)
    assert decision.mode == "unclassified"
    assert decision.validation_class == "unclassified"


@pytest.mark.parametrize(
    "body",
    [
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/result.md -->\n"
            "<!-- file-operation: add|ui|review-output/result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|review-output/another.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: add|docs|../result.md -->"
        ),
        (
            "<!-- artifact-impact: internal_diagnostics -->\n"
            "<!-- file-operation: copy|docs|review-output/result.md -->"
        ),
    ],
)
def test_wrong_stale_or_invalid_operation_declaration_stops_without_tests(body):
    decision = _decide_pr(
        [{"filename": "review-output/result.md", "status": "added"}],
        body=body,
    )
    assert decision.mode == "unclassified"


def test_declared_category_cannot_override_a_known_path_category():
    body = (
        "<!-- artifact-impact: internal_diagnostics -->\n"
        "<!-- file-operation: add|ui|docs/reviews/result.md -->"
    )
    decision = _decide_pr(
        [{"filename": "docs/reviews/result.md", "status": "added"}],
        body=body,
    )
    assert decision.mode == "unclassified"


def test_pull_request_template_examples_are_not_active_declarations():
    template = (
        Path(__file__).resolve().parents[1] / ".github" / "pull_request_template.md"
    ).read_text(encoding="utf-8")
    assert "<!-- file-operation:" not in template
    assert template.count("<!-- EXAMPLE-file-operation:") == 3
    assert "<!-- owner-ui-accepted:" not in template
    assert template.count("<!-- EXAMPLE-owner-ui-accepted:") == 1
    assert template.count("<!-- artifact-impact:") == 1
    assert "<!-- artifact-impact: REPLACE_ME -->" in template


def _commit_test_repository(repository: Path) -> tuple[str, str]:
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Admission Test"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "admission@example.invalid"],
        cwd=repository,
        check=True,
    )
    readme = repository / "README.md"
    readme.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repository, check=True)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    readme.write_text("head\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "head"], cwd=repository, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return base, head


def _run_git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_file(repository: Path, path: str, content: str, message: str) -> str:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _run_git(repository, "add", path)
    _run_git(repository, "commit", "-qm", message)
    return _run_git(repository, "rev-parse", "HEAD")


def _accepted_refresh_repository(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    repository = tmp_path / "accepted-refresh"
    repository.mkdir()
    _run_git(repository, "init", "-q", "-b", "master")
    _run_git(repository, "config", "user.name", "Admission Test")
    _run_git(repository, "config", "user.email", "admission@example.invalid")
    accepted_base = _commit_file(repository, "README.md", "base\n", "base")

    _run_git(repository, "switch", "-qc", "task")
    accepted_head = _commit_file(
        repository, "docs/policy.md", "accepted task\n", "accepted task"
    )

    _run_git(repository, "switch", "-q", "master")
    current_base = _commit_file(
        repository, "stats/current.json", "{}\n", "automated production"
    )

    _run_git(repository, "switch", "-q", "task")
    _run_git(repository, "merge", "--no-ff", "--no-edit", current_base)
    refreshed_head = _run_git(repository, "rev-parse", "HEAD")
    return repository, accepted_base, accepted_head, current_base, refreshed_head


def test_pr351_topology_refreshes_disjoint_accepted_delta(tmp_path: Path):
    repository, accepted_base, accepted_head, current_base, refreshed_head = (
        _accepted_refresh_repository(tmp_path)
    )

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=accepted_base,
        accepted_head=accepted_head,
        current_base=current_base,
        refreshed_head=refreshed_head,
    )

    assert decision.state == "READY_FOR_EXACT_VALIDATION"
    assert decision.reason == "accepted_delta_mechanically_preserved"
    assert decision.task_paths == ("docs/policy.md",)
    assert decision.master_paths == ("stats/current.json",)
    assert _run_git(repository, "show", "-s", "--format=%P", refreshed_head).split() == [
        accepted_head,
        current_base,
    ]

    _run_git(repository, "switch", "-q", "master")
    _run_git(repository, "merge", "--no-ff", "--no-edit", refreshed_head)
    merge_subject = _run_git(repository, "rev-parse", "HEAD")
    assert _run_git(repository, "show", "-s", "--format=%P", merge_subject).split() == [
        current_base,
        refreshed_head,
    ]
    assert _run_git(repository, "diff", "--name-only", refreshed_head, merge_subject) == ""

    current_evidence = _valid_merge_responses(
        base_sha=current_base,
        head_sha=refreshed_head,
        merge_sha=merge_subject,
    )
    assert _decide_merge(current_evidence, merge_sha=merge_subject).mode == (
        "pr-confirmation"
    )

    old_evidence = _valid_merge_responses(
        base_sha=accepted_base,
        head_sha=accepted_head,
        merge_sha=merge_subject,
    )
    old_evidence[f"{REPOSITORY_API}/commits/{merge_subject}"]["parents"] = [
        {"sha": current_base},
        {"sha": refreshed_head},
    ]
    old_decision = _decide_merge(old_evidence, merge_sha=merge_subject)
    assert old_decision.mode == "unclassified"
    assert "pull_request_base_head_do_not_match_merge_parents" in old_decision.reason


def test_accepted_refresh_cli_reports_exact_combined_subject(tmp_path: Path):
    repository, accepted_base, accepted_head, current_base, refreshed_head = (
        _accepted_refresh_repository(tmp_path)
    )

    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve().parents[1] / "ci_master_admission.py"),
        "--verify-accepted-refresh",
        "--accepted-base",
        accepted_base,
        "--accepted-head",
        accepted_head,
        "--current-base",
        current_base,
        "--repository-root",
        str(repository),
    ]
    precheck = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(precheck.stdout)["state"] == "READY_TO_MERGE"

    completed = subprocess.run(
        [*command, "--refreshed-head", refreshed_head],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["state"] == "READY_FOR_EXACT_VALIDATION"
    assert result["accepted_base"] == accepted_base
    assert result["accepted_head"] == accepted_head
    assert result["current_base"] == current_base
    assert result["refreshed_head"] == refreshed_head


def test_accepted_refresh_is_not_needed_when_base_did_not_move(tmp_path: Path):
    repository = tmp_path / "unchanged-base"
    base, head = _commit_test_repository(repository)

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=base,
        accepted_head=head,
        current_base=base,
    )

    assert decision.state == "NO_REFRESH_REQUIRED"


@pytest.mark.parametrize("master_operation", ["modify", "delete", "rename"])
def test_accepted_refresh_rejects_overlapping_operations(
    tmp_path: Path, master_operation: str
):
    repository = tmp_path / master_operation
    repository.mkdir()
    _run_git(repository, "init", "-q", "-b", "master")
    _run_git(repository, "config", "user.name", "Admission Test")
    _run_git(repository, "config", "user.email", "admission@example.invalid")
    accepted_base = _commit_file(repository, "shared.txt", "base\n", "base")

    _run_git(repository, "switch", "-qc", "task")
    accepted_head = _commit_file(repository, "shared.txt", "task\n", "task")

    _run_git(repository, "switch", "-q", "master")
    if master_operation == "modify":
        current_base = _commit_file(repository, "shared.txt", "master\n", "modify")
    elif master_operation == "delete":
        _run_git(repository, "rm", "-q", "shared.txt")
        _run_git(repository, "commit", "-qm", "delete")
        current_base = _run_git(repository, "rev-parse", "HEAD")
    else:
        _run_git(repository, "mv", "shared.txt", "renamed.txt")
        _run_git(repository, "commit", "-qm", "rename")
        current_base = _run_git(repository, "rev-parse", "HEAD")

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=accepted_base,
        accepted_head=accepted_head,
        current_base=current_base,
    )

    assert decision.state == "STOP"
    assert "accepted_and_master_paths_overlap" in decision.reason


def test_accepted_refresh_rejects_disjoint_paths_that_cannot_merge(tmp_path: Path):
    repository = tmp_path / "file-directory-conflict"
    repository.mkdir()
    _run_git(repository, "init", "-q", "-b", "master")
    _run_git(repository, "config", "user.name", "Admission Test")
    _run_git(repository, "config", "user.email", "admission@example.invalid")
    accepted_base = _commit_file(repository, "README.md", "base\n", "base")

    _run_git(repository, "switch", "-qc", "task")
    accepted_head = _commit_file(
        repository, "shared/item.txt", "task\n", "accepted task"
    )

    _run_git(repository, "switch", "-q", "master")
    current_base = _commit_file(repository, "shared", "master\n", "current base")

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=accepted_base,
        accepted_head=accepted_head,
        current_base=current_base,
    )

    assert decision.state == "STOP"
    assert "accepted_refresh_merge_conflict" in decision.reason


def test_accepted_refresh_rejects_changed_task_content(tmp_path: Path):
    repository, accepted_base, accepted_head, current_base, _ = (
        _accepted_refresh_repository(tmp_path)
    )
    (repository / "docs/policy.md").write_text(
        "changed after acceptance\n", encoding="utf-8"
    )
    _run_git(repository, "add", "docs/policy.md")
    _run_git(repository, "commit", "--amend", "-qm", "change accepted result")
    refreshed_head = _run_git(repository, "rev-parse", "HEAD")

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=accepted_base,
        accepted_head=accepted_head,
        current_base=current_base,
        refreshed_head=refreshed_head,
    )

    assert decision.state == "STOP"
    assert "accepted_task_content_changed" in decision.reason


def test_accepted_refresh_rejects_changed_current_base_content(tmp_path: Path):
    repository, accepted_base, accepted_head, current_base, _ = (
        _accepted_refresh_repository(tmp_path)
    )
    (repository / "stats/current.json").write_text(
        '{"changed": true}\n', encoding="utf-8"
    )
    _run_git(repository, "add", "stats/current.json")
    _run_git(repository, "commit", "--amend", "-qm", "change current base content")
    refreshed_head = _run_git(repository, "rev-parse", "HEAD")

    decision = decide_accepted_refresh(
        repository_root=repository,
        accepted_base=accepted_base,
        accepted_head=accepted_head,
        current_base=current_base,
        refreshed_head=refreshed_head,
    )

    assert decision.state == "STOP"
    assert "refreshed_delta_operations_changed" in decision.reason


def test_local_pr_contract_reuses_remote_admission_rules(tmp_path: Path):
    repository = tmp_path / "repository"
    base, head = _commit_test_repository(repository)

    ready, resolved_base, resolved_head = decide_local_pull_request(
        repository_root=repository,
        base=base,
        head=head,
        body="<!-- artifact-impact: none -->",
    )
    invalid, _, _ = decide_local_pull_request(
        repository_root=repository,
        base=base,
        head=head,
        body="<!-- artifact-impact: REPLACE_ME -->",
    )

    assert ready.mode == "targeted"
    assert ready.validation_class == "targeted:docs"
    assert resolved_base == base
    assert resolved_head == head
    assert invalid.mode == "unclassified"
    assert "unknown_artifact_impact:replace_me" in invalid.reason


def test_exact_owner_accepted_ui_subject_needs_no_repeat_ui_test():
    files = [
        {"filename": "assets/js/app.js", "status": "modified", "sha": "d" * 40},
        {"filename": "docs/STATUS.yaml", "status": "modified"},
    ]
    digest = owner_ui_subject_digest(files)
    decision = _decide_pr(
        files,
        body=(
            "<!-- artifact-impact: user_visible_ui -->\n"
            f"<!-- owner-ui-accepted: sha256:{digest} -->"
        ),
    )
    assert decision.mode == "targeted"
    assert decision.validation_class == "targeted:docs+ui"


@pytest.mark.parametrize(
    "body",
    [
        "<!-- artifact-impact: user_visible_ui -->",
        (
            "<!-- artifact-impact: user_visible_ui -->\n"
            f"<!-- owner-ui-accepted: sha256:{'e' * 64} -->"
        ),
        (
            "<!-- artifact-impact: user_visible_ui -->\n"
            f"<!-- owner-ui-accepted: sha256:{'e' * 64} -->\n"
            f"<!-- owner-ui-accepted: sha256:{'f' * 64} -->"
        ),
        "<!-- artifact-impact: none -->",
        (
            "<!-- artifact-impact: user_visible_ui -->\n"
            "<!-- owner-ui-accepted: sha256:not-a-digest -->"
        ),
    ],
)
def test_missing_stale_duplicate_or_undeclared_ui_acceptance_stops(body):
    decision = _decide_pr(
        [{"filename": "index.html", "status": "modified", "sha": "d" * 40}],
        body=body,
    )
    assert decision.mode == "unclassified"


def test_internal_ui_harness_change_does_not_need_owner_ui_acceptance():
    decision = _decide_pr(
        [{"filename": "tests/js/phase8-runtime.test.js", "status": "modified"}]
    )
    assert decision.mode == "targeted"
    assert decision.validation_class == "targeted:ui"


def test_stale_ui_impact_or_marker_without_visible_change_stops():
    for body in (
        "<!-- artifact-impact: user_visible_ui -->",
        (
            "<!-- artifact-impact: none -->\n"
            f"<!-- owner-ui-accepted: sha256:{'e' * 64} -->"
        ),
    ):
        assert _decide_pr(
            [{"filename": "package.json", "status": "modified"}], body=body
        ).mode == "unclassified"


def test_missing_or_invalid_impact_declaration_stops_without_tests():
    for body in ("", "<!-- artifact-impact: mystery -->"):
        assert _decide_pr(
            [{"filename": "README.md", "status": "modified"}], body=body
        ).mode == "unclassified"


def test_metadata_edit_without_body_or_base_change_runs_nothing():
    decision = _decide_pr(
        [{"filename": "README.md", "status": "modified"}],
        action="edited",
        changes={"title": {"from": "old"}},
    )
    assert decision.mode == "metadata-only"


def test_file_pagination_is_complete_before_classification():
    files = [
        {"filename": f"docs/history/item-{index}.md", "status": "modified"}
        for index in range(101)
    ]
    assert _decide_pr(files).validation_class == "targeted:docs"


def _valid_merge_responses(
    validation_class="targeted:governance",
    *,
    base_sha=BASE_SHA,
    head_sha=HEAD_SHA,
    merge_sha=MERGE_SHA,
):
    pull_request = {
        "number": 119,
        "body": "<!-- artifact-impact: none -->",
        "merged_at": "2026-07-28T07:38:13Z",
        "merge_commit_sha": merge_sha,
        "base": {"ref": "master", "sha": base_sha},
        "head": {"sha": head_sha},
    }
    jobs = []
    for name in sorted(expected_successful_jobs(validation_class) or ()):
        job = {"name": name, "conclusion": "success"}
        if name == AGGREGATE_JOB:
            job["steps"] = [
                {
                    "name": validation_subject_step(119, base_sha, head_sha),
                    "conclusion": "success",
                },
                {
                    "name": validation_class_step(validation_class),
                    "conclusion": "success",
                },
            ]
        jobs.append(job)
    return {
        f"{REPOSITORY_API}/commits/{merge_sha}": {
            "parents": [{"sha": base_sha}, {"sha": head_sha}]
        },
        f"{REPOSITORY_API}/commits/{merge_sha}/pulls?per_page=100": [pull_request],
        f"{REPOSITORY_API}/pulls/119": pull_request,
        f"{REPOSITORY_API}/pulls/119/files?per_page=100&page=1": [
            {"filename": ".github/workflows/ci.yml", "status": "modified"}
        ],
        (
            f"{REPOSITORY_API}/actions/workflows/ci.yml/runs?"
            f"event=pull_request&head_sha={head_sha}&status=success&per_page=100"
        ): {
            "total_count": 1,
            "workflow_runs": [
                {
                    "id": 42,
                    "run_attempt": 1,
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                    "head_sha": head_sha,
                    "path": ".github/workflows/ci.yml",
                    "updated_at": "2026-07-28T07:37:50Z",
                }
            ],
        },
        f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100": {
            "total_count": len(jobs),
            "jobs": jobs,
        },
    }


def _decide_merge(responses, *, merge_sha=MERGE_SHA):
    return decide_master_push(
        repository="owner/repo",
        merge_sha=merge_sha,
        fetch_json=lambda url: responses[url],
        api_url="https://api.github.test",
    )


def test_exact_merge_reuses_only_the_exact_targeted_evidence():
    decision = _decide_merge(_valid_merge_responses())
    assert decision == AdmissionDecision(
        mode="pr-confirmation",
        reason="exact_validated_merge:targeted:governance",
        pull_request=119,
        workflow_run=42,
        validation_class="targeted:governance",
    )


def test_pr351_topology_accepts_exact_current_base_and_task_head_evidence():
    accepted_base = BASE_SHA
    accepted_head = HEAD_SHA
    current_base = PRODUCTION_SOURCE_SHA
    assert len({accepted_base, accepted_head, current_base, MERGE_SHA}) == 4

    decision = _decide_merge(
        _valid_merge_responses(base_sha=current_base, head_sha=accepted_head)
    )

    assert decision.mode == "pr-confirmation"
    assert decision.reason == "exact_validated_merge:targeted:governance"


def test_pr351_topology_rejects_old_base_head_evidence_for_combined_merge():
    responses = _valid_merge_responses()
    responses[f"{REPOSITORY_API}/commits/{MERGE_SHA}"]["parents"] = [
        {"sha": PRODUCTION_SOURCE_SHA},
        {"sha": HEAD_SHA},
    ]

    decision = _decide_merge(responses)

    assert decision.mode == "unclassified"
    assert "pull_request_base_head_do_not_match_merge_parents" in decision.reason


def test_incomplete_merge_evidence_stops_without_full_suite():
    responses = _valid_merge_responses()
    jobs_url = f"{REPOSITORY_API}/actions/runs/42/attempts/1/jobs?per_page=100"
    responses[jobs_url]["jobs"].pop()
    responses[jobs_url]["total_count"] -= 1
    assert _decide_merge(responses).mode == "unclassified"


def test_direct_push_stops_without_full_suite():
    responses = {f"{REPOSITORY_API}/commits/{MERGE_SHA}": {"parents": [{"sha": BASE_SHA}]}}
    assert _decide_merge(responses).mode == "unclassified"


def test_targeted_job_matrix_has_no_heavy_baseline_jobs():
    assert expected_successful_jobs("targeted:code+docs") == frozenset(
        {ADMISSION_JOB, TARGETED_JOB, AGGREGATE_JOB}
    )
    assert expected_successful_jobs("unclassified") is None


def test_workflow_dispatch_stops_for_explicit_classification(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    decision = decide_from_environment()
    assert decision.mode == "unclassified"


def _production_responses(pages_subject_sha=PAGES_SUBJECT_SHA):
    repository_api = "https://api.github.test/repos/owner/repo"
    message = "\n".join(
        [
            "chore: update MTGO production data",
            "",
            f"Production-Run: {PRODUCTION_RUN_ID}",
            f"Production-Attempt: {PRODUCTION_RUN_ATTEMPT}",
            f"Production-Source: {PRODUCTION_SOURCE_SHA}",
            f"Generation-Subject-SHA256: {GENERATION_SUBJECT_SHA256}",
            f"Validated-Output-SHA256: {VALIDATED_OUTPUT_SHA256}",
        ]
    )
    jobs = [
        {"name": "Fetch MTGO candidate data", "conclusion": "success"},
        {"name": "Build and validate MTGO candidate", "conclusion": "success"},
        {
            "name": "Publish validated MTGO data",
            "status": "in_progress",
            "conclusion": None,
        },
    ]
    return {
        f"{repository_api}/compare/{PRODUCTION_COMMIT_SHA}...{pages_subject_sha}": {
            "status": (
                "identical"
                if pages_subject_sha == PRODUCTION_COMMIT_SHA
                else "ahead"
            ),
            "merge_base_commit": {"sha": PRODUCTION_COMMIT_SHA},
        },
        f"{repository_api}/commits/{PRODUCTION_COMMIT_SHA}": {
            "parents": [{"sha": PRODUCTION_SOURCE_SHA}],
            "commit": {"message": message},
        },
        f"{repository_api}/actions/runs/{PRODUCTION_RUN_ID}": {
            "id": PRODUCTION_RUN_ID,
            "run_attempt": PRODUCTION_RUN_ATTEMPT,
            "head_sha": PRODUCTION_SOURCE_SHA,
            "event": "schedule",
            "path": ".github/workflows/update.yml",
            "status": "in_progress",
            "conclusion": None,
        },
        (
            f"{repository_api}/actions/runs/{PRODUCTION_RUN_ID}/attempts/"
            f"{PRODUCTION_RUN_ATTEMPT}/jobs?per_page=100"
        ): {"total_count": len(jobs), "jobs": jobs},
    }


def _verify_production(responses, pages_subject_sha=PAGES_SUBJECT_SHA):
    return verify_production_evidence(
        repository="owner/repo",
        publication_commit=PRODUCTION_COMMIT_SHA,
        pages_subject_commit=pages_subject_sha,
        producer_run_id=PRODUCTION_RUN_ID,
        producer_run_attempt=PRODUCTION_RUN_ATTEMPT,
        source_commit=PRODUCTION_SOURCE_SHA,
        generation_subject_sha256=GENERATION_SUBJECT_SHA256,
        validated_output_sha256=VALIDATED_OUTPUT_SHA256,
        fetch_json=lambda url: responses[url],
        api_url="https://api.github.test",
    )


def test_ancestor_production_commit_is_admitted_for_the_pages_subject():
    assert _verify_production(_production_responses()) == (
        f"verified_production_publication:{PRODUCTION_COMMIT_SHA}:"
        f"run={PRODUCTION_RUN_ID}:attempt={PRODUCTION_RUN_ATTEMPT}"
    )


def test_exact_production_commit_remains_an_admitted_pages_subject():
    responses = _production_responses(PRODUCTION_COMMIT_SHA)
    assert _verify_production(responses, PRODUCTION_COMMIT_SHA).startswith(
        f"verified_production_publication:{PRODUCTION_COMMIT_SHA}:"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "ancestry",
        "parent",
        "trailer",
        "run",
        "fetch-job",
        "build-job",
        "publish-job",
    ],
)
def test_stale_or_incomplete_production_evidence_stops(mutation):
    responses = _production_responses()
    repository_api = "https://api.github.test/repos/owner/repo"
    if mutation == "ancestry":
        comparison = responses[
            f"{repository_api}/compare/{PRODUCTION_COMMIT_SHA}...{PAGES_SUBJECT_SHA}"
        ]
        comparison.update(
            {
                "status": "diverged",
                "merge_base_commit": {"sha": PRODUCTION_SOURCE_SHA},
            }
        )
    elif mutation == "parent":
        responses[f"{repository_api}/commits/{PRODUCTION_COMMIT_SHA}"]["parents"] = [
            {"sha": "f" * 40}
        ]
    elif mutation == "trailer":
        commit = responses[f"{repository_api}/commits/{PRODUCTION_COMMIT_SHA}"]
        commit["commit"]["message"] = commit["commit"]["message"].replace(
            VALIDATED_OUTPUT_SHA256, "f" * 64
        )
    elif mutation == "run":
        responses[f"{repository_api}/actions/runs/{PRODUCTION_RUN_ID}"]["head_sha"] = (
            "f" * 40
        )
    else:
        jobs_url = (
            f"{repository_api}/actions/runs/{PRODUCTION_RUN_ID}/attempts/"
            f"{PRODUCTION_RUN_ATTEMPT}/jobs?per_page=100"
        )
        job_name = (
            {
                "fetch-job": "Fetch MTGO candidate data",
                "build-job": "Build and validate MTGO candidate",
                "publish-job": "Publish validated MTGO data",
            }[mutation]
        )
        job = next(
            item for item in responses[jobs_url]["jobs"] if item["name"] == job_name
        )
        job.update({"status": "completed", "conclusion": "failure"})
    with pytest.raises(ValueError):
        _verify_production(responses)
