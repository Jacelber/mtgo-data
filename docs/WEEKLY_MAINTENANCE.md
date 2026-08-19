# Weekly MTGO maintenance

## Purpose and trigger

This runbook fixes the recurring handoff between production data, Codex-assisted
review, Owner decisions, and the later Landing editorial process. It does not
depend on Codex scheduled tasks.

The GitHub `MTGO production data update` workflow is the only timer. It is
scheduled every day at `09:00 UTC`, which is `18:00 Japan Standard Time`.
GitHub-hosted schedules are best-effort and may start later than the nominal
time. The workflow remains daily so a delayed official event or a failed run can
refresh the same weekly handoff on the next successful run.

After a successful production run, the workflow:

1. checks out the exact verified production publication, or the unchanged
   source commit when generation was correctly skipped;
2. builds one private `weekly-maintenance-readiness-<week>` Actions artifact;
3. creates or updates one GitHub Issue identified by the review week; and
4. stops without changing classifier rules, review metadata, Pickup approval,
   Landing content, or repository files.

The readiness artifact is retained for 21 days and is not included in the
Pages artifact. Repeated runs with the same readiness digest do not add Issue
noise. A changed weekly baseline updates and reopens the same Issue.

## End-to-end operating contract

| Step | Who | Work | Output for the next step |
| --- | --- | --- | --- |
| 1. Collect and publish production data | Automatic GitHub workflow | Fetch the allowlisted MTGO inputs, validate one candidate, publish the verified generated data when changed, and keep production failures fail-closed. | Exact publication SHA, run evidence, current Standard and Modern outputs. |
| 2. Build weekly readiness | Automatic GitHub workflow | Bind the current review week to Top 8 event IDs and classifier digests, and include every unresolved Unknown from the complete retained diagnostic corpus plus complete main decks and sideboards. Separately list Owner-accepted intentional Unknown records, classification blockers, Pickup candidate counts, and unavailable review inputs. | Private Schema-valid readiness JSON plus one deduplicated weekly Issue. |
| 3. Start the review | Owner | Read the Issue and explicitly ask Codex to begin with the named week and readiness artifact. Closing or ignoring the Issue means no review starts. | Authorization for one exact weekly review baseline. |
| 4. Freeze and verify the baseline | Codex | Confirm the cloud workflow run, publication SHA, week lifecycle, event IDs, classifier digests, and readiness digest. Create the six-sheet XLSX review carrier defined below from that exact baseline. Stop on drift or missing evidence. | Frozen review manifest, plain-language scope summary, and editable XLSX. |
| 5. Review Unknown decks | Codex and Owner alternate; Owner confirms | Put every unresolved historical and current Unknown in `Unknown Review`, one row per deck, with its complete main deck and sideboard. Codex supplies a preliminary technical proposal. The Owner writes only free-text classification understanding, naming preference, or questions; no action code, parent ID, parent name, or subtype is required. Codex then supplies an exact revised proposal, and the Owner finally confirms, requests another revision, or defers it. | One final Owner confirmation per unresolved deck or group. Only an incoherent random card pile may be explicitly accepted as intentional Unknown. |
| 6. Repair and reproduce classification when needed | Codex implements after separate authorization; Owner accepts | Make only accepted classifier changes, rerun the affected classification and derived weekly outputs, and re-freeze the changed baseline. Skip this step when no rule change is accepted. | Accepted classifier subject and refreshed weekly evidence, or an explicit no-change record. |
| 7. Review visual metadata | Codex proposes; Owner decides | Review representative-card choices and deck-color identities against the accepted deck identities. Missing deterministic diagnostics are reported as unavailable, never guessed. | Owner-approved metadata changes or an explicit no-change/defer record. |
| 8. Review Weekly Pickup | Codex prepares; Owner selects and writes | Present the generated candidates and exact deck evidence. The Owner may select any number, change category/order/cards/copy, add a different item, or select none. | Human-approved Pickup selection and editorial inputs bound to the reviewed week. |
| 9. Prepare optional Landing draft | Automatic producer or Codex, only after P12-10 is separately authorized | Generate structured facts and, if requested, an optional editorial draft from the accepted weekly inputs. The absence of a machine draft is valid. | Optional machine facts/draft presented as suggestions, never editorial authority. |
| 10. Create the human final Landing content | Owner, with optional Codex assistance | Accept, edit, delete, replace, or ignore any machine output. The Owner may write unrelated content or publish no editorial copy. | Human-final content and explicit approval state. |
| 11. Preview, accept, and publish | Codex implements and validates; Owner separately authorizes each gate | Render the exact final subject, perform proportionate checks, obtain Owner acceptance, then separately commit, open a Ready PR, merge, and deploy only when each gate is authorized. | Accepted public Landing and publication evidence, or a stopped unpublished review. |

## Authority boundaries

- Machine output is a draft or evidence aid. It never limits the Owner's final
  editorial conclusions.
- A readiness Issue is a notification, not authorization for repository or
  production mutation.
- Classifier changes, visual metadata changes, Pickup publication, Landing
  implementation, commit, push, pull request, merge, and deployment remain
  separately authorized gates.
- A provisional week may gain late events through its seal date. If its
  readiness digest changes, the same Issue is updated and the frozen review
  baseline must be refreshed before downstream work continues.
- Standard and Modern share the same review week but retain separate source
  event IDs, classifier digests, classifications, and Pickup candidates.
- Event age, singleton status, or low sample size never removes a coherent deck
  from the unresolved queue and is never by itself a reason to retain Unknown.
- An Unknown disappears from the unresolved queue only after a classifier result
  is regenerated or after the Owner explicitly accepts that exact deck as an
  incoherent `random_card_pile`. The latter decision is recorded in
  `configs/mtgo_intentional_unknowns.yaml` with immutable evidence.

## XLSX review carrier

Codex must supply the workbook before requesting any weekly classification,
visual-metadata, Pickup, or Landing decision. It contains the R1 six-sheet
layout:

1. `Run Control` - frozen cloud bindings, counts, stage state, and stop reason;
2. `Unknown Review` - one row per unresolved deck, complete main deck and
   sideboard, Codex preliminary proposal, free-text Owner opinion, Codex revised
   exact proposal, and a simple Owner final-confirmation field;
3. `Visual Metadata` - changed or missing representative-card and color items;
4. `Pickup Review` - generated candidates and editable Owner selection fields;
5. `Landing Copy` - optional machine draft plus unrestricted human-final fields;
6. `Field Guide` - field ownership, purpose, allowed values, and write target.

Machine-bound cells are blue, Codex recommendations are green, and Owner input
cells are yellow with validation lists where categorical. Machine-bound fields
must not be edited, but they constrain only provenance and numeric source facts;
they do not limit, endorse, or police the Owner's editorial conclusions. The
workbook is a review carrier, not an authoritative database. Codex validates and
writes accepted decisions back to the maintained repository sources.

The Owner is never asked to invent or type classifier action codes, parent IDs,
parent names, or subtype IDs. The first Owner field is unrestricted free text.
After reading it, Codex owns the exact technical recommendation. The only
categorical Owner field is the second-round final response:
`确认按 Codex 修订建议实施`, `需要再次修订`, or `暂缓`. `map_existing` and
other implementation terms may appear in Codex-owned columns but are not Owner
input vocabulary.

## Readiness meanings

`awaiting_owner_start` means the production and classification gates passed
and both format-scoped Pickup candidate files exist. It does not mean the
manual work is complete.

`blocked` means the weekly handoff found a classification failure or a missing
Pickup candidate. The blocker is resolved before the Owner starts the normal
review sequence.

Representative-card and deck-color exception counts are currently
`not available`; their manual-review status is intentional. Landing draft
status is also `not available` until P12-10 is separately designed,
implemented, and accepted.

## Recovery

- Production failure: use the existing stage-specific production failure
  Issue. No readiness artifact is treated as current.
- Readiness generation failure: use the deduplicated readiness-failure Issue
  and inspect the linked run. Do not infer readiness from partial output.
- Late event or changed classifier digest: use the updated artifact and reopen
  review from baseline freezing; do not silently reuse prior decisions.
- Missed nominal start time: wait for the bounded delayed run or manually
  dispatch the production workflow under separate production authorization.
  Codex scheduling is not a fallback.
