# Card Localization Architecture Evidence and Retest Contract — 2026-08-29

Status: `Corrective revision accepted by Owner; publication authorized`

This document replaces the unsupported architecture proposal previously drafted
at this path. It defines the evidence required before choosing local caching,
controlled direct image delivery, or a combination. It authorizes no source
request, image request, implementation, public artifact, or product change.

## 2026-08-29 classification correction

The published version incorrectly assumed that MTGCH must return one complete
per-card provenance field set before the trial could classify a Chinese name or
image. MTGCH defines no such unified source field. `official`, `community`, and
`english_fallback` are project-side classifications derived from provider
precedence:

1. Scryfall proves an official Simplified Chinese printing and supplies the
   official name or image for the exact card or face;
2. otherwise, an exact-identity Chinese name or image supplied by MTGCH is
   classified as MTGCH `community` under the Owner-recorded project permission;
3. otherwise, use the existing English fallback.

The first HTTP-200 grouped response in the trial therefore did not demonstrate
MTGCH response-contract drift. The local validator demanded undocumented
full-card fields from a documented card-description response. That is a test-
contract design error and requires this correction before any resumed source
or browser stage.

## Correction of the earlier diagnostic

`L10N-DIRECT-TRIAL` did not test image delivery. It completed thirty MTGCH
card-metadata resolutions, received HTTP 429 on resolution request 31, and
stopped before the first image request. The planned limits of four concurrent
image loads and two new image starts per second were never exercised.

The result proves only that the tested sequential per-card metadata-resolution
method encountered a rate limit. It supplies no evidence about:

- whether an exact MTGCH image URL loads from the deployed Pages origin;
- whether low-frequency hover, focus, or click requests succeed;
- image HTTP status, redirect host, decode, byte size, or latency;
- browser memory/disk caching or warm-load transfer behavior;
- whether failure can fall back to the existing English image acceptably; or
- how many current-subject Chinese images exist or how much storage they need.

DEC-138's conservative stop rule was followed correctly, but its incomplete
setup result cannot select a product architecture. The previously proposed
256-MiB/1,024-image cache, its ordering algorithm, and its blanket runtime
MTGCH prohibition are withdrawn as unsupported hypotheses.

## Existing evidence that remains valid

The following facts do not depend on the failed image trial:

- the current English Cache-B subject contains 71 complete-card images for the
  rolling four-week Landing Feature subject;
- current browser image loading uses one active request, a 150-ms minimum
  start interval, a 15-second attempt timeout, at most two attempts, and a
  1.5-second automatic-retry delay;
- desktop preview starts on hover or keyboard focus, touch preview starts on
  click, and rapidly abandoned hover work can cancel only queued work, not an
  already active network request;
- a bounded sample of current Standard/Modern 12-week MTGO decks plus the
  admitted Modern Tabletop event contains 1,442 distinct English card-name
  strings, but this is neither the complete public display subject nor a
  canonical identity count; and
- official, permitted community, and English fallback provenance rules remain
  governed by DEC-137.

These facts identify the real test modes, but they do not determine a Chinese
image architecture or capacity ceiling.

## Questions that require data

No architecture decision may be proposed until one evidence package answers
all of these questions.

| Decision question | Required measurement | Why current evidence is insufficient |
| --- | --- | --- |
| What must receive a localized name? | Exact catalog-rooted public document closure, extracted card-name occurrences, canonical card/face identities, and product/format/use bindings. | The 1,442-name sample omits indexed ranges and products and contains unresolved strings. |
| How much official/community coverage exists? | Counts and percentages of official Chinese name/image, permitted community name/image, and English fallback by exact identity and product. | The previous trial retained no complete inventory and stopped during metadata resolution. |
| What would a complete current mirror cost? | Actual or statistically bounded image-byte distribution, content-digest duplication, file count, and current Pages artifact headroom. | No MTGCH image byte was observed; 256 MiB and 1,024 files were chosen without these measurements. |
| Which images are eager versus user-requested? | Exact consumer paths and interaction class: initial/expanded inline rendering, hover/focus preview, or touch click. | Card occurrence does not imply equal runtime demand. |
| Does direct delivery work? | Exact-image cold and warm load status, decode, redirect, transfer bytes, latency, cache behavior, and English-fallback completion from the deployed Pages origin. | The earlier run never requested an image. |
| Can the manifest be refreshed safely? | Request count and result of a grouped metadata plan, including 403/429/5xx and contract drift. | Per-card `/result` behavior does not establish grouped build-time behavior. |
| How should six future formats affect the design? | Recomputed evidence when each format becomes catalog-available. | Planned formats have no complete public subject or real Chinese-image distribution; extrapolation is not acceptance evidence. |

## Trial subject

The diagnostic uses only products that are available for executable formats in
the exact `stats/catalog.json` snapshot bound to the trial. It does not fetch or
invent Phase-14 data.

The local inventory follows registered public references:

1. every MTGO decks document named by the available statistics index;
2. every MTGO Top 8 week and comparison base named by its available index;
3. the current Landing document and exact Cache-B rolling Feature subject; and
4. every Tabletop event deck document named by an available event index.

Field-specific extractors record card occurrences only from declared card-list,
Feature-card, key-card, and comparison-base fields. They do not treat prose,
archetype labels, player names, or arbitrary JSON strings as cards.

## Stage A — offline subject and consumer inventory

Stage A makes no network request. It produces aggregate, repository-external
evidence containing:

- included document paths and SHA-256 digests;
- input occurrence and unique English-name counts by product and format;
- exact use classes: eager inline, expanded inline, hover/focus, and touch
  click;
- the current Pages packaging byte/file totals without any proposed
  localization overlay; and
- the existing Cache-B subject count and configured ceiling as a separate
  accepted resource.

Any unregistered card-bearing consumer, unresolved public reference, or path
escape stops before Stage B. The inventory is an observed current-product
subject, not a six-format projection.

## Stage B — bounded identity and source inventory

After separate authorization, Stage B may obtain a current Scryfall dataset
suited to resolve canonical `oracle_id`, `scryfall_id`, and `face_index`, prove
official Simplified Chinese printing/name/image availability, and establish the
matched English-image control for every sampled identity. An Oracle Cards
snapshot may resolve identity but must not be treated as complete printing-
level official-Chinese evidence unless its actual contract supplies that data.

MTGCH metadata access must not repeat one `/result` search per card. Before the
first MTGCH request, the trial writes an aggregate request plan containing only
the number of relevant set groups and the pacing/ceiling. It then uses the
public set-grouped card endpoint with:

- one request in flight;
- at least five seconds between new metadata requests;
- at most 32 MTGCH metadata requests in the entire trial;
- `Retry-After` compliance; and
- an immediate stop on authentication, 403, 429, 5xx, identity ambiguity,
  unsafe image location, or documented response-contract drift.

The grouped MTGCH response needs only the documented identity linkage and
Chinese name/image information required to bind the value to the canonical
card or face. It does not need to declare `official` or `community`; the trial
derives that class by the precedence above. A validator may require only fields
documented for the endpoint it actually calls.

The 32-request ceiling bounds diagnostic load; it is not a claim that 32 groups
cover the product. If the cap cannot cover the planned strata, the evidence is
reported as incomplete and no architecture is selected.

Stage B reports only aggregate counts by product, format, source class, host,
media type, and single-/multi-face identity. Raw responses are deleted after
resolution. The exact selected sample identities and URLs may remain only in
one repository-external temporary trial directory until the second Stage-C
session closes; they never enter Git, Pages, an artifact, or the aggregate
report. No image byte, credential, cookie, or browser profile is retained.

## Deterministic image sample

The image trial covers only exact, permitted MTGCH image URLs resolved in Stage
B; the browser never calls the MTGCH card-search or metadata API.

The sample is selected without editorial choice:

1. partition eligible identities by final image host, media type, project-
   derived official or community class, and single-/multi-face form;
2. include every stratum;
3. order identities inside each stratum by SHA-256 of the canonical identity
   plus the bound subject digest; and
4. take a proportionate sample with a minimum of five per non-empty stratum,
   up to 100 unique MTGCH images total; if fewer than 100 are eligible, test all
   and report the weaker sample size.

If the five-per-stratum minima would exceed 100, the sample is incomplete and
the contract returns for review instead of silently dropping a source class.

One hundred all-successful unique trials would place the ordinary 95% “rule of
three” upper bound for an unobserved failure rate near 3%. This is sufficient
only for evaluating an optional path with exact English fallback, not for
claiming long-term uptime or making MTGCH mandatory.

## Stage C — exact-image browser trial

Stage C runs from an ephemeral browser opened on the deployed Pages origin. It
does not modify the deployed DOM, repository, public paths, or product code.
Each sampled identity has a matched existing Scryfall English-image control.

Run two sessions at least six hours apart so one short availability window is
not treated as stable behavior. Bind the same sample in both sessions and split
it deterministically into equal deliberate-mode and current-controller-mode
halves. Each session performs:

1. **Deliberate single-image mode:** one cold MTGCH image at a time with ten
   seconds between starts, paired with its Scryfall control.
2. **Current-controller mode:** exercise the actual one-active-request,
   150-ms-minimum-start queue through the same hover/focus and touch-click
   event shapes used by the current product, including rapid hover abandonment
   and queued cancellation.
3. **Warm mode:** repeat every deliberate/controller image once in the same
   browser context and record whether memory/disk cache avoids or materially
   reduces transfer.
4. **Fallback mode:** for every real failure, load the matched English image
   through the same queue and record total time until a complete image decodes.

Across both sessions the hard ceiling is 400 MTGCH image-load attempts and 400
matched Scryfall control attempts. There is one active image request at a time.
No retry beyond the current two-attempt controller behavior is allowed.
Authentication, identity ambiguity, unsafe redirect, budget breach, or an
Owner/source request to stop ends the trial immediately. A 403, 429, 5xx,
timeout, or decode failure is recorded and activates English fallback; it does
not trigger faster or additional probing.

Only aggregate metrics may be retained:

- attempted, HTTP-class, decoded, timed-out, and fallback-decoded counts;
- final-host and redirect-class counts;
- cold/warm transferred-byte distributions and cache-result counts;
- MTGCH and matched Scryfall median and p95 decode times; and
- results by declared stratum and interaction mode.

Raw card responses, image bytes, screenshots, browser profiles, and request
logs containing per-card identifiers are deleted when each session closes. The
temporary exact sample identity/URL plan remains only between the two sessions
and is deleted when the second session closes.

## Evidence-quality gates

The trial is conclusive only when:

- Stage A closes every registered current public consumer path;
- Stage B resolves enough permitted MTGCH image URLs to satisfy every stratum
  and either reaches 100 unique images or explicitly tests the entire smaller
  eligible population;
- both Stage-C sessions complete their declared cold, controller, warm, and
  fallback modes without budget, identity, or provider-classification
  ambiguity; and
- aggregate results can be matched to the frozen subject, source snapshots,
  browser version, Pages commit, and session times.

Any setup-stage 429 or incomplete sample is reported as an inconclusive setup
result. It does not automatically select local caching, direct delivery, or a
capacity value.

## Decision rules after the evidence exists

The later architecture decision must use the measured evidence as follows:

- **Controlled direct delivery is eligible** only if both sessions show no
  authentication, 403, or 429 response; decoded MTGCH success is at least 97%
  in every interaction mode; every real miss reaches decoded English fallback;
  MTGCH p95 decode time is no more than one second slower than the matched
  Scryfall control; redirects remain on predeclared hosts; and at least 90% of
  warm repeats avoid or reduce transfer by at least 90%.
- **Local-only Chinese images are eligible** only after the measured image
  count, byte distribution, digest deduplication, actual Pages headroom, and
  eager/on-demand split support an explicit current-subject bundle. The trial
  must derive the ceiling from those measurements; it may not reuse 256 MiB or
  1,024 files as defaults.
- **A mixed design is eligible** when eager images have a measured bounded
  local subject and the controlled direct path meets its criteria for
  on-demand misses.
- **English-image fallback remains the only supported image behavior** if the
  evidence is incomplete or neither image option meets its criteria. Chinese
  name work may still proceed independently if its own coverage evidence is
  complete.

No future-format capacity claim is permitted. Each newly available format
changes the subject and must rerun the offline inventory and capacity model;
the direct-image compatibility result may be reused only while its exact hosts,
contract, browser policy, and source permission remain unchanged.

## Required sequence and stop point

1. Accept and publish this evidence contract.
2. Separately authorize `L10N-ARCHITECTURE-EVIDENCE-TRIAL` to execute Stages A,
   B, and C without retaining source material or changing the product.
3. Accept and publish the aggregate evidence report.
4. Separately authorize `L10N-ARCHITECTURE-DECISION` to retain, modify, or
   reject each architecture option from the measured result.
5. Only an accepted and published architecture may define later implementation
   tasks.

The Owner accepted this contract and conditionally authorized Step 2 to begin
only after this exact contract is successfully merged and published. That
conditional authorization does not permit source access before the merge.

This document stops before Step 2. It does not authorize another MTGCH or
Scryfall request, a browser trial, code, Schema, workflow, sidecar, Pages,
commit, publication, merge, production, `L10N-B1`, `L10N-B2`, `L10N-C`, or
Phase 14.
