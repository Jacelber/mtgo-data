# CI Gate 3 complete-suite sharding prototype

## Purpose

Reduce PR and `master` validation wall-clock time without removing, weakening,
or duplicating any pytest coverage.

## Fixed boundaries

- CI remains read-only.
- Pull requests and pushes to `master` still collect the complete pytest suite.
- Production workflows, public data, statistics, schemas, dependencies, and
  front-end behavior remain unchanged.
- Gate 4 post-merge trigger reduction remains prohibited.

## Partition

The prototype uses the existing `committed_baseline` marker as the only
partition boundary:

| Shard | Pytest expression |
| --- | --- |
| `ordinary` | `not committed_baseline` |
| `committed-baseline` | `committed_baseline` |

The expressions are exact Boolean complements. Before implementation, pytest
collected 555 node IDs: 546 ordinary and 9 committed-baseline. Their
intersection was empty, their union contained all 555 node IDs, and there
were no missing or extra IDs.

The prototype adds one workflow-contract test. Its resulting collection is
556 node IDs: 547 ordinary and 9 committed-baseline.

## Workflow design

Three validation components run independently:

1. repository, rule, and Schema validation;
2. the two-entry pytest matrix;
3. a small aggregate job named `Repository validation (Python 3.12)`.

The matrix uses `fail-fast: false`, so both shard results remain visible. Each
shard has its own timing report and preserves pytest's exit status. The
aggregate check runs with `always()`, depends on static validation and the
complete matrix, and fails unless both dependency results are `success`.

The aggregate job preserves the established public check name while making it
impossible for a successful shard to hide another shard's failure.

## Local evidence

The accepted pre-sharding PR #118 completed its serial remote validation in
15m06s and is retained as the immediate remote comparison point. Its matching
post-merge `master` run `30335366323` also passed; the serial validation job
ran from 06:36:25Z to 06:52:51Z (16m26s).

On the same clean local base:

| Shard | Result | Wall time | Pytest call time |
| --- | --- | ---: | ---: |
| ordinary | 546 passed, 9 deselected | 337.98s | 336.10s |
| committed-baseline | 9 passed, 546 deselected | 135.67s | 134.60s |

Sequential wall time was approximately 473.65 seconds. With independent
runners, the local critical path is approximately 337.98 seconds, a projected
reduction of 135.67 seconds, or 28.6 percent. This exceeds the one-minute local
prototype threshold without manual file balancing or an added dependency.

Local absolute timings are not interchangeable with GitHub-hosted runner
timings. Remote publication therefore requires separate owner authorization,
complete remote shard counts, and at least one minute of actual wall-clock
improvement before Gate 3 is accepted.

## Timing-report correction

The timing recorder now groups `session.items` in
`pytest_collection_finish`. This occurs after marker deselection, so each
shard summary reports only the tests selected for that shard rather than all
collected tests. Full-suite behavior is unchanged.

## Stop conditions

Do not publish or accept the prototype if:

- shard node-ID union differs from complete collection;
- shard intersection is non-empty;
- either shard or static validation can fail while the aggregate check passes;
- timing summaries misreport selected or completed tests;
- remote wall-clock improvement is below one minute;
- production or public behavior changes.

## Current result

The completed local prototype collected 556 tests and passed both exact
complements independently:

| Shard | Final result | Wall time | Timing-report selection |
| --- | --- | ---: | ---: |
| ordinary | 547 passed, 9 deselected | 287.63s | 547 ordinary |
| committed-baseline | 9 passed, 547 deselected | 127.66s | 9 committed-baseline |

The ordinary shard is the local critical path. Relative to the 415.29-second
sum of the post-change shard runs, independent execution projects a reduction
of 127.66 seconds, or 30.7 percent. The focused workflow and timing tests pass,
and repository validation passes.

The local prototype therefore satisfies the partition, coverage, and projected
improvement gates.

## Remote acceptance

The owner authorized commit, push, PR creation, and merge after successful
checks. PR #119 run `30337562027` supplied the required GitHub-hosted evidence:

- static validation passed;
- the ordinary shard selected and passed 547 tests while deselecting 9;
- the committed-baseline shard selected and passed 9 tests while deselecting
  547;
- the aggregate `Repository validation (Python 3.12)` check passed;
- the complete run took approximately 10m32s, from 07:12:56Z to 07:23:28Z;
- the accepted serial PR #118 baseline took 15m06s, so the observed PR
  wall-clock reduction was approximately 4m34s.

The remote reduction exceeds the one-minute acceptance threshold. Gate 3 is
accepted for merge. Gate 4 remains closed.
