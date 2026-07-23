# Development Process Retrospective — 2026-07

## Purpose

This retrospective reviews recurring avoidable rework observed through Phase 6.
It converts historical incidents into mandatory controls in
`docs/DEVELOPMENT_WORKFLOW.md`. It does not change product scope, statistical
semantics, or the authorized next product task.

## Evidence reviewed

- Phase audit records from P3-06 through P6-05.
- Merged pull-request history through PR #85.
- GitHub Actions failures 29779522176 and 29795445118.
- The current repository workflow, status, tests, and line-ending state.
- Owner-reported repeated Windows checkout and publication authorization
  failures.

The review snapshot contained 85 merged pull requests. Thirty-one titles were
status, publication-record, reconciliation, or finalization changes. This count
is historical evidence, not a target metric.

## Repeated phenomena and controls

| Phenomenon | Evidence or example | Avoidable cost | Adopted control |
| --- | --- | --- | --- |
| Windows checkout converts LF before task work starts | P5-05 identified a byte-sensitive fixture converted by Windows checkout; P5-06 and P5-07 repeated LF/CRLF validation; a later disposable clone again appeared globally modified when `core.autocrlf=false` was set only after cloning | Abandoned workspaces, blob restoration, false diffs, repeated tests | Repository `.gitattributes`; set `core.autocrlf=false` in the clone command; fail closed on any non-clean initial status |
| Remote publication first fails, then changes mechanism | Repeated owner-observed Git `403` attempts; some changes to workflows additionally required the token `workflow` scope; isolated workspaces intentionally use a disabled push sentinel | Failed pushes, repeated authentication diagnosis, inconsistent publication paths | After explicit authorization, run a read-only auth, permission, scope, remote, branch, and base preflight; then use one push/PR path |
| A status-only pull request follows nearly every implementation pull request | 31 of 85 merged PR titles were status, publication, reconciliation, or finalization changes; P5-02 required both a publication record and a later finalization | Extra CI runs, extra merge metadata to record, recursive bookkeeping | GitHub is the publication source of truth; defer exact merge metadata to the next authorized change or phase closeout unless immediate closure is explicitly requested |
| Repository-wide old-state assertions survive a capability change | P6-05 updated Modern capability state but the full suite later found a Phase 3 closeout test that still required the old state | A full-suite failure and another full-suite run after otherwise complete implementation | Perform repository-wide impact discovery and create an invalidation map before editing |
| Deterministic tests depend on shallow Git history | P3-06 failed in CI because a live `git log` timestamp differed by checkout history depth | Local success followed by CI-only failure | Inject Git and clock results; derive volatile committed-baseline values from committed metadata |
| Full validation is repeated after inputs that cannot affect it | Focused suites were repeated around small edits; full suites and validators were sometimes rerun after documentation-only changes | Several minutes per run and unnecessary context use | Use focused, impacted, final-full, and docs-only validation layers with explicit invalidation rules |
| Fixture success is accepted before real-source compatibility is proven | P5-04 noted that fixture parsing did not prove the live source; P5-08 later expanded to the full DataTables path after comparison with the public reference implementation | Late integration redesign and repeated acceptance | Require a read-only live smoke test whenever acceptance claims real-source integration |
| Source statuses are modeled after statistics are already implemented | P5-08 initially retained `Disqualified` records without separating their statistical eligibility | Post-acceptance semantic correction | Enumerate statuses first; keep archival retention separate from win-rate and matchup eligibility; block unknowns |
| Incomplete external records are treated as fatal parser breaks | Actions run 29779522176 failed when one Legacy archive did not yet contain the decklist marker | One pending event aborted the multi-format production workflow | Classify incomplete records as deferred; reserve fatal failure for confirmed contract breaks; report both separately |
| Baseline regression tests run after production data changes | Actions run 29795445118 failed at `Run regression tests` after the production checkout had been mutated | False regression signal and manual rerun | Preserve three validation layers: committed baseline before fetch, candidate validation after generation, publication confirmation after push |
| Later-task work is pulled into the current task | P6-01 performed part of the framework conversion expected in P6-02 | Blurred review boundaries and uncertain completion criteria | Define task layers explicitly and compare final paths and behavior with the contract |
| Historical import contamination is assumed to be a live crawler defect | P6-04 found Premodern files under Modern; follow-up inspection showed the active Modern discovery path did not select Premodern | Risk of speculative crawler changes | Trace provenance first and enforce normalized format boundaries; change the crawler only when a current-path defect is reproduced |
| Intermittent browser-cache behavior is treated as a product bug | Some Scryfall hover images initially failed, while links were correct; the images later loaded without a code change | Unnecessary debugging and potential speculative patch | Reproduce, reload independently of cache, and inspect network behavior before editing |
| Broad file and log reads are repeated after output truncation | Large generated files and CI logs repeatedly exceeded useful output bounds during audits | Lost context and repeated tool calls | Search first, read bounded sections, request compact structured summaries, and expand only failed steps |
| Runtime readiness is discovered late | Some tasks only established or located a usable Python environment when validation began | Delayed feedback and environment-specific detours | Verify the declared task-local runtime and required commands during Gate 2 |

## Rules that should remain visible to every future task

1. A clean disposable workspace is an acceptance criterion, not a repair target.
2. Cross-layer state changes begin with impact discovery, not implementation.
3. Expensive validation is run according to invalidated inputs.
4. Live integration is not complete until the approved real source is sampled.
5. Source retention, statistical eligibility, and workflow fatality are separate
   decisions.
6. Publication authorization is preflighted read-only and exercised once.
7. GitHub records publication history; repository status records durable project
   state.
8. Narrow evidence retrieval is part of engineering quality because it prevents
   repeated diagnosis and mistaken conclusions.

## Follow-up measurement

At the next phase closeout, review whether:

- any disposable workspace was abandoned for line-ending noise;
- any first authorized push failed for a predictable permission or scope issue;
- any implementation task created an unrequested immediate status-only closure
  pull request;
- any final full-suite failure was caused by a consumer discoverable through the
  required impact search;
- any real-source integration required a semantic correction after acceptance;
- any broad tool output had to be repeated because it was truncated.

The desired result is zero recurrence. A recurrence should update the control,
not merely add another narrative incident.
