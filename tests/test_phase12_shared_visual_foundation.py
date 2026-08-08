"""Contract checks for the P12-05 shared visual foundation."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_CSS = ROOT / "assets" / "css" / "phase8-base.css"
MTGO_ENTRY = ROOT / "index.html"
TABLETOP_ENTRY = ROOT / "melee" / "index.html"
PRODUCTION_CAT = ROOT / "assets" / "images" / "cat-line-art-watermark.png"
DESIGN_CAT = (
    ROOT
    / "docs"
    / "design"
    / "assets"
    / "p12-04a"
    / "cat-line-art-watermark.png"
)


def test_shared_styles_publish_the_accepted_semantic_tokens() -> None:
    css = BASE_CSS.read_text(encoding="utf-8")
    expected_tokens = {
        "--canvas": "#efece5",
        "--surface": "#fffdf8",
        "--surface-strong": "#ffffff",
        "--ink": "#1a292b",
        "--muted": "#66716f",
        "--line": "#d8d1c5",
        "--brand": "#4b2c1f",
        "--brand-2": "#9a542c",
        "--brand-blue": "#637aa5",
        "--brand-teal": "#4c9992",
        "--accent": "#b9562f",
        "--accent-soft": "#f2dbcd",
        "--positive": "#1f7459",
        "--negative": "#aa4740",
        "--steady": "#737a78",
    }
    for name, value in expected_tokens.items():
        assert f"{name}: {value};" in css

    for foundation in (
        "--font-ui:",
        "--font-editorial:",
        "--text-base:",
        "--space-4:",
        "--focus-ring:",
        "--shadow:",
        "--control-height:",
        "--content-max:",
        '@media (max-width: 780px)',
        '@media (prefers-reduced-motion: reduce)',
    ):
        assert foundation in css


def test_both_public_entries_use_the_same_semantic_shell() -> None:
    for entry, cat_path in (
        (MTGO_ENTRY, "assets/images/cat-line-art-watermark.png"),
        (TABLETOP_ENTRY, "../assets/images/cat-line-art-watermark.png"),
    ):
        html = entry.read_text(encoding="utf-8")
        assert '<header class="app-header">' in html
        assert '<div class="header-main">' in html
        assert '<h1 id="site-title">猫猫万智周报</h1>' in html
        assert (
            f'<span class="cat-brand-watermark" aria-hidden="true"><img src="{cat_path}" alt=""></span>'
            in html
        )
        assert '<nav class="format-tabs" id="format-tabs"' in html
        assert '<nav class="product-tabs" id="product-tabs"' in html
        assert '<main class="page-shell">' in html
        assert 'id="lang-zh" class="active" type="button" aria-pressed="true"' in html
        assert 'id="lang-en" type="button" aria-pressed="false"' in html


def test_shared_navigation_roles_are_visually_distinct() -> None:
    css = BASE_CSS.read_text(encoding="utf-8")
    assert ".format-tabs button" in css
    assert "border-radius: var(--radius-pill);" in css
    assert ".lang-switch button" in css
    assert ".product-tabs button" in css
    assert ".section-tabs" in css
    assert ".section-tabs :where(button, a).active" in css


def test_production_cat_is_local_documented_and_byte_identical() -> None:
    assert PRODUCTION_CAT.read_bytes() == DESIGN_CAT.read_bytes()
    digest = hashlib.sha256(PRODUCTION_CAT.read_bytes()).hexdigest()
    assert digest == "cd5c1e145a811405de526dda8d5be98df932fb293dfa1ad580f146ae5e9630d9"
    provenance = (PRODUCTION_CAT.parent / "README.md").read_text(encoding="utf-8")
    assert digest in provenance
    assert "byte-for-byte copy" in provenance


def test_language_state_updates_visible_and_programmatic_selection() -> None:
    i18n = (ROOT / "assets" / "js" / "phase8" / "i18n.js").read_text(
        encoding="utf-8"
    )
    app = (ROOT / "assets" / "js" / "phase8" / "app.js").read_text(
        encoding="utf-8"
    )
    assert '"site.title": "猫猫万智周报"' in i18n
    assert 'zhButton.setAttribute("aria-pressed"' in app
    assert 'enButton.setAttribute("aria-pressed"' in app
