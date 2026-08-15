# P12-10 readiness - Pickup contract and known-state validation

Date: 2026-08-15

Base: `9ec4047762263e690b7163e4859efa21749b5019` (`master` after PR 208)

Branch: `codex/p12-10-readiness-pickup-contract`

Artifact impact: `internal_diagnostics`

## Purpose and authorization boundary

This task records the Owner-approved refreshed Landing thresholds, validates
the existing Standard and Modern Weekly Pickup known state, and freezes the
internal candidate, review-manifest, and workbook write-back contract required
before P12-10. It does not implement the Landing producer, create
`landing/current.json`, alter Pickup state or candidates, run the Landing
shadow, perform the no-publication Tuesday rehearsal, or change production.

Local implementation alone is authorized. Commit, remote publication, merge,
the rehearsal, P12-10 implementation, and production dispatch remain separate
Owner gates.

## Owner-approved refreshed threshold evidence

The Owner supplied and accepted the already-computed refreshed shadow summary
below and explicitly prohibited recalculation. This task records the evidence
verbatim and does not execute a shadow generator.

| Decision | Refreshed evidence | Accepted value |
| --- | --- | ---: |
| Environment | Standard median 8 rows and 88.04% coverage; Modern median 11.5 rows and 66.99% coverage | 3% |
| Share movement | Standard 1-6 items per week; Modern at most 2 with 8 empty weeks | 5pp |
| Build shift | Standard 1 item in 12 weeks; Modern 2-7 per week, median 4.5; threshold 15 would yield 3-10 Modern items | 20 |

The machine-readable copy is
`docs/audits/p12-10-readiness/pickup_review_contract.json`, where
`recomputed_by_task` is fixed to `false`.

## Pickup known-state result

The read-only validator binds each current known-state document to its accepted
R5 digest and entry count, then checks that every entry still resolves to a
parent in the final production rule document. It writes nothing and stops on
any mismatch.

| Format | Representation | Entries | SHA-256 | Result |
| --- | --- | ---: | --- | --- |
| Standard | parent display name | 91 | `8ee830827a1d554dc19b6b7e979ded056d0fb414fbf447fbb44619e917a3d006` | matches R5; every entry resolves |
| Modern | stable parent ID | 126 | `c589e26718fbac12bc164dd04dfc6dcb68c4a901df59ea1bf13242493a711235` | matches R5; every entry resolves |

The later Spellementals boundary fix changes deck routing between two already
known Standard parents and does not require a known-state migration. A future
digest, count, or parent-resolution mismatch is a stop condition, never an
implicit rewrite.

## Candidate extension contract

P12-10 will extend the existing format-scoped candidate documents; it will not
create a parallel root candidate configuration. `existing_changes` maps to
`new_technology`, while `new_archetypes` maps to `new_deck`.

An approved Landing item must carry one nested `landing` object containing an
order, Chinese and English headline, Chinese and English positioning text, and
exactly four unique card names from the featured deck's main deck or sideboard.
Existing approval and reviewer-comment fields remain internal and are not
public Landing fields.

## Review manifest and workbook boundary

The immutable review manifest binds the review ID and week to the exact master
commit, production workflow run, sorted source event IDs, classifier digest,
Pickup candidate digest, known-state digest, visual-metadata digest,
machine-fact digest, and workbook baseline digest. A binding change requires a
new review; it cannot be accepted through spreadsheet write-back.

The workbook is a repository-external review artifact. Machine-bound identity,
source, and digest columns are read-only. Owner-editable columns are limited to
approval, internal comments, Landing order, localized headline and positioning
copy, and four card selections. Import rejects added, deleted, duplicated, or
rebound rows before writing and may update only the existing format-scoped
Pickup candidate document.

## Remaining gates

After this local result is accepted and, if separately authorized, published,
P12-10 still requires:

1. one separately authorized no-publication Tuesday rehearsal; and
2. separate P12-10 implementation authorization.

No rehearsal, P12-10 code, public Schema, public data, workflow, UI, source
fetch, or production dispatch is part of this task.

## Local validation

- six targeted pytest nodes passed once with a repository-external basetemp;
- Ruff passed for the validator and both changed test files;
- the first Ruff launcher could not create its stale venv Python process and
  the system Python did not contain Ruff, so neither attempt executed lint;
  the existing standalone `ruff.exe` performed the single successful check;
- no Landing shadow, full pytest suite, Playwright test, rehearsal, source
  fetch, production generator, or workflow was run.
