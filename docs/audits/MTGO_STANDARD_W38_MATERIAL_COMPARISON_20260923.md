# Standard W38 retained material comparison (2026-09-23)

The scheduled MTGO update [35872070812](https://github.com/Jacelber/mtgo-data/actions/runs/35872070812)
stopped while building the Standard Landing. The accepted content submission
(`51cb7380af7615e68afc6c2c7fd9a096b677766a6a4e08650f8613fe3241dd90`)
binds classifier `c34f8b60...`; the later published page binds `7d901cce...`.
The old submission has no `material_digest`, so the shared comparison correctly
returns `evidence_required`. This record supplies the missing investigation;
it does not replace or redate the Owner's submission, decisions or completion.

## Independent comparison

- The accepted Standard preview source at `0aada431bb82e0d99350e76c23ac616ec70e5a3e`
  reproduced `machine_fact_digest=ba8e72fd...` with the historical generator.
  Applying the current material projection to those captured facts (all fact
  fields and the five observations, excluding only `classifier`) gives
  `377351ea0714cfddb64ebbad69372a5f05765f0858c2817eb48cd31534fe2e83`.
- The current generator at `c072cbbd13aa800cb638b4882bca8ec08400fc90`
  gives the same material digest. Its submitted content dimensions, source
  event IDs, selection policy and Top 8 link catalog match the accepted packet.
  Only `classifier_digest` and its dependent `machine_fact_digest` differ.
- The accepted Web review contains 247 complete Standard W38 records. Running
  the current generator on the same eight events returns 247 records, the same
  membership and identical producer fields and complete deck material in each
  row. Both normalized retained-material digests are
  `dcae9d5956b226660fa2307488969a99410b85f2c739f01f965c54fe908f9795`.
- Comparing the accepted final-preview `landing/current.json` to the published
  `landing/current.json` finds identical environment, populations, Feature and
  bilingual summary. The only differing top-level fields are `classifier` and
  `review_binding`, whose differences are those two technical digests.
- Between the accepted preview and the final #434 commit, the classifier
  engine version changed from `1.0.0` to `1.1.0` and canonical basic-land
  feature lookup was added. The Standard rules file did not change in that
  interval. The Owner's prior Azorius Prepare correction was already present
  in the accepted preview and its full-classification decision.

The historical source is the accepted W38 private preview and full review
retained in the active task, with matching submission/decision identifiers in
`stats/standard/mtgo/landing/review/2026-W38.yaml`. The repository's old and
current commits provide independent code and published-page evidence. No
unseen business difference was found in the compared W38 scope; later events
remain subject to their separate data-admission rules.

## Operational handling

The old packet is intentionally unchanged. A daily build that cannot prove a
submitted review against current material now reports the exact comparison
state and preserves the previously admitted Landing, subject to the existing
retained-bundle inspection. It still builds and validates data independently.
This fallback does not declare the old packet equivalent or approve new
Landing content. A future content update needs its own valid submission.

The failed run's `mtgo-fetch-candidate` was saved locally with both SHA256SUMS
entries verified before its one-day artifact expiry. This is the input for
resuming that run's production update; no new fetch is needed.
