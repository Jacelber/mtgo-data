# P8 Rolling Contract Test Hotfix

Status: `published`
Task: `P8-HOTFIX-ROLLING-CONTRACT-TESTS`
Base: `400a2c76006a3abea31631a86b1320ce317b5bc5` (`master`)
Branch: `codex/p8-hotfix-rolling-contract-tests`
Date: 2026-07-28

## Purpose

Restore clean-checkout CI after a normal daily production update changed
rolling Standard statistics and matchup windows.

## Root cause

Two migration tests were intended to prove that hierarchy and subtype additions
preserved parent behavior:

- `test_standard_hierarchical_migration_preserves_every_legacy_parent_cell`;
- `test_committed_parent_outputs_remain_phase6_compatible`.

Instead, both read current rolling production outputs and compared them with
counts or hashes captured during an earlier phase. Production commit
`400a2c76006a3abea31631a86b1320ce317b5bc5` changed those outputs normally, so
both tests failed even though the compatibility behavior was unchanged. The
same failures reproduce on pure master and are not caused by P8-05.

Refreshing the counts and hashes would only postpone the next failure and would
not strengthen regression protection.

## Focused correction

The hotfix keeps the intended behavior checks but moves them onto immutable
synthetic inputs:

- Standard name-keyed matchup aliases must equal the stable-ID parent overall
  and matrix rollups exactly;
- subtype-aware aggregation must preserve every parent statistical field from
  the parent-only aggregation of the same records;
- attaching subtype construction details must not modify the parent's
  archetype ID, best deck, or average deck;
- existing synthetic sibling-rollup, current-output conservation, and
  byte-identical committed-output tests remain in place.

No production code, fixture hash, generated statistic, public JSON, workflow,
classification rule, or statistical formula changes.

## Validation

- target matchup and subtype-statistics files: 40 passed;
- complete clean-checkout-equivalent pytest suite: 516 passed;
- Git whitespace validation: passed.

The owner authorized this independent hotfix and authorized resuming P8-05
publication. The hotfix was published through implementation commit `53ec3db1`,
PR #115, and merge commit `bc08063a4fd1e1cbc4bfb2160e895a880a8fcfb1`;
the remote check passed before merge.
