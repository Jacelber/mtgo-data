# Production operations and recovery

## Scope

This runbook routes an operator through controls that already exist. It does
not authorize a workflow dispatch, source fetch, secret operation, candidate
publication, merge, deployment, rollback, or data change. Read
`docs/STATUS.yaml` for durable live state before acting and obtain explicit
authorization for the exact operation from the active Owner conversation.

New Melee collections use the public upstream participant ID directly and do
not require an HMAC key. A first live v4 collection still requires a separate
preflight for event selection, whitelist state, live collection, and any
remote candidate branch.

Every proposed new whitelist event must follow
[`MELEE_EVENT_ADMISSION_RUNBOOK.md`](MELEE_EVENT_ADMISSION_RUNBOOK.md). That
runbook is the fixed staged admission process; it does not grant authority for
any event-specific stage.

## First response

For a GitHub Actions failure, inspect these in order:

1. the failed run's job result and `$GITHUB_STEP_SUMMARY`;
2. the open stage-specific `MTGO production failure` issue, when one exists;
3. `docs/STATUS.yaml` for durable blockers and pause state, then the active
   Owner conversation for the exact authorized response and stop point.

The executable boundaries are `.github/workflows/update.yml` for MTGO,
`.github/workflows/pages.yml` for Pages, and `.github/workflows/fetch_melee.yml`
for a Melee candidate. Logs diagnose the failed stage; never copy a raw error,
source response, credential, or private removal-request value into an issue.

## MTGO production

| Failed stage | Published output changed? | Minimum response |
| --- | --- | --- |
| `baseline` | No. Candidate generation cannot start. | Inspect the two offline CLI smokes. Repair only an identified code or environment problem, then use a separately authorized rerun. |
| `fetch` | No. Build and publish are blocked. | Check whether the run uploaded `mtgo-fetch-checkpoint`. A rerun of the same `master` SHA within seven days verifies and reuses compatible completed operations automatically; an absent, expired, corrupt, or different-SHA checkpoint starts clean. |
| `build` | No. The fetched candidate did not pass the output gate. | Inspect the first failed candidate check. Do not publish, hand-edit generated files, or rerun unrelated tests. Repair the cause and validate one new candidate. |
| `publish` | Usually no; confirm the remote `master` SHA before deciding. | Inspect the publish summary, exact local/remote SHA evidence, and Git error. Do not manually copy an artifact or create an unbound commit. Retry only after the remote state and failure cause are known. |
| cancellation | No failure issue is guaranteed, and checkpoint packaging may not have completed. | Inspect the cancelled step directly. Do not describe cancellation as a fetch failure or assume resumable state exists. |

One open failure issue is maintained per failed MTGO stage. A downstream
`skipped` job is not a second failure. When the generation-subject digest is
unchanged, the existing published bytes remain authoritative and the workflow
does not build, package, publish, or dispatch Pages.

## Pages

A Pages failure can occur after a validated data commit or accepted site-input
change already reached `master`. Identify the exact publication SHA and Pages
run before acting. Do not rerun data generation or candidate validation: those
belong to the immutable candidate that supplied the publication evidence.

An authorized recovery dispatch carries no partial production evidence. A
normal production dispatch must carry the complete producer run, attempt,
source commit, generation-subject digest, and validated-output digest; partial
evidence fails closed. After a successful deployment, confirm only the bound
SHA and HTTP availability of `index.html`, `melee/index.html`, and
`stats/catalog.json`, once for that deployment.

## Melee candidate and source identity

New complete snapshots use raw manifest v4, minimized resource v2, checkpoint
v3, and identity scheme `source-participant-id-v1`. The collector copies the
public Melee participant ID into `source_participant_id`; normalized output
continues to derive its event-scoped `participant_id`. A live collection still
requires an enabled, verified whitelist entry and separately authorized
`--complete --execute` operation.

| Situation | Required boundary |
| --- | --- |
| Completed v4 snapshot | Continue downstream from its persisted public source IDs; no key is needed. |
| Historical v3 snapshot | Continue to parse its persisted HMAC references read-only; do not rewrite or regenerate it. |
| Historical v2 snapshot | Continue to parse and retain it under the existing compatibility contract. |
| Interrupted v4 collection | Resume only the verified frozen request plan and direct-identity checkpoint. |
| Checkpoint identity/version mismatch | Stop. Do not combine v2/v3/v4 partial state or repair the checkpoint by hand. |
| Disposable rehearsal | Keep it outside retained production input unless retention is separately authorized. |

No HMAC secret or key ID is required by the v4 collection path. Historical v3
key metadata remains readable only for compatibility. The Melee workflow may
create a review branch; it never merges into `master` or deploys the site by
itself.

## Correction and removal requests

`NOTICE.md` defines review, not automatic suppression. Do not place a person's
name or a private request in a public repository configuration file. If the
Owner accepts a concrete removal request, stop and define a separately scoped
task for the affected source, event, fields, current publication, future
recollection, Git history, and third-party copies. A repository-wide string
scan is not an approved privacy control.
