# Card Localization Rights Review — 2026-08-29

Correction status: `Accepted by Owner; publication authorized`

## Purpose and authority

This review defines the `L10N-RIGHTS` operational gate for the planned card-
localization sidecar. It determines which source classes the repository may
admit in a later, separately authorized `L10N-B` task. It is a conservative
project policy, not legal advice. The Owner or a qualified rights review remains
authoritative and may narrow this boundary.

This task inspected public documentation and interface metadata only. It did
not call a card-data endpoint, download a card image, retain an MTGCH or
Scryfall response corpus, or change a public artifact.

## Evidence snapshot

The following pages were reviewed on 2026-08-29:

| Source | Evidence | Operational significance |
| --- | --- | --- |
| [MTGCH home page](https://mtgch.com/) | MTGCH states that the site operates under the Wizards Fan Content Policy and that, unless otherwise noted, its Magic images and data come from Scryfall and remain copyrighted by Wizards. | Provenance and copyright notices are present, but the notice is not a redistribution license from MTGCH. |
| [MTGCH API documentation](https://mtgch.com/api/v1/docs) and [OpenAPI document](https://mtgch.com/api/v1/openapi.json) | The public OpenAPI document identifies `SBWSZ API` version `1.0.0` and documents card-description, Chinese-name, and Chinese-image properties across different Schemas. It does not define one mandatory per-card field that classifies every returned Chinese value as official or community. Its top-level `termsOfService` and `license` values are absent. | The project must not invent an MTGCH provenance-field requirement. Official status is proved independently through Scryfall; otherwise an exact-identity Chinese value supplied by MTGCH is treated as MTGCH community content under the Owner-recorded project permission. API readability alone still does not establish a public redistribution license. |
| Owner attestation recorded 2026-08-29 | The project Owner states that they know the MTGCH founder and already have the founder's permission for this project's planned use of MTGCH community-localized names and rendered card images. The permission is personal and is not represented as a public MTGCH license or transferable precedent. | Under this repository's authority order, the Owner accepts the project-specific source permission. The sidecar may admit identifiable MTGCH community-rendered images under the bounded conditions below; unknown third-party material still fails closed. |
| [`HeliumOctahelide/magic-cards-zhs`](https://github.com/HeliumOctahelide/magic-cards-zhs) at commit [`ca1cc2d3d6fa970b6985027783682a3556c41339`](https://github.com/HeliumOctahelide/magic-cards-zhs/commit/ca1cc2d3d6fa970b6985027783682a3556c41339) | The README says English text comes from Scryfall and Chinese translations combine official text, MTGso translations, and volunteer translations. The repository declares CC BY-SA 4.0. | Community translation material has a reusable license subject to attribution, change indication, and ShareAlike. The license grants only rights the licensor can grant and does not replace Wizards' rights. |
| [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Sharing requires appropriate credit, a license link, and change indication. Adapted material must use the same license. The license warns that other rights may still restrict use. | A derived community-name dataset must carry source, license, snapshot, and modification notices, and its translation material must remain CC BY-SA 4.0. |
| [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy) | Free fan sites may use Wizards material when they remain unofficial, preserve legal notices, and follow the required disclaimer. The policy distinguishes fan creation from verbatim copying, reposting, and counterfeit or proxy cards. | The product must remain free, unofficial, additive, and correctly attributed. This policy does not validate an unrelated community renderer's separate rights. |
| [Scryfall API documentation](https://scryfall.com/docs/api) and [card imagery documentation](https://scryfall.com/docs/api/images) | Scryfall provides card data and images for additional Magic software, research, and community content. It prohibits paywalling, false endorsement, simple repackaging or proxying, and image alterations such as cropping legal notices, distortion, filtering, or added marks. | A bounded analytics sidecar may use an original Scryfall full-card image as an additive product resource. It must not become a mirror or transform the image. |
| [Scryfall API access guidance](https://scryfall.com/docs/faqs/i-m-having-trouble-accessing-the-scryfall-api-or-i-m-blocked-17) | Scryfall requires well-formed HTTPS requests with relevant `User-Agent` and `Accept` headers, keeps API traffic under 10 requests per second, and directs large workloads to bulk data. | A later build must use one bounded batch, cache/process locally, and avoid per-card browser traffic or redundant API searches. |

No dedicated public MTGCH redistribution terms or image license were found in
the reviewed home page, API documentation, OpenAPI metadata, or linked
translation-data repository. Public documentation alone therefore does not
grant redistribution permission. For this project only, the Owner's recorded
attestation supplies the source-specific permission decision; it must not be
presented as a general MTGCH license.

## Material and operation decision

| Material or operation | Decision | Required conditions |
| --- | --- | --- |
| Read MTGCH public documentation and OpenAPI metadata | Permitted | Read-only, bounded, no authentication, no private endpoint, and no retained card-response corpus. |
| Read a bounded MTGCH card-data snapshot during `L10N-B` | Conditionally permitted | Separate `L10N-B` authorization; build-time only; exact subject; declared headers and rate limit; external temporary storage; response digest and retrieval time recorded; no raw response in Git, Pages, or retained workflow artifacts. |
| Official Simplified Chinese card names | Conditionally permitted | Scryfall must prove an official Simplified Chinese printing for the exact canonical card or face; do not infer official status from an MTGCH field or from the presence of Chinese text. Publish only the bounded display fields needed by the product, with Wizards/Scryfall notices and no claim of endorsement. |
| Community Simplified Chinese card names | Conditionally permitted | If Scryfall does not prove an official Simplified Chinese name and MTGCH supplies a Chinese name bound to the exact canonical card or face, classify it in the project sidecar as `community` under the Owner-recorded founder permission. A separately used CC BY-SA 4.0 dataset retains its own source, snapshot, license, modification, and ShareAlike conditions. |
| Original official Simplified Chinese full-card image supplied through Scryfall | Conditionally permitted | The printing identity and official `zhs` image must be proven from Scryfall; retain only the exact bounded product subject; preserve the original bytes and all copyright and artist notices; do not crop, filter, watermark, recolor, distort, or imply endorsement; keep the product free and additive. |
| MTGCH-supplied community-rendered Chinese full-card image | Conditionally permitted | When Scryfall does not prove and supply an official Simplified Chinese image for the exact identity, an exact-identity Chinese image supplied through the approved MTGCH interface is project-classified as `community`. Rely on the Owner-recorded founder permission only for this free, unofficial, additive project. Preserve the original MTGCH bytes, MTGCH attribution, retrieval snapshot, and all embedded legal and artist notices. Do not present the image as official or as a public-license precedent. |
| User-submitted or third-party Chinese image obtained outside the approved MTGCH interface and not covered by another recorded permission | Prohibited | Fail closed unless a separate reusable grant or Owner decision covers that exact provider and material class. The absence of an MTGCH per-record source field does not turn an MTGCH response into unknown third-party material. |
| Chinese value that cannot be bound to the exact canonical card or face | Prohibited | Fail closed to the existing English name or complete-card image. Provider precedence can derive `official` versus `community`, but it cannot repair an identity mismatch or ambiguous face binding. |
| Format conversion or visual transformation of an admitted official image | Prohibited | Content-address the original bytes. Do not convert, recompress, crop, sharpen, blur, recolor, overlay, or otherwise transform them. |
| Browser call to MTGCH under the current rights-only decision | Not yet authorized | This rights gate alone selects no delivery architecture. Browsers keep the existing English path unless a later evidence-backed architecture decision explicitly admits bounded direct delivery with fallback. |
| Raw MTGCH or Scryfall card response in Git, Pages, or retained workflow output | Prohibited | Publish only the validated bounded sidecar fields and admitted image bytes required by the product. |

## Attribution contract for a later sidecar

`L10N-B` must make the following notices available from the manifest and the
user-visible product notice before admission:

1. **Wizards disclaimer:** identify the product as unofficial Fan Content, not
   approved or endorsed by Wizards, and state that portions of the materials
   are property of Wizards of the Coast with the applicable copyright notice.
2. **Scryfall source notice:** identify Scryfall as the source of admitted card
   data and official full-card images without implying endorsement; retain the
   existing Scryfall link and image/artist notices.
3. **Community-name notice:** identify
   `HeliumOctahelide/magic-cards-zhs`, link the source and CC BY-SA 4.0, record
   the source snapshot, state that the source mixes official, MTGso, and
   volunteer translations, and state that the product filters and projects a
   bounded subset.
4. **MTGCH community-image notice:** identify MTGCH as the immediate source,
   state that the image is an unofficial community localization used under
   project-specific permission confirmed by the Owner, and retain the source
   and retrieval snapshot without implying that MTGCH publishes a general
   redistribution license.
5. **Project-derived per-record classification:** keep `official`, `community`,
   and `english_fallback` distinct in the sidecar. This classification is not
   asserted to be an MTGCH source field. Official records retain the Scryfall
   printing evidence; MTGCH community records retain MTGCH as their immediate
   provider and the project-specific permission notice. No notice may relabel
   community material as official.
6. **License isolation:** CC BY-SA applies to the derived community translation
   material, not to project-authored code, statistics, or third-party Wizards
   images. The notice must not claim a broader license than the source can
   grant.

## `L10N-B` admission conditions

A later `L10N-B` task may be proposed only with a separate authorization. Its
task contract must enforce all of the following:

- use the accepted `L10N-A` identity and manifest contract;
- fetch only the exact bounded current product subject into an external
  temporary directory;
- classify a name and image independently;
- accept an exact-identity MTGCH Chinese name as `community` under the
  Owner-recorded founder permission when Scryfall does not prove an official
  Simplified Chinese name; apply the CC BY-SA attribution contract only when
  the separately licensed translation dataset is actually used;
- accept an official image only when Scryfall proves an official Simplified
  Chinese printing and provides the original full-card image;
- accept an exact-identity MTGCH Chinese image as `community` under the
  Owner-recorded founder permission when Scryfall does not prove and supply an
  official Simplified Chinese image, and preserve the exact MTGCH bytes,
  retrieval snapshot, and attribution;
- reject every identity-ambiguous, non-MTGCH third-party, unpermitted, or
  further-modified image;
- retain no raw upstream response and no image outside the closed admitted
  bundle;
- validate identities, source snapshot, source-specific byte digests, declared
  files, attribution, and zero identity-ambiguous or unpermitted image bytes before
  public admission; and
- preserve exact English fallback for every unresolved or missing record.

The rights gate does not authorize `L10N-B`, `L10N-C`, a source fetch, a public
artifact, Pages, production, or Phase 14.

## Permission boundary and reassessment

The Owner-recorded permission is accepted as a project-specific decision, not
as a public or transferable MTGCH license. If the Owner withdraws that
attestation, MTGCH changes ownership or source policy, the material is no
longer supplied through the approved MTGCH boundary, or a rights holder
requests removal, admission must stop and the affected records must fall back
to the existing English name or image. A working URL, a new API field, or
unrelated third-party reuse never expands this permission.
