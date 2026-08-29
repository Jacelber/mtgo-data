# Card Localization Architecture Evidence Trial — 2026-08-29

Status: `Corrected rerun accepted by Owner; completion authorized`

## Outcome

The corrected rerun closed the offline subject and the bounded identity/source
inventory. It did not complete the browser image trial and therefore remains
inconclusive for image architecture selection.

The important separation is:

- MTGCH grouped metadata access completed successfully: all 28 planned requests
  returned HTTP 200, with no 403, 429, 5xx, schema drift, unsafe host, identity
  ambiguity, or retry;
- the corrected provider-precedence rules produced complete Chinese-name and
  Chinese-image source assignments for all 1,866 resolved canonical identities;
- a deterministic 100-image sample covering every eligible
  host/media/source/face stratum was prepared; but
- the controlled in-app browser could not introduce those external exact URLs
  into the already deployed Pages controller or expose the required network
  observations. Its security boundary also prohibited script-URL injection,
  raw debugging access, or an alternate browser automation surface.

The browser stop occurred before the first sampled MTGCH image or matched
Scryfall control request. It is an execution-environment limitation, not an
MTGCH image-delivery failure. No local-only, controlled-direct, mixed, or
English-only image architecture is selected.

## Frozen subject

The corrected rerun used repository commit
`3c63967b23fa96b004163114e51ef17b3f8a6008`, the merge commit that published
DEC-141 and the corrected evidence contract. The catalog snapshot was
`stats/catalog.json` with SHA-256
`7e10b719368bc9b46158214b9b3f0143144a408989d7aa5d81610fef3b07503f`.
The closed public-document subject SHA-256 was
`9ddb39c04ebcc1c2e9fdb201733dc9dc88ac7d5f76a234e8f00ee97fd2640eb0`.

Only executable Standard and Modern products in that exact catalog were
included. Planned formats were not projected.

## Stage A — offline inventory

Stage A completed with zero network requests and reproduced the immutable
subject exactly. There was no unresolved registered path, unknown available
product, or path escape.

| Measurement | Result |
| --- | ---: |
| Registered documents closed | 47 |
| Card-name field occurrences | 108,651 |
| Distinct English input strings | 1,892 |
| Base Pages artifact, generated overlays excluded | 270,195,353 bytes / 1,936 files |
| Base Pages maximum | 1,073,741,824 bytes |
| Base Pages headroom before generated overlays | 803,546,471 bytes |
| Existing Cache-B subject | 71 unique images |
| Existing Cache-B configured ceiling | 67,108,864 bytes |

The product/format inventory was:

| Product | Format | Occurrences | Unique English names | Eager inline | Expanded inline | Hover/focus | Touch click |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MTGO Landing | Modern | 209 | 119 | 46 | 163 | 209 | 209 |
| MTGO Landing | Standard | 634 | 277 | 90 | 544 | 634 | 634 |
| MTGO statistics | Modern | 32,816 | 1,122 | 0 | 32,816 | 30,022 | 30,022 |
| MTGO statistics | Standard | 14,705 | 865 | 0 | 14,705 | 13,444 | 13,444 |
| MTGO Top 8 | Modern | 31,909 | 766 | 0 | 31,909 | 24,949 | 24,949 |
| MTGO Top 8 | Standard | 16,536 | 548 | 0 | 16,536 | 12,224 | 12,224 |
| Tabletop major events | Modern | 11,842 | 592 | 0 | 11,842 | 11,842 | 11,842 |

Use-class counts overlap by design. A card link in expanded deck detail is also
a hover/focus and touch-click image entry point.

## Stage B — Scryfall printing evidence

The rerun used the official Scryfall `all_cards` Bulk snapshot so canonical
identity, matched English controls, and official Simplified Chinese printings
could be proved from one bounded dataset. Four metadata reads and one snapshot
download occurred. Two local parser boundary corrections were then applied to
the already downloaded immutable snapshot: an Scryfall error-placeholder URL
was treated as a missing image for that printing, and a name-colliding derived
record without `oracle_id` was excluded from canonical identity matching. No
additional snapshot was downloaded.

| Measurement | Result |
| --- | ---: |
| Snapshot type | `all_cards` |
| Snapshot ID | `922288cb-4bef-45e1-bb30-0c2bd3d3534f` |
| Snapshot updated | `2026-08-28T21:17:41.873+00:00` |
| Snapshot bytes | 392,267,935 |
| Snapshot SHA-256 | `e1d54401a2ac27bff43b318f636699f341e0c3e1e486dcddc426c8847e47d059` |
| Scryfall metadata requests | 4 |
| Scryfall Bulk downloads | 1 |
| Input English strings | 1,892 |
| Resolved English strings | 1,869 |
| Resolved canonical `oracle_id + face_index` identities | 1,866 |
| Unresolved English strings retained only as a count/digest | 23 |
| Official Chinese-name identities | 1,193 |
| Official Chinese-image identities | 1,186 |
| Identities requiring bounded MTGCH grouping | 692 |

The raw Bulk snapshot and metadata body were deleted after successful local
processing. The 23 unresolved input strings remain truthful
`english_fallback` cases; their exact values were not retained in the report.

## Stage B — corrected MTGCH grouped inventory

The OpenAPI remained `SBWSZ API` version `1.0.0`. The corrected validator used
the documented `GET /api/v1/set/{set_code}/cards/` summary fields and derived
`official`/`community`/`english_fallback` through provider precedence rather
than demanding an upstream provenance field.

| Measurement | Result |
| --- | ---: |
| OpenAPI documentation reads | 2 |
| Planned grouped requests | 28 |
| Completed grouped requests | 28 |
| Maximum requests in flight | 1 |
| Minimum interval between starts | 5 seconds |
| HTTP 200 responses | 28 |
| HTTP 403 / 429 / 5xx responses | 0 / 0 / 0 |
| Response items processed | 10,939 |
| Raw responses retained | 0 |
| Planned canonical identities | 692 |
| MTGCH community Chinese-name identities | 673 |
| Scryfall-official Chinese-name identities in the queried set | 19 |
| MTGCH community Chinese-image identities | 680 |
| Scryfall-official Chinese-image identities in the queried set | 12 |

Across all 1,866 resolved canonical identities, provider precedence therefore
assigned Chinese names as 1,193 official plus 673 community, and Chinese images
as 1,186 official plus 680 community. No resolved identity required an English
fallback for either value. This does not erase the 23 unresolved original input
strings; those remain aggregate English fallbacks outside the resolved identity
set.

The deterministic image sample reached the declared 100-image ceiling and
covered every eligible stratum:

| Final host | Media type | Source class | Face form | Eligible | Sampled |
| --- | --- | --- | --- | ---: | ---: |
| `images.mtgch.com` | `image/webp` | `community` | Single face | 612 | 90 |
| `images.mtgch.com` | `image/webp` | `community` | Multi face | 68 | 10 |

The grouped-response combined SHA-256 was
`74ebdfe0b9336040eb903efac43b7a2d2ff5f4584bcb6a3a66fa14abafec9073`.

## Stage C — stopped before the first sampled image request

The deployed Pages application opened successfully in a temporary controlled
browser, and the repository's bound controller was confirmed to use one active
image request, a 150-ms minimum start interval, a 15-second attempt timeout,
at most two attempts, and a 1.5-second retry delay.

The exact sample URLs existed only in the external temporary plan, as required.
They were not present in the deployed DOM. The controlled browser interface
could interact with existing elements but could not set an exact external URL
on the deployed controller, execute arbitrary page-world image code, or expose
the required HTTP status/redirect/transfer/cache observations. A harmless
script-URL capability probe was rejected by the browser security boundary,
which expressly prohibited using a raw debugging protocol or another browser
surface as a workaround.

Directly navigating the tab to each image URL would have changed the test into
a top-level image-host navigation. It would not have been a Pages-origin load,
would not have exercised the actual queue or hover/focus/touch shapes, and
would not have supplied valid fallback/cache evidence. The trial therefore
stopped instead of substituting a different data flow.

| Measurement | Result |
| --- | ---: |
| Temporary Pages browser tabs opened / closed | 2 / 2 |
| Sampled MTGCH image attempts | 0 |
| Matched Scryfall control attempts | 0 |
| Sampled fallback attempts | 0 |
| Browser screenshots retained | 0 |
| Per-card browser request logs retained | 0 |
| Six-hour session clock started | No |

This result contains no evidence about MTGCH image HTTP status, redirects,
decode success, latency, transfer bytes, caching, controller pacing under the
sample, or English-fallback completion. It must not be described as one image
request failing or as MTGCH being unavailable.

## Evidence-quality gates

| Gate | Result |
| --- | --- |
| Catalog-rooted current consumer closure | Pass |
| Canonical identity/source inventory | Pass for 1,866 resolved identities; 23 original strings remain explicit English fallbacks |
| Every eligible source/host/media/face stratum plus 100 or full smaller sample | Pass at sample-planning boundary: 100 selected across both strata |
| Two Pages-origin browser sessions at least six hours apart | Fail: first session could not start under the approved browser capability |
| Architecture eligibility criteria | Not evaluable |

The evidence package is therefore incomplete under DEC-140. Stage A and Stage
B are valid measurements for the frozen subject, but neither direct delivery
nor a local cache ceiling can be accepted or rejected without the required
image observations.

## Retention and integrity

The raw Scryfall snapshot, Scryfall metadata body, MTGCH responses, complete
input-name list, complete identity plan, exact sample identity/URL plan, image
bytes, screenshots, browser tab, and per-card request log were deleted or
closed at trial stop. The exact sample plan had SHA-256
`eba8d98de1759ef23ef4d4f636ffa9452b78775e17fc877ba86c9e013fd38fec`
before deletion; only that digest and aggregate stratum counts remain.

No repository product, Schema, workflow, Pages path, generated data,
classifier, or front-end file changed. The retained aggregate evidence digests
are:

- Stage A aggregate:
  `08cd8caae7248d397462da17c3a565d4c5170b2b00d7e677dd1478b601cfc758`;
- Scryfall aggregate:
  `1dd782fb88f6c7e734361bae09baf587748bd72b6578571f1865dc7a56f0a1f5`;
- MTGCH aggregate:
  `41fa9729c97e6dee4b705a2c927c5938abe84ad7e09b3da9301f62a44729856a`;
- pre-MTGCH grouped request plan:
  `9f00fdeb11579cdd79e7049d034c1a5b9e292798c61189454509d9a1a6d9c33f`.

## Required next gate

Do not open `L10N-ARCHITECTURE-DECISION`. Owner acceptance authorizes completion
publication of this exact corrected aggregate report only.

After that report is accepted and published, define a separate
`L10N-STAGE-C-EXECUTION-CONTRACT` before another image request. That contract
must name an approved execution environment that can consume the frozen exact
sample from the deployed Pages origin, exercise the actual controller event
shapes, and collect the declared status/redirect/byte/latency/cache metrics
without bypassing the in-app browser's security boundary. It must also restore
or regenerate the sample deterministically, preserve the existing 400-plus-400
global budgets, and repeat the two sessions at least six hours apart.

The recommended model for that contract is `gpt-5.6-sol` with high reasoning.
This report does not authorize the new contract, its execution, an architecture
decision, implementation, Pages, production, `L10N-B1`, `L10N-B2`, `L10N-C`,
or Phase 14.
