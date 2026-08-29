# Card Localization Stage-C Execution Contract — 2026-08-29

Status: `Accepted; single-session amendment recorded by DEC-144`

## Outcome

This contract closes the executor-design gap recorded by DEC-142. It selects a
repository-owned Playwright/Chromium diagnostic that an Owner operates on one
controlled local machine for one complete browser session. It does not select an
image-delivery architecture and does not make a card, metadata, or image
request.

The selected structure is:

1. a later `L10N-STAGE-C-RUNNER` task implements and validates the diagnostic
   only against local synthetic fixtures;
2. a separately authorized `L10N-STAGE-C-TRIAL` task regenerates the exact
   deterministic sample and runs one complete session; and
3. only an accepted and published aggregate result may unblock
   `L10N-ARCHITECTURE-DECISION`.

The in-app browser remains within its security boundary. The new diagnostic is
not injected into that browser and does not use raw debugging access, a script
URL, or top-level navigation to an image host.

## Current task contract

| Field | Value |
| --- | --- |
| Task ID | `L10N-STAGE-C-EXECUTION-CONTRACT` |
| Objective | Define one auditable Stage-C executor and its exact data, measurement, retention, budget, and stop boundaries. |
| Base commit | `fabf436cca2b2a8adfa5135188730bd9acffcdf5` |
| Branch | `codex/l10n-stage-c-execution-contract` |
| Workspace | `D:/dl/crawlerpj/.codex-workspaces/l10n-stage-c-execution-contract-20260829-01` |
| Artifact impact | Documentation only; no product or statistical artifact changes. |
| Allowed paths | This audit, `docs/DECISIONS.md`, `docs/ROADMAP.md`, and `docs/STATUS.yaml`. |
| Local authority | Authorized by the Owner on 2026-08-29. |
| Commit / publication / merge | Not authorized until Owner acceptance of the unchanged local subject. |
| Stop point | Present the complete local documentation subject for Owner review. |

No code, dependency, Schema, workflow, asset, generated data, public catalog,
front-end behavior, classifier, event configuration, Pages package, source
request, or browser image request is authorized by this task.

## Problem and evidence

The corrected evidence rerun completed Stages A and B but stopped before its
first sampled image request. The approved in-app browser could open deployed
Pages and interact with existing elements, but it could neither bind the
external exact sample URLs into the deployed controller nor expose the required
status, redirect, transfer, latency, and cache observations. That stop was an
executor-capability gap, not an MTGCH result.

The repository already pins `@playwright/test` 1.62.1 and already runs Chromium
browser checks. Playwright exposes request/response completion and failure
events, redirect ancestry, request timing, and request byte sizes. It also
supports touch-enabled browser contexts. A non-persistent browser context does
not write browsing data to disk, so cold and warm observations can occur in one
session without retaining a browser profile after that session closes.

A standard GitHub-hosted runner is rejected for the real trial because passing
the exact sample through a workflow artifact is unnecessary and would create a
retained copy outside the local trial boundary. The test needs the Owner's
controlled local Pages/browser environment, not a cloud runner.

Official capability references:

- Playwright BrowserContext:
  <https://playwright.dev/docs/api/class-browsercontext>
- Playwright Request:
  <https://playwright.dev/docs/api/class-request>
- Playwright TestOptions:
  <https://playwright.dev/docs/api/class-testoptions>
- GitHub-hosted runners:
  <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>
- GitHub workflow artifacts:
  <https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts>

## Selected execution environment

The real trial must use all of the following:

- one Owner-controlled Windows machine for preparation and the browser session;
- the repository-pinned Node and Playwright dependency plus Playwright-managed
  Chromium, without installing an alternate browser automation stack;
- a repository-owned command-line runner introduced only by the later runner
  task;
- fresh non-persistent desktop and touch browser contexts for the session;
- one exact external sample plan deleted at finalization; and
- explicit Owner invocation rather than a background automation, hosted
  workflow, or retained cloud artifact.

The future runner must refuse to start if it is launched inside GitHub Actions,
if the plan directory resolves inside the repository or any worktree, if trace,
video, screenshot, HAR, or raw request logging is enabled, or if its browser and
dependency versions do not match its accepted implementation evidence.

## Repository-owned runner boundary

The later implementation task may propose these exact paths:

```text
scripts/run_card_localization_stage_c_trial.mjs
tests/browser/card-localization-stage-c-runner.spec.js
tests/fixtures/card-localization-stage-c/
```

That task must use only synthetic, same-origin fixture URLs and local fixture
responses. It must not contact Scryfall, MTGCH, GitHub Pages, or another public
origin. Its validation must prove command parsing, deterministic ordering,
interaction dispatch, aggregate redaction, budget enforcement, drift stops,
and deletion behavior without placing a real card name, identity, or URL in a
fixture.

The later real-trial command surface is fixed conceptually as:

```text
node scripts/run_card_localization_stage_c_trial.mjs prepare --trial-dir <absolute-external-directory> --pages-url <deployed-pages-url>
node scripts/run_card_localization_stage_c_trial.mjs session --trial-dir <same-directory> --number 1
node scripts/run_card_localization_stage_c_trial.mjs finalize --trial-dir <same-directory> --aggregate-out <repository-external-aggregate-path>
```

These commands are interface requirements, not current executable commands.
The implementation task may improve argument names only if its accepted
contract and documentation are updated before the real trial.

## Pages and controller binding

Before the session, the runner must open the declared deployed Pages entry
and prove all of the following without changing the deployed files:

1. the final `location.origin` and pathname equal the predeclared public entry;
2. SHA-256 digests of the served HTML, `stats/catalog.json`, and the exact card-
   preview controller asset equal the digests frozen during `prepare`;
3. the public catalog still closes the same executable Standard and Modern
   consumer subject used to regenerate the sample;
4. `P8CardImages` and the actual preview event path are present;
5. the controller still exposes one active request, a 150-ms minimum start
   interval, a 15-second attempt timeout, at most two source attempts, and a
   1.5-second retry delay; and
6. no service worker, request interception, cache-disabling route, extension,
   proxy, authentication state, or persistent browser profile alters the load.

The binding is to served-byte digests, not merely “latest Pages” or the current
`master` SHA. Documentation-only merges need not redeploy product bytes, and a
Git commit alone cannot prove what a browser actually loaded. Any digest or
controller-constant drift stops before the first sampled image.

The runner may add one transient test container to the page's runtime DOM after
the binding checks. That container may carry only the current sample item being
exercised and must be removed after the item. It does not alter deployed HTML,
assets, public paths, or repository bytes. The complete sample is never placed
in the DOM at once.

## Deterministic sample regeneration

The exact sample plan from the corrected rerun was deleted as required. Its
digest and aggregate strata are evidence, but they cannot reconstruct exact
identities or URLs. The real trial must therefore create a new source-snapshot
subject rather than claim reuse of deleted material.

`prepare` first recomputes Stage A offline. It may reuse the previous aggregate
only if all 47 registered public-document digests, the catalog digest, and the
combined subject digest exactly match the accepted values. Otherwise it records
a new Stage-A aggregate and the later result is explicitly a refreshed subject.

After separate authorization, the new preparation budget is:

- one suitable Scryfall `all_cards` Bulk snapshot, with bounded metadata needed
  to locate that one snapshot;
- at most 32 set-grouped MTGCH metadata requests, one in flight and at least
  five seconds between starts; and
- no image request during preparation.

Provider precedence and identity rules remain DEC-140/141: Scryfall proves
official Simplified Chinese material; absent that proof, exact-identity Chinese
material supplied by MTGCH is community under the Owner-recorded permission;
absent both, English is fallback. MTGCH is not required to supply a provenance
field.

The sample algorithm remains unchanged: partition eligible exact MTGCH images
by final host, media type, project-derived source class, and face form; include
every stratum; order by SHA-256 of canonical identity plus bound subject digest;
then take a proportionate minimum-five-per-stratum sample up to 100 unique
images. Fewer than 100 eligible images means test the entire smaller population.
Minima exceeding 100, identity ambiguity, unsafe location, or incomplete
stratum coverage stops preparation.

## External temporary state and retention

Before preparation, the runner resolves and records only the digest of the
chosen trial directory path. It must prove the directory is outside the
repository, all worktrees, Pages output, OneDrive or another synchronized
folder, and workflow-artifact locations. The directory is accessible only to
the Owner's local account.

The directory may temporarily contain:

- the exact canonical identity, MTGCH URL, and matched Scryfall control URL for
  the deterministic sample;
- the frozen served-byte digests, sample digest, source snapshot digests, and
  aggregate stratum counts;
- session timestamp; and
- aggregate counters that contain no exact identity or URL.

It must not contain raw Scryfall or MTGCH responses after preparation, image
bytes, cookies, credentials, a browser profile, trace, HAR, video, screenshot,
DOM snapshot, console transcript, or per-card request log. The session closes
and deletes its browser contexts. `finalize`, any terminal stop, or an
Owner/source stop request closes
the context and deletes the exact plan. A redaction or deletion failure makes
the result inconclusive and blocks publication of the aggregate until repaired.

## Browser actions

The session begins with fresh non-persistent desktop and touch contexts. The
deterministic split is 50% deliberate
mode and 50% controller mode, with odd remainders assigned by sample-hash order.

The session performs:

1. **Deliberate mode:** load one cold MTGCH image at a time through the transient
   Pages-origin container, wait ten seconds between logical starts, and pair it
   with the matched Scryfall control.
2. **Controller mode:** bind one transient card link to the exact current
   controller, then dispatch the product's real hover, keyboard-focus, or
   touch-click event shape. Interaction assignment is deterministic by sample
   hash. The set includes rapid hover abandonment and queued cancellation.
3. **Warm mode:** repeat each item once in the same context through its original
   mode and event shape.
4. **Fallback mode:** when a real MTGCH load finally fails, allow the same queue
   to load the matched English image and record time to complete decode.

Desktop hover/focus and touch-click use separate non-persistent contexts within
the same session, run sequentially so only one image is active globally. The
touch context must set `hasTouch: true` and dispatch an actual tap. No item may
be tested by top-level image navigation, direct Node HTTP, or a different page
origin and then reported as Pages-origin evidence.

## Observation contract

The runner observes page/context request, response, request-finished, and
request-failed events. For each logical load it may keep the exact URL only in
volatile memory long enough to join those events to the current sample item.
Redirect chains come from `redirectedFrom`; status comes from the final response;
transfer sizes and timing come from Playwright request APIs. Image completion
requires `img.decode()` and positive `naturalWidth`/`naturalHeight`.

Resource Timing may supplement the measurements but cannot alone prove caching
for a cross-origin response. A warm load is classified as transfer-avoided only
when the image decodes and Playwright observes no new network start or reports
zero response-body transfer for the matching request. It is transfer-reduced
only when the warm response-body bytes are at least 90% below the same item's
cold bytes. If neither Playwright nor browser timing can distinguish a cached
load from an unobservable cross-origin transfer, record
`cache_observation_unavailable` and stop the evidence as inconclusive.

Retained output is aggregate only:

- logical loads, physical network starts, HTTP-class, decoded, timed-out, and
  fallback-decoded counts;
- final-host and redirect-class counts limited to predeclared host classes;
- cold/warm response-body byte distributions and transfer-avoided/reduced/
  unchanged/unavailable counts;
- MTGCH and matched Scryfall median and p95 time to successful decode; and
- counts by declared stratum, session, and interaction mode.

No retained field or error text may contain a card name, canonical identity,
exact URL, URL path/query, raw response header/body, or sample position that
allows an identity to be reconstructed. Unexpected exception messages are
redacted before display; the unredacted exception is not written to disk.

## Budget accounting

The accepted 100-image design produces 200 planned logical MTGCH loads and 200
matched control loads: 100 cold plus 100 warm in one session. The
current controller can make at most two physical source starts inside one
logical load. To avoid the earlier ambiguity, the runner records and enforces
both units:

| Budget | Hard ceiling for the complete session |
| --- | ---: |
| Unique MTGCH sample images | 100 |
| Logical MTGCH loads | 200 |
| Logical matched Scryfall control loads | 200 |
| Physical MTGCH network starts, including bounded controller retry | 400 |
| Physical matched-control network starts, including bounded retry | 400 |
| Concurrent image requests across all contexts | 1 |

The 800-start ceiling is not permission to add a retry. It is the maximum
physical consequence of the existing two-attempt controller applied to the
accepted 200 logical loads. Deliberate mode does not invent a second
retry policy. No failure permits faster probing, a third source start, or a
replacement sample item.

## Stop conditions

Stop before further sampled traffic and classify the result as inconclusive on
any of the following:

- the machine, dependency, Chromium, Pages bytes, catalog subject, controller
  constants, exact sample digest, source snapshot, or allowed host set drifts;
- the runner detects GitHub Actions, a persistent browser profile, request
  interception, cache disabling, trace, HAR, video, screenshot, proxy, browser
  extension, authentication, or credentials;
- a source or redirect leaves the predeclared HTTPS host set, returns a non-
  image payload, or becomes identity-ambiguous;
- logical or physical request budgets, concurrency, pacing, or retry ceilings
  would be exceeded;
- status, redirect, decode, bytes, latency, cache, or fallback cannot be
  observed under this contract;
- an exact URL, card name, identity, raw response, image byte, screenshot,
  browser profile, or per-card log enters retained output; or
- the Owner or source asks the project to stop.

A 403, 429, 5xx, timeout, or decode failure is first recorded in aggregate and
activates the declared English fallback. It does not authorize more probing.
If the event also prevents completing the required modes or crosses another
stop condition, the session closes immediately. Setup failure is never
relabeled as image-delivery evidence.

## Acceptance criteria and controlled conclusions

The later runner implementation is acceptable only when synthetic tests prove
every binding, interaction, measurement, redaction, budget, and cleanup rule.
The later real trial is conclusive only when the current subject closes, every
stratum is represented, the complete session finishes, every declared metric is
observable, and the aggregate can be bound to subject, source, browser, Pages,
sample, and session-time digests without retaining exact identities.

This contract establishes that the selected executor is technically auditable.
It does not establish that MTGCH images succeed, fail, cache, redirect safely,
or meet latency criteria. It does not establish a local cache size. DEC-140's
architecture eligibility rules remain unchanged and cannot be applied until a
real result is accepted and published.

## Required next gates

1. Owner accepts this exact documentation subject.
2. Separately authorize commit, Ready PR, required checks, merge, and
   documentation publication for the accepted bytes.
3. Separately authorize `L10N-STAGE-C-RUNNER`; implement and validate it only
   with local synthetic fixtures, then stop for Owner acceptance.
4. After runner publication, separately authorize `L10N-STAGE-C-TRIAL` and its
   fresh source/image budgets. The Owner runs one complete real session on the
   controlled local machine.
5. Accept and publish only the aggregate result.
6. Separately authorize `L10N-ARCHITECTURE-DECISION`.

The recommended model for the runner and trial is `gpt-5.6-sol` with high
reasoning because the work couples browser-event fidelity, privacy/retention
boundaries, network measurement, and fail-closed governance. This contract
authorizes none of those later gates.
