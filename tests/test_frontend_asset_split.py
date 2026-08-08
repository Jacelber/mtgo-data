import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "index.html"
SITE_CSS = REPO_ROOT / "assets" / "css" / "site.css"
COMMON_JS = REPO_ROOT / "assets" / "js" / "common.js"
MATCHUP_JS = REPO_ROOT / "assets" / "js" / "matchup.js"
MTGO_JS = REPO_ROOT / "assets" / "js" / "mtgo.js"
PHASE8_CSS = REPO_ROOT / "assets" / "css" / "phase8-base.css"
PHASE8_CANDIDATE_CSS = REPO_ROOT / "assets" / "css" / "phase8-candidate.css"
PHASE8_JS = REPO_ROOT / "assets" / "js" / "phase8"
PHASE8_APP_FILES = (
    "app-core.js",
    "app-freshness.js",
    "app-mtgo.js",
    "app-tabletop.js",
    "app.js",
)


def test_frontend_uses_ordered_static_assets_without_inline_blocks():
    html = INDEX.read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="assets/css/phase8-base.css">' in html
    assert (
        '<link rel="stylesheet" href="assets/css/phase8-candidate.css">' in html
    )
    assert "<style" not in html
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)

    script_sources = re.findall(r'<script src="([^"]+)"></script>', html)
    assert script_sources == [
        "assets/js/phase8/runtime.js",
        "assets/js/phase8/i18n.js",
        "assets/js/phase8/matchup-model.js",
        "assets/js/phase8/mtgo-controller.js",
        "assets/js/phase8/app-core.js",
        "assets/js/phase8/app-freshness.js",
        "assets/js/phase8/app-mtgo.js",
        "assets/js/phase8/app.js",
    ]
    assert 'type="module"' not in html
    assert "tabletop-controller.js" not in html
    assert "chart.umd.min.js" not in html


def test_frontend_assets_are_present_and_index_is_materially_smaller():
    assert PHASE8_CSS.is_file()
    assert PHASE8_CANDIDATE_CSS.is_file()
    assert SITE_CSS.is_file()
    assert COMMON_JS.is_file()
    assert MATCHUP_JS.is_file()
    assert MTGO_JS.is_file()
    assert len(INDEX.read_text(encoding="utf-8").splitlines()) < 100


def test_phase8_app_is_split_into_focused_classic_scripts():
    sources = {
        name: (PHASE8_JS / name).read_text(encoding="utf-8")
        for name in PHASE8_APP_FILES
    }

    assert all((PHASE8_JS / name).stat().st_size < 25_000 for name in sources)
    assert "const state = {" in sources["app-core.js"]
    assert "function freshnessStrip(items)" in sources["app-freshness.js"]
    assert "async function statsView()" in sources["app-mtgo.js"]
    assert "async function pickupView()" in sources["app-mtgo.js"]
    assert "async function tabletopView()" in sources["app-tabletop.js"]
    assert "async function renderView()" in sources["app.js"]
    assert "async function initialize()" in sources["app.js"]
    assert all(
        "import " not in source and "export " not in source
        for source in sources.values()
    )


def test_split_retains_classic_assets_as_an_unchanged_rollback_baseline():
    common = COMMON_JS.read_text(encoding="utf-8")
    mtgo = MTGO_JS.read_text(encoding="utf-8")

    assert "function setLang(l)" in mtgo
    assert mtgo.rstrip().endswith("refreshAll();")
    assert "function cardUrl(en)" in common
    assert "function escapeHtml(s)" in common
    assert "stats/${currentFormat}/mtgo/" in mtgo
