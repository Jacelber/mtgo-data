# GOV-07-SNAPSHOT-RETIREMENT

Status: `Owner accepted; same-task completion authorized`

## Contract

- Workspace: `D:/dl/crawlerpj/.codex-workspaces/gov-07-snapshot-retirement-20260815-01`
- Branch: `codex/gov-07-snapshot-retirement`
- Base: `fa347998696deddd63b54e8bad7d014dad71d8b5`
- Artifact impact: `none`
- Objective: retire rolling-output byte snapshots and completed R4 shadow-review
  fixtures without changing product code, data, statistical meaning, Schemas,
  public paths, or UI behavior.
- The Owner accepted the local subject on 2026-08-15. Commit, Ready pull
  request, required checks, merge, and applicable automatic publication may
  complete continuously under DEC-094.

The exact deletion operations are:

| Operation | Category | Path |
| --- | --- | --- |
| delete | code | `ci_timing.py` |
| delete | code | `tests/test_ci_timing.py` |
| delete | code | `tests/test_classifier_r4_shadow.py` |
| delete | code | `tests/test_classifier_r4_standard_shadow.py` |

These declarations classify validation only. They do not authorize publication
or another task.

## Failure classification

The sampled baseline failures did not identify a product or statistical defect:

| Evidence | Classification | Reason |
| --- | --- | --- |
| Production run `29795445118` | expected baseline movement | Five fixed-reference tests ran after production directories changed and treated legitimate daily additions as regressions. |
| First clean checkout after `c50d599730d1c0bbce26bb609e9cddae1e6fcc66` | stale expected inputs | Five tests supplied old dates, timestamps, counts, and Pickup week; DEC-036 records that the generator and candidate checks were not defective. |
| Commit `745672c88a09498aebc3bae925422ae9a0fd68a2` | formatting-only snapshot signal | The six generated JSON changes only removed the final newline; no value, structure, calculation, or product behavior changed. |

No sampled failure demonstrated unique protection that required retaining a
rolling-output byte comparison.

## Retirement boundary

Before GOV-07, the `committed_baseline` marker selected eight pytest nodes. The
one report accounting/subtype test contains value-independent semantic checks;
it remains active without the marker. The other seven nodes regenerated rolling
statistics, matchups, Top 8, or the complete Standard product and compared the
bytes with the currently committed output.

Four more unmarked nodes imposed the same tax on rolling classification reports,
Pickup candidates, and Standard/Modern completeness output. GOV-07 removes all
eleven rolling-output snapshot nodes. Existing Schema checks, output invariants,
conservation checks, Top 8 rank and immutability rules, conflict reporting, and
candidate-publication guards remain their semantic replacements.

The completed R4 Modern and Standard shadow tests contained approximately 267 KB
of historical inline review cases. R5 production contracts already bind the
accepted rule documents and frozen-corpus behavior, while the R4 dispositions,
queues, closeout documents, tools, and audit artifacts remain available as
historical evidence. The two oversized test files therefore leave active test
discovery without deleting the evidence they documented.

The marker-specific timing utility and its test are also removed because no
workflow invokes them and their only special grouping ceased to exist. Runtime
measurement remains available from GitHub Actions job and step durations.

## Explicitly retained

- `validate_production_candidate.py` dynamic pre-fetch snapshots and candidate
  comparisons, because they guard the actual candidate rather than an expected
  rolling value;
- value-independent output, Schema, consumer, privacy, allowlist, and
  suppression checks at the publication boundary;
- small semantic and temporary-directory determinism tests that do not compare
  against a manually maintained rolling baseline;
- protected Melee source and event `434455` compatibility contracts;
- frozen classifier corpora and R4 audit artifacts; GOV-08 may separately decide
  whether active ordinary tests still need them.

## Minimal validation contract

1. Static search must find no configured or decorated `committed_baseline`
   marker and no retired rolling snapshot test name.
2. Ruff checks only the modified retained Python test files.
3. Pytest collection checks only the modified retained test files, proving that
   imports and marker configuration remain valid without executing the suite.
4. The directly affected workflow-contract nodes check that both production
   workflows still run the retained clean-checkout suite before candidate work.
5. The retained report semantic node runs once because its marker and name
   changed; it is the only behavioral test whose identity changed.
6. No full pytest, removed snapshot, R4 shadow, generator, fetch, browser,
   production, or public deployment command runs locally.

The completed local evidence is:

- Ruff passed once for the eleven modified retained Python test files.
- Pytest collected 132 nodes from those retained files in 1.16 seconds without
  executing the suite.
- The retained report invariant, MTGO and Melee workflow-order contracts,
  repository-external pytest temporary-directory guard, and live-status
  contract ran once: five passed in 4.00 seconds.
- The final static scope and diff checks are recorded in the Owner handoff.
- Full pytest, retired snapshots, R4 shadow tests, generators, live fetch,
  browser tests, production, and deployment were intentionally not run.

Owner acceptance of the unchanged local subject activates same-task completion
under DEC-094. GOV-08 and every product task remain separately unauthorized.
