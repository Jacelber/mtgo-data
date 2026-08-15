# Production operations and recovery

## Scope

This runbook routes an operator through controls that already exist. It does
not authorize a workflow dispatch, source fetch, secret operation, candidate
publication, merge, deployment, rollback, or data change. Read
`docs/STATUS.yaml` before acting and obtain the authorization recorded there.

No production Melee HMAC key is currently provisioned. The first live v3 test
event therefore requires a separate preflight for event selection, key
handling, workflow injection, live collection, and any remote candidate branch.

## First response

For a GitHub Actions failure, inspect these in order:

1. the failed run's job result and `$GITHUB_STEP_SUMMARY`;
2. the open stage-specific `MTGO production failure` issue, when one exists;
3. `docs/STATUS.yaml` for the current blocker, authorization, and stop point.

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

## Melee candidate and HMAC

An event with a retained complete snapshot does not need an HMAC key for
downstream candidate generation. A new live v3 collection requires an enabled,
verified whitelist entry, `--complete --execute`, at least 32 bytes of approved
key material, and a unique non-secret key ID. Missing or invalid settings fail
before network or filesystem side effects.

| Situation | Required boundary |
| --- | --- |
| Completed v3 snapshot | Continue downstream from its persisted participant references; the key is not needed for parsing or generation. |
| Interrupted collection, original key available | Resume only the verified frozen plan with the same key material and key ID. |
| Interrupted collection, key lost | Treat it as non-resumable. Start a clean snapshot with a new key and new key ID; do not join old and new state. |
| Planned rotation | Finish or abandon old-key checkpoints first, then begin a new snapshot boundary with a new key and key ID. |
| Disposable rehearsal | Use a distinct test key and key ID, and do not represent the snapshot as production-retained. |
| Rehearsal that may be retained | Use the production-managed key from the start so later resume and recollection follow one identity contract. |

The manifest and checkpoint contain only the key ID. The secret must not enter
the repository, workflow YAML, command history, logs, artifacts, documentation,
or candidate branch. The Melee workflow may create a review branch; it never
merges into `master` or deploys the site by itself.

## Correction and removal requests

`NOTICE.md` defines review, not automatic suppression. Do not place a person's
name or a private request in a public repository configuration file. If the
Owner accepts a concrete removal request, stop and define a separately scoped
task for the affected source, event, fields, current publication, future
recollection, Git history, and third-party copies. A repository-wide string
scan is not an approved privacy control.
