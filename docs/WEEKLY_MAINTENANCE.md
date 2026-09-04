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
2. builds one private `weekly-maintenance-readiness-<review-label>` Actions artifact;
3. creates or updates a GitHub Issue for each format/review week requiring work; and
4. stops without changing classifier rules, review metadata, Landing editorial
   approval, Landing content, or repository files.

The readiness artifact is retained for 21 days and is not included in the
Pages artifact. Repeated runs with the same readiness digest do not add Issue
noise. A changed diagnostic baseline updates the same Issue, but its open or
closed state follows the generated review lifecycle instead of being forced
open by every digest change.

## End-to-end operating contract

| Step | Who | Work | Output for the next step |
| --- | --- | --- | --- |
| 1. Collect and refresh approved public data | Automatic GitHub workflow | Fetch allowlisted MTGO inputs. New events remain retained/private-review inputs until explicit data acceptance. Regenerate public products only from the approved event set; validate and publish the entire candidate or nothing. | Successful collection evidence, unchanged or restated approved public products, and pending retained events. |
| 2. Build weekly readiness | Automatic GitHub workflow | Discover each format's oldest closed pending week independently of its public week. Export full official classifications and machine-priority records privately. Keep retained-corpus Unknown diagnostics separate from the weekly review population. Report data acceptance, exact publication, Landing preparation, and completion as distinct facts. An unexplained review/classification failure is reported for that format; it cannot authorize publication or stop the other format's valid business progress. | Private readiness 1.7 plus deduplicated format/week notices; legacy 1.6 remains readable. |
| 3. Establish the review-ready scope | Owner specifies; Codex verifies | The Owner names the week and any Melee events to include. A named Melee event must have complete retained source, a reproducible candidate, current classification, every available decklist needed for review, and no engineering blocker. Public visibility is not required. | One MTGO week plus optional, separately identified review-ready Melee events. |
| 4. Start and freeze one operational lane | Owner starts; Codex verifies | Codex binds the successful MTGO production subject and each named Melee review subject. Successfully collected MTGO events are treated as fixed weekly inputs. Missing expected events, impossible official coverage, or malformed production output is an engineering defect and pauses the lane; Weekly does not build a second production validator or source-mutation tracker. | One exact review subject or a separate engineering-repair interruption. |
| 5. Prepare both review layers | Codex | Produce a machine-priority packet from existing Unknown, conflict, multiple-match, overridden-match, subtype, deviation, and classifier-impact diagnostics. Also export every official MTGO classification for every weekly event, up to rank 32, and every available classification for each included Melee event. The full tables contain classification and exact locators, not all deck cards. | Machine-priority evidence plus complete MTGO and optional Melee classification tables. |
| 6. Complete the full classification review | Owner reviews; Codex investigates | The Owner scans every row, uses the priority packet to start with higher-risk records, and identifies any additional suspected error. Codex returns the complete main deck, sideboard, current rules, similar decks, and reasoning only for machine-selected or Owner-selected records. Standard and Modern progress independently; MTGO and Melee remain source-labelled. | Accepted identity, subtype, bilingual-name, and intentional-Unknown decisions for the complete weekly review scope. |
| 7. Implement and prove classifier impact | Codex | Implement only accepted classifier/name decisions. For each affected format, classify the same complete retained MTGO and Melee corpus once with the accepted rules and once with the candidate rules. Continue only when every requested target changed as accepted and every other change is explained; new Unknown, conflict, identity migration, classification loss, or subtype drift is returned for classifier-design review. | One accepted classifier subject with no unexplained retained-corpus impact, or a fail-closed Owner blocker. |
| 8. Accept and publish reviewed data | Owner accepts full classification; Codex continues | Record explicit data admission for that format and week, independently of Landing and completion. Restate all applicable public MTGO products from the same approved set, including accepted historical classifier corrections; Melee reproduction remains separate. Validate the complete candidate, then perform the authorized exact-subject publication and verification. No extra technical authorization is needed inside the accepted lane. Skip unchanged generation, not a newly advanced data scope. | First publication: approved Statistics, Matchup, Representative Decks, Top 8, Completeness, metadata/catalogs and public reports; Weekly completion remains unrecorded. |
| 9. Screen Landing and decide metadata deltas | Codex screens; Owner decides only if needed | Run Landing screening after classification is final. Only new, missing, changed, or genuinely judgment-dependent representative cards, colors, or other display metadata return to the Owner. If no such delta exists, skip this touchpoint. | Accepted bounded metadata delta or an explicit no-change result. |
| 10. Author and accept Landing | Owner authors/reviews; Codex validates | The Owner writes Chinese content. Codex validates it, drafts English, receives one English acceptance or correction, imports only the accepted workbook hash, generates the preview, and presents the final weekly content/data/normal-rendering result. Final preview is not a recurring UI redesign review. | Exact bilingual Landing content and final preview subject. |
| 11. Publish Landing and complete | Owner accepts; Codex completes | After final preview acceptance, preserve the exact subject through GOV-11 commit, one Ready PR, required CI, merge, applicable publication, and cloud verification. This is the second, content publication. Only after both publication results and all business steps are verified, record completion for the finished format. The other format and Melee remain independent. | Accepted Landing and actual format-specific Weekly completion, never inferred from the first data publication. |

Classifier recommendations in step 7 follow two additional controls. Codex first
tests whether an existing rule can be modified across the complete retained
same-format corpus; it adds a parent or alternative rule only when the identity
does not exist or one existing rule cannot represent both the retained and new
construction. Card-count thresholds start with the least restrictive viable
value, normally testing two and three before four. A recommendation may require
four only when the lower value causes a demonstrated identity migration,
conflict, or identity loss, and the workbook records that evidence. If final
implementation exposes an impact not disclosed in the reviewed workbook, the
changed subject returns to Owner confirmation before commit or publication.

Use the narrow retained-corpus comparison entry point after accepted rule edits:

```text
python -B tools/compare_classifier_impact.py --format <format> --accepted-rules <accepted.yaml> --candidate-rules <candidate.yaml> --expected-changes <accepted-changes.json>
```

The tool dynamically discovers the format's retained MTGO events and retained
Melee event decklists, builds one input subject, and runs both rule sets on that
same in-memory corpus. It reports every status, identity, subtype, selected-rule,
match, override, conflict, and invalid-deck change. `ACCEPTED_CHANGE_SET` is the
only changed-rule result that continues. `UNEXPLAINED_IMPACT` returns to
classifier design; `NO_RULE_CHANGE` skips unnecessary regeneration. The
expected-change file is task evidence, not a registry.

Build the classification-review source documents with:

```text
python -B tools/export_weekly_classification_review.py mtgo --week <week> --format <format> --output <review.json>
python -B tools/export_weekly_classification_review.py melee --format <format> --event-id <event> --output <review.json>
```

Codex renders these source documents as human XLSX carriers. To investigate one
MTGO row, use `mtgo-detail` with its event and rank. For one Melee row, use
`melee-detail` with its event and participant ID. Only those focused outputs
contain the complete main deck, sideboard, current classification, matched
rules, and exact locator.

After both format reviews and Landing subjects have been accepted, build the
minimal registry row without editing the registry through the tool:

```text
python -B tools/export_weekly_classification_review.py completion --week <week> --standard-review <standard-review.json> --modern-review <modern-review.json> --standard-landing-digest <digest> --modern-landing-digest <digest> --completed-on <date> --evidence <url> --output <completion-record.json>
```

Codex reviews that exact row before adding it to the existing completion
registry. The command does not publish, authorize, or write weekly state.

### Reviewed data publication operations

`configs/mtgo_weekly_review_completions.yaml` 1.2 has two separate sections:
`data_admissions` is public membership authority; `records` is maintenance
completion evidence. Neither implies the other. Initial explicit event IDs are
`grandfathered_existing_public_scope`, not historical full human review.
Standard and Modern advance independently through continuous accepted natural
weeks. An observed empty intervening week can be crossed; a later arrival with
an unlisted ID remains pending even when its date is before the public frontier.
An accepted later nonempty week waits behind an unreviewed nonempty week.

After the Owner accepts the exact full classification table, Codex uses:

```text
python -B -m mtgmeta.mtgo --format <format> publication inspect
python -B -m mtgmeta.mtgo --format <format> publication admission-record --week <week> --expected-review-digest <digest> --accepted-on <date> --evidence <acceptance-reference> --output <private-path>/admission.json
```

The second command prepares a row; it does not grant authority or edit the
registry. Codex places that exact accepted row under the format's
`weekly_acceptances`. An additional accepted late-event delta replaces that
week's row with its explicitly accepted complete set; no date rule admits it.
Existing intentional-Unknown and classifier-impact policies still apply.

With pinned Python/browser dependencies already installed, run the offline
format operation (no fetch, dependency installation, commit, or publication):

```text
python -B -m mtgmeta.mtgo --format <format> publication stage
python -B -m mtgmeta.mtgo --format <format> publication stage --execute
```

Default staging generates and checks a separate candidate without changing final
files. Execute additionally replaces only validated allowed products, using the
existing classifier-closure rollback implementation on failure/interruption.
It leaves accepted Landing untouched. After content acceptance, use the same
operation with `--include-landing`; stale/materially changed accepted content
returns to the Owner. Do not run both commands on the same unchanged subject
merely to duplicate evidence: choose plan-only for inspection or execute for an
authorized local materialization. Normal GOV-11 remote gates follow separately.

After the accepted format's data and Landing are actually published:

```text
python -B tools/export_weekly_classification_review.py format-completion --format <format> --week <week> --review <private-path>/review.json --landing-digest <digest> --completed-on <date> --evidence <publication-reference> --output <private-path>/completion.json
```

This verifies explicit classification acceptance and published data/Landing
before preparing the existing completion record. It never marks the other
format complete. Private review outputs, including full tables and pending
Landing preparation, must not enter Pages-admitted report/statistics paths.
Display metadata decisions occur after deterministic regeneration and screening
expose a real delta, not prematurely to force one decision batch.

### Cross-source same-format supplements

The weekly readiness JSON and completion registry remain MTGO-only. A Tabletop
supplement is immutable task-local evidence that the Owner may include in the
same-format weekly lane through the active conversation. It is never written to
`docs/STATUS.yaml` and never inserted into MTGO event IDs, Unknown counts,
readiness status, Landing candidates, or completion records.

The supplement contains only the target week, format, source, event ID, exact
review-ready candidate or classification subject and locator, classifier
subject and digest, available-classification count, unresolved Unknown count,
and separately excluded unavailable-decklist count. Review-ready means the
source is completely retained, the event/candidate is reproducible, current
classification and all available review decklists exist, and no engineering
defect blocks human review. Public or live status is not required. The evidence
contains no authorization, progress, or workflow state. Missing exact
provenance fails closed; inclusion remains an Owner decision in Chat.

For one review week:

1. freeze the exact MTGO readiness subject and every supplement explicitly
   included by the Owner;
2. keep Standard and Modern decisions independent, while reviewing MTGO and
   Tabletop cohorts for the same format in one classifier decision session;
3. record every Owner disposition with its source and event provenance;
4. if a shared rule change is accepted, validate one classifier subject against
   the complete retained same-format corpus and every reviewed cohort; and
5. review every available classification in both cohorts, not only Unknowns;
6. reproduce affected MTGO and Tabletop outputs only through their existing
   separate source paths after the shared decision is accepted. A retained
   Melee snapshot is reused without recollection.

An unavailable Melee decklist is reported separately and is never converted to
Unknown. If an Owner-named event is not yet review-ready, Weekly waits while the
Melee engineering or candidate task completes. Adding another event after
freeze is an explicit Owner scope change and cannot silently enlarge the lane.

### Fixed weekly input and production-defect firewall

Successfully fetched and validated MTGO event files are the fixed input for the
normal weekly lane. Weekly does not monitor for later official mutation, rebuild
historical fetch baselines, or compare successive readiness artifacts as a
source-mutation proxy.

If the Owner or Codex finds a missing expected event, obvious mismatch with the
known official publication range, duplicate/invalid rank, unreadable retained
input, or a production Schema/integrity failure that should already have been
rejected, freeze the weekly subject and stop. Record the exact problem, complete
a separately authorized production engineering repair, then restart or resume
the same weekly review from its fixed inputs. Do not absorb the repair into
Weekly or construct a second completeness framework.

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
- Future work may let collection and retention continue while admitting
  user-visible classification and classifier-derived products only after Owner
  review. This runbook records reusable event IDs, classifier subjects,
  completion evidence, and Melee review-ready evidence, but does not change the
  current MTGO or Melee publication boundary or create another publication
  registry.
- A readiness Issue is a notification, not authorization for repository or
  production mutation.
- One Owner instruction starts the exact weekly operational lane. Owner-
  accepted substantive classifier, name, metadata, Chinese/English editorial,
  and final-preview decisions remain required. Exact implementation,
  retained-source regeneration, closure, workbook import, generation,
  validation, publication, and verification then continue under that lane
  without repeated technical authorization, while GOV-11 acceptance and remote
  gates still bind the exact subject.
- A successful production subject is fixed input for the weekly review. Missing
  expected events or malformed production output pauses Weekly for a separate
  engineering repair; Weekly does not monitor unobservable upstream mutation.
- Standard and Modern share the same review week but retain separate source
  event IDs, classifier digests, classifications, and Landing candidates.
- MTGO and Tabletop may share one same-format human classifier decision session,
  but their source records, Unknown counts, readiness and completion states,
  generated outputs, and publication gates remain separate.
- A Tabletop supplement is evidence only until the Owner includes it in the
  weekly lane. Inclusion never authorizes recollection. Once the Owner accepts a
  shared classifier decision, deterministic retained-source regeneration and
  closure may continue through each source's existing path inside that lane.
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

The Owner always receives two classification layers. The machine-priority
packet contains existing Unknown, conflict, multiple-match, overridden-match,
subtype, deviation, classifier-impact, and other maintained diagnostics. It is
an ordering aid and never asserts that unlisted classifications are correct.
The complete Chinese MTGO table covers every weekly event and every officially
published record, capped at rank 32. Each event is presented separately with
date, player count, available high-score count, rank, player, Chinese parent and
subtype, exact source locator, and classifier provenance. It does not embed all
main decks or sideboards. When Melee is included, a separate full table covers
every available decklist classification and lists unavailable decklists
separately.

Complete cards and rule reasoning are supplied only for a record selected by
the machine packet or named by the Owner from a full table. After the Owner
finishes the full scan, Codex merges and deduplicates both discovery sources
before proposing classifier changes. Permanent tests use synthetic events and
counts; a real weekly workbook is operational evidence, never a repository
oracle.

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
read-only and supports `chinese` and `bilingual`. After bilingual acceptance,
`import-xlsx` may write private Landing review state only from that exact
accepted hash as deterministic continuation of the same lane.

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

`completed` means the week has an Owner-accepted completion record in
`configs/mtgo_weekly_review_completions.yaml`. Legacy records retain their
Top-8-only meaning. A Weekly V2 record binds, for both Standard and Modern, the
Owner-reviewed event IDs, accepted classifier subject, digest of every official
classification through rank 32, and published Landing content. Melee remains
outside this MTGO registry. The Issue is closed.

`revalidation_required` means a recorded completion no longer matches its
declared legacy Top 8 subject or its Weekly V2 event/classifier/full-review
subject, or its published Landing content. It is a review-evidence mismatch,
not a general source-mutation detector.

Only new, missing, materially changed, or suspicious representative-card and
deck-color exceptions remain manual review inputs. After P12-10 acceptance, the
automatic producer reports deterministic Landing machine facts and machine-fact
bindings; optional draft prose remains an explicitly requested aid, not a
required output or editorial constraint.
`landing.status=ready_for_human_review` therefore means both format bindings
are current and the screening inputs are reviewable. `optional_draft_status`
remains `not_requested` unless a separately requested aid is introduced; it
never blocks readiness. Human-final progress and authorization live only in the
active Owner conversation, not in readiness, STATUS, or task-local evidence.

## Recovery

- Production failure: use the existing stage-specific production failure
  Issue. No readiness artifact is treated as current.
- Readiness generation failure: use the deduplicated readiness-failure Issue
  and inspect the linked run. Do not infer readiness from partial output.
- Production integrity defect found during Weekly: freeze the weekly subject,
  record the exact failure, complete a separate engineering repair task, then
  resume or restart Weekly from the repaired production subject. Do not add a
  second rank, duplicate, source-completeness, or Schema validator to Weekly.
- Missed nominal start time: wait for the bounded delayed run or manually
  dispatch the production workflow under separate production authorization.
  Codex scheduling is not a fallback.
