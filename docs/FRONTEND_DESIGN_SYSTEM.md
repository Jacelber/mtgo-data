# Front-end design system

## 1. Authority and scope

This document is the durable visual and interaction authority for the MTGO and
Tabletop static products. It freezes the owner-accepted P12-04 direction before
production implementation. `docs/design/p12-04a-selected-desktop.html` is the
reference composition; its sample values are illustrative, not product data.

The system is named **Editorial Analysis Console (A3)**: an editorial reading
surface with the information architecture and operational clarity of an
analysis console. It applies to the shared shell, Landing, statistics, matchup,
weekly Top 8, Tabletop, and reusable deck-detail surfaces. It does not merge
their data or force every view to use Landing's density.

Production implementation begins only in separately authorized P12-05 and later
tasks. This contract changes no front-end source, public path, generated data,
Schema, workflow, or statistical meaning.

## 2. Product identity

The Chinese header title is **猫猫万智周报**. It has no English subtitle while
Chinese is active. The selected cat treatment is direction B: the local
transparent line-art asset
`docs/design/assets/p12-04a/cat-line-art-watermark.png` appears as a decorative
header watermark. It is not data, a control, or a replacement for text.

The header palette is inspired by the warm brown, burnt orange, muted blue, and
turquoise relationships of a Magic card back without copying card-back artwork.
Do not use the Magic or Wizards logo as the site brand. Repository-owned brand
assets must record their source and transformation; production assets must be
local and must not depend on a third-party runtime request.

P12-15 adds only durable shell additions around the accepted A3 composition: a
warm cream and brown cat-line-art favicon, a fixed 1200 by 630 bilingual share
image with no card art or changing weekly claims, and a narrow footer after all
page content. The footer supplies the Scryfall source link and the required
Wizards Fan Content notice in the active language; it is not a Landing panel.
These additions must preserve the existing Landing structure, image treatment,
and responsive behavior.

## 3. Color

Use these semantic tokens as the shared starting palette:

```css
--canvas: #efece5;
--surface: #fffdf8;
--surface-strong: #ffffff;
--ink: #1a292b;
--muted: #66716f;
--line: #d8d1c5;
--brand: #4b2c1f;
--brand-2: #9a542c;
--brand-blue: #637aa5;
--brand-teal: #4c9992;
--accent: #b9562f;
--accent-soft: #f2dbcd;
--positive: #1f7459;
--negative: #aa4740;
--steady: #68706e;
--shadow: 0 3px 12px rgba(30, 42, 42, .05);
```

The selected header background is:

```css
background:
  radial-gradient(circle at 70% 45%, rgba(213, 151, 73, .2), transparent 32%),
  linear-gradient(112deg, #281b17 0%, #694020 19%, #8f4827 49%, #7c4827 77%, #2b201a 100%);
```

Text and controls must meet the applicable WCAG contrast target. Positive,
negative, and steady colors are supplementary: labels, values, icons, or
patterns must carry the meaning without color.

## 4. Typography

Use the platform system UI stack for controls, operational labels, tables, and
body copy. Use `Georgia`, `"Noto Serif SC"`, and a serif fallback for the brand
and selected editorial headings. Numeric columns use tabular numerals.

The shared production baseline is 16 CSS pixels for body copy, 14 pixels for
table and key operational labels, and 13 pixels for secondary source or status
copy. The language switch may remain visually compact at 12 pixels because its
two controls retain accessible names, programmatic state, and 24-pixel targets.
The accepted Landing table baseline is 14 CSS pixels for headings, 17 pixels
for values and body copy, and 19 pixels for deck names. Mobile may adjust the
scale to fit its semantic-card layout but must remain comfortably readable and
must not hide required text. Establish the complete production type ramp once
in shared tokens during P12-05 rather than adding page-local sizes.

## 5. Spacing, density, and hierarchy

Use a small shared spacing scale and three explicit density roles:

- **editorial** for the weekly brief and featured narratives;
- **standard** for shared panels, notices, selectors, and deck details;
- **compact** for data-dense tables and matrices.

Warm canvas separates the page from white reading surfaces. Borders are quiet;
shadow is shallow and never the only boundary. Section order communicates the
Landing story: header, weekly change brief, completeness, current environment,
then approved new-deck and new-technology features. Do not apply large empty
spacing to dense statistical views merely to resemble Landing.

## 6. Navigation and controls

Format selectors are bordered pills. The Chinese/English control is smaller,
borderless text in the upper-right, with the active language indicated by
weight, color, underline, and programmatic state. It must not resemble a format
button.

Top-level product navigation and in-page Landing section navigation are
different concepts and must be visually distinguishable. Weekly Pickup is not
a top-level product: current and historical approved content comes from the
Landing-owned feature archive and appears in the Landing feature section. The
section may have a week selector, but selecting a week changes only feature
content. Legacy Pickup URLs remain compatibility redirects, not a product or
data-source identity.

Within newly reviewed Landing copy, every exact deck link belongs to the
applicable selected feature week. The link selects that week, expands the exact
item, moves it into view, and exposes stable URL and focus state. A top-copy
token without a selected feature is rejected before rendering. The established
Top 8 detail destination remains for Top 8 links outside Landing copy and as a
legacy defensive fallback.

Controls use semantic `button`, `a`, `select`, or appropriate form elements,
visible focus, meaningful accessible names, and touch-friendly targets. Normal
text meets 4.5:1 contrast; large text, controls, and focus indicators meet
3:1. Interactive targets have a 24 by 24 CSS-pixel floor, while primary touch
controls should remain larger where the layout permits. The target floor
applies to the interactive hit area and focus indicator; compact informational
or expansion glyphs may remain visually smaller when their parent control keeps
the full target. A
disabled or unavailable product is explicit rather than silently inert.

## 7. Panels, tables, and deck details

Weekly brief entries are full-width editorial lines. They may include an
environment observation, a linked event result, schedule information, or
another editor-added row. Deck names and changed values may be emphasized;
internal row tags and approval vocabulary are not rendered. No mandatory large
weekly conclusion or KPI card is required.

Desktop environment data uses an aligned table; mobile translates the same
records into semantic deck cards rather than forcing page-level horizontal
scrolling. The composition strip and environment list use the same current-week
3% inclusion set. Names and percentages are available on hover and keyboard;
touch uses first tap for disclosure and second tap for navigation. A selected
deck detail opens directly beneath its row or card and reuses the established
statistics/Landing-feature deck-detail component.

Activating a composition segment on desktop or mobile must make the newly
expanded deck detail perceptible by moving it into the viewport after rendering;
the interaction must not leave the user at the composition strip with the
result hidden below. Preserve keyboard focus, browser state, and reduced-motion
behavior.

When an owner-maintained first representative card is available, its art crop
is the composition segment fill. This changes only the fill: segment order,
width, threshold, tooltip, keyboard behavior, and click/touch navigation remain
the same. The tooltip renders only the deck name and share, never the card name.
An unmapped or failed image falls back to the accepted high-contrast segment
palette without guessing from classifier rules.

Composition segment widths remain proportional to the underlying share and
therefore may be narrower than 24 CSS pixels. This is an essential visualization
exception, not the only route to the information: each included identity has an
equivalent named control in the accompanying table or card list. Every mapped
segment is still an independent button with its own accessible name and expanded
state; residual non-navigation segments are labelled, focusable images without
interactive descendants.

Numeric table headers and their column values share the same right-alignment
anchor. Optional help icons and active sort arrows use a reserved accessory rail
that starts 4 pixels to the right of that anchor. They form one compact group,
do not participate in the label's normal flow, and do not shift the label away
from its data column.

P12-08A applies that semantic-card rule to the retained MTGO statistics and
Tabletop overview lists. Deck identity, core and secondary metrics, and the
existing expansion action remain available, with detail inserted directly
beneath the originating card. Landing feature items already use semantic cards
and retain their narrow-screen heading and metric wrapping. The Top 8 cross-event
comparison and matchup matrices remain bounded horizontal scrollers with a
sticky identity column and a dismissible first-use scroll cue. Responsive
adaptation must not discard data.

Bounded horizontal scrolling is acceptable for format or product navigation
and truly wide matrices. It must not create page overflow or hide the active
item without a discoverable way to reach it.

## 8. Card images and mana identity

Each Landing environment row may show two manually selected representative
cards in a fixed column. These representative images are landscape art crops:
the Owner-refined pre-overlap size is 118 by 82 CSS pixels on desktop and 90 by
63 pixels on mobile. The representative-card column must keep the visible gap
to the current-share column compact after overlap, and the first approved
representative must sit above the second in the overlap. Each approved feature
shows exactly four reviewer-selected full-card images at the physical-card
ratio; all approved items are present, with new decks before new technology.

At mobile widths, place the representative stack lower relative to the deck
heading and remove excessive whitespace beneath it. Preserve the accepted 90 by
63 dimensions, overlap amount and first-card stacking priority, and leave the
desktop placement unchanged.

Card and mana-color identity is metadata maintained outside classifier rules.
Reserve image dimensions before loading, lazy-load below-the-fold images, bound
third-party concurrency, and use a stable placeholder on failure. The readable
card or deck name and navigation must remain available without the image.

The Feature heading is the bilingual deck name derived from the stable
format/classifier identity, not weekly free text. Within each format, render all
new-deck items before new-technology items. Inside a category, follow the exact
deck-link order in final Landing top copy, reading multiple links left to right;
append items absent from top copy afterward. This content-order rule does not
change the accepted card layout or visual hierarchy.

Feature card frames use the physical-card ratio of 63:88 before a request
starts; the environment representative art crops use the landscape dimensions
defined above.
Third-party images begin loading within 400 CSS pixels of the viewport, with at
most four requests in flight. A failed image remains a labelled placeholder and
offers one explicit retry; it never blocks the surrounding deck or feature.
Touch-first devices open card art in a focus-trapped full-screen preview on the
first card-name tap. Backdrop, close button, Escape, and browser Back dismiss it
and restore focus and scroll; an explicit button opens Scryfall in a new tab.
Pointer devices retain the established hover preview and direct card-name link.

## 9. Responsive behavior

Use one semantic markup contract with a primary breakpoint at 780 CSS pixels.
Design and test desktop plus 390- and 412-pixel widths. The accepted cat
watermark frame is 230 by 114 pixels on desktop and a compact 84 by 64 pixels on
mobile; both use the same asset and are `aria-hidden`.

On small screens, navigation becomes bounded horizontal scrollers, completeness
facts wrap, environment rows become cards, deck details and feature details use
one column, and the four feature cards move below their copy. Every current,
previous-week, and previous-four-week share, direction, deck identity, feature
category, week selector, and detail route remains available.

## 10. Interaction and motion

One action expands a deck or feature detail; do not require a second nested
expansion. Hover interactions must have focus and touch equivalents. No required
information may depend on animation. Motion is brief, functional, and disabled
or reduced under `prefers-reduced-motion`.

The shared shell provides one fixed bottom-right return-to-top control on the
Landing, every retained MTGO view, and Tabletop. It remains clear of safe-area
insets and page controls, does not obscure content at 390 pixels, has a localized
accessible name and visible focus, works by keyboard, and uses immediate rather
than smooth movement when reduced motion is requested.

## 11. Accessibility and failure states

Use semantic landmarks, headings, tables or labelled cards, explicit form
labels, visible focus, logical source order, and useful accessible names. Keep
names and values in text; never encode identity or direction only by color,
position, or an image. Decorative cat art is ignored by assistive technology.

Dynamic product rerenders restore focus to the equivalent initiating control,
and closing an inline detail returns focus to its originating deck control.
Unavailable navigation exposes its reason through `aria-describedby` while
remaining focusable so the visible status message and explanation are available
to keyboard and assistive-technology users.

Unavailable, unknown, `no_events`, empty approved-feature, loading, and retry
states must be distinguishable. A malformed or inconsistent admitted document
is an error, not an empty state. Card-image failure is non-blocking. Internal
terms such as candidate, artificial/manual review, reviewer, or approval must
not appear in reader-facing UI; the user sees only finished editorial content.

Initial loading uses text-first structural placeholders without invented
values. Already readable content stays visible during deferred requests and
refresh checks; a failure is reported next to the control or record that caused
it, with a foreground retry that always starts a new request. Only successful
documents enter the session cache. Cache entries are bounded by count and byte
budget, while in-flight foreground and refresh requests remain separate.

When a visible tab returns after five minutes, the current view may check for
updates without replacing readable content. Every document needed for that view
is staged as one group; unchanged groups are accepted silently, changed groups
wait for an explicit Apply action, and a partial or failed group leaves the old
view intact. Offline-to-online changes announce availability but do not retry
automatically. Loading, retry, stale, and pending-update state is transient and
does not enter shareable URLs.

## 12. Implementation and acceptance

P12-05 turns these values into shared static tokens and shell components.
P12-09 establishes the shared loading, retry, refresh, and card-preview rules
above. P12-06 through P12-15 migrate and extend individual views. P12-16 verifies all
retained products, formats, languages, desktop and 390-pixel behavior, URLs,
compatibility, loading, console state, and reversible Landing cutover. Any
intentional deviation from this authority must be documented and owner-approved
rather than introduced as a page-local exception.
