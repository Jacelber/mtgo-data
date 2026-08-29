# Card Localization Architecture Evidence Trial — 2026-08-29

Status: `Corrective report accepted by Owner; publication authorized`

## Outcome

The trial stopped during Stage B after the first MTGCH set-grouped card
metadata request. That request returned HTTP 200. The local validator then
required a synthetic full-card field set—including fields it intended to use
as upstream provenance—and reported `card_schema_contract_drift` when the
documented card-description response did not contain that set.

That stop code was wrong. MTGCH has no unified field that must classify every
Chinese name or image as official or community. The project derives the class:
Scryfall proves official Simplified Chinese material; absent that proof, an
exact-identity Chinese value supplied by MTGCH is `community` under the Owner-
recorded project permission; absent both, use `english_fallback`. The observed
response is therefore evidence of a validator/contract-design error, not an
MTGCH response failure.

No MTGCH image, Scryfall control image, browser trial, warm-cache repeat, or
fallback image was requested. The result is an invalid local validation design,
not a grouped-source or image-delivery failure. It selects no local-only,
direct, mixed, or English-only architecture.

## Frozen subject

The trial ran from repository commit
`89ea7400a60f437b2e2c45cf1c45e837c0ef19e7`, the merge commit that published
DEC-140 and the accepted evidence contract. The catalog snapshot was
`stats/catalog.json` with SHA-256
`7e10b719368bc9b46158214b9b3f0143144a408989d7aa5d81610fef3b07503f`.
The closed public-document subject SHA-256 was
`9ddb39c04ebcc1c2e9fdb201733dc9dc88ac7d5f76a234e8f00ee97fd2640eb0`.

Only executable Standard and Modern products in that exact catalog were
included. Planned formats were not projected.

## Stage A — offline inventory

Stage A completed with zero network requests and no unresolved registered
path, unknown available product, or path escape.

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

Use-class counts overlap by design. For example, a card link in expanded deck
detail is both expanded inline text and a hover/focus plus touch-click image
entry point.

## Stage B — Scryfall identity preparation

The current Scryfall Oracle Cards JSONL Bulk contract differed from the older
single-JSON contract: its metadata exposed `jsonl_download_uri` and
`compressed_size`. Seven small Bulk-metadata reads occurred: three diagnosed
that contract change, and four were redundant setup retries while the local
parser was corrected for JSONL, multiple printings, and pure-digital identity
collisions. One 24,532,450-byte JSONL snapshot was downloaded once, reused
locally during those parser corrections, streamed, hashed, and deleted.

| Measurement | Result |
| --- | ---: |
| Snapshot ID | `27bf3214-1271-490b-bdfe-c0be6c23d02e` |
| Snapshot updated | `2026-08-28T21:01:53.804+00:00` |
| Snapshot SHA-256 | `4abcf05c19926129e10620fe2d7e8e51c786aa051a157a66e82a4679174a0395` |
| Scryfall metadata requests | 7 |
| Scryfall Bulk downloads | 1 |
| Input English strings | 1,892 |
| Resolved English strings | 1,869 |
| Resolved canonical `oracle_id + face_index` identities | 1,866 |
| Unresolved English strings | 23 |
| Relevant printing set groups | 154 |

The resolver had to distinguish multiple printings of one oracle identity and
exclude pure-digital identity collisions from the MTGO/Tabletop subject. The
23 unresolved strings remain aggregate coverage gaps; their exact names were
not retained in the trial files or report.

A deterministic greedy maximum-coverage plan selected 32 set groups, the
contract ceiling, covering 1,365 canonical identities. The aggregate request
plan was written before the first MTGCH card-data request. It declared one
request in flight and at least five seconds between starts.

## Stage B — invalid local validator stop

The public OpenAPI remained `SBWSZ API` version `1.0.0` and declared
`GET /api/v1/set/{set_code}/cards/` with a
`PaginatedCardDescriptionResponse`. The trial made one card-metadata request:

| Measurement | Result |
| --- | --- |
| Request number | 1 of at most 32 |
| Concurrency | 1 |
| HTTP result | 200 |
| Retried | No |
| Reported stop code | `card_schema_contract_drift` |
| Correct classification | `validator_contract_design_error` |
| Raw response retained | No |
| Full temporary subject/name/identity plan retained | No |
| Exact eligible image URLs selected | 0 |

The response was not proven unusable. The validator required every item to
contain `id`, `oracle_id`, set/collector identity, English and Chinese image
maps, Chinese-language/name properties, and atomic official/translated-name
properties. That combined set was a local invention rather than the documented
contract of the card-description endpoint.

The validator should instead obtain official Simplified Chinese proof from a
suitable Scryfall printing dataset, accept only documented MTGCH response
properties, bind any returned Chinese value to the exact canonical identity,
and derive the sidecar class by provider precedence. Because the raw response
was deleted as required, this run cannot retroactively determine whether the
documented summary already carried enough identity and image information for
the corrected test. That must be measured only in a separately authorized
rerun after the corrected contract is accepted and published.

## Stage C — not started

Stage C required a correctly classified deterministic sample from Stage B.
Because the invalid validator stopped before selecting any exact image URL, no
browser session was opened
and the six-hour separation clock did not start. Consequently, the trial
contains no evidence about MTGCH image HTTP status, redirects, decode success,
latency, transfer bytes, browser caching, controller pacing, or English
fallback completion.

## Evidence-quality gates

| Gate | Result |
| --- | --- |
| Catalog-rooted current consumer closure | Pass |
| Canonical identity/source inventory | Incomplete: 23 unresolved input strings; MTGCH classification invalidated by local validator design |
| Every source/host/media/face stratum plus 100 or full smaller sample | Not reached |
| Two Pages-origin browser sessions at least six hours apart | Not reached |
| Architecture eligibility criteria | Not evaluable |

The evidence package is therefore incomplete under DEC-140, but not because
MTGCH was shown to lack fields or fail. The measured
Pages base size is valid, but it cannot derive a Chinese-image cache ceiling
without image count, byte distribution, content-digest duplication, and
eager/on-demand coverage. Direct delivery likewise cannot be accepted or
rejected without an image trial.

## Retention and integrity

Only aggregate external evidence and task-local diagnostic scripts remained at
trial close. The Scryfall raw snapshot, MTGCH raw response, complete input-name
list, complete identity plan, image bytes, browser profile, screenshots, and
per-card request log were absent from the trial directory. No repository
product, Schema, workflow, Pages path, generated data, classifier, or front-end
file changed.

The retained aggregate evidence digests are:

- Stage A aggregate:
  `f0becd016f3f3262f10bb170c49381d3133487e37bff3c14e828bb93d0e5a482`;
- Scryfall aggregate:
  `c77e3fea744b09cd8923992ac5ab31c3074d7590003b5ba1d89ec2fb8c23c52d`;
- pre-MTGCH aggregate request plan:
  `dd1704461b75a5f16c808b4ddc3cf3badfd0a623afb3c5d3cb4f46bcf4a47db5`.

## Required next gate

Do not open `L10N-ARCHITECTURE-DECISION`. First accept and publish the corrected
classification and evidence contract. A later separately authorized rerun must
use Scryfall printing-level evidence for the official class and validate the
MTGCH grouped endpoint only against its documented response. If that response
does not contain enough identity or Chinese-value information to build a sample,
the rerun must stop on that specific measured gap and return for a separately
reviewed bounded retrieval design; it must not resurrect a nonexistent MTGCH
provenance-field requirement or silently return to per-name `/result` searches.

Owner acceptance may authorize publication of this corrected documentation
subject only. It does not authorize another source request, a rerun, an
architecture decision, implementation, Pages, production, `L10N-B1`,
`L10N-B2`, `L10N-C`, or Phase 14.
