# Agent entry

Use Chinese with the Owner unless requested otherwise. Explain the overall
problem, concrete action and expected result in plain language.

## Start or resume

- Recover the current Owner instruction and confirmed plan for this delivery.
- Read [STATUS](docs/STATUS.yaml) for durable facts, not permissions.
- Use [GOVERNANCE](docs/GOVERNANCE.md) for responsibility, authorization,
  acceptance, failure handling and completion. Reuse valid context.
- Read [ROADMAP](docs/ROADMAP.md) when task position or future scope matters.
- Inspect the branch and unexplained changes before editing. Use an isolated
  preparation branch, preserve others' work, and keep default push disabled.
- Verify current remote facts when they affect integration or publication.

## Read by actual impact

| Question | Source |
| --- | --- |
| What product should exist? | [PROJECT_SCOPE](docs/PROJECT_SCOPE.md) |
| What do numbers and missing states mean? | [STATISTICS_SPEC](docs/STATISTICS_SPEC.md) |
| What data, identities and visibility apply? | [DATA_ARCHITECTURE](docs/DATA_ARCHITECTURE.md) |
| Which result needs which proof? | [QUALITY](docs/QUALITY.md) |
| How to prepare, deliver, resume or restore? | [DELIVERY](docs/DELIVERY.md) |
| Is a named Melee event eligible? | [MELEE_ADMISSION](docs/operations/MELEE_ADMISSION.md) |

These sources answer different questions; they are not a precedence chain.
Git/GitHub and artifacts describe actual operations and objects. Old history,
conversations and memories do not revive retired governance or authorize work.

## Continue to the agreed result

An authorized plan covers its units up to agreed Owner acceptance, then the
same delivery's technical completion. Do not ask again for ordinary commits,
PRs, repairs, merge or applicable publication already within scope. Follow
GOVERNANCE's single decision boundary for genuinely new Owner choices.

Name the concrete risk before checking it. Reuse applicable results; do not
run full suites for unknown paths, stage changes or new commits. Necessary
failure blocks delivery while authorized diagnosis and repair continue.

Fix generators rather than hand-editing statistics. Preserve approved source,
public and privacy boundaries. Never commit credentials or execute archived
tools during restoration. Restore products under the approved recovery policy.

Report progress and limitations honestly. Completion includes the agreed result
and applicable publication confirmation. Stop at the actual endpoint. Give a
useful next step without turning progress reports into approval requests.
