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
| 2. Build weekly readiness | Automatic GitHub workflow | Bind the current review week to Top 8 event IDs and classifier digests, and require each Pickup candidate file to carry the same classifier digest. Include every unresolved Unknown from the complete retained diagnostic corpus plus complete main decks and sideboards. Separately list Owner-accepted intentional Unknown records, classification blockers, Pickup candidate counts, stale candidates, and unavailable review inputs. | Private Schema-valid readiness JSON plus one deduplicated weekly Issue. |
| 3. Start the review | Owner | Read the Issue and explicitly ask Codex to begin with the named week and readiness artifact. Closing or ignoring the Issue means no review starts. | Authorization for one exact weekly review baseline. |
| 4. Freeze and verify the baseline | Codex | Confirm the cloud workflow run, publication SHA, week lifecycle, event IDs, classifier digests, and readiness digest. Create the seven-sheet XLSX review carrier defined below from that exact baseline. Stop on drift or missing evidence. | Frozen review manifest, plain-language scope summary, and editable XLSX. |
| 5. Review Unknown decks | Codex and Owner alternate; Owner confirms | Put every unresolved historical and current Unknown in `Unknown Review`, one row per deck, with its complete main deck and sideboard. Codex supplies a preliminary technical proposal. The Owner writes only free-text classification understanding, naming preference, or questions; no action code, parent ID, parent name, or subtype is required. Codex then supplies an exact revised proposal, and the Owner finally confirms, requests another revision, or defers it. | One final Owner confirmation per unresolved deck or group. Only an incoherent random card pile may be explicitly accepted as intentional Unknown. |
| 6. Repair and reproduce classification when needed | Codex implements after separate authorization; Owner accepts | Make only accepted classifier changes, rerun the affected classification and derived weekly outputs, and re-freeze the changed baseline. Skip this step when no rule change is accepted. | Accepted classifier subject and refreshed weekly evidence, or an explicit no-change record. |
| 7. Review visual metadata | Codex proposes; Owner decides | Review representative-card choices and deck-color identities against the accepted deck identities. Missing deterministic diagnostics are reported as unavailable, never guessed. | Owner-approved metadata changes or an explicit no-change/defer record. |
| 8. Review Weekly Pickup | Codex prepares; Owner selects and writes | Export the filtered candidates and complete ordered Top 8 pool to XLSX. Each candidate carries structured reasons plus exact event, rank, deck and classifier provenance. There is no machine primary pick. The Owner may select any number, replace a representative, add any other exact Top 8 deck, change category/order/cards/copy, or select none. | Human-approved Pickup selection and unrestricted editorial inputs bound to the reviewed week and classifier subject. |
| 9. Publish and verify Weekly Pickup | Codex implements after the applicable Owner approval | Run `pickup publish` once for Standard and once for Modern. Each command writes the accepted rows and Chinese copy to the format-scoped Pickup week document and index, and automatically refreshes format metadata and the global catalog. Publish them through the normal reviewed PR and Pages path, then verify both the JSON and the existing Pickup page in the cloud. Landing work must not start from a private candidate file or an unpublished workbook. | Verified cloud Pickup week documents, catalog availability, Pages commit, and reader-visible Pickup pages for Standard and Modern. |
| 10. Prepare Landing summary review | Automatic producer or Codex | Read the approved Pickup week from its published format-scoped week document, then combine that reviewed input with every eligible share movement, return, exit, and construction-shift fact in the private Landing review source and XLSX. Do not infer post-ban continuation or impose a presentation count. | Complete Landing draft evidence that identifies the exact published Pickup input and machine-fact digest. |
| 11. Create and explicitly review the human final Landing content | Owner, with optional Codex assistance | Accept, merge, edit, delete, replace, or ignore any machine output; write unrelated content; and choose zero or more final rows. Link each row to zero, one, or multiple fact IDs when useful. Explicitly mark the review complete even when zero rows are chosen. | Ordered human-final rows and explicit reviewed state. |
| 12. Preview, accept, and publish Landing | Codex implements and validates; Owner separately authorizes each gate | Render the exact final Landing subject, perform proportionate checks, obtain Owner acceptance, then separately commit, open a Ready PR, merge, and deploy only when each gate is authorized. | Accepted public Landing and publication evidence, or a stopped unpublished review. |

Classifier recommendations in step 5 follow two additional controls. Codex first
tests whether an existing rule can be modified across the complete retained
same-format corpus; it adds a parent or alternative rule only when the identity
does not exist or one existing rule cannot represent both the retained and new
construction. Card-count thresholds start with the least restrictive viable
value, normally testing two and three before four. A recommendation may require
four only when the lower value causes a demonstrated identity migration,
conflict, or identity loss, and the workbook records that evidence. If final
implementation exposes an impact not disclosed in the reviewed workbook, the
changed subject returns to Owner confirmation before commit or publication.

### Weekly Pickup screening

The machine candidate list starts from exact ranks 1 through 8 in every admitted
event. It does not use a rank-beyond-8 fallback and does not deduplicate the
complete review pool. `Unknown` records remain visible in the complete Top 8
evidence but cannot become automatic Pickup candidates until classification is
resolved.

Candidate generation applies these five reviewed routes:

1. Ban-aftermath continuation is Owner-only. The machine makes no ban-policy
   inference. The Owner may select any exact Top 8 row from `All Top 8`, including
   multiple decks from one archetype or date.
2. A known parent is eligible for share increase when current-week high-score
   share exceeds the aggregated raw-count share from the four preceding complete
   weeks by at least five percentage points. A return requires no high-score
   record in that reference, prior historical presence, at least 3% current
   share, and one current Top 8. One representative is chosen by better rank,
   larger event, then later result date and time.
3. A release-set card is eligible only in the release week containing the
   official `MTG Arena Release Date` and the immediately following week. The
   maintained manifest contains new-to-Magic names only, excluding reprints,
   basic lands and alternate treatments. One main- or sideboard copy is enough.
   Candidates group by parent and exact new-card package. Within one package,
   representative order is rank, event size and later result; new-card counts
   and copy quantities remain evidence only and never outrank tournament result.
4. A new archetype is a new strategic parent identity, not merely a new display
   name, stable ID, color correction or classifier migration. Explicit identity
   continuity prevents old strategies from reappearing as new. One current Top
   8 is sufficient; representative order is rank, event size and later result.
5. A construction shift compares the exact current Top 8 main deck with the
   preceding four-week mean for its maintained subtype, or with its parent when
   that parent defines no subtypes. The reference requires eight decks and the
   existing weighted-L1 score must be at least 20. The highest score represents
   one identity; rank, event size and later result break ties. Sideboards remain
   editorial evidence and do not trigger the route.

If one exact event deck satisfies multiple routes, its reasons merge into one
row. Different event decks selected for different routes remain separate even
when they share one parent, except that the new-card route first reduces one
parent and exact new-card package to its tournament-result representative.
Machine fields are evidence, not editorial limits:
the Owner may delete, rewrite or replace every conclusion and every copy field.

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
visual-metadata, Pickup, or Landing decision. Pickup screening extends the R1
carrier to this seven-sheet layout:

1. `Run Control` - frozen cloud bindings, counts, stage state, and stop reason;
2. `Unknown Review` - one row per unresolved deck, complete main deck and
   sideboard, Codex preliminary proposal, free-text Owner opinion, Codex revised
   exact proposal, and a simple Owner final-confirmation field;
3. `Visual Metadata` - changed or missing representative-card and color items;
4. `Pickup Review` - filtered candidates, complete decklists, structured machine
   reasons, a simple `select` or `skip` review result, and unrestricted Owner
   content fields;
5. `All Top 8` - every event rank 1 through 8 in event-date and rank order, with
   exact deck and classification evidence; this is not an automatic candidate
   list and exists for Owner-only additions such as ban aftermath;
6. `Landing Copy` - optional machine draft plus unrestricted human-final fields;
7. `Field Guide` - field ownership, purpose, allowed values, and write target.

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

`blocked` means the weekly handoff found a classification failure, a missing
Pickup candidate, or a Pickup candidate whose event/lifecycle/classifier
provenance is stale. An unreviewed stale candidate is regenerated automatically.
A stale candidate containing human approval or copy is preserved, marked
`stale_review_required`, and must be regenerated and reviewed again instead of
being silently overwritten or published. The blocker is resolved before the
Owner starts the normal review sequence.

Representative-card and deck-color exception counts remain manual review
inputs. After P12-10 acceptance, the automatic producer reports deterministic
Landing machine facts and machine-fact bindings; optional draft prose remains
an explicitly requested aid, not a required output or editorial constraint.

## Recovery

- Production failure: use the existing stage-specific production failure
  Issue. No readiness artifact is treated as current.
- Readiness generation failure: use the deduplicated readiness-failure Issue
  and inspect the linked run. Do not infer readiness from partial output.
- Late event or changed classifier digest: regenerate unreviewed Pickup
  candidates. Preserve reviewed stale candidates as evidence, block readiness
  and publication, then use the updated artifact and reopen review from baseline
  freezing; do not silently reuse prior decisions.
- Missed nominal start time: wait for the bounded delayed run or manually
  dispatch the production workflow under separate production authorization.
  Codex scheduling is not a fallback.
