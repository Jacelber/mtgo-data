# Landing editorial pipeline

## Purpose

This document is the implementation route map for replacing the obsolete
standalone Weekly Pickup handoff with one Landing-owned editorial pipeline. It
defines the target responsibilities, data boundaries, ordered migration tasks,
review gates, stop points, rollback conditions, and the steady weekly run after
cutover.

The route is intentionally staged. No stage may use a later stage's authority,
and no old Pickup producer, public document, or reader path may be removed until
its replacement has been generated, reviewed, switched, and verified in the
cloud.

## Problem being corrected

The current Landing has three incompatible content paths:

1. machine screening and Landing feature review fields live in private Pickup
   candidate YAML;
2. Landing summary preparation requires a separately published Pickup week;
   and
3. current features read private candidate state while historical features
   expect a `features` collection in Pickup week documents that existing
   published documents do not contain.

The standalone Pickup page is no longer a reader-facing product, so retaining a
public Pickup publication solely as an intermediate Landing handoff adds a
second publication gate without providing a complete Landing feature archive.
This is a structural source-of-truth problem, not a missing-card rendering
fallback.

## Approved target state

Landing is the only reader-facing weekly editorial product. The useful parts of
the existing Pickup implementation are retained as Landing-owned internal
capabilities; the obsolete public product boundary is retired only after
migration.

| Current responsibility | Target treatment | Target owner |
| --- | --- | --- |
| Exact Top 8 screening through the five reviewed routes | Retain and rename as Landing editorial screening | Internal Landing producer |
| Candidate deduplication and merged reason tags | Retain unchanged unless separately reviewed | Internal Landing producer |
| Known-archetype continuity state | Retain, but update independently of whether any feature is selected | Internal Landing review state |
| Candidate provenance and complete decklists | Retain in the private Landing review source | Internal Landing review state |
| Human selection, category, localized positioning/copy, and four featured cards | Move into one Landing review contract | Owner through the XLSX carrier |
| Public `pickup/<week>.json` handoff | Stop producing after cutover | Replaced by Landing current and feature-history documents |
| Standalone Pickup page, renderer, navigation identity, and styles | Remove only after verified cutover and no-caller proof | Front-end cleanup task |
| Existing Pickup W27 and W33 documents | Freeze as migration and rollback inputs | Compatibility evidence |
| Legacy `product=weekly-pickup` URLs | Preserve as redirects to the requested Landing feature week | Compatibility layer |

Machine candidates and machine-written copy remain aids. The Owner may add any
exact Top 8 deck, merge items, change categories, remove or completely
rewrite every conclusion, or write unrelated content. A zero-feature result is
valid only when final top copy contains no deck token: every exact deck that
remains in top copy must also remain a selected feature. Provenance bindings
and this cross-sheet membership rule protect navigation integrity; neither
restricts editorial meaning.

## Target data flow

```text
verified production and classification
                 |
                 v
Landing editorial screening + complete Top 8 catalog
                 |
                 v
private Landing review source <-> XLSX review carrier
                 |
        explicit bilingual review
                 |
                 v
      local Landing preview
                 |
          Owner acceptance
                 |
        +--------+--------+
        |                 |
        v                 v
landing/current.json   landing/features/<week>.json
                          + features/index.json
        |                 |
        +--------+--------+
                 v
             Landing UI
```

The target repository boundaries are:

```text
# Private, excluded from Pages
stats/<format>/mtgo/landing/review/<week>.yaml
stats/<format>/mtgo/landing/review/known_archetypes.json

# Public
stats/<format>/mtgo/landing/current.json
stats/<format>/mtgo/landing/features/index.json
stats/<format>/mtgo/landing/features/<week>.json
```

The exact private review Schema is introduced in the backend task. It must bind
the review week, format, source event IDs, classifier digest, screening-policy
digest, machine-fact digest, complete Top 8 link catalog, selected features,
localized final text, and chat-gated reviewed state materialized only by the
authorized importer. That internal state is not a duplicate workbook approval
cell. Pages admission must use an allowlist; placing private review state
beneath `stats/` does not authorize its publication.

`landing/current.json` remains the only latest complete Landing document. The
feature archive is a bounded archive of the bottom new-deck and new-technology
section only. Selecting an archived feature week never changes the current
weekly brief, environment, composition, or construction facts and does not
create historical Landing browsing.

## Ordered migration program

### P12-15A - Route-map documentation

**Scope:** documentation only.

1. Record this target contract in the authoritative scope, architecture,
   roadmap, decision, status, and weekly-maintenance documents.
2. Mark the completed P12-15 metadata and legacy-URL work accurately.
3. Register every later task, prerequisite, output, stop point, and deletion
   condition.

**Output:** an accepted implementation route map.

**Stop point:** do not create the workbook, change code, change public data, or
change the page before Owner acceptance of this task.

### P12-15B - Landing review workbook

**Scope:** review artifact only; no page or public-data change.

1. Inspect the accepted prior workbook and preserve all Owner-authored content,
   including the corrected Modern order.
2. Create one five-sheet workbook: `Review Control`, `Landing Copy`, `Featured
   Decks`, `All Top 8`, and `Field Guide`.
3. Put each selected deck's format, event, date, rank, archetype, player, and
   `deck:<ID>` token directly in `Landing Copy` as a reference block.
4. Put exact deck identity, decklist, machine reasons, editable selection,
   category, positioning, English-review fields, and four card fields in
   `Featured Decks`. Show the derived English and Chinese deck names plus their
   localization status as read-only fields; do not ask for a weekly feature
   title or feature order.
5. Parse every exact token already present in retained or draft top copy and
   add the matching deck to `Featured Decks` as mandatory `KEEP` before the
   workbook reaches the Owner. Merge by exact deck ID; there is no
   top-copy-only role.
6. Include every exact current-week rank-one-through-eight deck in `All Top 8`
   for unrestricted additions.
7. Preload Standard W27, Standard W33, and Modern W33 recovery inputs without
   overwriting existing Owner content.

**Output:** a visually verified XLSX review carrier.

**Stop point:** wait for the Owner to complete missing Chinese content,
selection, category, and cards, then submit that authored workbook once in
chat. Do not require duplicate approval cells.

### P12-15C - Content completion and bilingual review

**Scope:** review state only; no page or public-data change.

1. Resolve XLSX shared-string references from raw OOXML before interpreting any
   editable cell. Normalize a referenced empty string to a true blank and fail
   closed when the workbook importer disagrees; the numeric index itself is
   never Owner content.
2. Validate workbook deck tokens, event and rank identities, and selected cards.
   The exact token set in kept top copy must be a subset of the exact `KEEP`
   feature token set. A missing or dropped matching row blocks completion.
3. Preserve the Owner's Chinese text exactly and add Codex English drafts.
4. Build the initial format-scoped bilingual classifier-name review keyed by
   `(format, parent_id, subtype_id-or-none)`. Preserve the classifier's English
   name, propose Chinese names, and obtain the Owner's final confirmation. The
   recovery workbook may show English as the Chinese fallback until this
   review is complete; the fallback is not an approved Chinese name.
5. Return the same workbook lineage for Owner correction or one final English
   acceptance in chat.
6. Validate Chinese and bilingual stages from actual content, exact tokens,
   cards, identities, and the submitted workbook hash. Do not use duplicate
   top-copy, feature, Chinese, or English approval cells as admission facts. An
   intentional zero-feature result is valid only when final top copy contains
   no deck token.

**Output:** complete bilingual Owner-reviewed content for the exact frozen
baseline.

**Stop point:** do not implement or publish the page from incomplete or stale
content.

### P12-15D - Internal Landing editorial backend

**Scope:** internal producer, state, importer, Schema, and focused tests; no
front-end switch.

1. Extract the useful candidate algorithms from `pickup.py` into a
   Landing-owned editorial module while keeping a temporary compatibility
   wrapper.
2. Introduce the private Landing review source and deterministic XLSX
   import/export boundary.
3. Move known-archetype continuity state into the Landing review boundary and
   update it after an accepted classified weekly baseline, even when no feature
   is selected.
4. Remove the Landing generator's dependency on a separately published Pickup
   week. Both top copy and current features must consume the same reviewed
   Landing source.
5. Retain one stable exact-deck destination identity for every selected feature
   so the reader can resolve feature membership without using localized display
   text.
6. Add one format-scoped bilingual classifier-name catalog keyed by stable
   parent/subtype identity. Derive the public feature title from this catalog;
   do not store or import a weekly free-text title.
7. Derive feature order per format: `new_deck` first, then `new_technology`;
   inside each category follow exact deck-token appearance in final top copy,
   reading multiple tokens in one row from left to right. Append features not
   mentioned in top copy to the end of their category using a deterministic
   source-order and exact-deck-ID tie-break. The producer may serialize this
   derived order, but the workbook never asks the Owner to enter it.
8. Add fail-closed validation for stale event IDs, classifier or policy
   digests, unknown deck tokens, missing bilingual name coverage, invalid card
   choices, and missing stage acceptance or content. Also fail closed when any
   kept localized top-copy
   token lacks an exact selected feature record; do not generate a
   top-copy-only destination for newly reviewed content.

**Output:** a complete internal Landing editorial pipeline that can generate
new files without changing the live reader path.

The implemented private boundary uses
`src/mtgmeta/mtgo/landing_editorial.py`,
`src/mtgmeta/mtgo/landing_screening.py`,
`configs/mtgo_archetype_names.yaml`, and
`stats/<format>/mtgo/landing/review/`. Candidate screening is exposed as
`landing-review prepare`; the standalone Pickup command and capability are
retired. Landing generation does not read a published Pickup week. Import is exposed as
`landing-review import-xlsx` and requires the exact accepted workbook SHA-256.
The P12-15C v6 recovery subject imports Standard W27/W33 and Modern W33, but no
public feature archive or reader switch is created in this task.

**Stop point:** keep the existing front end and public Pickup files unchanged.

### P12-15E - Public feature archive and recovery preview

**Scope:** new Landing public-data contract, historical migration, and local
preview; no production publication before Owner acceptance.

1. Add the Landing feature index and week-document Schemas, catalog references,
   production-candidate admission, and Pages allowlist.
2. Generate Standard W27, Standard W33, and Modern W33 feature documents from
   the reviewed recovery content.
3. Generate the latest complete Landing documents from the same reviewed
   source.
4. Switch a local preview to the Landing feature archive while preserving the
   accepted structure and every design element not explicitly amended by the
   route below.
5. Make every admitted inline Landing-copy deck token select its exact feature
   in the applicable format and week, expand the item, move it into view, and
   expose stable URL/focus state. Retain the exact Top 8 fallback only as a
   defensive compatibility route for legacy documents; a newly reviewed
   unmatched token is invalid and cannot be generated.
6. Verify Chinese and English, Standard and Modern, W27 and W33 selection,
   exact deck links, derived titles, derived category/link order, four-card
   display, desktop, mobile, and explicit empty weeks.

**Output:** one Owner-reviewable local page backed entirely by the new Landing
contracts.

**Stop point:** wait for hands-on Owner acceptance. Do not publish or remove old
Pickup resources.

The local implementation uses `destination_id: deck:<20-hex-id>` as the exact
feature destination. The Landing reader requests only
`landing/features/index.json` and its selected week document; it does not use a
Pickup week for current or historical features. A summary link writes
`section=features`, the selected `week`, and the exact `feature` destination to
the URL. Loading that URL selects the week, opens the matching feature, moves it
into view, and focuses its disclosure control. A legacy link without an admitted
destination may still use its exact Top 8 event/rank route, but newly generated
reviewed summary content cannot take that fallback.

Standard W27 is represented as an explicit zero-feature week rather than a
missing document, but zero-feature archive weeks are not offered in the public
week selector. An old direct URL for a zero-feature week falls back to the latest
selectable week and replaces the stale week parameter. Standard W33 and Modern
W33 carry the complete materialized reviewed feature sets. The current W33
feature collection is byte-equivalent at the structured-data level to the
corresponding archive collection because both are built in one generation
operation from the same private review source.

### P12-15E-I18N - Classifier-name localization across retained views

**Scope:** publish and consume the approved classifier-name translations across
retained views; do not change classifier rules, statistics, or accepted layout.

1. Begin only after hands-on acceptance of the P12-15E data-backed local
   preview.
2. Generate a format-scoped public bilingual name contract from
   `configs/mtgo_archetype_names.yaml` at
   `stats/<format>/archetype_names.json`, with the classifier taxonomy
   remaining the English authority and the approved catalog remaining the
   Chinese authority.
3. Audit every retained MTGO and applicable Tabletop consumer for stable parent
   and subtype IDs. Add missing stable identity fields at producer boundaries
   rather than matching localized or English display text.
4. Resolve classifier-backed labels by selected language in Landing,
   Statistics, Matchups, Top 8, and applicable Tabletop views. Keep Unknown and
   non-classifier interface vocabulary in the existing UI translation layer.
5. Fail closed when a known published classifier identity lacks approved
   Chinese coverage. Do not mutate the classifier taxonomy or duplicate weekly
   free-text names.
6. Verify Chinese and English independently across Standard, Modern, every
   retained view, direct URLs, language switching, desktop, and 390 pixels.

**Output:** one Owner-reviewable local release candidate in which every
classifier-backed parent and subtype label follows the selected language.

**Stop point:** wait for hands-on Owner acceptance. Do not publish independently
of the P12-15F combined cutover.

### P12-15E-UX - Feature-release interaction corrections

**Scope:** three bounded Owner-approved interaction corrections against the
accepted P12-15E and P12-15E-I18N local release candidate; no production
publication.

1. Make composition-segment activation on desktop and mobile move the newly
   expanded deck detail into a perceptible viewport position while preserving
   keyboard focus and reduced-motion behavior.
2. At mobile widths, move the accepted representative-card stack lower and
   remove the excessive whitespace below it without changing its 90 by 63 size,
   first-card overlap priority, or desktop placement.
3. Add one shared fixed bottom-right return-to-top control to the Landing, every
   retained MTGO view, and Tabletop. It must respect safe-area insets, avoid
   covering content at 390 pixels, expose localized accessible naming, work by
   keyboard, and disable smooth motion when requested.
4. Verify both languages, both MTGO formats, every retained top-level view,
   Tabletop, desktop, 390 pixels, browser history, focus restoration, and zero
   console errors.

**Output:** one hands-on Owner-reviewable interaction-corrected release
candidate that remains backed by the P12-15E Landing contracts.

**Stop point:** wait for hands-on Owner acceptance. Do not publish independently
of the P12-15F feature cutover.

### P12-15F - Cloud cutover

**Scope:** accepted data, reader path, cross-view classifier-name localization,
and P12-15E-UX interaction publication.

1. Begin only after hands-on acceptance of P12-15E, P12-15E-I18N, and
   P12-15E-UX.
2. Publish the reviewed latest Landing, feature archive, feature-aware inline
   links, public bilingual classifier-name contract, localized retained-view
   consumers, and accepted interaction corrections atomically through the
   normal Ready-PR and Pages path.
3. Change the feature selector to request only Landing feature-history paths.
4. Verify the merge-triggered Pages deployment, current content, W27 and W33
   history, both languages and formats, deck links, and legacy Pickup redirects.
5. Prove that no live Landing request depends on public Pickup week documents.

**Output:** a verified cloud Landing with current and historical feature
content.

**Stop point:** freeze the verified release and retain the legacy Pickup files
and compatibility wrapper for rollback until a separate cleanup is accepted.

### P12-15G - Pickup retirement cleanup

**Scope:** dead-code and obsolete-contract removal only after P12-15F evidence.

1. Prove there are no production, metadata, catalog, front-end, test, or Pages
   callers of the standalone Pickup product or publisher.
2. Remove the standalone renderer, navigation identity, unused styles, public
   publisher, obsolete public Schemas, and metadata capability.
3. Keep the legacy URL redirect. Delete or relocate frozen legacy documents only
   under a separately declared file-operation and rollback plan.
4. Update the final architecture and complete Phase 12 closeout prerequisites.

**Output:** no standalone Pickup product and no hidden public-public handoff;
only Landing-owned screening, review, current publication, and feature history
remain.

**Stop point:** proceed to P12-16 only after this cleanup or an explicit Owner
decision to defer a named compatibility artifact.

## Steady weekly operating contract after cutover

| Step | Who | Work | Output for the next step |
| --- | --- | --- | --- |
| 1. Production | Automatic workflow | Fetch allowlisted events, generate and validate statistics, Top 8, Unknown diagnostics, and machine editorial candidates. | Verified cloud baseline and readiness artifact. |
| 2. Establish and freeze the review-ready scope | Owner names scope; Codex verifies | Start the named week once in Chat and optionally include exact review-ready Melee events. Treat successful MTGO production as fixed input. A production integrity defect pauses Weekly for a separate repair. | Exact MTGO week and optional source-separated Melee review subjects. |
| 3. Complete classification review | Codex prepares; Owner reviews all rows | Present both machine-priority evidence and the complete Chinese classification tables: every official MTGO record through rank 32 and every available classification in included Melee events. Supply full cards and rule analysis only for flagged or Owner-selected rows. | Accepted identity, subtype, bilingual-name, and intentional-Unknown decisions. |
| 4. Prove and reproduce accepted changes | Codex | Implement accepted rules, compare accepted and candidate classifiers on the same complete retained format corpus, stop on unexplained impact, regenerate MTGO and Melee separately, run closure/name coverage, and rebuild the complete review tables. | Exact accepted classifier subject and source-separated current outputs. |
| 5. Screen Landing and decide metadata deltas | Codex screens; Owner decides if needed | Screen the final classified subject. Ask only about actual new, missing, changed, or judgment-dependent display metadata; skip the step when there is no delta. | Accepted bounded metadata result. |
| 6. Author and accept Landing | Owner authors/reviews; Codex validates/builds | The Owner writes Chinese content. Codex validates it, drafts English, receives one English acceptance or correction, imports only that accepted workbook hash, generates current and feature-history documents, and presents the final content/data/normal-rendering preview. | Exact accepted bilingual preview or a fail-closed blocker. |
| 7. Publish and verify | Owner accepts; Codex completes | Preserve the final accepted subject through GOV-11 commit, Ready PR, required checks, merge, applicable publication, exact cloud verification, and a Weekly V2 full-classification completion record. | Completed weekly maintenance evidence and immutable publication subject. |

The automatic workflow never approves editorial content and never publishes a
new Landing review on its own. A later daily production run may refresh only an
unreviewed review source. Once either top copy or feature review contains human
work, changed source events or digests mark it stale and require explicit
re-review rather than silent overwrite.

## Workbook ownership contract

The Landing workbook is separate from Unknown and visual-metadata maintenance.
Its sheets and user-facing fields are limited to the Landing editorial task:

1. `Review Control` - immutable baseline, calculated completeness counts, and
   read-only instructions for the two chat-gated stages; no duplicate Owner
   approval fields;
2. `Landing Copy` - ordered final text, Codex English draft, Owner English final,
   and an in-sheet reference block for every selected deck and `deck:<ID>`;
3. `Featured Decks` - candidate evidence and complete decklists plus editable
   selection, category, positioning, and four cards; derived bilingual deck
   names and localization status are read-only, and feature order comes from
   final top-copy token order rather than an input column;
4. `All Top 8` - every exact rank-one-through-eight deck available for manual
   addition; and
5. `Field Guide` - only fields the Owner needs to enter or review.

There is no separate `Landing Links` sheet. Displays and URLs are generated
from validated deck IDs. Internal input IDs, digests, action codes, parent IDs,
and implementation vocabulary are omitted from Owner input columns. The XLSX
is a review carrier; accepted content is imported into the private Landing
review source before preview or publication.

The Owner's submitted content is the review decision. One Chinese-stage chat
submission and one later bilingual acceptance are sufficient; the same authored
content is not approved again through workbook status dropdowns. The read-only
`landing-review validate-xlsx --stage chinese|bilingual --expected-sha256`
command checks actual content and provenance without writing repository state.
Within an Owner-started weekly lane, `import-xlsx` needs no separate technical
authorization and accepts only the exact Owner-accepted, bilingual-validated
hash.

The reference block has no `COPY LINK ONLY` state. Every exact token appearing
in a kept top-copy row must resolve to a `KEEP` row in `Featured Decks`. The
workbook generator performs this union before the Owner starts each week; the
content-completion importer repeats the same set check after Owner edits.
Category, order, localized editorial fields, and representative cards remain
Owner-reviewed even when membership is mandatory.

An Excel save may serialize a visually empty editable cell as a shared-string
reference whose resolved text is empty. Before every workbook read or rewrite,
the importer must independently resolve `xl/sharedStrings.xml` against the
worksheet cell references. A resolved empty string is normalized to blank even
if a higher-level library exposes the numeric shared-string index such as `15`
or `46`. A repeated numeric value across unrelated optional text fields is an
anomaly that requires this preflight; a render produced by the same importer is
not independent confirmation. After any rewrite, re-open the exported XLSX and
verify both the raw OOXML blank semantics and the user-visible render.

## Migration and deletion controls

- Standard W27, Standard W33, and Modern W33 are the required initial recovery
  set. A format/week missing complete feature content remains blocked rather
  than silently appearing empty.
- Existing Owner-authored text and order are preserved byte-for-byte when the
  recovery workbook is created. Codex fills only newly identified fields or
  clearly marked draft columns.
- The front end does not switch until the new feature index and every required
  week document validate and render locally.
- Legacy Pickup documents are not deleted during backend implementation,
  migration, preview, or initial cloud cutover.
- Cleanup requires a no-caller search, cloud verification of the replacement,
  an explicit path-by-path deletion or relocation declaration, and a tested
  rollback that does not depend on rebuilding lost Owner content.
- The accepted Landing UI design remains authoritative except for the bounded
  DEC-114 amendments assigned to P12-15E and P12-15E-UX. Data-source migration
  by itself does not authorize any other layout, interaction, sizing, or visual
  change.
