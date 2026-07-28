# Phase 8 Front-end and Supporting Data Plan

Status: owner-approved planning baseline<br>
Approved on: 2026-07-25<br>
Implementation status: not started<br>
Production changes authorized: no

## 1. Purpose

Phase 8 will redesign the public information architecture around format-first
navigation, add the Tabletop Major Events front end, expose the already
generated parent/subtype hierarchy consistently, and add only the backend
contracts that the approved interface still lacks.

This plan prevents two sequencing errors:

1. implementing backend payloads before the final interaction design identifies
   their consumers; and
2. implementing the final front end before the required statistics, coverage
   metadata, and deck-detail contracts are stable and tested.

The required order is:

1. audit the current UI and public data;
2. design and approve the final UI locally;
3. freeze the UI behavior and backend data contract;
4. implement and validate the required backend additions;
5. implement the approved production front end;
6. run cross-product regression and real-browser acceptance.

## 2. Approved navigation and interaction requirements

### 2.1 Format-first navigation

The primary analysis selector at the top of the public experience is the
Constructed format, such as Standard or Modern.

After a format is selected, the user can select the products available for that
format:

1. MTGO official event statistics;
2. MTGO matchup win rates;
3. MTGO weekly Top 8 decklists;
4. Tabletop Major Events;
5. Weekly Pickup.

The source products remain statistically and technically separate. The
format-first shell may link between `/index.html` and `/melee/index.html` while
retaining the selected format, but it must not merge MTGO and tabletop records
or load them into one statistic.

An unavailable product for a selected format must be hidden or presented as an
explicit unavailable state based on generated catalogs. The front end must not
invent availability from hard-coded format lists.

### 2.2 Parent and subtype behavior

Parent archetypes are the default display level.

For every hierarchical table or matchup axis:

- selecting an expandable parent shows its maintained subtypes;
- matchup rows and columns expand independently;
- one global control shows or hides all eligible subtypes;
- a parent with zero or one maintained subtype exposes no expansion control and
  does not reveal a redundant subtype row;
- collapsing restores the exact parent aggregate;
- the browser uses supplied counts and approved rollups and does not invent or
  reclassify a subtype.

When a subtype is shown without its parent row, its visible label must still be
self-contained, for example `Grixis Prowess` rather than only `Grixis`.
The public contract must provide a stable full display label without changing
the subtype ID or classifier taxonomy.

Across MTGO and Tabletop matchup products, the visible primary win rate is the
literal valid-match win share, `W / (W + L + D)`. Normal played draws remain in
the denominator and do not count as wins. Primary overview and `Overall`
values include mirrors, matrix diagonal cells display their real mirror W-L-D
rates, and an explicit non-mirror rate remains available as supporting output.

### 2.3 Deck-construction details

Representative deck, average construction, deviation, recent construction
change, Core/Flex cards, and related construction details are subtype products
when a parent has maintained subtypes.

- Selecting an expandable parent only expands its subtypes.
- It does not open a parent-averaged deck detail.
- Selecting a subtype opens that subtype's independently calculated detail.
- A parent with no maintained subtype may retain its existing parent-level
  detail because the parent is already the most specific maintained identity.
- A parent with one maintained subtype remains visually unexpanded and uses one
  non-duplicated detail presentation.

The existing subtype-specific MTGO range and deck outputs are the starting
contract. Phase 8 must audit and reuse them before proposing new calculations.

### 2.4 Weekly MTGO Top 8 decklists

For each enabled MTGO format, provide a weekly view that:

- selects one complete week from a generated week catalog;
- lists every admitted event in that week;
- lists the first eight finishing decklists for each event when available;
- identifies event, date, finish, parent archetype, subtype, and stable full
  subtype label;
- retains visible missing-deck or source-quality states rather than silently
  removing incomplete rows.

Selecting a listed deck opens the shared deck-detail presentation:

- the left side is the exact selected event decklist, not the representative
  deck;
- the detail shows that deck's deviation from the applicable subtype base;
- the comparison side shows the applicable subtype average deck;
- identity, event provenance, range/base provenance, and unavailable values are
  explicit.

The detail component should be shared with the subtype detail used by MTGO
official statistics. The payloads may differ, but the interaction and visual
structure should not be duplicated.

### 2.5 Visible source completeness

MTGO matchup views must show range-specific source completeness near their
source description:

- expected or admitted events in the selected interval;
- events with usable Videre matchup archives;
- missing or deferred events;
- the exact numerator and denominator;
- the resulting completeness rate;
- exclusions needed to interpret the value.

MTGO official high-score views must also show decklist completeness near the
existing range summary. The backend must retain the raw inputs used to derive:

- the theoretical high-score decklist count from reviewed event rounds and
  participant counts;
- the observed usable high-score decklist count;
- the resulting high-score decklist completeness rate;
- events or source states that cannot support the denominator.

The exact formulas, event eligibility, rounding, and unavailable-state behavior
must be approved in the statistical contract before generator implementation.
The front end must not estimate either completeness metric.

## 3. Design method and external-service policy

The default design method is local:

1. inspect the existing public pages and generated JSON;
2. document information hierarchy and component states;
3. create disposable local HTML/CSS/JavaScript prototypes in the isolated task
   workspace;
4. review them in a local browser with representative real public data;
5. record the approved behavior in a repository UI specification.

Superdesign is not part of the default Phase 8 toolchain. Its installation or
authentication does not authorize external generation or upload.

Superdesign may be proposed only when local prototypes reveal a specific
high-fidelity visual exploration problem that materially benefits from parallel
design generation. Before any use, the owner must receive and approve:

- the unresolved design problem;
- why local prototyping is insufficient or disproportionately expensive;
- the expected design outputs and number of generation/iteration rounds;
- current pricing, free-tier, quota, and model limitations that can be verified;
- every prompt, source file, image, and data category that would leave the
  workspace;
- a privacy-minimized context plan;
- the local alternative and the expected cost/benefit difference.

Authorization is scoped to the stated external design operation and does not
authorize later generations, uploads, code changes, publication, or production
deployment. Superdesign output is advisory; repository specifications, tests,
and owner acceptance remain authoritative.

## 4. Phase 8 task order

### P8-01 — Current UI and public-data consumer audit

Purpose:

- reproduce the current Standard and Modern public behavior locally;
- inventory entry points, controls, modules, public JSON, and catalog
  dependencies;
- map each approved UI requirement to an existing field, a missing field, or an
  unresolved statistical decision;
- identify responsive, accessibility, localization, and GitHub Pages risks;
- prove which subtype calculations are already complete and must not be
  rebuilt.

Deliverables:

- `docs/audits/P8-01.md`;
- a UI-to-data requirement matrix;
- representative local screenshots or notes that contain no new production
  behavior;
- a bounded list of backend gaps for P8-04 through P8-07.

No production source, generated output, statistical rule, or public page changes
belong to P8-01.

### P8-02 — Local information architecture and interaction prototypes

Purpose:

- create a faithful current-page baseline;
- prototype the format-first shell and secondary product selector;
- prototype parent/subtype tables, independent matchup axes, global subtype
  control, Top 8 week selection, deck detail, completeness display, and
  unavailable/error states;
- test desktop and narrow-screen behavior with representative data.

Use local disposable prototypes by default. Do not invoke Superdesign without
the separate approval gate in section 3.

### P8-03 — Owner review and UI freeze

Purpose:

- compare and revise the local prototypes;
- select the final information hierarchy and visual direction;
- freeze the initial component states, labels, navigation, responsive behavior,
  shared detail behavior, and backend consumer requirements;
- publish the accepted UI specification and backend consumer contract.

P8-03 is a mandatory owner-acceptance gate. Backend production changes must not
begin before the owner accepts the initial UI specification. This freeze is
strong enough to prevent speculative backend work, but it is not the last
visual acceptance: representative real payloads receive a second owner review
at P8-07 before production front-end implementation.

### P8-04 — Statistical and public data contract

Purpose:

- define the versioned migration from the existing draw-adjusted, primary
  non-mirror rate to literal all-match win rate while retaining explicit
  supporting non-mirror fields and visible mirror cells;
- define the two completeness metrics precisely;
- define weekly Top 8 event, rank, deck, and week eligibility;
- define the stable full subtype display-label contract;
- define exact-deck, subtype-average, deviation, provenance, empty-state, and
  error payloads;
- define a direct per-event, per-scope Tabletop overall row with aggregate
  completion and match records so the browser does not reconstruct it;
- expose event structure, supported scopes, and matchup-scope compatibility,
  while keeping mixed all-Constructed high-score values explicitly unavailable;
- update statistical specifications, architecture, JSON Schemas, fixtures, and
  compatibility requirements before generator changes.

This task must preserve existing parent results and source separation. Any
formula or denominator requiring an owner decision stops here for approval.

### P8-05 — Weekly MTGO Top 8 backend product

Purpose:

- generate deterministic per-format complete-week and event Top 8 catalogs;
- expose exact decklist references and subtype identity;
- calculate or reference subtype-based deviation and average-deck comparison;
- retain missing-deck and provenance diagnostics;
- integrate public Schemas, catalogs, candidate boundaries, and regression
  tests.

### P8-06 — MTGO completeness backend product

Purpose:

- generate range-specific Videre expected/available/missing coverage;
- generate reviewed theoretical/observed high-score decklist completeness;
- retain numerators, denominators, exclusions, unavailable reasons, and source
  provenance;
- prevent the browser from reconstructing statistical denominators.

### P8-07 — Backend consumer-readiness and real-data UI revalidation

Purpose:

- run Standard and Modern end-to-end regeneration;
- confirm parent projections remain compatible;
- confirm subtype-specific construction metrics are consumed rather than
  recomputed;
- validate Top 8 and completeness outputs against real retained production data;
- freeze the public paths and payload versions needed by the front end;
- load representative real Standard and Modern payloads into the accepted
  review UI;
- review real row counts, label lengths, table density, unavailable values,
  warnings, completeness states, deck details, and responsive behavior;
- obtain explicit owner acceptance of any final display or interaction changes
  before P8-08 begins.

No final UI implementation begins until P8-07 passes. Display-only findings may
amend the UI specification here. A finding that requires a new field, formula,
denominator, or Schema returns to a separately authorized contract/backend task;
the browser must not reconstruct the missing statistic.

### P8-08 — P8-07 prototype productionization and shared candidate shell

Purpose:

- use the owner-accepted P8-07 real-data prototype as the implementation source
  instead of re-splitting the Phase 4 legacy page;
- move the accepted shell, navigation, loading, error, deck-detail,
  accessibility, and hierarchical interaction behavior into focused static
  modules;
- keep MTGO and Tabletop controllers, loaders, state, and caches structurally
  separate while sharing presentation utilities;
- load the published catalog and real retained JSON through the approved
  consumer contracts;
- publish only a parallel production candidate during this task.

The deployed `/index.html` and its Phase 4 assets remain unchanged as a
regression oracle and rollback baseline. P8-08 does not create the final
`/melee/index.html`, switch a production entry point, alter a statistical
formula, or change a public data contract.

### P8-09 — MTGO format-first production UI

Purpose:

- connect the accepted P8-08 MTGO controller and shared shell to `/index.html`;
- implement the approved format-first shell for enabled MTGO formats;
- implement official statistics, hierarchical matchup, weekly Top 8, and Weekly
  Pickup views;
- implement parent/subtype controls and full subtype labels;
- implement shared exact/representative/average deck detail;
- display both completeness products and quality warnings;
- verify every retained legacy behavior and public path before retiring any
  compatibility asset.

### P8-10 — Tabletop Major Events production UI

Purpose:

- connect the accepted P8-08 Tabletop controller to `/melee/index.html` using
  the shared shell;
- select format, event, and statistical scope from the published catalogs;
- render hierarchical event overview and matchup statistics;
- expose event quality, selection-bias, exclusion, and source information;
- keep all tabletop values separate from MTGO products.

P8-09 and P8-10 are separate production-entry changes and each retains its own
owner authorization and acceptance gate.

### P8-11 — Cross-product regression and Phase 8 closeout

Purpose:

- run complete automated validation;
- run local and deployed-browser acceptance for Standard and Modern;
- test desktop and narrow-screen layouts, keyboard operation, loading,
  unavailable, empty, and error states;
- verify GitHub Pages paths and source separation;
- confirm the collapsed parent views reproduce the approved baselines;
- update status, decisions, documentation, and the Phase 8 recovery tag only
  after owner acceptance.

## 5. Phase gates

Phase 8 has three mandatory stop points:

1. after P8-01, before selecting prototype directions;
2. after P8-03, before any backend production change;
3. during P8-07, after representative real data has been reviewed and before
   implementing the final production UI.

Every task still requires its own focused authorization. Acceptance,
publication, workflow dispatch, deployment verification, and the Phase 8 tag
remain separately controlled under `docs/DEVELOPMENT_WORKFLOW.md`.

## 6. Phase acceptance

Phase 8 is complete only when:

- format is the primary analysis selector;
- the five approved product views are catalog-driven by format;
- MTGO and tabletop entry points and statistics remain separate;
- parent archetypes are the default and subtype expansion follows the maintained
  taxonomy on tables and both matchup axes;
- parents with zero or one subtype expose no redundant control;
- visible subtype labels are self-contained;
- construction details use the most specific maintained identity;
- weekly MTGO Top 8 decklists and shared deck comparison details work;
- Videre and high-score decklist completeness are visible and backed by approved
  generated numerators and denominators;
- the approved Modern Pro Tour is viewable independently from MTGO Modern;
- Standard and Modern baselines, public paths, Schemas, workflows, and GitHub
  Pages deployment pass regression;
- owner browser acceptance is complete.
