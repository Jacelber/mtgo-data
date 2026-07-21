# Notices and licensing scope

## Project-authored material

Copyright (c) 2026 Jacelber and project contributors.

Software code in this repository is available under the MIT License in [`LICENSE`](LICENSE).

Project-authored documentation and archetype classification rules are available under the [Creative Commons Attribution 4.0 International license](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0). When reusing that material, provide appropriate credit, link to the license, and indicate whether changes were made.

The CC BY 4.0 grant applies only to original documentation and classification-rule authorship contributed to this project. It does not apply to third-party data or intellectual property described below.

## Third-party classification definitions

The Modern classification definitions in `my_archetypes/modern.yaml` are adapted from Joan G.E., [`j6e/mtg-meta-analyzer`](https://github.com/j6e/mtg-meta-analyzer), file `data/archetypes/modern.yaml` at commit `0ecd26bd734cedc6c40e7c753115f796613a32ba`. The source classification content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

This project changed the source material by converting it to the shared versioned rule schema, adding stable archetype and rule IDs, encoding the source selection behavior as explicit priorities, declaring mainboard-only card zones, retaining unmatched decks as explicit Unknown results, and omitting the source corpus-dependent centroid fallback. Detailed provenance and compatibility evidence are recorded in `docs/audits/P6-01.md` and DEC-039.

## Tournament and source data

This repository contains or derives information from third-party tournament sources, including Magic Online tournament results and, in planned product areas, selected Melee event records. It may include tournament metadata, standings, match results, decklists, player or account identifiers published by a source, and derived aggregate statistics.

The project does not claim ownership of underlying third-party tournament records and does not relicense them under the MIT or CC BY 4.0 licenses. Use of source data remains subject to applicable law and the source provider's terms, policies, and rights. Downstream users are responsible for determining whether their use of third-party data is permitted.

Source provenance and data-quality metadata should be preserved where the relevant generated format supports them. Removal of provenance does not expand the rights granted for source data.

The OM1-to-SPM card-name alias artifact in `src/mtgmeta/data/om1_spm_aliases.json` is derived from the [MTGJSON OM1 dataset](https://mtgjson.com/api/v5/OM1.json). MTGJSON is distributed under the [MIT License](https://github.com/mtgjson/mtgjson/blob/main/LICENSE). The artifact records its source version and retrieval date. This attribution does not relicense Magic card names or other Wizards of the Coast materials.

## Magic: The Gathering materials

Magic: The Gathering, Magic Online, MTGO, card names, card text, artwork, set symbols, and related marks and materials are property of their respective rights holders. Wizards of the Coast is not affiliated with or endorsing this project.

Melee and other source names or marks are property of their respective rights holders. Their appearance identifies a data source and does not imply affiliation or endorsement.

No license is granted by this repository to third-party trademarks, artwork, card content, website content, or other third-party intellectual property.

## No warranty

Generated statistics and classifications may contain omissions, source errors, ambiguous results, incomplete decklists, or classification mistakes. They are provided for research and informational purposes without warranty. The software warranty disclaimer is stated in [`LICENSE`](LICENSE).
