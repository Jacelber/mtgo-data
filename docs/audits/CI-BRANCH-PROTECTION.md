# CI Gate 2 branch-protection review

## Purpose

Establish a reliable `master` protection boundary before changing duplicated
CI validation. This task changes no test selection, workflow trigger,
production behavior, public output, or statistical behavior.

## Read-only findings

The review was performed against production commit
`dcabfe1a864d21febc5ec558974e476e2cfd68f8`.

- `master` has no classic branch-protection rule.
- The repository has no repository ruleset.
- The repository is public and owned by the personal account `Jacelber`.
- The required PR job has the exact check context
  `Repository validation (Python 3.12)`.
- That check is emitted by the official `github-actions` integration with
  integration ID `15368`.
- All three existing merge methods remain enabled.
- `.github/workflows/update.yml` publishes generated data directly to
  `master` with the repository `GITHUB_TOKEN`.

GitHub documents that repository rulesets can require pull requests, status
checks, and non-fast-forward protection while granting bypass permission to a
specific GitHub App. GitHub also documents that `GITHUB_TOKEN` is an
installation token for the GitHub Actions App. These properties make a
repository ruleset preferable to classic branch protection for this
repository's controlled production publisher.

## Live API constraint

The authorized attempt to create this ruleset in `disabled` mode was rejected
with HTTP 422 before any setting was created:

`Actor GitHub Actions integration must be part of the ruleset source or owner organization`

The repository is owned by a personal account. Although GitHub supports
GitHub-App bypass actors generally, its API does not accept the built-in
GitHub Actions integration as a bypass actor for this ruleset source. The
proposed bypass therefore cannot be activated as written.

## Originally proposed full ruleset

Name: `Protect master validation and production publication`

Target:

- branch ruleset;
- `refs/heads/master` only.

Rules:

1. require changes to enter through a pull request;
2. require `Repository validation (Python 3.12)` from integration `15368`;
3. use loose status checks, so an already-tested PR is not forced to rerun
   solely because another PR merged first;
4. require zero approving reviews, because this is a single-owner repository
   and self-approval is not available;
5. block branch deletion;
6. block non-fast-forward pushes;
7. preserve merge, squash, and rebase as allowed merge methods.

Bypass:

- only integration `15368`, actor type `Integration`, mode `always`;
- no user, repository-role, deploy-key, or broad administrator bypass entry.

The integration bypass is required solely for the existing MTGO production
workflow to publish already-validated generated data directly to `master`.
The PR workflow has `contents: read`. The separately maintained Melee
candidate workflow also has `contents: write`, but publishes only to a
candidate branch; the proposed ruleset targets `master` only. Both publishing
jobs are restricted to workflow definitions dispatched from `master`.

## Activation sequence

Remote repository-setting changes require separate owner authorization.
After authorization:

1. create the ruleset with enforcement `disabled`;
2. read it back and compare every target, rule, check context, integration ID,
   and bypass actor with this document;
3. activate the verified ruleset;
4. publish this documentation branch and confirm that its PR cannot merge
   until `Repository validation (Python 3.12)` succeeds;
5. merge the PR and verify the ruleset remains active;
6. manually dispatch one production update and verify the GitHub Actions App
   can still publish generated data or complete cleanly with no changes;
7. read back the active ruleset and record its ID and verification runs.

No test reduction or trigger change is allowed during this task.

## Failure and rollback

Disable the new ruleset immediately if:

- the expected PR check is not recognized;
- an untested PR can merge;
- a human direct push is accepted;
- force push or deletion is accepted;
- the authorized production workflow cannot publish;
- any actor other than integration `15368` receives bypass permission.

Disabling the newly created ruleset restores the pre-task repository setting.
The existing complete PR, `master`, and production validation remain unchanged,
so rollback does not weaken the validation that existed before this task.

## Owner-approved minimum ruleset

The owner chose the low-risk fallback that preserves the existing production
publisher and complete validation:

- ruleset ID: `19874624`;
- name: `Protect master history`;
- enforcement: `active`;
- target: `refs/heads/master`;
- bypass actors: none;
- rules: `deletion` and `non_fast_forward`.

The ruleset was first created with enforcement `disabled`, read back, compared
with the approved two-rule payload, activated, and read back again. GitHub's
effective-rules endpoint confirms that both rules from ruleset `19874624`
apply to `master`.

This ruleset does not require pull requests or status checks. Normal
fast-forward PR merges and the MTGO production workflow's validated
fast-forward data publication remain allowed. A duplicate production run was
therefore not dispatched solely to test this history-only rule.

## Gate result

Gate 2 is complete at the approved minimum-history-protection level. The
full mandatory PR-check boundary remains unavailable with the current
personal-account production publisher.

Gate 3 may optimize wall-clock time by sharding the complete suite on both PR
and `master`. Gate 4 must continue to prohibit removal of the complete
post-merge validation until a separately approved production publisher
identity or admission-check design exists.
