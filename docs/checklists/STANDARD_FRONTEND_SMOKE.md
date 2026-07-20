# Standard Front-end Smoke Checklist

Use this checklist after changing Standard public JSON, its generators, or the MTGO page. Serve the repository root over HTTP; direct `file://` loading is not representative of GitHub Pages.

1. Open `/index.html` and confirm the page loads without console errors.
2. Confirm the update date is displayed from `stats/standard/mtgo/meta.json`.
3. Select 1, 4, and 12 weeks; confirm the metagame table and deck details load for each visible range.
4. Open Weekly Pickup; confirm its week selector and the selected report load.
5. Open Matchups; select 1, 4, and 12 weeks and confirm the overall table and matrix render.
6. Confirm failed optional data requests show the existing fallback state instead of breaking the page.

Automated prerequisite:

```text
python -m pytest tests/test_standard_public_contract.py
```

The current page intentionally keeps 36-week statistics and matchup data out of the visible selectors while retaining those generated documents in the public catalogs. The automated contract verifies all four generated ranges, including 36 weeks. Restoring the 36-week buttons is a separately reviewed front-end behavior change.

The automated contract protects public paths, catalog targets, period alignment, aggregate counts, matchup reciprocity, and pickup metadata. It intentionally does not freeze daily values or replace browser inspection.
