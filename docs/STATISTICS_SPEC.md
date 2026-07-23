# Statistics Specification

## 1. Document purpose

This document defines the authoritative statistical rules for the `mtgo-data` project.

It applies to:

- MTGO Environment Trends;
- Tabletop Major Events sourced from approved Melee tournaments;
- shared statistical utilities;
- generated statistics JSON;
- front-end labels, tooltips, warnings, and quality reports;
- automated tests for statistical behavior.

Do not change a statistical formula only in implementation code.

Any intentional formula change must also update:

- this document;
- affected tests;
- affected JSON Schemas;
- `DECISIONS.md`;
- generated-data version information when compatibility is affected.

---

## 2. General principles

### 2.1 Constructed focus

The project measures Constructed deck performance.

For mixed Draft and Constructed events:

- Draft rounds are excluded from Constructed deck statistics;
- Draft points are excluded from Constructed average-point calculations;
- Draft matches are excluded from Constructed win rates;
- Draft matches are excluded from Constructed matchup matrices;
- overall standings points must not be used as Constructed deck points.

Limited results may be retained as source or contextual data when needed to verify event phases, advancement, or final standings.

### 2.2 Source separation

MTGO and tabletop data must not be combined into one statistic.

Do not combine them for:

- metagame share;
- high-score share;
- conversion;
- average points;
- win rate;
- matchup matrices;
- representative decklists.

Shared formulas may be implemented in common utility code, but their inputs and outputs must preserve the source identity.

### 2.3 Reconstruct from round-level data

For tabletop events, performance statistics should be reconstructed from round-level results whenever possible.

Final standings totals alone are not sufficient because they may include:

- Draft points;
- byes;
- intentional draws;
- awarded wins;
- playoff results;
- penalties;
- unplayed rounds;
- corrections not visible in deck records.

The normalized event data must preserve enough information to explain how each statistic was calculated.

### 2.4 Missing is not zero

Use `null` or an explicit unavailable state when a metric cannot be calculated reliably.

Do not display missing data as zero.

Examples:

- unknown Day 2 cut;
- unavailable round classification;
- missing decklist;
- unverified awarded win;
- unavailable theoretical round count;
- no valid matches.

### 2.5 No silent anomaly removal

Excluded or unresolved records must appear in a quality report.

Examples include:

- unknown round types;
- missing opponents;
- duplicate players;
- incomplete decklists;
- conflicting standings;
- unrecognized match results;
- suspected no-shows;
- suspected awarded wins;
- source totals that do not reconcile.

---

## 3. Core terminology

### 3.1 Deck

A deck is a valid Constructed decklist associated with one tournament player or one MTGO event result.

A deck without a reliable archetype match is classified as `Unknown`.

A missing or unusable decklist is not automatically the same as an `Unknown` archetype. The normalized data must distinguish:

- valid deck classified as a known archetype;
- valid deck classified as `Unknown`;
- missing decklist;
- invalid decklist;
- excluded player.

### 3.2 Archetype

An archetype is identified by a stable machine-readable archetype ID.

Display names may change without changing the archetype ID.

Statistics must aggregate by archetype ID rather than only by display name.

A classification result may also contain an optional subtype ID and subtype display name. A subtype is a rule-level variant within one parent archetype. Primary metagame, performance, and conversion statistics continue to aggregate by the parent archetype ID. Hierarchical matchup statistics are separately defined in section 11.8. Subtypes must not split or double-count the parent archetype population.

The Phase 2 compatibility migration may expose subtypes only for distinct legacy rule entries that already resolve to the same legacy archetype. It must not change any deck's parent archetype result. New subtype taxonomy and subtype-level statistical presentation require separate approval after the compatibility classifier is complete.

### 3.3 Theoretical round

A theoretical round is a scheduled Constructed Swiss round that a player was expected or eligible to play for the metric’s population.

Theoretical rounds are used to prevent early drops from inflating average points per round.

An unplayed theoretical round caused by an ordinary drop contributes:

- zero points to the numerator;
- one theoretical round to the denominator;
- no match to the win-rate or matchup denominator.

A player who did not qualify for Day 2 is not assigned Day 2 theoretical rounds.

### 3.4 Effective theoretical round

An effective theoretical round is a theoretical round after removing a round from which the player was officially exempt.

The main approved exemption is an official Top 8 lock procedure where a player stops playing and receives an administrative or awarded result.

Do not treat an ordinary drop as an exemption.

### 3.5 Played match

A played match is a real Constructed match with a recognized competitive result.

It does not include:

- bye;
- no-show;
- unplayed drop round;
- administrative result;
- Top 8 lock awarded win;
- unknown result;
- playoff result when calculating primary Swiss statistics;
- intentional draw reported as `0-0-3`.
- a match involving a participant whose event status is `disqualified`.

### 3.6 Match draw

A normal played match draw is a real match that ended drawn, such as a timed match ending with an appropriate game record.

A `0-0-3` intentional draw is treated separately and is not a played match for win-rate or matchup purposes.

---

## 4. Event structures

Every tabletop event must use one of the following structures.

### 4.1 `constructed_day2`

A pure Constructed event with a separate Day 2 field.

Primary scopes:

- Day 1 Constructed;
- Day 2 Constructed;
- Combined Constructed Swiss.

This mode may report Day 2 participation and conversion because advancement is based on the same Constructed competition, subject to event-specific rules.

### 4.2 `constructed_single_stage`

A pure Constructed event without a separate Day 2 field.

Primary scope:

- all Constructed Swiss rounds.

This mode uses a high-score region when an appropriate high-performing population is needed.

### 4.3 `mixed`

An event containing both Draft and Constructed phases.

Examples include Pro Tours and World Championships.

Primary scopes:

- Day 1 Constructed;
- Day 2 Constructed;
- all Constructed Swiss rounds.

For this mode:

- Draft is excluded from deck-performance calculations;
- overall standings score is not a Constructed score;
- overall Day 2 qualification is not a pure deck-performance conversion;
- Day 2 Constructed statistics describe a field selected partly by Draft performance;
- selection-bias warnings are mandatory.

---

## 5. Round classification

Each tabletop round must be assigned a normalized phase. Event stage, round phase, and actual game format are separate dimensions and must not be collapsed into one field.

Allowed primary values are:

- `draft`;
- `constructed`;
- `playoff`;
- `unknown`.

Every round should retain a stage designation when known:

- `day1`;
- `day2`;
- `playoff`;
- `other`.

Every round should also retain its actual game format, such as `limited`, `modern`, or `unknown`. This is necessary when a playoff uses a different format from the event's Constructed Swiss rounds. For example, a Draft Top 8 has stage `playoff`, phase `playoff`, and game format `limited`.

A normalized round should contain or allow derivation of:

- round ID;
- source round name;
- source round number;
- normalized round number;
- stage;
- phase;
- actual game format;
- whether it is Swiss;
- whether it is playoff;
- whether it counts toward each statistical scope.

An `unknown` round must not be included in primary Constructed statistics until reviewed or explicitly configured.

Round assignments should be verifiable through event configuration, official event information, and collected source data.

---

## 6. Result-type handling

Every normalized player-round result must have an explicit result type.

Recommended normalized values include:

- `played_win`;
- `played_loss`;
- `played_draw`;
- `intentional_draw`;
- `bye`;
- `no_show`;
- `drop_unplayed`;
- `awarded_win_top8_lock`;
- `administrative_result`;
- `unknown`;
- `draft_result`;
- `playoff_result`.

Result normalization must use explicit source evidence for each competitor. The
order of competitors in a source array is not evidence of winner or loser. A
played result is valid only when two identified competitors have a consistent
win/loss or draw/draw pair and compatible match points. Ambiguous records remain
`unknown` and are excluded.

Event-specific corrections must be stored as reviewed configuration with the
source match ID, complete competitor identities and results, a reason, and
reviewable source URLs. In particular, `awarded_win_top8_lock` must not be
inferred from rank, late-round timing, or an apparent win alone.

### 6.1 Handling matrix

| Result type | Constructed points | Win-rate denominator | Matchup matrix | Theoretical round | Notes |
|---|---:|---:|---:|---:|---|
| Played win | 3 | Yes | Yes | Yes | Real Constructed match |
| Played loss | 0 | Yes | Yes | Yes | Real Constructed match |
| Played draw | 1 | Yes | Yes | Yes | Counts as 0.5 win |
| Intentional draw `0-0-3` | 1 | No | No | Yes | Retain separately |
| Bye | 3 | No | No | Yes | No real opponent |
| No-show | 0 | No | No | Conditional | Must be reviewed |
| Drop/unplayed round | 0 | No | No | Yes | Prevents drop inflation |
| Top 8 lock awarded win | 0 | No | No | No, if verified exemption | Retain original source value |
| Other administrative result | Conditional | No by default | No | Conditional | Requires event-specific review |
| Unknown result | No | No | No | Conditional | Must appear in quality report |
| Draft result | No | No | No | No | Excluded from Constructed stats |
| Playoff result | No for primary Swiss metrics | No for primary Swiss win rate | No for primary matrix | No | May be shown separately |

### 6.2 Real wins and losses

Real Constructed wins and losses count toward:

- Constructed points;
- match win rate;
- matchup matrices;
- actual match count;
- theoretical-round completion.

### 6.3 Normal played draws

A normal played draw counts as:

- one Constructed point;
- one played match;
- half a win in match-win-rate calculations;
- a draw in matchup W-L-D records.

### 6.4 Intentional draws reported as `0-0-3`

A result reported as `0-0-3` is treated as an intentional or unplayed draw.

It counts as:

- one point for average-point calculations;
- one theoretical round.

It does not count toward:

- played match count;
- match win rate;
- matchup matrix.

The output must preserve an intentional-draw count so users can understand how many points came from excluded draws.

Do not silently convert `0-0-3` into a normal played draw.

### 6.5 Byes

A verified bye counts as:

- three points for average-point calculations;
- one theoretical round.

It does not count toward:

- played match count;
- match win rate;
- matchup matrix.

Bye counts must be shown in quality or supporting statistics.

### 6.6 No-shows

A no-show is not a valid played match.

A no-show result must be excluded from:

- win rate;
- matchup matrix.

Whether it uses a theoretical round depends on the player’s event participation and the event structure.

Suspected no-shows must be listed in the quality report and must not be silently classified as ordinary played losses.

### 6.7 Drops

When a player drops before completing all scheduled rounds for the relevant scope:

- completed real matches retain their results;
- scheduled but unplayed rounds contribute zero points;
- scheduled but unplayed rounds remain in the theoretical-round denominator;
- unplayed rounds do not count as matches;
- unplayed rounds do not enter the matchup matrix.

This rule is designed to avoid inflating the average score of decks whose players dropped after poor results.

Example:

A player starts a five-round Constructed phase, loses the first two rounds, and drops.

The player contributes:

- 0 Constructed points;
- 5 theoretical Constructed rounds;
- 2 played matches;
- 2 match losses;
- 3 unplayed drop rounds.

The player’s average points per theoretical round is:

`0 / 5 = 0.00`

The player’s played match win rate is:

`0 / 2 = 0.00`

### 6.8 Top 8 lock awarded wins

Some professional events allow a player who has achieved the required number of match wins to stop playing before the end of Swiss rounds.

The source may display an awarded win or another administrative result for a round that was not played.

A result may be normalized as `awarded_win_top8_lock` only when supported by:

- official event rules or fact sheet;
- round-by-round evidence;
- standings evidence;
- event-specific configuration;
- or another reviewable source.

A verified Top 8 lock awarded win:

- contributes zero Constructed points to performance statistics;
- does not count as a played match;
- does not count toward win rate;
- does not enter the matchup matrix;
- does not count as an effective theoretical round;
- must be counted and displayed separately.

The original source result must remain available in raw or normalized metadata.

Do not infer every late-round win by a highly ranked player to be an awarded win.

### 6.9 Playoffs

Quarterfinals, semifinals, and finals are excluded from the primary Swiss statistics.

Reasons include:

- very small sample size;
- different pairing structure;
- elimination incentives;
- insufficient value for the primary archetype matrix.

Playoff results may be shown separately as event context, final placement, or deck detail.

They must not be merged silently into the primary Swiss win rate or matchup matrix.

### 6.10 Disqualified participants

A disqualified participant and their source records must remain in the
normalized archive for provenance, standings reconciliation, and review. Their
status must remain explicitly `disqualified`; do not collapse it into an
ordinary drop.

Every match involving a disqualified participant is excluded as a complete
match unit from:

- played-match win-rate samples;
- archetype matchup matrices;
- primary Constructed match-performance counts.

The opponent side of the same match is also excluded. Removing only one side
would break W-L-D conservation and could retain a result affected by the conduct
that caused the disqualification. Original results, points, rounds, opponents,
decklist, and standings remain available as contextual data. The quality output
must report the disqualified participant and the exclusion without treating a
reviewed disqualification as an unknown or blocking source error.

---

## 7. Average points per theoretical round

### 7.1 Purpose

Average points per theoretical round measures point acquisition while limiting distortion from early drops.

It is a deck-performance metric distinct from played match win rate.

### 7.2 General formula

For archetype \(a\):


\[
APPR_a =
\frac{
\sum \text{included Constructed points for decks in } a
}{
\sum \text{effective theoretical Constructed rounds for decks in } a
}
\]

The valid range is normally:

- minimum: `0.00`;
- maximum: `3.00`.

The numerator may include points from:

- played wins;
- played draws;
- intentional draws;
- byes.

The numerator excludes:

- Draft points;
- playoff points;
- unverified administrative results;
- Top 8 lock awarded wins.

### 7.3 Micro-average requirement

Aggregate average points per round must use the total-points divided by total-rounds micro-average.

Do not calculate the simple average of already-calculated event or player averages when denominators differ.

Correct:


\[
\frac{\sum points}{\sum rounds}
\]

Not generally correct:


\[
\frac{\sum player\_averages}{number\_of\_players}
\]

### 7.4 MTGO average points

The current MTGO baseline infers theoretical Swiss rounds from event player count.

For each MTGO deck:

- use the event’s theoretical Swiss round count;
- use the player’s recorded Swiss score;
- treat unplayed rounds after a drop as zero-point theoretical rounds.

For an archetype across multiple events:


\[
MTGO\ APPR_a =
\frac{
\sum recorded\ Swiss\ points
}{
\sum event\ theoretical\ rounds
}
\]

Existing Standard behavior must be regression-tested before generalization.

### 7.5 Pure Constructed Day 1 average

For a `constructed_day2` event:


\[
Day1\ APPR_a =
\frac{
Day1\ Constructed\ points_a
}{
Day1\ effective\ theoretical\ Constructed\ rounds_a
}
\]

All valid starting decks are included unless explicitly excluded by data-quality rules.

Ordinary Day 1 drops retain all scheduled Day 1 Constructed rounds in the denominator.

### 7.6 Pure Constructed Day 2 average

Only players who actually qualified for or were officially included in Day 2 belong to the Day 2 population.

For archetype \(a\):


\[
Day2\ APPR_a =
\frac{
Day2\ Constructed\ points_a
}{
Day2\ effective\ theoretical\ Constructed\ rounds_a
}
\]

The denominator includes scheduled Day 2 Constructed rounds for each Day 2 participant, except verified Top 8 lock exemptions.

Ordinary Day 2 drops do not reduce the theoretical denominator.

Day 2 average points must be displayed with:

- Day 2 deck count;
- effective theoretical round count;
- played match count;
- completion rate;
- intentional-draw count;
- bye count;
- Top 8 lock count;
- awarded-win count;
- selection-bias notice when applicable.

Day 2 average points alone is not sufficient to describe Day 2 performance.

### 7.7 Mixed-event Day 1 Constructed average

For a `mixed` event, calculate only the Day 1 Constructed phase.

Example structure:

- Draft rounds 1–3;
- Constructed rounds 4–8.

Only rounds 4–8 belong to Day 1 Constructed statistics.

For archetype \(a\):


\[
Mixed\ Day1\ APPR_a =
\frac{
Day1\ Constructed\ points_a
}{
Day1\ effective\ theoretical\ Constructed\ rounds_a
}
\]

Draft points and the overall Day 1 standings total are excluded.

### 7.8 Mixed-event Day 2 Constructed average

For a mixed event, the Day 2 population has been selected using combined Draft and Constructed performance.

The calculation is:


\[
Mixed\ Day2\ APPR_a =
\frac{
Day2\ Constructed\ points_a
}{
Day2\ effective\ theoretical\ Constructed\ rounds_a
}
\]

This metric describes performance within the qualified field.

It must not be described as an unbiased continuation of the initial field.

The front end must display a notice similar to:

> Day 2 participants were selected using combined event performance, including Draft where applicable. Day 2 Constructed statistics describe the qualified field and may reflect player-selection effects.

### 7.9 Combined Constructed average

Combined Constructed average includes eligible Day 1 and Day 2 Constructed rounds.

For each player:

- include Day 1 Constructed theoretical rounds if the player was in the Day 1 field;
- include Day 2 Constructed theoretical rounds only if the player qualified for or officially participated in Day 2;
- remove verified Top 8 lock exemptions;
- do not assign Day 2 rounds to players who failed to qualify.

For archetype \(a\):


\[
Combined\ APPR_a =
\frac{
Day1\ points_a + Day2\ points_a
}{
Day1\ effective\ rounds_a + Day2\ effective\ rounds_a
}
\]

This is a phase-weighted micro-average.

It must be labeled as a combined qualified-field statistic rather than a statistic in which every starting player had the same opportunity to play every round.

---

## 8. High-score region

### 8.1 Purpose

The high-score region identifies decks finishing strictly above half of the maximum possible points for the applicable theoretical-round scope.

It is used when:

- an event has no separate Day 2 cut;
- a Constructed phase within a mixed event needs an independent performance threshold;
- MTGO events use the existing high-score logic;
- Day 1 or Day 2 phase performance requires a high-performing subset.

### 8.2 Threshold formula

For \(R\) theoretical rounds:


\[
HighScoreThreshold(R) =
3 \times \left(\left\lfloor \frac{R}{2} \right\rfloor + 1\right)
\]

This is equivalent to taking a score strictly above half of the maximum available points and rounding upward to an achievable three-point win tier.

Examples:

| Theoretical rounds | Maximum points | High-score threshold |
|---:|---:|---:|
| 3 | 9 | 6 |
| 4 | 12 | 9 |
| 5 | 15 | 9 |
| 6 | 18 | 12 |
| 7 | 21 | 12 |
| 8 | 24 | 15 |
| 9 | 27 | 15 |
| 10 | 30 | 18 |
| 11 | 33 | 18 |
| 12 | 36 | 21 |

This preserves the existing MTGO Standard threshold behavior.

### 8.3 High-score count

For archetype \(a\):


\[
HighScoreCount_a =
\text{number of decks in archetype } a
\text{ meeting the threshold}
\]

### 8.4 High-score share

High-score share measures representation inside the high-score population:


\[
HighScoreShare_a =
\frac{
HighScoreCount_a
}{
TotalHighScoreDecks
}
\]

This answers:

> What proportion of the high-score field is this archetype?

### 8.5 High-score conversion

High-score conversion measures the proportion of an archetype’s starting decks that reached the high-score region:


\[
HighScoreConversion_a =
\frac{
HighScoreCount_a
}{
InitialDeckCount_a
}
\]

This answers:

> What proportion of this archetype reached the high-score region?

High-score share and high-score conversion must not be confused.

### 8.6 MTGO Top 8 conversion

If MTGO outputs retain Top 8 conversion from the high-score field, label it separately:


\[
Top8ConversionFromHighScore_a =
\frac{
Top8Count_a
}{
HighScoreCount_a
}
\]

Do not use the generic field name `conversion` for multiple formulas in new schemas.

Preferred explicit field names are:

- `high_score_conversion`;
- `top8_conversion_from_high_score`;
- `day2_conversion`.

### 8.7 Mixed-event Day 1 high-score metrics

For a mixed event:

- use Day 1 Constructed points only;
- use Day 1 Constructed theoretical rounds only;
- include all valid starting Constructed decks;
- exclude Draft points.

These metrics provide a Constructed-only high-performing subset without using Draft-influenced Day 2 qualification.

### 8.8 Day 2 high-score metrics

Day 2 high-score performance may be reported for Day 2 participants.

Where effective theoretical rounds differ because of verified Top 8 locks, evaluate each player against the threshold for that player’s effective theoretical rounds.

Day 2 outputs should include:

- Day 2 high-score count;
- Day 2 high-score share;
- Day 2 high-score rate.

The Day 2 high-score rate is:


\[
Day2HighScoreRate_a =
\frac{
Day2HighScoreCount_a
}{
Day2DeckCount_a
}
\]

Use `rate` rather than `conversion` because the population already consists of Day 2 participants.

When effective round counts vary substantially, the output must expose the round-count distribution and display a comparability warning.

---

## 9. Day 2 participation metrics

### 9.1 Pure Constructed events

For a pure Constructed event with a documented Day 2 cut, report:

#### Day 2 deck count


\[
Day2Count_a =
\text{number of Day 2 participants using archetype } a
\]

#### Day 2 metagame share


\[
Day2Share_a =
\frac{
Day2Count_a
}{
TotalDay2Decks
}
\]

#### Day 2 conversion


\[
Day2Conversion_a =
\frac{
Day2Count_a
}{
InitialDeckCount_a
}
\]

These metrics may be used as deck-performance indicators because advancement is based on the same Constructed event, while still acknowledging player-skill and pairing effects.

### 9.2 Mixed events

For a mixed event, Day 2 participation is influenced by both Draft and Constructed performance.

Therefore:

- Day 2 count may be shown;
- Day 2 share may be shown as a description of the qualified field;
- Day 2 participation may be shown as background information;
- Day 2 conversion must not be presented as a pure deck-performance metric;
- the primary deck-performance conversion for Day 1 should use the Day 1 Constructed high-score region.

If a raw Day 2 qualification rate is displayed for context, it must be labeled clearly as mixed-performance qualification and accompanied by a Draft-influence warning.

---

## 10. Match win rate

### 10.1 General formula

For valid played matches:


\[
MatchWinRate =
\frac{
Wins + 0.5 \times Draws
}{
Wins + Losses + Draws
}
\]

Exclude:

- byes;
- intentional draws reported as `0-0-3`;
- no-shows;
- drop/unplayed rounds;
- awarded wins;
- administrative results;
- unknown results;
- Draft matches;
- playoffs from the primary Swiss win rate.

### 10.2 Archetype win rate

For archetype \(a\):


\[
WinRate_a =
\frac{
Wins_a + 0.5 \times Draws_a
}{
Wins_a + Losses_a + Draws_a
}
\]

The output must retain:

- wins;
- losses;
- draws;
- valid match count;
- calculated win rate.

Do not store only the final percentage.

### 10.3 Mirror matches

Mirror matches naturally produce an aggregate archetype result near 50% and do not measure performance against the surrounding metagame.

The primary comparative archetype win rate should exclude mirror matches.

Outputs may additionally provide an all-match rate including mirrors for accounting and diagnostics.

Fields should be explicit, for example:

- `non_mirror_record`;
- `non_mirror_win_rate`;
- `all_match_record`;
- `all_match_win_rate`;
- `mirror_match_count`.

The front end should label which rate is displayed.

### 10.4 Day 1 Constructed win rate

Day 1 Constructed win rate uses valid played Constructed matches from Day 1 only.

Advantages:

- reflects the broader initial field;
- reduces Day 2 qualification-selection effects.

Limitations:

- early drops cause non-random missing matches;
- some archetypes may have small samples;
- players who start poorly may contribute fewer actual matches.

Day 1 completion and drop information must be available alongside the rate.

### 10.5 Day 2 Constructed win rate

Day 2 Constructed win rate uses valid played Constructed matches from Day 2 participants only.

It measures performance within the qualified field.

Limitations include:

- qualification selection;
- stronger average player population;
- Draft-influenced selection in mixed events;
- smaller archetype samples;
- Top 8 lock exemptions;
- intentional draws near the end of Swiss.

Day 2 win rate must be displayed with match count and selection-bias context.

### 10.6 All Constructed Swiss win rate

All Constructed Swiss win rate combines valid Day 1 and Day 2 Constructed Swiss matches.

It provides the largest available real-match sample.

It must be calculated from aggregated W-L-D counts:


\[
AllConstructedWinRate =
\frac{
W_{D1} + W_{D2} + 0.5(D_{D1} + D_{D2})
}{
W_{D1} + W_{D2} + L_{D1} + L_{D2} + D_{D1} + D_{D2}
}
\]

Do not average the Day 1 and Day 2 percentages.

### 10.7 Default scope

For mixed-format event pages:

- average-point and high-score headline metrics should distinguish Day 1, Day 2, and Combined;
- the primary matchup and overall win-rate view may default to all Constructed Swiss rounds;
- users must be able to switch to Day 1 only and Day 2 only;
- Day 1 win rate should be visible as a comparison;
- the event configuration may override the default if quality checks justify it.

A default-scope override must be recorded in event configuration and explained in generated metadata.

---

## 11. Matchup matrix

### 11.1 Matrix definition

For a row archetype \(A\) against column archetype \(B\), store the result from archetype \(A\)’s perspective:

- wins by \(A\);
- losses by \(A\);
- draws;
- valid match count;
- match win rate.


\[
MatrixWinRate_{A,B} =
\frac{
Wins_{A,B} + 0.5 \times Draws_{A,B}
}{
Wins_{A,B} + Losses_{A,B} + Draws_{A,B}
}
\]

The inverse cell must reconcile:

- \(Wins_{A,B} = Losses_{B,A}\);
- \(Losses_{A,B} = Wins_{B,A}\);
- draws must match;
- valid match counts must match.

### 11.2 Primary exclusions

The primary matrix excludes:

- mirrors, unless a mirror cell is shown separately;
- byes;
- `0-0-3` intentional draws;
- no-shows;
- unplayed drop rounds;
- awarded wins;
- administrative results;
- unknown result types;
- Draft;
- playoffs.

### 11.3 Unknown archetypes

Matches involving a valid but unclassified deck must remain available for reconciliation and quality reporting.

The front end may hide the `Unknown` row and column by default, but the generated data should preserve them or preserve equivalent accounting information.

A known archetype’s overall record against an Unknown opponent must not be silently attributed to another archetype.

### 11.4 Scope controls

When data is available, the tabletop matrix should support:

- `all_constructed_swiss`;
- `day1_constructed`;
- `day2_constructed`.

Playoff matches may be provided in a separate contextual dataset but not as a primary matrix scope.

### 11.5 Single-event matrix

A single-event matrix uses only matches from one event.

Every matrix output must identify:

- source;
- format;
- event ID;
- event name;
- scope;
- included rounds;
- excluded result counts;
- generation time;
- schema version.

### 11.6 Multi-event matrix

A multi-event tabletop matrix may combine multiple events only when they are compatible.

Minimum compatibility requirements are:

- same Constructed format;
- same source product;
- supported normalized schema versions;
- compatible round scopes;
- no unresolved event-level round classification;
- events explicitly selected or enabled for consolidation.

Combine underlying counts:


\[
CombinedW = \sum W_i
\]


\[
CombinedL = \sum L_i
\]


\[
CombinedD = \sum D_i
\]

Then calculate:


\[
CombinedWinRate =
\frac{
CombinedW + 0.5 \times CombinedD
}{
CombinedW + CombinedL + CombinedD
}
\]

Do not calculate the simple average of event win-rate percentages.

The output must list every included event ID.

MTGO data must never be included in a tabletop multi-event matrix.

### 11.7 Multiple decks or deck changes

If event rules allow a player to use different Constructed decks in different phases, the normalized data must associate each match with the correct deck and archetype.

Do not assign every match automatically to the player’s first or final deck without verification.

If the correct phase-specific deck cannot be determined, affected matches must be excluded and reported.

### 11.8 Hierarchical parent and subtype matchups

The default matchup matrix remains the parent-archetype matrix. A hierarchical
matchup output may additionally allow the row axis and column axis to expand
independently from a parent archetype into its defined subtypes.

The statistical generator must retain each eligible competitor's stable parent
archetype ID and selected subtype ID, when one is selected. It must aggregate
canonical directed W-L-D counts at the most specific selected identity and make
the following views derivable from those counts:

- parent archetype against parent archetype;
- subtype against parent archetype;
- parent archetype against subtype;
- subtype against subtype.

Every displayed rate must be calculated from the summed W-L-D counts using the
formula in section 11.1. Do not average already-calculated parent, subtype, row,
column, event, or time-window percentages.

Collapsing all subtype nodes beneath a parent must reproduce that parent's
parent-level W-L-D counts exactly. Expanding or collapsing either axis must not
change the number of underlying eligible matches, double-count a match, or
change the fully collapsed parent matrix.

A parent archetype with no subtype definitions is a complete non-expandable
node. A classified deck under such a parent correctly has `subtype_id: null`;
this is not a residual or Unknown classification. A parent with exactly one
defined subtype is also non-expandable in the front end, although the generated
data may retain that subtype for audit and future compatibility. Expandability
is determined by the maintained taxonomy, not by how many subtype samples
happen to appear in one time window.

The current Standard and Modern rules contain no classified deck under a parent
that defines subtypes without also selecting one of those subtypes. If that
state appears later, it is a blocking classification or data-quality condition
until OPEN-005 is resolved. The generator must not silently omit the deck,
attribute it to another subtype, or invent an `Other` or `Unspecified` subtype.

Unknown archetypes remain governed by section 11.3. A subtype is never treated
as an unrelated parent archetype.

Before the hierarchical matchup front end is accepted, Standard must be run
through the same shared hierarchical calculation used for Modern. Its fully
collapsed parent matrix must reproduce the existing Standard parent-level
matchup output. This migration is required even if the legacy Standard public
files remain available temporarily as compatibility outputs.

---

## 12. Confidence intervals and sample size

### 12.1 Required counts

Every displayed win rate must retain its sample size.

A percentage without a valid match count is incomplete.

### 12.2 Confidence interval

Where confidence intervals are shown, use a 95% Wilson score interval.

For a record containing draws, use:


\[
effective\ wins = wins + 0.5 \times draws
\]


\[
n = wins + losses + draws
\]

The resulting Wilson interval is an approximation for the half-win treatment of draws and should be documented in output metadata.

### 12.3 Low-sample warnings

The exact display thresholds should be configurable rather than hard-coded only in front-end code.

The initial recommended warning levels are:

- fewer than 10 matches: very low sample;
- 10–29 matches: low sample;
- 30 or more matches: standard display.

A warning does not require deleting the statistic.

The front end should reduce visual certainty rather than pretending the value is precise.

### 12.4 No valid matches

When valid match count is zero:

- win rate must be `null`;
- confidence interval must be `null`;
- the front end must display `N/A` or an equivalent unavailable label;
- do not display `0%`.

---

## 13. Metagame share

### 13.1 Initial metagame share

For archetype \(a\):


\[
InitialMetagameShare_a =
\frac{
InitialDeckCount_a
}{
TotalValidInitialDecks
}
\]

The denominator includes valid classified decks and valid `Unknown` decks unless a generated field explicitly states otherwise.

Missing or invalid decklists must be reported separately.

### 13.2 Day 2 metagame share

For archetype \(a\):


\[
Day2MetagameShare_a =
\frac{
Day2DeckCount_a
}{
TotalValidDay2Decks
}
\]

For mixed events, this describes the qualified field but is not a pure Constructed conversion result.

### 13.3 High-score share

High-score share uses the high-score population as its denominator and must not be labeled simply as metagame share.

---

## 14. Day 2 performance presentation

### 14.1 Day 2 average is necessary but insufficient

Day 2 average points should be displayed, but it must not be used alone.

For each archetype, the Day 2 view should include, where available:

- Day 2 deck count;
- Day 2 field share;
- Day 2 average points per effective theoretical Constructed round;
- Day 2 high-score count;
- Day 2 high-score share;
- Day 2 high-score rate;
- Day 2 non-mirror match win rate;
- Day 2 W-L-D record;
- valid match count;
- effective theoretical round count;
- completed-round rate;
- intentional-draw count;
- bye count;
- Top 8 lock player count;
- awarded-win count;
- confidence interval;
- low-sample warning.

### 14.2 Why multiple metrics are required

Average points and match win rate measure different things.

Average points per theoretical round:

- includes the effect of ordinary drops;
- includes standings points from byes and intentional draws;
- uses scheduled opportunity as the denominator;
- is sensitive to official exemptions.

Match win rate:

- uses only played matches;
- excludes byes and intentional draws;
- is not directly penalized for unplayed drop rounds;
- is more suitable for matchup analysis.

High-score rate:

- measures how often a Day 2 deck reached a strong Day 2 point result;
- may be sensitive to varying effective round counts.

These metrics must be interpreted together.

### 14.3 Top 8 lock reporting

When Top 8 lock rules affect Day 2:

- show the number of affected players;
- show the number of exempted rounds;
- show the number of source-reported awarded wins;
- exclude those wins from played-match statistics;
- exclude verified exempted rounds from effective theoretical rounds;
- include an event-level explanatory note.

If lock status is uncertain, do not silently apply the exemption.

---

## 15. Drop and coverage diagnostics

### 15.1 Purpose

Day 1-only statistics can be affected by early drops.

Day 1 plus Day 2 statistics can be affected by qualification selection.

The system must expose diagnostics for both forms of bias rather than claiming that one scope is unbiased.

### 15.2 Completion rate

For a population:


\[
CompletionRate =
\frac{
CompletedOrOfficiallyExemptTheoreticalRounds
}{
ScheduledTheoreticalRounds
}
\]

The output should also retain:

- theoretical rounds;
- played matches;
- intentional draws;
- byes;
- exempted rounds;
- unplayed drop rounds.

### 15.3 Archetype-level completion

Completion diagnostics should be available per archetype when sample size permits.

This helps identify whether one archetype’s Day 1 match sample is unusually affected by early drops.

### 15.4 Drop distribution

Quality or supporting output should record:

- number of players dropping;
- round after which they dropped;
- record at drop when available;
- archetype;
- number of unplayed theoretical rounds.

### 15.5 Phase comparison

For each archetype with sufficient samples, the system should retain:

- Day 1 win rate;
- Day 2 win rate;
- all Constructed Swiss win rate;
- difference between Day 1 and all-Constructed rate;
- difference between Day 1 and Day 2 rate.

A large difference should produce a contextual warning, not an automatic claim of causation.

The initial recommended difference warning is five percentage points when both compared samples meet the configured minimum.

---

## 16. MTGO-specific statistics

### 16.1 Time ranges

MTGO statistics are aggregated over complete event-date ranges such as:

- 1 week;
- 4 weeks;
- 12 weeks;
- 36 weeks when retained by the existing product.

The exact available ranges must be listed in generated index data rather than assumed only by the front end.

### 16.2 Latest complete week

The existing Standard implementation identifies a latest complete calendar week.

This behavior must be preserved by regression tests before the pipeline becomes format-parameterized.

### 16.3 Average deck and deviation

Average decklists, representative decklists, Core/Flex classification, construction deviation, and recent construction change are MTGO product features.

These calculations are not automatically required for tabletop event pages.

Their detailed existing behavior should be documented and regression-tested during the Standard baseline phase before intentional formula changes.

### 16.4 Weekly Pickup

Weekly Pickup remains an MTGO-specific product feature.

It must not be applied automatically to isolated tabletop events.

### 16.5 MTGO matchup source

MTGO matchup data may come from a different collection mechanism than MTGO decklist and standings data.

The generated metadata must identify the source and coverage of matchup records.

Do not imply complete match coverage when only a subset is available.

---

## 17. Tabletop per-event outputs

Each tabletop event should generate enough information for the following logical outputs.

### 17.1 Event metadata

Includes:

- event ID;
- event name;
- format;
- source URL;
- event structure;
- event dates;
- scheduled rounds;
- phase assignments;
- advancement information;
- fetch time;
- generation time;
- schema version.

### 17.2 Overview

Includes:

- deck counts;
- metagame shares;
- average-point metrics;
- high-score metrics;
- Day 2 metrics;
- win-rate metrics;
- sample sizes;
- exclusion counts;
- warnings.

### 17.3 Deck data

Includes:

- player;
- archetype ID;
- display archetype;
- decklist;
- standings context;
- phase participation;
- relevant records.

### 17.4 Matchup data

Includes:

- scope;
- included events;
- matrix W-L-D counts;
- win rates;
- confidence intervals;
- sample warnings;
- excluded result counts.

### 17.5 Quality data

Includes:

- source record totals;
- missing decklists;
- Unknown classifications;
- classification conflicts;
- unknown rounds;
- unknown results;
- no-shows;
- byes;
- intentional draws;
- drops;
- awarded wins;
- reconciliation failures;
- blocking and non-blocking warnings.

---

## 18. Rounding and output precision

### 18.1 Stored values

Generated JSON should preserve enough precision for recalculation and display.

Recommended storage:

- counts as integers;
- rates as decimal fractions from `0` to `1`;
- average points as numeric values from `0` to `3`;
- confidence bounds as decimal fractions;
- raw numerator and denominator fields alongside calculated values.

### 18.2 Display values

Recommended front-end display:

- metagame and conversion rates: one decimal percentage point;
- win rates: one decimal percentage point;
- average points per round: two decimal places;
- confidence intervals: one decimal percentage point;
- counts: integers.

Example:

- stored win rate: `0.5346`;
- displayed win rate: `53.5%`.

### 18.3 Calculation order

Do not round intermediate W-L-D counts, point totals, or denominators.

Round only the final stored or displayed calculated value according to the output contract.

---

## 19. Data-quality gates

An event must not be silently published as complete when primary statistics cannot be trusted.

Potential blocking conditions include:

- event not present in whitelist;
- format mismatch;
- missing event structure;
- substantial unresolved round classification;
- missing primary standings;
- match rows that cannot be associated with players;
- duplicate identities that materially affect results;
- decklist coverage below an approved threshold;
- unresolved result types affecting primary statistics;
- failure to reconcile matchup cells;
- JSON Schema failure.

Non-blocking warnings may include:

- small samples;
- limited Day 2 population;
- a small number of Unknown decks;
- confirmed byes;
- confirmed intentional draws;
- confirmed drops;
- verified Top 8 lock exemptions.

Blocking thresholds must be configurable and documented.

For the Phase 5 normalized-event boundary, the following deterministic checks
apply before any classification or statistical output exists:

- the event must be explicitly enabled and verified in the whitelist;
- the normalized event must pass its versioned JSON Schema before and after
  quality assessment;
- reviewed metadata, raw-artifact integrity digests, stable identities, and all
  cross-record references must reconcile;
- match result semantics and Constructed/matchup eligibility must agree with the
  reviewed round phase, actual format, Swiss flag, and per-competitor result;
- at least one verified played match must belong to the configured Constructed
  Swiss scope;
- any unresolved or blocking issue makes the event non-publishable.

A missing or unavailable decklist is a non-blocking warning at this ingestion
boundary. It does not make a match result untrustworthy by itself. This rule does
not establish a decklist-coverage threshold for later classification or public
statistics; exact coverage and sample warning thresholds remain open under
OPEN-002.

---

## 20. Required statistical tests

Automated tests must cover at least:

- high-score threshold examples;
- average points using theoretical rounds;
- early `0-2` drop behavior;
- early `0-9` or equivalent drop behavior;
- played win and loss handling;
- normal played draw handling;
- `0-0-3` intentional-draw exclusion from win rate;
- bye exclusion from win rate;
- no-show exclusion;
- awarded-win exclusion;
- disqualified-participant match exclusion with both match sides retained;
- Top 8 lock theoretical-round exemption;
- Draft exclusion;
- playoff exclusion;
- Day 1 scope;
- Day 2 scope;
- Combined Constructed scope;
- non-qualifiers not receiving Day 2 theoretical rounds;
- W-L-D aggregation;
- mirror exclusion;
- matchup inverse-cell reconciliation;
- multi-event raw-count aggregation;
- missing data returning `null`;
- low-sample warnings;
- source separation between MTGO and tabletop data.

Regression tests must also preserve the existing Standard outputs before major refactoring.

---

## 21. Interpretation requirements

The front end and generated metadata must avoid misleading labels.

Use explicit labels such as:

- Initial metagame share;
- High-score share;
- High-score conversion;
- Day 2 field share;
- Day 2 conversion;
- Day 1 Constructed average points;
- Day 2 Constructed average points;
- Combined Constructed average points;
- Day 1 Constructed win rate;
- Day 2 Constructed win rate;
- All Constructed Swiss win rate;
- Non-mirror win rate.

Do not use a generic label such as `conversion` when multiple conversion denominators exist.

Do not describe:

- mixed-event Day 2 qualification as pure deck conversion;
- awarded wins as played match wins;
- byes as matchup wins;
- intentional draws as played match draws;
- missing values as zero;
- a low-sample percentage as conclusive;
- combined Day 1 and Day 2 data as free from selection bias.

---

## 22. Approved default presentation

### 22.1 Pure Constructed with Day 2

Default overview should show:

- initial metagame;
- Day 1 performance;
- Day 2 participation and conversion;
- Day 2 performance;
- Combined Constructed performance;
- quality and sample warnings.

Default matchup scope may use all Constructed Swiss rounds, with Day 1 and Day 2 switches.

### 22.2 Pure Constructed without Day 2

Default overview should show:

- initial metagame;
- average points per theoretical round;
- high-score count;
- high-score share;
- high-score conversion;
- overall Constructed win rate;
- quality and sample warnings.

### 22.3 Mixed events

Default overview should separate:

- Day 1 Constructed;
- Day 2 Constructed;
- Combined Constructed.

For mixed events:

- Day 1 high-score performance is the primary Constructed-only advancement-style metric;
- Day 2 statistics describe the selected qualified field;
- Day 2 average must be accompanied by Day 2 win rate, high-score rate, sample size, completion, and Top 8 lock information;
- all Constructed Swiss may be the default matchup scope;
- Day 1-only and Day 2-only switches are required;
- a selection-bias notice is required.

---

## 23. Unresolved implementation details

The following may be finalized during implementation without changing the approved statistical principles:

- exact low-sample visual style;
- exact configurable decklist-coverage blocking threshold;
- exact wording of front-end tooltips;
- whether confidence intervals are displayed directly in every table cell or in details;
- how hidden `Unknown` matrix rows are exposed to users;
- event-specific detection method for Top 8 lock results;
- event-specific handling of unusual administrative penalties.

Any resolution must be recorded in configuration, tests, or `DECISIONS.md` as appropriate.

Implementation details must not contradict the formulas and exclusions in this document.
