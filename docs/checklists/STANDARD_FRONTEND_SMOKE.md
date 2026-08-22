# Standard Front-end Smoke Checklist

Use this checklist after changing Standard public JSON, its generators, or the MTGO page. Serve the repository root over HTTP; direct `file://` loading is not representative of GitHub Pages.

1. Open `/index.html` and confirm the page loads without console errors.
2. Confirm the update date is displayed from `stats/standard/mtgo/meta.json`.
3. Select 1, 4, and 12 weeks; confirm the metagame table and deck details load for each visible range.
4. Open Landing; confirm the latest brief loads, the feature-week selector loads
   the selected Landing feature document without changing the brief, and one
   legacy Weekly Pickup URL redirects to that feature week.
5. Open Matchups; select 1, 4, and 12 weeks and confirm the overall table and matrix render.
6. Confirm failed optional data requests show the existing fallback state instead of breaking the page.

Automated prerequisite for a newly generated public-data candidate:

```text
python validate_schemas.py
python validate_output_invariants.py
```

Run those commands once on that candidate. A UI-only change has no Python
prerequisite; its acceptance is the Owner browser review after the native UI
model smoke.

The current page intentionally keeps 36-week statistics and matchup data out of the visible selectors while retaining those generated documents in the public catalogs. The automated contract verifies all four generated ranges, including 36 weeks. Restoring the 36-week buttons is a separately reviewed front-end behavior change.

The output gate protects public paths, catalog targets, period alignment,
aggregate counts, matchup reciprocity, and Landing feature metadata. It intentionally
does not freeze daily values or replace browser inspection.
