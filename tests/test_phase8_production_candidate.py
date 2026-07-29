"""P8-08 modular production-candidate boundaries."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
P8_07 = ROOT / "docs" / "prototypes" / "P8-07" / "index.html"
P8_08 = ROOT / "docs" / "prototypes" / "P8-08" / "index.html"
PHASE8_JS = ROOT / "assets" / "js" / "phase8"


def _scripts(path: Path) -> list[str]:
    return re.findall(
        r'<script src="([^"]+)"></script>',
        path.read_text(encoding="utf-8"),
    )


def test_candidate_and_review_entries_use_the_same_ordered_modules() -> None:
    expected = [
        "../../../assets/js/phase8/runtime.js",
        "../../../assets/js/phase8/i18n.js",
        "../../../assets/js/phase8/matchup-model.js",
        "../../../assets/js/phase8/mtgo-controller.js",
        "../../../assets/js/phase8/tabletop-controller.js",
        "../../../assets/js/phase8/app.js",
    ]

    assert _scripts(P8_07) == expected
    assert _scripts(P8_08) == expected
    assert "P8-08 模块化生产候选" in P8_08.read_text(encoding="utf-8")


def test_production_entry_uses_phase8_while_legacy_assets_remain_available() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "assets/js/phase8/app.js" in html
    assert "assets/js/phase8/tabletop-controller.js" not in html
    assert (ROOT / "assets" / "js" / "common.js").is_file()
    assert (ROOT / "assets" / "js" / "matchup.js").is_file()
    assert (ROOT / "assets" / "js" / "mtgo.js").is_file()
    assert (ROOT / "melee" / "index.html").is_file()


def test_scoped_clients_admit_only_their_source_tree() -> None:
    runtime = (PHASE8_JS / "runtime.js").read_text(encoding="utf-8")
    mtgo = (PHASE8_JS / "mtgo-controller.js").read_text(encoding="utf-8")
    tabletop = (PHASE8_JS / "tabletop-controller.js").read_text(
        encoding="utf-8"
    )

    assert "const cache = new Map()" in runtime
    assert 'path === "stats/catalog.json"' in runtime
    assert r"\/mtgo\/" in mtgo
    assert r"\/melee\/" not in mtgo
    assert r"\/melee\/" in tabletop
    assert r"\/mtgo\/" not in tabletop
    assert "mtgoController.loadComparisonDecks(format)" in tabletop


def test_app_delegates_all_product_loading_to_scoped_controllers() -> None:
    app = (PHASE8_JS / "app.js").read_text(encoding="utf-8")

    assert re.search(r"MtgoController\s*\.loadStatistics", app)
    assert re.search(r"MtgoController\s*\.loadMatchup", app)
    assert re.search(r"MtgoController\s*\.loadTop8", app)
    assert re.search(r"MtgoController\s*\.loadPickup", app)
    assert re.search(r"TabletopController\s*\.loadEvent", app)
    assert "fetch(" not in app
