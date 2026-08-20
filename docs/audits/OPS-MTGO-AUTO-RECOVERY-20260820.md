# MTGO automatic recovery repair

Date: 2026-08-20
Task: `OPS-MTGO-AUTO-RECOVERY-20260820`
Base: `e5ce16edc5e0122efe22a3987e7fc17254aeb833`
Artifact impact: `internal_diagnostics`
Validation categories: `targeted:code+docs+governance` plus the focused
MTGO recovery regression

## Incident evidence

Scheduled production run `32354507054` failed during Pioneer event collection
at
`https://www.mtgo.com/decklist/pioneer-challenge-32-2026-07-2312849498`.
The same event URL was reported failed twice after HTTP 200 content lacked the
expected embedded decklist marker. A read-only request later on 2026-08-20
returned the marker, confirming that no repository or source-data change was
required for recovery.

This is the third recent scheduled interruption requiring a later run or human
attention. Runs `32127810627` and `32328276312` failed after exhausting five
requests to MTGO monthly listing pages. Their later manual reruns succeeded.
The latest failure is therefore the same operational class—temporary MTGO
source unavailability—even though its exact response symptom differs from the
two listing timeouts.

The August monthly listing also exposed the July Pioneer event link. The fetcher
then requested the same failed July event again while processing the July
listing. Cross-month spillover unnecessarily duplicated failure work before the
workflow could recover.

## Focused repair

The fetcher distinguishes temporary download or pre-JSON page-framing failures
from permanent event-contract, completeness, storage, and local I/O failures.
The CLI emits a dedicated exit code only when all observed failures are in the
temporary class.

The existing read-only fetch job handles that exit code with three bounded
rounds and cooldowns of 120 and 300 seconds. Every round reuses the same working
tree, so already fetched files remain available; the existing operation is
marked complete only after success. Permanent failures stop immediately. Final
exhaustion still fails the job, uploads the verified same-commit checkpoint,
blocks build and publish, and leaves failure reporting intact.

Listing observations are filtered to the requested month. An exhausted monthly
listing failure stops older-month scanning and returns control to the outer
recovery promptly.

## Scope and state restoration

The repair changes only workflow orchestration, MTGO source-error
classification, structural regression tests, and their decision/audit records.
It does not fetch live production data, regenerate artifacts, dispatch
production, publish a branch, change source selection or statistical meaning,
or alter protected event `434455` bytes.

The preemption does not replace the live weekly task. `docs/STATUS.yaml` remains
byte-identical to the base snapshot, so completion of this local repair restores
the repository's declared current-task state without carrying an emergency
task transition into the handoff.
