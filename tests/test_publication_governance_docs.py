from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md").read_text(encoding="utf-8")
EFFICIENCY = (
    ROOT / "docs" / "audits" / "CI_EFFICIENCY_PLAN.md"
).read_text(encoding="utf-8")
STATUS = (ROOT / "docs" / "STATUS.yaml").read_text(encoding="utf-8")


def test_repository_publication_path_is_gh_only_and_command_scoped():
    assert "documented remote-mutation client is `gh`" in AGENTS
    assert "do not first attempt PR creation" in AGENTS
    assert "credential.helper=!gh auth git-credential" in WORKFLOW
    assert "gh pr create --repo Jacelber/mtgo-data" in WORKFLOW
    assert "gh pr checks <pr-number>" in WORKFLOW
    assert "gh pr merge <pr-number>" in WORKFLOW
    assert "do not prove token expiration" in WORKFLOW


def test_post_merge_metadata_does_not_create_a_status_only_pr():
    assert "Do not create a second pull request solely" in AGENTS
    assert "Do not automatically create a second status-only pull request" in WORKFLOW
    assert "Do not create or switch to a" in WORKFLOW
    assert (
        "`publication-record`, `status`, `reconciliation`, or `finalization`"
        in WORKFLOW
    )
    assert "PR #122 is a" in EFFICIENCY
    assert "recorded recurrence of the prohibited status-only pattern" in EFFICIENCY


def test_status_records_the_control_without_authorizing_p8_08():
    assert 'id: "P8-PUBLICATION-WORKFLOW-GOVERNANCE"' in STATUS
    assert 'remote_mutation_client: "gh"' in STATUS
    assert "github_app_mutations_allowed: false" in STATUS
    assert 'status: "deferred_by_policy"' in STATUS
    assert "create_status_only_pull_request_after_merge: false" in STATUS
    assert "p8_08_authorized: false" in STATUS
