from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_statistics_uses_one_high_score_composition_bar() -> None:
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")
    interaction = (ROOT / "assets/js/phase8/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "assets/css/phase8-candidate.css").read_text(encoding="utf-8")

    chart = mtgo[mtgo.index("function chartHtml"):mtgo.index("function sortedArchetypes")]
    assert "composition-bar" in chart
    assert "composition-segment" in chart
    assert "Number(item.high_score_share) >= 0.03" in chart
    assert "Number(item.high_score_share) < 0.03" in chart
    assert 'item.id !== "unknown"' in chart
    assert 'item.id === "unknown"' in chart
    assert "composition-legend" not in chart
    assert "data-composition-identity" in chart
    assert "data-tooltip" in chart
    assert "top8_share" not in chart
    assert "pie" not in mtgo.lower()
    assert "pie" not in interaction.lower()
    assert ".pie-" not in styles


def test_composition_uses_explicit_card_art_without_rendering_card_names() -> None:
    core = (ROOT / "assets/js/phase8/app-core.js").read_text(encoding="utf-8")
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")
    interaction = (ROOT / "assets/js/phase8/app.js").read_text(encoding="utf-8")

    expected = {
        "izzet-prowess": "boomerang-basics.jpg",
        "izzet-spellementals": "sunderflock.jpg",
        "mono-green-landfall": "earthbender-ascension.jpg",
        "selesnya-offense": "practiced-offense.jpg",
        "jeskai-lessons": "accumulate-wisdom.jpg",
        "4-color-tablet": "inevitable-defeat.jpg",
    }
    for identity, filename in expected.items():
        css_path = f"../images/representative-cards/standard/{filename}"
        file_path = f"assets/images/representative-cards/standard/{filename}"
        assert f'"{identity}": "{css_path}"' in core
        assert (ROOT / file_path).is_file()

    chart = mtgo[mtgo.index("function chartHtml"):mtgo.index("function sortedArchetypes")]
    assert 'const detail = `${item.name} · ${value}`' in chart
    assert "REPRESENTATIVE_CARD_ART[state.format]?.[item.id]" in chart
    assert "card.name" not in chart
    assert "touchedCompositionIdentity" in interaction
    assert 'matchMedia("(hover: none)")' in interaction
    assert "data-stats-parent" in mtgo


def test_top8_share_remains_in_the_authoritative_table() -> None:
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")

    assert "pct(record.top8_share)" in mtgo
    assert 'sortHeader(t("stats.top8_share"), "top8_share")' in mtgo


def test_mana_identity_is_explicit_and_uses_local_svg_assets() -> None:
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")

    assert '"izzet-prowess": ["u", "r"]' in mtgo
    assert '"prowess/izzet": ["u", "r"]' in mtgo
    assert '"goryos-reanimator/esper": ["w", "u", "b"]' in mtgo
    assert "assets/images/mana/${color}.svg" in mtgo
    assert "MANA_IDENTITIES[state.format]?.[identityId]" in mtgo
    assert "infer" not in mtgo[mtgo.index("const MANA_IDENTITIES"):mtgo.index("function locateDeck")]

    for symbol in "wubrgc":
        assert (ROOT / f"assets/images/mana/{symbol}.svg").is_file()


def test_product_name_is_not_redefined_by_chart_work() -> None:
    i18n = (ROOT / "assets/js/phase8/i18n.js").read_text(encoding="utf-8")

    assert '"product.stats": "MTGO占比统计"' in i18n
    assert '"chart.title": "高分牌表环境构成"' in i18n
    assert '"chart.threshold"' in i18n
    assert "3%" in i18n
