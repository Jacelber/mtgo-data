# GOV-05 test temporary isolation

## Scope

GOV-05 prevents pytest temporary files from becoming repository inputs and
defines when existing test evidence must be reused. It changes test bootstrap,
CI invocation, and development governance only. It does not change product
code, classifiers, statistics, generated data, Schemas, public paths, or
production state.

## Temporary-directory contract

Every pytest process loads `pytest_temp_guard.py`. An explicit `--basetemp`
inside the checkout is a usage error raised before collection. Without an
explicit value, local runs select a process-unique directory under the
checkout's external sibling `.pytest-temp` directory. GitHub Actions passes an
explicit shard-specific path under `RUNNER_TEMP`.

The repository validator continues to derive its inventory from
`git ls-files --cached --others --exclude-standard`. GOV-05 does not broaden or
weaken that inventory. A real unignored source file remains subject to strict
encoding and syntax validation; an external test artifact is not repository
content.

## Evidence reuse and rerun contract

A valid result is identified by the code tree, environment layer, test node ID,
and relevant inputs. Within the same tree and layer, a passed result must not
be rerun merely because another test failed.

- A known and controlled local infrastructure error is recorded as
  `accepted_infrastructure_exception`, with its cause and unaffected passed
  evidence preserved. It is not relabeled as a test pass and does not trigger a
  complete local rerun.
- An unknown failure permits only the failed node ID and the smallest affected
  test set to be rerun while diagnosing it.
- A change to tested code, shared fixtures, dependencies, pytest bootstrap, or
  relevant inputs invalidates only the evidence it can affect. Validation of
  the resulting tree is its first validation, not a rerun of the old tree.
- Local GOV-05 acceptance runs only the focused regression and static checks.
  It intentionally does not duplicate the complete ordinary, baseline,
  Playwright, rule, Schema, or Pages suites.

The final pull-request head receives one independent complete clean-Linux CI
validation. A red GitHub check is never manually described as green. Do not
rerun the same failed workflow head: diagnose it, and if a repair is required,
validate the new head once. After a successful PR run, an exact two-parent
merge uses admission's existing `pr-confirmation` path and does not rerun the
pytest, browser, or static suites. Missing or ambiguous remote evidence remains
fail closed.

## Local acceptance sequence

1. Run `tests/test_pytest_temp_guard.py` once after the guard stabilizes.
2. Run the directly affected workflow and repository-inventory tests once.
3. Run Ruff on changed Python, repository validation, `git diff --check`, and a
   clean-status artifact review once.
4. Stop before commit or publication unless separately authorized.

The focused regression set must remain below five seconds on the maintained
local Python runtime.
