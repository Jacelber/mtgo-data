# MTGO production timeout and repeated-failure repair

Date: 2026-08-15  
Task: `OPS-MTGO-PRODUCTION-TIMEOUT-FAILFAST-20260815`  
Base: `b01ec998f4d9f36728589d26871cb38de4f6f015`  
Artifact impact: `internal_diagnostics` with mandatory complete validation

## Incident evidence

Scheduled production run `31838657545` was not cancelled by concurrency or an
Owner action. Its `Fetch MTGO candidate data` job reached its 45-minute hard
timeout:

- the clean-checkout suite passed all 966 tests in 28 minutes 51 seconds;
- the Standard official-event collection then spent about 15 minutes 43
  seconds exhausting five attempts against both 2026-08 and 2026-07 MTGO
  monthly listing URLs;
- the job was cancelled immediately after Legacy collection began;
- cancellation prevented the resumable-checkpoint packaging steps from
  running, and build and publish were skipped.

The preceding successful scheduled run `31742869239` shows that ordinary live
collection itself took about two minutes after its clean baseline. The defect
is therefore shared timeout budgeting plus repeated work after an already known
upstream failure, not a need to remove validation.

## Focused repair

The complete clean-checkout pytest suite moves to a read-only `baseline` job.
The read-only `fetch` job depends on that success, snapshots the same immutable
trigger commit, and receives its own 45-minute timeout budget. No test is
removed, skipped, marked non-blocking, or repeated inside the same production
run.

After the first official event-format collection failure, fetch stops the
remaining official event-format loop because every remaining format uses the
same MTGO monthly-listing service. Independent Videre match operations still
run. The job then fails normally and uploads its verified seven-day checkpoint,
instead of waiting until GitHub cancels the job before recovery steps can run.

Build and publication remain blocked unless both baseline and fetch succeed.
Only publish retains repository write permission. The notification job now
identifies baseline and fetch failures from their separate job results.

## Scope boundary

This local repair changes workflow orchestration and its structural regression
contract only. It does not fetch live data, dispatch production, change source
selection, alter statistical meaning, modify generated data, publish a branch,
or satisfy the no-publication Tuesday rehearsal. Commit, Ready publication,
merge, production dispatch, and the later rehearsal remain separate gates.
