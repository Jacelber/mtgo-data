import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "index.html"
SITE_CSS = REPO_ROOT / "assets" / "css" / "site.css"
COMMON_JS = REPO_ROOT / "assets" / "js" / "common.js"
MATCHUP_JS = REPO_ROOT / "assets" / "js" / "matchup.js"
MTGO_JS = REPO_ROOT / "assets" / "js" / "mtgo.js"


def test_frontend_uses_ordered_static_assets_without_inline_blocks():
    html = INDEX.read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="assets/css/site.css">' in html
    assert "<style" not in html
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)

    script_sources = re.findall(r'<script src="([^"]+)"></script>', html)
    assert script_sources == [
        "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
        "assets/js/common.js",
        "assets/js/matchup.js",
        "assets/js/mtgo.js",
    ]
    assert 'type="module"' not in html


def test_frontend_assets_are_present_and_index_is_materially_smaller():
    assert SITE_CSS.is_file()
    assert COMMON_JS.is_file()
    assert MATCHUP_JS.is_file()
    assert MTGO_JS.is_file()
    assert len(INDEX.read_text(encoding="utf-8").splitlines()) < 150


def test_split_preserves_classic_global_hooks_and_initialization():
    html = INDEX.read_text(encoding="utf-8")
    common = COMMON_JS.read_text(encoding="utf-8")
    mtgo = MTGO_JS.read_text(encoding="utf-8")

    assert "onclick=\"setLang('zh')\"" in html
    assert "onclick=\"setLang('en')\"" in html
    assert "function setLang(l)" in mtgo
    assert mtgo.rstrip().endswith("refreshAll();")
    assert "function cardUrl(en)" in common
    assert "function escapeHtml(s)" in common
    assert "stats/${currentFormat}/mtgo/" in mtgo
