# Phase 13 multi-event matchup design

Date: 2026-08-27

Base: `6cda56e23281b60b36e383943ba70d00fdce1e06` (`master`)

Branch: `codex/phase13-design`

Status: Owner accepted; implementation not authorized

Owner acceptance: 2026-08-27

Artifact impact: `internal_diagnostics`

## Problem

The Tabletop product can publish and render one validated Melee event, but it
cannot yet combine matchup evidence from two or more compatible events. The
current browser already retains selected event IDs and enforces the initial
`all_constructed` scope transition, but it deliberately renders a pending
message when more than one event is selected.

The missing capability crosses four layers:

1. the event catalog does not expose the complete compatibility evidence needed
   to admit a combination;
2. the Python producer has no pure multi-event raw-count reference aggregator;
3. the browser loads only one event matchup document and does not serialize the
   reserved `events` URL state; and
4. production has only one approved Modern Tabletop event, so real multi-event
   behavior cannot be publicly enabled yet.

## Expected effect

After the separately authorized Phase 13 implementation tasks are complete,
the application code will be able to combine compatible Tabletop matchup
documents by summing raw W-L-D counts and recalculating literal win rates and
Wilson intervals. Cross-format, cross-source, incompatible taxonomy, blocking
quality, unsupported scope, and incompatible Schema combinations will fail
closed. Per-event overview statistics will remain independent.

The capability may be present in production code while remaining unavailable
to users. Public multi-event selection stays dormant until at least two real
events are separately approved and admitted to the public catalog.

## Authority and frozen boundaries

This design applies the existing decisions rather than introducing a new
statistical meaning:

- DEC-001 keeps MTGO and Tabletop source data, statistics, catalogs, and
  product behavior separate.
- DEC-018 requires raw-count aggregation and prohibits averaging event rates or
  combining event overview metrics.
- DEC-026 requires visible sample sizes and reconstructable percentages.
- DEC-060 keeps the visible matchup method literal: wins divided by wins,
  losses, and normal played draws.
- DEC-061 limits initial multi-event selection to `all_constructed`.
- DEC-078 prohibits new consumers of draw-adjusted compatibility data.

The following remain outside Phase 13:

- MTGO multi-event aggregation;
- cross-format aggregation;
- Day 1 or Day 2 multi-event aggregation;
- combined metagame share, conversion, average-points, high-score, standings,
  or deck-detail statistics;
- arbitrary Melee discovery or collection;
- automatic event-whitelist changes;
- production workflow dispatch;
- public admission of a test event; and
- Phase 14 format work.

## Current implementation inventory

| Layer | Existing capability | Phase 13 gap |
| --- | --- | --- |
| Per-event producer | `src/mtgmeta/melee/matchup.py` emits validated hierarchical W-L-D matrices for one event. | No cross-event compatibility admission or raw-count union. |
| Publication | `src/mtgmeta/melee/publish.py` emits one event metadata record and one format catalog entry. | The catalog lacks a complete matchup-compatibility block and deterministic multi-event loading contract. |
| Schema | `schemas/melee-event-matchup.schema.json` and related event Schemas protect single-event documents. | No versioned in-memory multi-event result contract or catalog compatibility contract. |
| Browser model | `assets/js/phase8/matchup-model.js` already recalculates literal records from leaf-level counts. | It cannot align and combine multiple event matrices. |
| Browser controller | `assets/js/phase8/tabletop-controller.js` validates one event and resolves single/multi scope state. | It loads only one event and cannot reject an incompatible selected set before rendering. |
| Browser state | The UI already retains a selected-event set and shows a safe pending state for multiple events. | `events=<sorted,unique,event_ids>` remains reserved but unread and unwritten. |
| Production data | Modern event `434455` is the sole admitted Tabletop event. | No second approved real event exists, so the public capability must remain dormant. |

## Selected architecture

### Canonical calculation and browser execution

Use one Python pure function as the reference implementation and one browser
pure function for interactive execution. Both consume the same synthetic
contract fixtures, and their emitted raw counts and literal records must
reconcile exactly within the documented numeric precision.

The browser must not average percentages. It loads the selected events'
validated per-event matchup documents, extracts canonical leaf-level wins,
losses, and draws, sums them by stable identity, rolls the combined leaf matrix
up to parents, and recalculates:

- matches as `wins + losses + draws`;
- literal win rate as `wins / matches`;
- the 95% Wilson interval from literal wins and valid matches; and
- the low-sample warning from the existing shared threshold.

The Python implementation is the non-UI statistical reference and supports
deterministic fixture generation and reconciliation. The browser implementation
is necessary because a static site cannot pre-generate every possible selected
event combination without a combinatorial artifact set.

### Canonical aggregation inputs

Use validated per-event `matchup.json` documents plus their event metadata and
catalog entries. The per-event matchup producer has already applied round and
result exclusions and retained the underlying leaf-level W-L-D counts. Phase 13
must not reparse raw source responses or re-decide match eligibility during
interactive aggregation.

The combined matrix uses only each event's `all_constructed` leaf matrix.
Parent matrices and overall non-mirror records are rebuilt from the combined
leaf matrix rather than summed independently. This provides one canonical
source and preserves reconciliation:

- each directed cell has an inverse cell;
- diagonal cells retain real mirror matches;
- overall records exclude the row's mirror cells; and
- directed observations equal twice the included physical match count.

### Compatibility admission

A selected set is eligible only when all of the following are true:

1. it contains at least two distinct event IDs after sorting and deduplication;
2. every event comes from `melee` and the Tabletop product;
3. every event has the same Constructed format;
4. every event declares `all_constructed`;
5. every event and matchup input passes its active Schema validation;
6. no event has a blocking quality state;
7. taxonomy Schema versions and taxonomy SHA-256 values are identical;
8. matchup Schema versions are supported by one explicit compatibility rule;
9. shared parent, subtype, and leaf IDs have identical meanings; and
10. every selected event is present in the active catalog used by the
    consumer.

Production admission additionally requires every event to be separately
Owner-approved and published. A synthetic fixture or non-public real-event
test does not satisfy that production condition.

### Identity alignment and deterministic order

Equal taxonomy digests establish the maintained same-format identity contract.
Observed identities may still differ because an archetype can be absent from
one event. Build the combined hierarchy as the union of observed stable IDs,
using the maintained taxonomy order as the canonical order. A shared ID with
different parent, subtype, name, or display metadata is incompatible and stops
aggregation.

Missing cells are zero-count cells, but missing or malformed documents are not
zero events. Unknown remains an explicit stable identity when present and is
never silently redistributed.

### Result document

The in-memory multi-event result should carry at least:

- its own Schema version and `multi_event_matchup` document type;
- `source: melee`, product, and Constructed format;
- `scope: all_constructed`;
- sorted unique included event IDs and names;
- per-input paths, Schema versions, and SHA-256 values;
- the compatibility checks and their admitted values;
- the combined hierarchy and raw-count leaf matrix;
- reconstructed parent matrix and non-mirror overall records;
- included physical match count and excluded-count reconciliation;
- literal rate method, Wilson interval method, and low-sample threshold; and
- warnings that identify contributing event IDs.

Do not introduce a new draw-adjusted output or make the browser depend on the
legacy per-event `win_rate` compatibility field. The combined consumer uses raw
counts and emitted literal records only.

### URL and state behavior

Phase 13 activates the reserved `events` parameter only for the Tabletop
matchup view:

- serialize sorted, unique, catalog-admitted numeric event IDs joined by
  commas;
- reject stale, malformed, cross-format, or unavailable IDs;
- keep `event=<active_event_id>` only as the single-event overview identity and
  deterministic focus fallback;
- select `all_constructed` immediately when a second compatible event is
  added;
- restore a remembered single-event scope only when the remaining event still
  declares it;
- make user selection changes browser-history entries; and
- restore the same admitted set on reload and `popstate`.

Expanded rows and columns, hover state, filters, and other transient matrix
state remain outside the URL.

## Implementation sequence

Every item below is a separate task and requires separate Owner authorization.
Completion or acceptance of one item never authorizes the next.

### P13-01 - Pure raw-count aggregation core

Add the Python reference aggregator and focused synthetic tests. Freeze the
compatibility error vocabulary, stable-identity union, inverse-cell and
physical-match conservation, raw-count summation, parent roll-up, literal rate,
Wilson interval, and low-sample behavior. Do not add a public Schema, generated
output, browser code, or real-source access.

### P13-02 - Versioned multi-event and catalog compatibility contracts

Define the in-memory multi-event result Schema and add the minimum compatible
catalog metadata needed to admit selected events. Update producers, Schemas,
fixtures, manifest behavior where applicable, and focused validators. Do not
regenerate or publish current production data in this task.

### P13-03 - Browser reference parity

Add a pure JavaScript multi-event aggregator to the existing matchup model and
prove it against the same synthetic contract used by Python. It must reject the
same incompatible inputs and produce matching counts, rates, intervals, order,
and warning state. Do not change navigation, event controls, or production
availability.

### P13-04 - Multi-event loading, URL, and state transitions

Teach the Tabletop controller to load every selected matchup document, validate
the complete set before committing staged refreshes, activate the canonical
`events` URL representation, and preserve the DEC-061 single-to-multi scope
transition. Keep overview mode single-event and independent.

### P13-05 - Tabletop rendering and dormant production integration

Replace the multi-event pending placeholder with the combined matchup renderer,
included-event identity, sample size, warnings, and explanatory locked-scope
state. Use synthetic catalog and event fixtures for browser review. Production
continues to expose only catalog-admitted events; with one admitted event, no
public multi-event selection becomes available.

### P13-06 - Non-public real-event validation

Run the final real-source test only after P13-01 through P13-05 pass their
synthetic and local acceptance. Stop before this task and request the exact
Melee event URL from the Owner.

The supplied event is a test input only. It must not be added to the committed
production whitelist, public event catalog, global consumer catalog, Pages
artifact, or production front end. It does not authorize a production workflow
dispatch or publication.

## P13-01 bounded task contract

This is the recommended first implementation task after this design is
accepted and separately authorized.

### Objective

Implement a deterministic, side-effect-free Python reference aggregator that
combines two or more synthetic compatible Tabletop matchup documents from raw
leaf W-L-D counts and fails closed on incompatible inputs.

### Artifact impact

`internal_diagnostics`

Only the non-public task audit is expected to change as an artifact. No
generated, rendered, statistical public JSON, or public-path artifact is
expected to change.

### Expected paths

- `src/mtgmeta/melee/multi_event_matchup.py` (new maintained Python path);
- `tests/test_melee_multi_event_matchup.py` (new focused test path);
- `docs/TEST_TRIGGER_MATRIX.md`;
- `docs/audits/P13-01.md`; and
- `docs/STATUS.yaml`.

### Required synthetic subjects

1. two compatible same-format events with different observed identity subsets;
2. counts whose weighted raw-count result differs from the simple average of
   event percentages;
3. normal played draws proving the literal denominator;
4. mirrors proving diagonal retention and overall exclusion;
5. Unknown identity preservation;
6. duplicate and unsorted selected event IDs;
7. cross-source and cross-format rejection;
8. taxonomy version, taxonomy digest, and identity-metadata mismatch rejection;
9. unsupported matchup Schema rejection;
10. blocking quality and missing `all_constructed` rejection; and
11. inverse-cell, parent-roll-up, included-match, and directed-observation
    reconciliation.

### Prohibited changes

- no existing statistical field meaning changes;
- no Schema, manifest, generated data, catalog, front-end, workflow, public
  path, whitelist, classifier, or production changes;
- no network access or real event collection;
- no use of MTGO data; and
- no start of P13-02.

### Validation

Run the new exact focused test subject and changed-scope repository validation
once on the final tree. Do not run a full pytest suite, Schema suite, Node test,
browser test, or production test because P13-01 changes none of their triggers.

### Stop point

Present the pure aggregator, complete diff, compatibility failures, and focused
test evidence to the Owner. Stop pending acceptance and separate completion
authority; do not start P13-02.

## Final real-event test contract

### Owner gate

At P13-06, the Owner supplies the exact Melee tournament URL. Before any live
request, confirm and record:

- the event ID parsed from that URL;
- explicit authorization for that exact event and test run;
- the event category, Constructed format, structure, dates, and relevant
  rounds;
- whether it is compatible with the retained Modern event `434455` for a
  positive multi-event test;
- use of a distinct disposable HMAC test key and key ID; and
- disposable retention: no raw, normalized, generated, or participant data is
  committed or published.

If the supplied event is not Modern or otherwise incompatible with `434455`,
use it to prove fail-closed rejection, report that it cannot provide positive
real aggregation acceptance, and stop for the Owner to choose whether to supply
another event. Do not search for or select a replacement event automatically.

### Execution boundary

Use a fresh disposable clone and an uncommitted local test registration for the
exact supplied event. The fail-closed whitelist client must still validate that
registration before collection. Keep the test registration, v3 minimized raw
snapshot, normalized event, classifications, opportunity ledger, generated
statistics, combined result, and review output outside any commit.

Do not modify the committed `configs/melee_events.yaml`, production catalogs,
Pages allowlist, workflows, or public outputs. Do not run `fetch_melee.yml` or
another GitHub workflow. Do not use a production HMAC key or retain its value in
commands, logs, reports, checkpoints, or manifests.

The real event is not used by the front end. P13-05 browser acceptance remains
fixture-backed; P13-06 validates the producer and aggregation contract only.

### Required checks

1. collect only the exact Owner-supplied event through the approved minimized
   v3 contract;
2. validate every retained resource and prohibited-field scan;
3. normalize, classify, build the opportunity ledger, and generate the
   single-event matchup in the disposable workspace;
4. report Unknown classifications, conflicts, unknown rounds or results,
   quality issues, and every exclusion without coercion;
5. run compatibility admission against event `434455` and the supplied event;
6. if compatible, aggregate `all_constructed` raw leaf W-L-D counts and prove
   event-to-combined reconciliation, inverse cells, parent roll-up, physical
   matches, literal rates, Wilson intervals, and sample warnings;
7. verify that no overview metric was aggregated and no MTGO record entered the
   calculation;
8. verify the production whitelist, catalogs, public paths, Pages artifact, and
   remote repository are unchanged; and
9. retain only a non-sensitive summary of counts, compatibility outcomes, and
   validation results after the disposable test material is removed.

### Success effect

A passing P13-06 proves that the completed implementation accepts a current
real source shape and reconciles a real compatible event pair without making
the test event public. It does not admit that event, enable public multi-event
selection, authorize production, or authorize Phase 14.

## Phase acceptance and production gate

Phase 13 engineering acceptance requires:

- Python and browser results reconcile on the shared synthetic contract;
- incompatible selections fail closed before rendering;
- single-event behavior and current event `434455` remain compatible;
- canonical URL and history restoration work for supported selections;
- sample sizes, warnings, and included event identities are visible;
- no overview metric is combined;
- the non-public real-event test completes one positive compatible aggregation;
  an incompatible supplied event records rejection evidence and stops pending
  another Owner decision rather than satisfying this criterion; and
- all production and public paths remain unchanged unless separately
  authorized.

Public enablement remains a later gate. It requires at least two compatible real
events to be independently reviewed, approved, admitted, published, and present
in the active catalog. The P13-06 test event does not count toward that gate.

## Model guidance

Use `gpt-5.6-sol` with `high` reasoning for P13-01 through P13-05. The work is
cross-layer and statistically sensitive, while the bounded tasks and synthetic
contracts make `high` a better cost-risk balance than routinely using `xhigh`.
Use `xhigh` for P13-06 only if the supplied live event exposes an unfamiliar
source shape, ambiguous round structure, or unresolved quality evidence.

## Owner decision required

Review and either accept or amend:

1. the Python-reference plus browser-execution architecture;
2. the six-task implementation sequence;
3. P13-01 as the first bounded implementation task; and
4. the P13-06 non-public, Owner-link-gated real-event contract.

The Owner accepted this design on 2026-08-27. That acceptance authorizes only
completion and publication of this documentation task. P13-01 still requires a
separate explicit authorization.
