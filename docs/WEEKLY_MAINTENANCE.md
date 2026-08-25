# Weekly MTGO maintenance

## Purpose and trigger

This runbook fixes the recurring handoff between production data, Codex-assisted
review, Owner decisions, and the Landing editorial process. It does not depend
on Codex scheduled tasks. The staged migration and implementation stop points
are authoritative in `docs/LANDING_EDITORIAL_PIPELINE.md`.

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
4. stops without changing classifier rules, review metadata, Landing editorial
   approval, Landing content, or repository files.

The readiness artifact is retained for 21 days and is not included in the
Pages artifact. Repeated runs with the same readiness digest do not add Issue
noise. A changed weekly baseline updates and reopens the same Issue.

## End-to-end operating contract

| Step | Who | Work | Output for the next step |
| --- | --- | --- | --- |
| 1. Collect and publish production data | Automatic GitHub workflow | Fetch the allowlisted MTGO inputs, validate one candidate, publish the verified generated data when changed, and keep production failures fail-closed. | Exact publication SHA, run evidence, current Standard and Modern outputs. |
| 2. Build weekly readiness | Automatic GitHub workflow | Bind the current review week to Top 8 event IDs and classifier digests, require each Landing editorial candidate source to carry the same classifier and screening-policy digests, and reuse the authoritative Landing Top 8 subject to report the exact machine-fact digest later used by Landing admission plus the complete-link-catalog binding. Never substitute a Top 8 summary digest for the Landing machine-fact digest. The primary Unknown count and complete decklists are the exact intersection with the review week's source event IDs. Preserve every retained-corpus unresolved and intentional Unknown in a separately labelled queue, including an explicit outside-review-week subset that cannot change the weekly count or readiness status. Separately list classification blockers, editorial candidate counts, stale candidates, unavailable review inputs, and the non-blocking status of optional machine prose. | Private Schema-valid readiness JSON plus one deduplicated weekly Issue. |
| 3. Start the review | Owner | Read the Issue and explicitly ask Codex to begin with the named week and readiness artifact. Closing or ignoring the Issue means no review starts. | Authorization for one exact weekly review baseline. |
| 4. Freeze and verify the baseline | Codex | Confirm the cloud workflow run, publication SHA, week lifecycle, event IDs, classifier digests, and readiness digest. Stop on drift or missing evidence. | Frozen review manifest and plain-language scope summary. |
| 5. Review Unknown decks | Codex and Owner alternate; Owner confirms | Review every unresolved Unknown whose event belongs to the frozen review week unless it was already reclassified or explicitly accepted as intentional Unknown. Keep older and future-week unresolved records visible in the separate retained-corpus queue for their own explicitly started review; they do not silently expand the current weekly task. Handle coherent clusters in chat with complete representative decklists; use XLSX only for singleton batch review. Codex supplies a preliminary technical proposal, reads unrestricted Owner feedback, then supplies an exact revised proposal. | One final Owner confirmation per review-week unresolved deck or group. Only an incoherent random card pile may be explicitly accepted as intentional Unknown. |
| 6. Repair and reproduce classification when needed | Codex implements after separate authorization; Owner accepts | Make only accepted classifier changes. When a parent/subtype identity is added or renamed, include its format-scoped English/Chinese name maintenance in the same review and require Owner confirmation of the Chinese name; always run bilingual-name coverage before accepting the refreshed baseline. Then rerun the affected classification and derived weekly outputs and re-freeze the changed baseline. Skip rule edits when no rule change is accepted, but never skip the coverage check. | Accepted classifier subject, complete bilingual identity coverage, and refreshed weekly evidence, or an explicit no-rule-change record with passing coverage. |
| 7. Audit every Top 8 classification | Codex prepares; Owner checks | Export every current-week Top 8 deck in event-date and rank order with its final classification. This temporary human audit remains required until the Owner explicitly retires it. | Owner-checked weekly classification baseline. |
| 8. Review visual metadata | Codex proposes; Owner decides | Review representative-card choices and deck-color identities against the accepted deck identities. Missing deterministic diagnostics are reported as unavailable, never guessed. | Owner-approved metadata changes or an explicit no-change/defer record. |
| 9. Screen Landing features | Automatic Landing editorial producer | Run `landing-review prepare --if-absent`, apply the five reviewed routes to exact Top 8 results, and keep the complete ordered Top 8 pool. Merge reason tags only when they select the same exact deck. There is no machine primary pick. | Private Landing candidates, structured evidence, and complete Top 8 link catalog. |
| 10. Prepare the Landing workbook | Codex | Create the five-sheet Landing carrier defined below. Preserve prior Owner content, expose exact deck tokens in the copy sheet, and, before presenting the workbook, add every exact deck already referenced by retained or draft top copy to `Featured Decks` as a mandatory `KEEP` row. Merge these rows with ordinary machine candidates by exact deck ID. Derive bilingual deck titles from the classifier-name catalog and derive feature order from category plus final top-copy token order; omit both as Owner input fields. | Editable Landing review carrier bound to the frozen baseline, with no top-copy-only deck and no manual feature-title/order work. |
| 11. Complete Chinese review | Owner submits once; Codex validates | Select any number of other candidates, add any other exact Top 8 deck, merge or split presentation items, change category/cards/positioning, delete or completely rewrite machine copy, write unrelated content, or select none only when the final top copy contains no deck token. Every exact deck added to kept top copy must also be added to `Featured Decks`; it cannot be dropped while that token remains. The Owner's one chat submission closes the Chinese authoring stage; no duplicate approval cell is required. Codex hashes the submitted workbook and runs `landing-review validate-xlsx --stage chinese --expected-sha256`. | Machine-valid Chinese final content and a feature selection containing every top-copy deck. |
| 12. Draft and review English | Codex drafts; Owner accepts once | Codex translates the Owner-final Chinese content without changing it. The Owner edits the English or accepts the supplied draft once in chat; no duplicate workbook approval state is required. Codex then hashes that workbook and runs the bilingual validation stage. | Machine-valid bilingual Landing review state. |
| 13. Build and validate the preview | Codex | After separately authorized import, bind the exact bilingual-accepted workbook hash with `landing-review import-xlsx --expected-sha256`; import repeats the complete bilingual validation before any private review file is written. Validate week, source events, classifier and policy digests, the exact Landing machine-fact digest shared with readiness and generation, deck tokens, rank, bilingual-name coverage, derived order, and featured cards. Build the current and feature-history documents from that same private review source, then render the accepted UI. | Exact local Landing preview or a fail-closed review blocker. |
| 14. Accept and publish Landing | Owner accepts; Codex completes | After hands-on acceptance, complete the unchanged task through commit, one Ready PR, required checks, merge, and Pages publication. Publish the latest Landing and selected feature-history week together; there is no intermediate public Pickup publication. | Accepted public Landing and immutable publication subject. |
| 15. Verify cloud | Codex | Verify current copy, historical feature selection, both formats and languages, exact deck links, card display, legacy Pickup redirects, and absence of live Pickup data requests. | Completed weekly-maintenance evidence. |

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

### Landing feature screening

The machine candidate list starts from exact ranks 1 through 8 in every admitted
event. It does not use a rank-beyond-8 fallback and does not deduplicate the
complete review pool. `Unknown` records remain visible in the complete Top 8
evidence but cannot become automatic Landing candidates until classification is
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
- Classifier changes, visual metadata changes, Landing review import, preview,
  commit, push, pull request, merge, and deployment remain governed task and
  acceptance gates. There is no standalone Pickup publication gate after the
  P12-15F cutover.
- A provisional week may gain late events through its seal date. If its
  readiness digest changes, the same Issue is updated and the frozen review
  baseline must be refreshed before downstream work continues.
- Standard and Modern share the same review week but retain separate source
  event IDs, classifier digests, classifications, and Landing candidates.
- The review-week Unknown count is restricted to those source event IDs. The
  complete retained-corpus Unknown queue remains available as separate evidence;
  records outside the review week do not block or enlarge the current review.
- Event age, singleton status, or low sample size never removes a coherent deck
  from the unresolved queue and is never by itself a reason to retain Unknown.
- An Unknown disappears from the unresolved queue only after a classifier result
  is regenerated or after the Owner explicitly accepts that exact deck as an
  incoherent `random_card_pile`. The latter decision is recorded in
  `configs/mtgo_intentional_unknowns.yaml` with immutable evidence.

## Review carriers

Unknown, visual-metadata, and Landing review are separate jobs. Do not rebuild
one seven-sheet workbook that forces the Owner to navigate unrelated stages.
Coherent Unknown clusters are reviewed in chat with complete representative
decklists. Only singleton Unknown batch review uses an XLSX. The temporary
complete Top 8 classification audit uses its own XLSX.

After those upstream stages are accepted, Codex supplies one Landing-only
five-sheet carrier:

1. `Review Control` - frozen baseline, calculated completeness counts, and
   read-only instructions for the chat-gated Chinese and English stages; it has
   no duplicate Owner approval dropdowns;
2. `Landing Copy` - unrestricted ordered final copy, Codex English draft,
   Owner English final, and an in-sheet reference block containing each
   selected deck's format, event, date, rank, archetype, player, and
   `deck:<20-hex deck ID>` token;
3. `Featured Decks` - filtered candidates with complete decklists and machine
   reasons plus simple selection, category, positioning, and four-card Owner
   fields; bilingual deck names and localization status are read-only, and
   feature order is derived rather than entered;
4. `All Top 8` - every exact event rank 1 through 8 for unrestricted manual
   additions; and
5. `Field Guide` - only fields the Owner must enter or review.

Machine-bound cells are blue, Codex recommendations are green, and Owner input
cells are yellow with validation lists where categorical. Machine-bound fields
must not be edited, but they constrain only provenance and numeric source facts;
they do not limit, endorse, or police the Owner's editorial conclusions. The
workbook is a review carrier, not an authoritative database. Codex validates and
writes accepted decisions into the private Landing review source before any
preview or publication.

The importer never reads workbook cells as untyped positional values. It
resolves raw OOXML shared strings, inline strings, cached formulas, numbers,
booleans, and true blanks before mapping named headers. This prevents an empty
Owner cell from inheriting an unrelated shared-string index or number. The
accepted workbook SHA-256, complete Top 8 catalog, classifier/policy/fact
digests, and bilingual catalog digest are stored together in the private week
document; any later mismatch requires explicit re-review.

Owner intent is recorded once per authored stage. Saving and submitting the
Chinese workbook in chat is the Chinese-stage decision; editing or accepting
the later English draft once in chat is the bilingual-stage decision. The
workbook stores the actual decisions, while `Review Control` only explains the
scope and reports machine completeness. `landing-review validate-xlsx` is
read-only and supports `chinese` and `bilingual`; only the separately authorized
`import-xlsx` command may write private Landing review state.

For Landing final copy, the Owner writes unrestricted Chinese text and may
write or later review English text. Codex supplies an English draft only after
the Chinese final is complete. The final localized text places an exact
`deck:<20-hex deck ID>` token wherever a reviewed Top 8 deck link should appear.
Both localized texts must reference the same token set, but their prose and
token positions may differ. Codex derives the link order from each text,
validates every token against the current-week Top 8 catalog, and generates the
localized `<archetype> · <player> · <rank>` display automatically.
The token is the later UI replacement anchor; only its generated display becomes
the hyperlink, never the entire summary row. There is no separate `Landing
Links` sheet. Columns that do not support Owner input or review are omitted.

Top-copy membership implies feature membership. Before each weekly workbook is
shown to the Owner, Codex parses every exact deck token in the retained and
machine-draft top copy and unions those exact decks into `Featured Decks` as
`KEEP`, even when the ordinary five-route screen did not select them. If the
Owner later adds a token, the matching feature row must be added in the same
workbook lineage. Removing that feature is valid only after the token is removed
or replaced in every kept localized top-copy row. Category, positioning, and
four cards remain editable Owner decisions. Feature title comes from the
format-scoped bilingual classifier-name catalog. Feature order is derived per
format by placing `new_deck` before `new_technology`, then following exact deck
tokens in kept top copy (row order, then left to right); features absent from
top copy are appended to their category deterministically. Mandatory
membership does not invent editorial positioning.

Classifier-name maintenance is part of weekly classifier maintenance, not a
later editorial repair. The catalog key is `(format, parent_id,
subtype_id-or-none)`. A new or renamed classifier identity must carry its
classifier-owned English name and an Owner-confirmed Chinese name in the same
accepted change. A coverage failure blocks the refreshed weekly baseline and
therefore blocks Landing workbook preparation; it is never silently repaired
by asking the Owner to type a weekly feature title.

The Owner is never asked to invent or type classifier action codes, parent IDs,
parent names, or subtype IDs. The first Owner field is unrestricted free text.
After reading it, Codex owns the exact technical recommendation. The only
categorical Owner field is the second-round final response:
`确认按 Codex 修订建议实施`, `需要再次修订`, or `暂缓`. `map_existing` and
other implementation terms may appear in Codex-owned columns but are not Owner
input vocabulary.

## Readiness meanings

`awaiting_owner_start` means the production and classification gates passed
and both format-scoped Landing candidate sources exist. It does not mean the
manual work is complete.

`blocked` means the weekly handoff found a classification failure, a missing
Landing candidate, or a Landing candidate whose event/lifecycle/classifier
or screening-policy provenance is stale, or a Landing machine-fact binding that
does not match the exact format, week, events, or classifier. An unreviewed stale candidate is regenerated automatically.
A stale candidate containing human approval or copy is preserved, marked
`stale_review_required`, and must be regenerated and reviewed again instead of
being silently overwritten or published. The blocker is resolved before the
Owner starts the normal review sequence.

Representative-card and deck-color exception counts remain manual review
inputs. After P12-10 acceptance, the automatic producer reports deterministic
Landing machine facts and machine-fact bindings; optional draft prose remains
an explicitly requested aid, not a required output or editorial constraint.
`landing.status=ready_for_human_review` therefore means both format bindings
are current and the screening inputs are reviewable. `optional_draft_status`
remains `not_requested` unless a separately requested aid is introduced; it
never blocks readiness. Human-final progress and authorization remain in
`docs/STATUS.yaml`, not in the production handoff.

## Recovery

- Production failure: use the existing stage-specific production failure
  Issue. No readiness artifact is treated as current.
- Readiness generation failure: use the deduplicated readiness-failure Issue
  and inspect the linked run. Do not infer readiness from partial output.
- Late event or changed classifier digest: regenerate unreviewed Landing
  candidates. Preserve reviewed stale candidates as evidence, block readiness
  and publication, then use the updated artifact and reopen review from baseline
  freezing; do not silently reuse prior decisions.
- Missed nominal start time: wait for the bounded delayed run or manually
  dispatch the production workflow under separate production authorization.
  Codex scheduling is not a fallback.
