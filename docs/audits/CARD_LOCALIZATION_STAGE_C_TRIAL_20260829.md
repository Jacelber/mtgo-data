# Card Localization Stage-C Observed-Window Trial — 2026-08-29

Status: `Local result complete; publication authorized`

## Outcome

MTGCH direct Chinese-image delivery worked for the complete tested window. The
Pages-origin browser loaded and decoded all 200 planned MTGCH logical cases and
all 200 matched Scryfall control cases, with zero failed decode and zero
timeout. The sample contained 100 unique community images: 90 single-face and
10 multi-face cards.

This is evidence for one 34-minute observation window. It proves that MTGCH is
not fundamentally unusable under the tested low-frequency product behavior. It
does not prove cross-time, daily, monthly, or long-term availability.

The earlier two-session/six-hour rule is withdrawn. No measurement established
that six hours would change the source, CDN, or network environment, while an
immediate repeat would add no independent evidence. The runner and contracts
now require one complete session and prohibit reporting the result as long-term
uptime evidence.

No image architecture is selected by this task.

## Bound subject and source evidence

The public subject remained the accepted Standard/Modern catalog closure:

| Binding | SHA-256 |
| --- | --- |
| Public-document subject | `9ddb39c04ebcc1c2e9fdb201733dc9dc88ac7d5f76a234e8f00ee97fd2640eb0` |
| Served catalog | `7e10b719368bc9b46158214b9b3f0143144a408989d7aa5d81610fef3b07503f` |
| Served HTML | `bdcb0d85cc67780d6a7bba9fe7e774cbb41cd2854ea8fd3c8552b80cecf11805` |
| Served card-preview controller | `c4a11563d112694e0bc1836f7db8c4b5575a8528e7c5aa1eb275cf138399794a` |

The successful source preparation reproduced the already accepted Stage-B
boundary exactly:

- 1,892 distinct input strings;
- 1,869 resolved strings and 23 unresolved strings;
- 1,866 canonical card/face identities;
- 1,186 official Simplified-Chinese image identities;
- 680 MTGCH community-image identities;
- 28 of 28 final grouped MTGCH responses returned HTTP 200 and processed
  10,939 items; and
- the grouped-response combined SHA-256 remained
  `74ebdfe0b9336040eb903efac43b7a2d2ff5f4584bcb6a3a66fa14abafec9073`.

Source preparation was not operationally clean. Several parser-development
attempts stopped before image testing, and one discarded attempt made 16 MTGCH
grouped requests before its incorrect population was rejected. Those attempts
mean the cumulative debugging traffic exceeded the per-preparation request
ceiling. They are not presented as a compliant source run or as image-delivery
evidence. The final exact population is usable because it reproduces the
previously accepted immutable Stage-B subject and source digests; the browser
result below begins only after that binding succeeded.

## Browser execution

| Measurement | Result |
| --- | ---: |
| Browser | Chromium `151.0.7922.34` |
| Playwright | `1.62.1` |
| Started (UTC) | `2026-08-29T06:47:18.747Z` |
| Completed (UTC) | `2026-08-29T07:21:22.348Z` |
| Unique MTGCH images | 100 |
| Deliberate / hover / focus / touch assignments | 50 / 15 / 20 / 15 |
| Single-face / multi-face sample | 90 / 10 |
| Concurrent image requests | 1 |

The deliberate half used one cold image at a time with ten seconds between
starts. The controller half used the deployed product's hover, keyboard-focus,
and actual touch-click event shapes. Every item had one warm repeat and one
matched Scryfall English-image control.

## Aggregate result

| Metric | MTGCH Chinese images | Scryfall controls |
| --- | ---: | ---: |
| Logical loads | 200 | 200 |
| Physical network starts | 132 | 125 |
| Successful decodes | 200 | 200 |
| Failed decodes | 0 | 0 |
| Timeouts | 0 | 0 |
| Median successful decode | 15 ms | 72 ms |
| p95 successful decode | 1,442 ms | 749 ms |
| Median observed response-body transfer | 0 bytes | 73,839 bytes |
| p95 observed response-body transfer | 60,185 bytes | 106,078 bytes |

The MTGCH p95 was 693 ms slower than the control, within the predeclared
one-second optional-direct threshold. No source failure occurred, so English
fallback was not activated and this run cannot measure real-failure fallback
latency. Synthetic validation separately proves that a source HTTP failure is
counted and the matched English fallback decodes.

For warm repeats, 183 of 200 avoided a new transfer, 14 reduced transfer by at
least 90%, and 3 were unchanged. Thus 197 of 200 (98.5%) avoided or materially
reduced transfer, above the 90% criterion. The aggregate's `transport` class
does not mean an image failed: it denotes a logical load for which no final new
HTTP response was observed, typically because the browser reused a decoded
cached resource. Every such logical load still decoded successfully.

All observed cross-host redirects stayed within the predeclared allowed host
classes. No authentication, 403, 429, 5xx, unsafe host, non-image payload,
decode failure, timeout, unobservable cache result, or budget stop occurred in
the browser session.

## Controlled conclusion

For the frozen subject and tested window, controlled MTGCH direct delivery with
exact English fallback is **eligible for consideration** under DEC-140:

- decoded MTGCH success was 100% overall and in every interaction assignment;
- no authentication, 403, or 429 occurred;
- the p95 difference from Scryfall was below one second;
- redirects remained within the declared host set; and
- 98.5% of warm repeats avoided or materially reduced transfer.

This means direct delivery may be evaluated in the separately authorized
architecture decision. It does not make MTGCH mandatory, establish long-term
uptime, select direct delivery, change the existing English Cache-B behavior,
or authorize product implementation.

## Retention and verification

The final redacted aggregate SHA-256 is
`34edbe8be15adaf2a97c7e1fc5fbd7db867a57fb683817c309f4d447bc1e5f27`.
The external exact identity/URL plan was deleted at finalization. No image byte,
raw response, screenshot, trace, HAR, video, browser profile, cookie,
credential, or per-card request log is retained in the repository.

After the unsupported repeat rule was removed, the focused synthetic
Playwright suite passed all nine cases in one worker. It covers deterministic
sampling, the 200/400 logical/physical ceilings, real controller interaction,
single-session finalization, aggregate redaction, cache classification,
controller drift, rejection of a second session, HTTP-failure fallback,
preparation cleanup, and rejection of repository-local trial state.

Changed-scope repository validation passed all 12 changed paths: Python 2/2,
JavaScript 1/1, YAML 1/1, coupled references 16/16, and hygiene 12/12.

Publication preflight exposed that the admission classifier did not recognize
the already published Stage-C runner path after its initial addition. The
correction classifies only
`scripts/run_card_localization_stage_c_trial.mjs` as a UI diagnostic and adds a
focused admission test; it does not classify the wider `scripts/` directory.
All 67 focused admission tests passed.
