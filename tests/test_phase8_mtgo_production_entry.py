"""P8-09 MTGO production-entry contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PHASE8_JS = ROOT / "assets" / "js" / "phase8"
APP_FILES = ("app-core.js", "app-mtgo.js", "app-tabletop.js", "app.js")
P8_07 = ROOT / "docs" / "prototypes" / "P8-07" / "index.html"
P8_08 = ROOT / "docs" / "prototypes" / "P8-08" / "index.html"


def _scripts(path: Path) -> list[str]:
    return re.findall(
        r'<script src="([^"]+)"></script>',
        path.read_text(encoding="utf-8"),
    )


def _runtime_path(base: str, path: str) -> dict:
    script = r"""
global.document = {documentElement: {dataset: {statsBase: process.argv[1]}}};
require("./assets/js/phase8/runtime.js");
let result;
try {
  result = {ok: true, path: global.P8Runtime.publicPath(process.argv[2])};
} catch (error) {
  result = {ok: false, message: error.message};
}
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", script, base, path],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_root_is_the_mtgo_surface_and_has_no_review_copy() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert 'data-stats-base="./"' in html
    assert 'data-surface="mtgo"' in html
    assert 'id="lang-zh"' in html
    assert 'id="lang-en"' in html
    assert 'id="payload-status"' in html
    assert "prototype-mark" not in html
    assert "review-banner" not in html
    assert "P8-08" not in html
    assert "tabletop-controller.js" not in html
    assert 'data-mtgo-entry="./index.html"' in html
    assert 'data-tabletop-entry="./melee/index.html"' in html
    assert (ROOT / "melee" / "index.html").is_file()


def test_review_entries_keep_review_surface_and_relative_data_base() -> None:
    for path in (P8_07, P8_08):
        html = path.read_text(encoding="utf-8")

        assert 'data-stats-base="../../../"' in html
        assert 'data-surface="review"' in html
        assert "../../../assets/js/phase8/i18n.js" in html


def test_runtime_resolves_only_stats_paths_from_the_entry_base() -> None:
    assert _runtime_path("./", "stats/catalog.json") == {
        "ok": True,
        "path": "./stats/catalog.json",
    }
    assert _runtime_path("../../../", "stats/modern/mtgo/statistics_4w.json") == {
        "ok": True,
        "path": "../../../stats/modern/mtgo/statistics_4w.json",
    }
    assert _runtime_path("../", "stats/modern/melee/index.json") == {
        "ok": True,
        "path": "../stats/modern/melee/index.json",
    }
    rejected = _runtime_path("./", "../secrets.json")
    assert rejected["ok"] is False


def test_root_uses_only_the_mtgo_phase8_module_boundary() -> None:
    assert _scripts(INDEX) == [
        "assets/js/phase8/runtime.js",
        "assets/js/phase8/i18n.js",
        "assets/js/phase8/matchup-model.js",
        "assets/js/phase8/mtgo-controller.js",
        "assets/js/phase8/app-core.js",
        "assets/js/phase8/app-mtgo.js",
        "assets/js/phase8/app.js",
    ]


def test_app_has_cross_entry_routing_and_real_language_switching() -> None:
    app = "\n".join(
        (PHASE8_JS / name).read_text(encoding="utf-8")
        for name in APP_FILES
    )

    assert "dataset.surface" in app
    assert "navigateToProductEntry" in app
    assert "window.location.assign" in app
    assert "URLSearchParams(window.location.search)" in app
    assert "I18n.setLanguage" in app
    assert "本轮先确认中文界面" not in app


def test_i18n_defines_both_languages_for_every_mtgo_product() -> None:
    i18n = (PHASE8_JS / "i18n.js").read_text(encoding="utf-8")

    assert 'zh: {' in i18n
    assert 'en: {' in i18n
    assert "MTGO High-Score & Top 8 Shares" in i18n
    for key in (
        "product.stats",
        "product.matchups",
        "product.top8",
        "product.pickup",
        "source.stats",
        "source.matchups",
        "completeness",
        "deck.average",
        "deck.representative",
    ):
        assert f'"{key}"' in i18n


def test_top8_view_does_not_present_internal_week_lifecycle() -> None:
    app = (PHASE8_JS / "app-mtgo.js").read_text(encoding="utf-8")
    i18n = (PHASE8_JS / "i18n.js").read_text(encoding="utf-8")

    assert "weekEntry.status" not in app
    assert "weekEntry.seal_on" not in app
    for key in ("top8.provisional", "top8.sealed"):
        assert f'"{key}"' not in i18n
