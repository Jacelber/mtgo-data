# WEEKLY-MAINTENANCE-CONTRACT-R1

Status: `owner_accepted_publication_authorized`

Date: 2026-08-13 (Japan time)

Artifact impact: `internal_diagnostics`

## 1. Objective

Define one Tuesday operating contract for the four recurring owner activities:

1. review new `Unknown` results and decide whether classifier maintenance is
   required;
2. maintain mana identities and environment representative cards;
3. review Weekly Pickup candidates and publish only selected items; and
4. write and approve the Landing headline and environment summary after the
   Landing product exists.

The contract separates deterministic code execution, Codex preparation and
implementation, and Owner decisions. Codex initiates the weekly exchange after
Tuesday's production run reaches a terminal state; the Owner does not need to
remember to start it. It does not implement P12-10, change a classifier,
publish Pickup, dispatch production, or authorize a repository write.

## 2. Existing boundaries that this contract preserves

- The daily MTGO production workflow runs at 20:00 UTC, or 05:00 Japan time.
- Scheduled automation generates Pickup candidates but never approves or
  publishes them and never advances known-archetype state.
- Classification reports are generated artifacts. They are never edited by a
  reviewer to suppress an `Unknown`, conflict, or invalid result.
- `Unknown` is visible and non-blocking by itself. Conflicts, invalid decks,
  residual subtype violations, or a reviewer decision that classifier rules
  must change stop downstream editorial preparation until the classifier and
  affected outputs are regenerated.
- Pickup remains format-scoped. Its existing candidate YAML is the future
  Landing feature-review boundary; no second root-level approval system is
  introduced.
- Mana identities and representative cards are manual product metadata keyed
  by stable identity. Code must not infer a replacement.
- A missing representative card or failed image request degrades to readable
  text; it does not invent a card and does not block statistical publication.
- An empty approved Pickup selection and a future Landing `no_events` state are
  valid outcomes.
- Pending candidates, reviewer notes, and working spreadsheets never enter the
  Pages artifact.

## 3. Accepted R1 operating decisions

The repository's week lifecycle does not currently make the immediately prior
Monday-to-Sunday week immutable on the following Monday. It remains
`provisional` for seven additional days and seals on the next Monday.

The Owner accepted the following policy on 2026-08-13:

- cadence machine value: `provisional_with_re_review`;
- Tuesday reviews the latest complete week for timeliness, even while it is
  provisional.
- Every review is bound to exact `source_event_ids`, the classifier digest, and
  the relevant machine-fact or metadata digest.
- Immediately before publication, code must verify those bindings again.
- If a late event changes a binding, only affected human decisions return to
  `needs_re_review`; the last admitted public Landing remains online.
- The week becomes immutable on its recorded `seal_on` date.
- Owner approval is required for both Chinese and English editorial fields;
  Codex may draft either language but cannot approve it.
- Standard and Modern may proceed independently when the other format is
  blocked, unless the blocker affects shared classifier or publication
  integrity.
- Zero Pickup selections and zero Landing observations are valid and must not
  be padded.
- Representative card 2 is initialized once before P12-10; later Tuesdays are
  exception-only for both card slots.

The `sealed-only` alternative was considered and not selected; it remains a
documented fallback if the Owner later prefers a fixed one-week delay over the
late-event re-review path.

## 4. Proactive trigger and conversation handshake

The weekly lane begins with Codex, not with an Owner command.

1. A Codex heartbeat runs each Tuesday at 09:00 Japan time and checks the exact
   scheduled production run that began at 05:00 Japan time. It is read-only:
   it may inspect GitHub, committed artifacts, and deployment evidence, but it
   may not dispatch, rerun, cancel, edit, commit, publish, or merge anything.
2. If the production run has not reached a terminal state, Codex waits or
   rechecks within the same monitoring run. It sends no normal maintenance
   request while the evidence is incomplete.
3. On success, Codex sends one entry report keyed by the production run and
   review week. On failure, it sends a failure entry report and stops before
   editorial review.
4. The successful entry report includes the review week and lifecycle state,
   production run and `master` SHA, source-event counts, strict diagnostic
   counts, five separate Unknown measures, visual-metadata exception count,
   Pickup candidate/shortlist counts, Landing readiness, and blockers. It ends
   in state `awaiting_owner_start`.
5. The Owner may begin at any convenient time by replying in the same task.
   Silence is neither approval nor rejection, has no deadline, and causes no
   repository or production change.
6. When the Owner begins, Codex performs a freshness check against the entry
   report bindings. If the production run, `master` SHA, source-event IDs, or a
   relevant digest changed, Codex first sends a delta report and replaces only
   the affected review inputs. Human review starts only from fresh bindings.

The local Codex heartbeat implementing this trigger is active under automation
ID `mtgo`. Its prompt records the same read-only and stop boundaries above.

The five Unknown measures are deliberately distinct:

- `unknown_total_all_available`: every Unknown in the current all-available
  diagnostic corpus;
- `unknown_in_review_week`: Unknown records whose source event belongs to the
  reviewed week;
- `unknown_new_since_last_review`: stable deck IDs newly Unknown since the
  previous accepted review;
- `unknown_still_open`: previously reviewed Unknown records that remain open;
- `unknown_resolved_since_last_review`: previously reviewed Unknown records
  that are no longer Unknown.

Until a weekly delta generator exists, unavailable delta measures must be
reported as `not_available`, never conflated with zero.

## 5. Tuesday schedule in Japan time

The times below are service targets, not workflow cron changes.

| Time | Stage | Exit condition |
| --- | --- | --- |
| 05:00-08:30 | Daily production completes | Successful run, exact `master` SHA, current source-event lists, generated reports and Pickup candidates available |
| 09:00 or production terminal | A. Proactive entry report | Codex sends one success/failure report; a successful report enters `awaiting_owner_start` |
| Owner's convenient time | B. Freshness check and manifest freeze | Current bindings match the entry report, or Codex first sends a delta report |
| After Owner starts | C. Classification health | Strict reports pass; every new/current `Unknown` has an Owner disposition; any requested rule change becomes a separate classifier task |
| After C | D. Visual metadata exceptions | Only new, threshold-entering, missing, stale or manually flagged identities are reviewed; unchanged mappings are not re-entered |
| After D | E. Pickup review | Owner selects zero or more exact candidates and supplies required localized copy/cards |
| After E | F. Landing editorial review | After P12-10 exists, machine facts are frozen and Owner supplies headline/summary without changing numeric facts |
| After review | G. Validation and acceptance | Machine validation passes, Codex presents diff/rendered result, Owner accepts and separately authorizes publication |
| After acceptance | H. Publication | Ready PR, required CI, merge, Pages deployment and live verification; no next task starts automatically |

If a stage is blocked, later stages may be prepared only when their inputs are
unchanged by the blocker. They must not be published out of order.

## 6. Responsibility and handoff matrix

### A. Detect production completion and send the entry report

**Code execution**

- expose the scheduled run identity, terminal status, head SHA and stage result;
- expose current generated diagnostics and candidate artifacts without changing
  them; and
- make repeated reads idempotent for the same production run and review week.

**Codex**

- inspect remote authoritative state after the run reaches a terminal state;
- send exactly one normal entry report per production run and review week;
- clearly distinguish zero from `not_available`; and
- stop in `awaiting_owner_start` until the Owner replies.

**Owner**

- has no action required to trigger the report; and
- begins review later in the same task when convenient.

**Handoff**: one proactive entry report with a stable review ID and an explicit
`awaiting_owner_start` state.

### B. Freshness check and freeze review manifest

**Code execution**

- identify the latest complete week for Standard and Modern;
- read `week_status`, `provisional_through`, `seal_on` and sorted
  `source_event_ids`;
- record the production workflow run, current `master` SHA, classifier digest,
  Pickup candidate digest, known-state digest and current visual-metadata
  digest; and
- fail if formats disagree on the intended review week without an explicit
  per-format exception.

**Codex**

- verify the manifest against remote `master`, not an older local checkout;
- compare it with the proactive entry report and send a delta report before any
  Owner decision if a binding changed;
- summarize missing or stale inputs in plain language; and
- create the review workbook from machine artifacts without copying private or
  unnecessary player information into editorial fields.

**Owner**

- confirm the review week and cadence policy; and
- decide whether a format with incomplete inputs is skipped or blocks the
  entire weekly release.

**Handoff**: one immutable review manifest plus an editable workbook whose
machine-bound fields are locked conceptually and never treated as human facts.

### C. Unknown and classifier review

**Code execution**

- generate strict conflict, invalid-input, residual-subtype and `Unknown`
  reports for both formats;
- compare stable deck IDs with the previous accepted weekly review to label
  records `new`, `still_unknown`, or `resolved`; and
- include enough de-identified main-deck evidence for review.

**Codex**

- group related `Unknown` records without inventing a classifier result;
- check current rules and identify whether an existing rule should have
  matched;
- propose one of `keep_unknown`, `map_existing`, `modify_rule`, `new_rule`, or
  `defer`; and
- if code changes are indicated, stop the weekly lane and propose a separate
  classifier task with affected formats and regression scope.

**Owner**

- select the disposition and target stable identity when applicable; and
- explicitly accept intentional `Unknown` records or authorize a separate
  classifier task.

**Handoff**: Owner decisions keyed by `format + deck_id`. Human decisions never
edit generated reports directly.

**Blocking rule**: an `Unknown` alone is non-blocking. A conflict, invalid deck,
residual subtype violation, or `modify_rule`/`new_rule` decision blocks all
statistics-dependent downstream approval until regeneration.

### D. Mana identity and representative-card review

**Code execution**

- derive the complete identity set rendered in current 1-, 4- and 12-week
  products;
- identify mappings that are missing, newly visible, no longer referenced, or
  manually flagged;
- for every environment parent at or above 3% in any reviewed range, validate
  that configured card 1 occurs in a related current deck;
- after Landing is authorized, perform the same check for card 2; and
- resolve image assets and emit diagnostics rather than substituting cards.

**Codex**

- present only exceptions, not all maintained mappings every week;
- suggest mana or card changes with exact related-deck evidence;
- apply only Owner-approved changes to the single maintained metadata source;
  and
- verify the existing chart continues to consume card 1 while Landing may
  later consume cards 1 and 2.

**Owner**

- choose `keep`, `update`, or `defer` for each exception;
- provide explicit mana colors and card names for updates; and
- review the complete second-card initialization once before P12-10, after
  which weekly work is exception-only.

**Handoff**: decisions keyed by `format + identity_key`. Blank proposed values
mean no change, not deletion. Deletion requires an explicit separately reviewed
action.

### E. Weekly Pickup review

**Code execution**

- generate the existing format-scoped `candidates_<week>.yaml` and
  `base_reference_<week>.yaml`;
- preserve any candidate with manual decisions;
- flag `needs_re_review` when late source events change the bound event list;
- rank existing-deck candidates by deviation and new-deck candidates by finish;
  and
- publish only exact entries whose Owner decision is approved and whose source
  binding still matches.

**Codex**

- summarize candidates without changing their order or statistical values;
- compare questionable deviation against the generated base reference;
- recommend a short list, but leave category, copy, cards and final selection
  to the Owner;
- write accepted decisions back into the existing candidate boundary; and
- validate the resulting public Pickup and future Landing feature document.

**Owner**

- choose `publish`, `skip`, or `defer` for each candidate;
- for current standalone Pickup, approve the exact deck and localized comment;
- for Landing, classify approved items as `new_deck` or `new_technology`, write
  localized headline and positioning copy, and select exactly four display
  cards; and
- accept an empty feature list when nothing merits publication.

**Handoff**: the workbook is a review view. The authoritative write target is
the existing format-scoped Pickup candidate YAML, extended by P12-10 rather
than replaced by a parallel CSV state store.

### F. Landing headline and environment summary

This stage is inactive until P12-10 produces a Schema-valid machine-facts
candidate.

**Code execution**

- generate up to five structured eligible observations and the environment
  table from the current week, previous week and aggregated prior four weeks;
- bind every fact to source events, classifier digest and machine-fact digest;
- expose the fixed 3%, five-percentage-point and 20-point thresholds; and
- reject editorial text that references an identity or observation absent from
  the bound candidate.

**Codex**

- translate the machine facts into a concise editorial briefing without adding
  unsupported claims or claiming statistical significance;
- check Chinese and English fields for factual equivalence;
- insert only Owner-approved copy; and
- render both languages for Owner acceptance.

**Owner**

- select the lead observation;
- write or approve `headline_zh`, `headline_en`, `summary_zh` and `summary_en`;
- approve zero to five observations without forcing filler; and
- decide to retain the last admitted Landing when current editorial review is
  incomplete.

**Handoff**: localized editorial fields bound to exact machine facts. Numeric
values and identities are not manually typed into prose without a fact
reference.

## 7. Weekly state machine

```text
production_terminal
  -> entry_report_sent
  -> awaiting_owner_start
  -> freshness_rechecked
  -> machine_prepared
  -> codex_reviewed
  -> owner_reviewed
  -> validation_passed
  -> owner_accepted
  -> publication_authorized
  -> published
```

Exceptional transitions:

- any binding change before publication -> `needs_re_review`;
- production failure -> `blocked_production` and a failure entry report;
- classifier change requested -> `blocked_classifier_task`;
- malformed or inconsistent candidate -> `blocked_validation`;
- no Owner selection -> `valid_empty` for Pickup features;
- Landing copy incomplete -> `retain_last_admitted`;
- publication or Pages failure -> `published_not_verified` until recovered;
- a provisional publication remains eligible for re-review until `seal_on`.

No state authorizes the next state implicitly. In particular, Owner review does
not authorize repository publication, and merge does not authorize a manual
production dispatch.

## 8. Workbook contract

The R1 workbook contains five editable review sheets and one read-only guide:

1. `Run Control` - proactive trigger, waiting/freshness state, review binding,
   cadence, five distinct Unknown measures, stage states and stop reason;
2. `Unknown Review` - one row per new/current `Unknown` exception;
3. `Visual Metadata` - one row per changed or missing mana/card mapping;
4. `Pickup Review` - one row per machine candidate, referencing rather than
   copying full decklists;
5. `Landing Copy` - one row per format and week, inactive before P12-10; and
6. `Field Guide` - allowed values, ownership, purpose and write target.

Blue cells are machine-provided and must not be edited. Pale yellow cells are
Owner inputs. Codex may prepare recommendations in pale green cells but cannot
promote them to Owner decisions. Categorical Owner cells use validation lists.

The workbook is a review artifact, not a second database. P12-10 must define a
deterministic importer or an explicit Codex-mediated write-back with validation
to the existing repository sources before this workbook can drive production.

## 9. Blocking and degradation table

| Condition | Statistics/Pickup | New Landing admission | Existing public Landing |
| --- | --- | --- | --- |
| Production workflow failed or source manifest missing | block | block | retain |
| Conflict, invalid deck or residual subtype violation | block | block | retain |
| Intentional reviewed `Unknown` | continue with explicit Unknown | continue | unchanged |
| Owner requests classifier change | pause until regenerated | block | retain |
| Source IDs/digest changed after review | affected item re-review | block | retain |
| No Pickup item approved | valid empty | valid empty feature list | replace only after full candidate approval |
| Representative card missing | readable text-only degradation | readable text-only degradation | unchanged |
| Card image request failed | stable placeholder | stable placeholder | unchanged |
| Landing copy incomplete | unaffected | block | retain |
| PR/CI/Pages failure | no claim of publication | no claim of publication | retain previous verified deployment |

## 10. Current W32 dry-run snapshot

This design was checked against committed `master` at
`d5aba55dc62f1d2ed68d7584aa33524be7803e35`:

- both formats target `2026-W32`, currently provisional and sealing on
  2026-08-17;
- Standard binds 8 source events, has 42 existing Pickup candidates, zero new
  candidates, zero approvals, 8 non-blocking Unknown records in the
  all-available-events report, and zero Unknown records dated inside W32;
- Modern binds 11 source events, has 79 existing Pickup candidates, zero new
  candidates, zero approvals, and zero Unknown records; and
- the candidate volume demonstrates why weekly human review must begin from a
  Codex shortlist while preserving the complete machine candidate file.

The three since-last-review Unknown measures are `not_available` because the
weekly delta generator does not exist yet. This is evidence for the interface
design, not authorization to approve or publish W32.

## 11. P12-10 readiness checklist

P12-10 remains blocked until all items below are separately completed and
accepted:

- [x] accept provisional-with-re-review cadence;
- [x] validate Standard and Modern Pickup known state against the accepted R5
      migration and final parent identities;
- [x] accept the already-computed refreshed 8-12-week Landing shadow evidence
      without recalculating it in the readiness-contract task;
- [x] reconfirm the 3%, five-percentage-point and 20-point thresholds;
- [x] initialize and approve representative card 2 for every required identity;
- [x] define the Pickup candidate extensions for Landing editorial fields and
      four feature cards;
- [x] define and validate the review manifest and workbook write-back path;
- [ ] perform one no-publication Tuesday rehearsal; and
- [ ] obtain separate P12-10 implementation authorization.

## 12. Owner decisions recorded for R1 acceptance

1. Cadence: `provisional_with_re_review` accepted.
2. Language responsibility: Owner approval is required for Chinese and English;
   Codex may draft both.
3. Format independence: Standard and Modern may proceed independently unless a
   shared-integrity blocker applies.
4. Empty week: zero Pickup items and zero Landing observations are valid.
5. Card maintenance: card 2 receives one complete initialization before
   P12-10, then exception-only maintenance.
6. Trigger: Codex proactively sends the entry report after Tuesday production
   reaches a terminal state; the Owner begins later when convenient.

The Owner accepted this design and separately authorized its commit, Ready pull
request, complete CI, and merge on 2026-08-13. Production mutation, P12-10, and
every later task remain separately unauthorized.
