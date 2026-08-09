"""P8-10 Tabletop production-entry and cross-entry routing contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ROOT_ENTRY = ROOT / "index.html"
TABLETOP_ENTRY = ROOT / "melee" / "index.html"
PHASE8_JS = ROOT / "assets" / "js" / "phase8"
APP_FILES = (
    "app-core.js",
    "app-freshness.js",
    "app-mtgo.js",
    "app-tabletop.js",
    "app-mobile-render.js",
    "app-mobile-interactions.js",
    "app.js",
)


def _scripts(path: Path) -> list[str]:
    return re.findall(
        r'<script src="([^"]+)"></script>',
        path.read_text(encoding="utf-8"),
    )


def test_tabletop_entry_has_its_own_surface_and_relative_public_base() -> None:
    html = TABLETOP_ENTRY.read_text(encoding="utf-8")

    assert 'data-stats-base="../"' in html
    assert 'data-surface="tabletop"' in html
    assert 'data-mtgo-entry="../index.html"' in html
    assert 'data-tabletop-entry="./index.html"' in html
    assert 'id="lang-zh"' in html
    assert 'id="lang-en"' in html
    assert 'id="payload-status"' in html
    assert "prototype-mark" not in html
    assert "review-banner" not in html


def test_tabletop_entry_loads_both_scoped_clients_in_order() -> None:
    assert _scripts(TABLETOP_ENTRY) == [
        "../assets/js/phase8/runtime.js",
        "../assets/js/phase8/i18n.js",
        "../assets/js/phase8/matchup-model.js",
        "../assets/js/phase8/mtgo-controller.js",
        "../assets/js/phase8/tabletop-controller.js",
        "../assets/js/phase8/app-core.js",
        "../assets/js/phase8/app-freshness.js",
        "../assets/js/phase8/app-mtgo.js",
        "../assets/js/phase8/app-tabletop.js",
        "../assets/js/phase8/app-mobile-render.js",
        "../assets/js/phase8/app-mobile-interactions.js",
        "../assets/js/phase8/app.js",
    ]


def test_root_keeps_the_mtgo_boundary_and_declares_tabletop_route() -> None:
    html = ROOT_ENTRY.read_text(encoding="utf-8")

    assert 'data-surface="mtgo"' in html
    assert 'data-tabletop-entry="./melee/index.html"' in html
    assert "assets/js/phase8/tabletop-controller.js" not in html


def test_app_routes_products_between_surfaces_and_reads_url_state() -> None:
    app = "\n".join(
        (PHASE8_JS / name).read_text(encoding="utf-8")
        for name in APP_FILES
    )

    assert 'const PRODUCT_SURFACES = {' in app
    assert '"tabletop-major-events": "tabletop"' in app
    assert "function navigateToProductEntry" in app
    assert "window.location.assign" in app
    assert "URLSearchParams(window.location.search)" in app
    assert "requestedFormat" in app
    assert "requestedProduct" in app
    assert "surfaceProductAvailable" not in app


def test_tabletop_copy_is_bilingual_and_not_embedded_in_renderer() -> None:
    app = (PHASE8_JS / "app-tabletop.js").read_text(encoding="utf-8")
    i18n = (PHASE8_JS / "i18n.js").read_text(encoding="utf-8")

    assert not re.search(r"[\u4e00-\u9fff]", app)
    for key in (
        "tabletop.overview",
        "tabletop.matchups",
        "tabletop.select_event",
        "tabletop.scope.day1",
        "tabletop.scope.day2",
        "tabletop.scope.all_constructed",
        "tabletop.overview_title",
        "tabletop.average_points",
        "tabletop.win_rate",
        "tabletop.valid_matches",
        "tabletop.completion_rate",
        "tabletop.data_quality",
        "tabletop.disqualified",
        "tabletop.day2_bias",
        "tabletop.mtgo_reference",
    ):
        assert i18n.count(f'"{key}"') == 2


def test_catalog_exposes_only_the_approved_modern_tabletop_product() -> None:
    catalog = json.loads(
        (ROOT / "stats" / "catalog.json").read_text(encoding="utf-8")
    )
    available = []
    for format_entry in catalog["formats"]:
        product = next(
            item
            for item in format_entry["products"]
            if item["id"] == "tabletop-major-events"
        )
        if product["available"]:
            available.append((format_entry["id"], product["path"]))

    assert available == [("modern", "stats/modern/melee/index.json")]
