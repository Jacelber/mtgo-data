"""P8-09 MTGO production-entry contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PHASE8_JS = ROOT / "assets" / "js" / "phase8"
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
    assert not (ROOT / "melee" / "index.html").exists()


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
    rejected = _runtime_path("./", "../secrets.json")
    assert rejected["ok"] is False


def test_root_uses_only_the_mtgo_phase8_module_boundary() -> None:
    assert _scripts(INDEX) == [
        "assets/js/phase8/runtime.js",
        "assets/js/phase8/i18n.js",
        "assets/js/phase8/matchup-model.js",
        "assets/js/phase8/mtgo-controller.js",
        "assets/js/phase8/app.js",
    ]


def test_app_has_surface_gating_and_real_language_switching() -> None:
    app = (PHASE8_JS / "app.js").read_text(encoding="utf-8")

    assert "dataset.surface" in app
    assert "surfaceProductAvailable" in app
    assert (
        'ENTRY_SURFACE === "mtgo" && productId === "tabletop-major-events"'
        in app
    )
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
