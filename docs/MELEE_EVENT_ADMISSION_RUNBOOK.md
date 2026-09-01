# Melee event admission runbook

## Purpose and authority

Use this runbook for every proposed addition to `configs/melee_events.yaml`.
It turns an Owner-supplied Melee tournament link into separately reviewable
admission, collection, candidate, publication, and live-acceptance tasks. It
does not itself authorize any of those tasks.

`docs/STATUS.yaml` remains the only live authorization source. An event link,
read-only review, successful rehearsal, whitelist entry, completed collection,
or passing candidate is evidence for the next gate, never authority to cross
it. Refreshes of an already admitted event use the existing-event operation
path and do not silently inherit new-event admission authority.

## Fixed sequence

The stages below are mandatory and ordered. A stage may be split into smaller
tasks when its stop condition requires a product, statistical, compatibility,
privacy, or production decision. Do not combine stages merely to avoid an
Owner gate.

### 0. Intake and event identity

**Problem:** a Melee URL identifies a source page but does not prove that the
event belongs in Tabletop Major Events or authorize source access.

**Operation:** record the exact tournament ID and canonical
`https://melee.gg/Tournament/View/<event_id>` URL. Confirm that the Owner is
proposing the main event rather than a side event, and declare whether the
current task is read-only review, disposable rehearsal, whitelist admission,
or production work.

**Effect:** every later artifact and authorization is bound to one explicit
event ID.

**Stop:** reject an ambiguous URL or event identity. Do not discover or select
another Melee event automatically.

### 1. Qualification and structure evidence

**Problem:** the event page alone may not prove event category, Constructed
format, team status, day boundary, cut rule, playoff format, or decklist and
result completeness.

**Operation:** collect read-only evidence from the event page and an official
organizer, player guide, fact sheet, or schedule. Confirm:

- an approved event category and supported Constructed format;
- a completed tabletop main event that is not a team event;
- event name, start and end dates, organizer, and canonical URL;
- one of `mixed`, `constructed_day2`, or `constructed_single_stage`;
- every Swiss and playoff round label, stage, actual game format, and whether
  it belongs in primary statistics;
- advancement or cut rules, including any supported Top 8 lock behavior;
- usable decklists, standings, matches, and result coverage; and
- event-specific exceptions that require reviewed overrides or explanatory
  metadata.

Use `all_constructed_swiss` as the default statistical match scope and keep
playoffs out of primary win-rate and matchup statistics. Retaining playoffs as
context does not include them in those calculations.

**Effect:** the proposed whitelist contract reflects proved tournament
semantics instead of assumptions.

**Stop:** if a material phase, format, round, cut, result, or decklist boundary
cannot be proved, do not mark the event verified. Propose a separately
authorized disposable rehearsal or defer/reject the event.

### 2. Optional disposable rehearsal

**Problem:** public documentation may be insufficient to prove real source
labels or completeness before permanent admission.

**Operation:** only with event-specific authority, collect once into a
disposable non-production location, reuse that snapshot throughout diagnosis,
and produce a quality and compatibility report. Keep the event out of the
whitelist, retained production input, generated catalogs, Pages, and front
ends. Delete the complete disposable subject after the report is accepted.

**Effect:** the Owner can choose admit, repair, defer, or reject using real
evidence without turning a trial into production data.

**Stop:** trial success does not authorize whitelist admission, retention, a
candidate branch, publication, or another event.

### 3. Whitelist admission

**Problem:** collection must fail before source access unless the exact event
is enabled and verified in the authoritative registry.

**Operation:** under a focused whitelist task, add one complete entry to
`configs/melee_events.yaml`. Include the ID, URL, name, dates, format, series,
structure, enabled and review states, tabletop and team flags, raw request
plan, Swiss and playoff inclusion, phase map, advancement evidence when
applicable, statistical policy, source evidence, special handling, and notes.
Validate the registry, Schema, duplicate rejection, format availability, and
zero-side-effect rejection of unlisted, disabled, or unverified IDs.

Do not fetch or generate data in the whitelist task. Owner acceptance of the
unchanged whitelist subject may complete that task through its Ready PR and
merge; it does not authorize collection.

**Effect:** the event becomes eligible for an explicitly authorized operation
without becoming collected or public merely because the configuration exists.

**Stop:** do not merge a partial, guessed, disabled-by-accident, or
format-inconsistent entry.

### 4. Existing-cohort and publication preflight

**Problem:** adding an event can overwrite an existing catalog entry, change a
default selection, or combine events built under incompatible taxonomy,
Schema, scope, quality, or protected-event evidence.

**Operation:** before the first production collection, inspect the maintained
publisher, source-specific candidate validator, current format event catalog,
global consumer catalog, active taxonomy, and protected-event compatibility
manifests. Prove that the candidate path:

- adds the selected event without deleting or silently rewriting another
  event;
- makes any default-event change explicit and Owner-reviewed;
- emits the current catalog Schema and active-taxonomy identity;
- admits multi-event selection only for same-format, non-blocking events whose
  matchup and taxonomy identities reconcile;
- regenerates an affected derived event cohort only through a separately
  authorized migration while leaving immutable raw and normalized inputs
  unchanged; and
- updates a protected compatibility manifest only with replacement evidence,
  a decision record, and separate Owner approval.

If existing code still assumes one event, first complete a code-only
multi-event publication repair. If an existing protected event is stale under
the current taxonomy, complete its separately authorized derived-data and
compatibility migration before admitting the new event to multi-event use.

**Effect:** the new event expands the product rather than replacing or
silently invalidating the existing cohort.

**Stop:** do not dispatch production while a publisher would emit only the
selected event, an existing projection would change unexpectedly, or active
taxonomy compatibility cannot be proved.

### 5. Production candidate collection

**Problem:** a merged whitelist entry still contains no retained source or
reviewable product candidate.

**Operation:** with separate workflow-dispatch, live-collection, retention,
and candidate-branch authority, run **Melee production candidate** from the
exact approved `master` commit with the exact event ID and one closed operation
state. Use `collect-new` only when no review branch exists. Use
`resume-retained` only with the exact authorized 40-character review-branch
checkpoint; the workflow must prove that the remote branch still equals that
checkpoint before source resolution. A recovery may never fall back to a new
collection. A new event performs
one complete collection using raw manifest v4, minimized resource v2,
checkpoint v3, and `source-participant-id-v1`; it then retains, classifies,
builds the opportunity ledger, generates event statistics and matchup data,
packages metadata and catalogs, and validates the bounded candidate.

After candidate scope validation, stage only the exact event-bound paths before
complete candidate validation. This seals the exact Git-index subject so the
complete validator and later candidate commit consume the same paths without
publishing them. Run the dynamic
public-output Schema manifest and the internal Melee event, classification, and
opportunity manifest. Candidate validation may defer only synchronization of
the Tabletop row in `README.md`; published-state validation remains strict and
undefined validation or operation states fail closed.

The workflow may push only `data/melee-<event_id>`. It never writes `master`,
opens or merges a pull request, or deploys Pages.

**Effect:** one immutable, event-bound candidate is available for review.

**Stop:** stop on a changed request plan, incompatible checkpoint, failed
baseline, source failure, blocking quality issue, undeclared path, deletion,
cross-event write, cross-format write, MTGO write, or candidate-validation
failure. Do not hand-edit generated output or repeat a successful collection.

### 6. Candidate data and classification acceptance

**Problem:** a successful workflow proves execution, not that the event is
correct or suitable for publication.

**Operation:** review dynamic reconciliations rather than historical hard-coded
counts: participants, standings, decklists, rounds, matches, eligible
Constructed opportunities, and source completeness. Inspect unknown rounds and
results, byes, no-shows, intentional draws, awarded wins, disqualifications,
playoffs, Unknown classifications, conflicts, invalid decks, and every quality
warning. Confirm that generated product files use event-scoped derived
`participant_id`; direct source IDs remain only in the accepted retained Git
boundary.

If a classifier rule or event semantic must change, stop and open the matching
separate task. After that task is accepted and merged, reuse the same immutable
snapshot and regenerate the candidate; do not refetch it.

**Effect:** the exact candidate has human-readable evidence that its source,
normalization, classification, statistics, and privacy boundaries agree.

**Stop:** no blocking issue, unresolved unknown round, conflict, invalid deck,
unexplained count regression, stale taxonomy, or unreviewed exception may enter
publication.

### 7. Product and multi-event acceptance

**Problem:** individually valid event documents may still fail catalog-driven
discovery, multi-event reconciliation, or the existing Tabletop interface.

**Operation:** validate `overview.json`, `decks.json`, `matchup.json`,
`quality.json`, `meta.json`, the format event catalog, and
`stats/catalog.json`. Confirm single-event scopes, the recommended latest-event
default when the Owner accepts that product change, and `all_constructed` as
the only multi-event scope. Aggregate underlying W-L-D counts and recalculate
rates and intervals; never average event percentages. Verify the existing
event, new event, combined selection, language behavior, direct Tabletop route,
and MTGO/Tabletop separation in the maintained browser consumer.

**Effect:** the event works both as an independent tournament and, when fully
compatible, as part of the same-format multi-event product.

**Stop:** a single-event launch may proceed only if the approved scope
explicitly excludes multi-event admission. Never silently omit an incompatible
selected event or downgrade the active taxonomy to make it pass.

### 8. Candidate publication

**Problem:** a workflow review branch is not a public release.

**Operation:** after Owner acceptance of the exact unchanged candidate, create
one Ready PR from `data/melee-<event_id>`, run the required candidate and
repository checks, review the complete diff, and merge only after all required
checks pass. The accepted subject must include every intended raw, normalized,
derived, catalog, compatibility, and status change and no unrelated path. For
a new event, the same publication PR must also update the `README.md` current
public-product row and `docs/STATUS.yaml`; PR admission rejects an incomplete
new-event bundle before targeted checks begin. Pages compatibility validation
must compare every declared protected catalog projection, while allowing only
the unrelated catalog growth named by its expansion policy.

**Effect:** the reviewed event reaches the exact `master` commit that will
supply Pages.

**Stop:** stop on a changed subject, failed check, conflict, permission
blocker, unexpected generated change, or new product/statistical decision.

### 9. Pages deployment, live acceptance, and closeout

**Problem:** a merged data commit is not sufficient evidence that users can
access the correct release.

**Operation:** use the applicable authorized Pages path and bind deployment to
the exact merged `master` SHA. Verify once for that deployment:

- `/melee/index.html` and the expected language and event-selection behavior;
- every new event resource and both event catalogs;
- single-event and approved multi-event counts and scopes;
- playoff exclusion from primary statistics;
- absence of source participant IDs from generated public product documents;
- the current protected-event compatibility baseline; and
- no MTGO data, statistics, routes, or default behavior changed unexpectedly.

Record the completed task in the normal history location. Roll back through a
reviewed Git publication change; never delete or rewrite an immutable retained
snapshot as a shortcut.

**Effect:** the new event is publicly discoverable, reproducible, and bound to
reviewed source and deployment evidence.

**Stop:** do not describe the event as live until the exact-SHA deployment and
required public resources pass.

## Authorization matrix

| Action | Required authority |
| --- | --- |
| Read public event and official documentation | Read-only task scope |
| Disposable real-source rehearsal | Exact event and disposable-collection authority |
| Edit and merge the whitelist | Focused whitelist task and Owner acceptance |
| Repair publisher, validator, Schema, or compatibility contracts | Separate implementation task and Owner acceptance |
| Regenerate an existing protected event | Separate data migration and compatibility authority |
| Dispatch `fetch_melee.yml` | Exact event, closed operation state, and workflow-dispatch, live-collection or exact-checkpoint recovery, retention, and candidate-branch authority |
| Create and merge the candidate PR | Owner acceptance of the exact candidate |
| Deploy or recover Pages | Applicable exact-SHA deployment authority |
| Begin another event or refresh | A new task; no authority carries over |

## Reuse template

For each new event, create event-specific task IDs and preserve this order:

1. `MELEE-<event_id>-QUALIFICATION`
2. optional `MELEE-<event_id>-DISPOSABLE-TRIAL`
3. `MELEE-<event_id>-WHITELIST-ADMISSION`
4. any separately required publication or compatibility repair
5. `MELEE-<event_id>-PRODUCTION-CANDIDATE`
6. `MELEE-<event_id>-CANDIDATE-ACCEPTANCE`
7. `MELEE-<event_id>-PUBLICATION`
8. `MELEE-<event_id>-LIVE-ACCEPTANCE`

The event-specific task contract may narrow this list only when current
evidence proves a stage is already satisfied by the same immutable subject. It
must never use an earlier event's acceptance, collection, or deployment as
authority for a new one.
