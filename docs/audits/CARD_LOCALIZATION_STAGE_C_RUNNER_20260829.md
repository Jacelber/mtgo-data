# Card Localization Stage-C Runner Evidence — 2026-08-29

Status: `Locally complete under continuous Owner authorization`

## Outcome

The repository-owned Stage-C browser runner is implemented and validated only
against loopback synthetic fixtures. The focused suite passed all nine cases.
No Scryfall, MTGCH, GitHub Pages, card-image, or other public-origin request was
made while implementing or validating this subject.

The runner is an internal diagnostic. It does not change either product, select
an image-delivery architecture, create a localization sidecar, or add any file
to Pages.

## Implemented structure

The runner uses the repository-pinned Playwright 1.62.1 and its managed
Chromium. It provides four operations through one command-line entry point:

1. source preparation for the later real trial writes `plan-input.json` only
   inside the approved repository-external trial directory;
2. `prepare` validates and deterministically samples that input, binds the
   served Pages HTML/catalog/controller bytes, deletes `plan-input.json`, and
   freezes `exact-plan.json` plus aggregate-safe state;
3. `session --number 1|2` opens fresh non-persistent desktop and touch contexts,
   rechecks every binding, exercises the sample, and retains aggregate counters;
4. `finalize` writes the redacted aggregate and deletes `exact-plan.json`.

The source-preparation step remains part of the separately authorized
`L10N-STAGE-C-TRIAL`, not this synthetic implementation task. This makes the
data boundary explicit: the diagnostic runner consumes one exact external plan;
it never stores the current public card population or source responses in the
repository. `prepare` accepts `--plan-input`; when omitted, it reads
`<trial-dir>/plan-input.json`.

The supported interface is:

```text
node scripts/run_card_localization_stage_c_trial.mjs prepare --trial-dir <absolute-external-directory> --pages-url <deployed-pages-url> [--plan-input <external-plan-input>]
node scripts/run_card_localization_stage_c_trial.mjs session --trial-dir <same-directory> --number 1
node scripts/run_card_localization_stage_c_trial.mjs session --trial-dir <same-directory> --number 2
node scripts/run_card_localization_stage_c_trial.mjs finalize --trial-dir <same-directory> --aggregate-out <repository-external-aggregate-path>
```

## Enforced trial boundary

The implementation enforces the contract in these layers:

- **Location and runtime:** the exact plan must be outside this repository and
  every detected Git worktree, synchronized/build/artifact locations are
  rejected, and real mode rejects CI, GitHub Actions, proxy variables,
  credentials in URLs, non-HTTPS URLs, and unexpected provider hosts.
- **Subject binding:** preparation freezes SHA-256 digests of the served HTML,
  catalog, and actual card-preview controller. Every session reopens the page
  and stops on any digest, executable-format, controller-constant, controller-
  availability, service-worker, cookie, Playwright, Chromium, or exact-plan
  drift.
- **Traffic:** the deterministic sample is capped at 100 and includes every
  declared host/media/source/face stratum with a minimum of five where
  available. Execution is sequential. Deliberate real-mode starts are at least
  ten seconds apart, while the bound controller retains its one-active,
  150-millisecond, two-attempt, 15-second-timeout, 1.5-second-retry contract.
  In one complete session, each provider is capped at 200 logical loads and
  400 physical starts.
- **Browser behavior:** half of the sample uses deliberate Pages-origin image
  loading; half uses the product controller with deterministic hover, keyboard
  focus, or actual touch tap. Desktop and touch run in separate fresh contexts.
  The controller's rapid-hover abandonment and queued-cancellation behavior is
  exercised by the synthetic evidence.
- **Observation:** response class, redirect class, final-host class, physical
  starts, response-body bytes, decode result, decode latency, fallback result,
  and cold/warm transfer behavior are reduced to aggregate counters and
  distributions. HTTP failures are counted before the matched English control
  is evaluated.
- **Retention:** exact identity and URLs exist only in the external input/plan.
  The aggregate is checked against every exact identity and URL before writing.
  Terminal preparation, drift, unsupported-session, budget, cache-observation, redaction,
  and finalization stops delete the exact plan. The runner never enables a
  trace, HAR, screenshot, video, browser profile, raw response archive, image-
  byte archive, or per-card request log.

Card names, decklists, and image URLs are public information. The retention rule
does not call them secrets or private user data; it prevents a temporary exact
test population and per-request diagnostic detail from becoming a new,
unreviewed permanent repository artifact. Credentials, cookies, and
authentication state remain separately prohibited security material.

## Focused verification

The synthetic suite passed these nine cases in one worker:

1. deterministic, order-independent, stratum-complete sampling and the 50/50
   deliberate/controller split;
2. command parsing plus logical and physical single-session budget stops;
3. real controller rapid-hover abandonment and queued-image cancellation;
4. complete single-session desktop/touch execution, aggregate redaction, cache
   classification, and final exact-plan deletion;
5. served-controller byte drift stop and exact-plan deletion;
6. unsupported second-session stop and exact-plan deletion;
7. source HTTP 5xx counting with successful matched-control fallback decode;
8. preparation-stop deletion of the external exact input; and
9. rejection of a trial directory inside the repository.

The focused command was:

```text
npx playwright test --grep="deterministic sampling|command parsing|bound controller|loopback runner|served controller drift|second session|source HTTP failure|preparation stop|trial directory" --reporter=line
```

Original two-session result: `9 passed (25.8s)`. After DEC-144 removed the
unsupported repeat rule, the focused single-session suite passed `9/9` cases
in one worker (`22.7s`).

Changed-scope repository validation also passed for all seven changed paths:
JavaScript 1/1, JSON 1/1, YAML 1/1, references 16/16, and hygiene 7/7. Node
syntax checks and complete diff whitespace validation passed.

## Controlled conclusion

The runner can produce the measurements required by DEC-143 and fails closed on
the synthetic risks proven above. This is implementation evidence only. It says
nothing yet about whether MTGCH images succeed, fail, redirect, cache, or load
quickly for the current public card population.

Under the Owner's continuous authorization, the next gate after exact Ready-PR
publication and merge is `L10N-STAGE-C-TRIAL`: regenerate the current subject
and exact external plan within the accepted source budgets, run session 1, then
finalize the one complete observed-window session. The result must not be
presented as cross-time or long-term availability evidence. No architecture
decision or product implementation follows automatically.
