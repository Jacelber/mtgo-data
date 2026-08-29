# Pre-Phase-14 completed roadmap detail

This file preserves the completed localization reset, minimal implementation
contract, acceptance boundary, and retained source evidence. It is historical
and non-authoritative. Current authorization remains solely in
`docs/STATUS.yaml`.

## Problem

Chinese pages showed English card names and used only the English card-image
path. A superseded localization program added a separate identity manifest,
Bulk snapshot handling, source digests, capacity proxies, and three staged
implementation routes without delivering product behavior.

## Accepted route

DEC-146 superseded the separate sidecar and staged mixed-delivery route. The
repository centralizes maintained aliases, front-face spelling, and legacy
single-slash lookup candidates in `card_names.py`; localization and existing
classification consumers reuse those helpers rather than maintain separate
converters.

| Task | Problem | Operation | Effect | Recommended model |
| --- | --- | --- | --- | --- |
| `L10N-RESET` | Unused B1/B2/C artifacts and live planning could be mistaken for the active product route. | Remove the unused builder, Schema, tests, dedicated CI trigger, and staged roadmap; record DEC-146 without changing product behavior. | One clean English baseline remained and the abandoned route no longer granted implied authority. | `gpt-5.6-terra`, medium reasoning |
| `L10N-SIMPLE` | Chinese card names and images were not displayed. | Build one flat English-name-to-MTGCH map through the shared card-name candidates; place only current default-Landing Chinese images in Pages; use MTGCH image URLs elsewhere on Chinese pages; retain the existing Landing cache and Scryfall paths on English pages; select through one browser helper. | Chinese names and images use the smallest production path without another Schema, identity manifest, Bulk snapshot, or staged admission route. | `gpt-5.6-sol`, high reasoning |

## Delivery boundary

The generated `assets/card-localization/cards.json` overlay maps resolved
English product keys to Chinese display names and, when available, trusted
MTGCH Chinese image URLs. Current default-Landing Chinese images are generated
as local Pages files. Other Chinese images load from MTGCH on demand, while
other English images retain Scryfall. A Chinese name without a Chinese image
keeps the Chinese name and falls back only the image to the English source.

The implementation changes no statistics, classifier meaning, event
configuration, generated statistical JSON, dependency, or existing English
Landing cache contract. It retains no raw MTGCH response corpus.

## Acceptance

The Owner accepted the local browser subject on 2026-08-29. The reviewed scope
covered Chinese current-Landing names and local images, on-demand MTGCH images
in MTGO and Tabletop deck details, preserved English behavior, and the
Chinese-name-only Scryfall image fallback demonstrated by `Battlefield
Improvisation` (`战场急创`).

The accepted MTGCH permission record and DEC-137 through DEC-144 observations
remain historical evidence. No availability, latency, cache, image-size, Bulk,
or name-conversion experiment is required again for this completed route.
Phase 14 remains separately unauthorized.
