# P7-CI-EFFICIENCY-02 — CI timing observation

## Purpose

Record comparable test-cost evidence before changing validation triggers,
parallelizing tests, or reducing any post-merge check.

## Scope

The read-only repository-validation workflow continues to run the complete
pytest suite once on pull requests and pushes to `master`. During that existing
run, a local pytest plugin records call-phase durations without changing test
selection or outcomes. The workflow summary then records:

- selected and completed test counts;
- ordinary and `committed_baseline` call-time totals;
- the 25 slowest completed test calls; and
- the pytest exit status.

The temporary JSON report remains in the runner temporary directory. It is not
published as a repository artifact and does not contain production data,
credentials, or player information.

## Boundaries

This task does not change the complete-suite requirement, CI triggers,
permissions, concurrency, production workflow, Pages deployment, statistical
behavior, public output, or source data. It must not be used as evidence that
one test group can be skipped; representative successful PR, `master`, and
production runs are required before proposing CI sharding or trigger changes.

## Initial audit evidence

On 2026-07-24, four successful PR validation runs took 9m05s to 9m48s and four
successful `master` validation runs took 9m03s to 9m59s. Their full pytest
steps occupied approximately 8m22s to 9m10s; checkout, interpreter setup, and
dependency installation were not material contributors. Pages deployments took
approximately 40–55 seconds. The observation therefore targets pytest cost,
not dependency caching or Pages optimization.
