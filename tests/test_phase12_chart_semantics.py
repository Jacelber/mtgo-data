import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _visual_metadata() -> dict:
    script = """
require("./assets/js/phase8/archetype-visuals.js");
process.stdout.write(JSON.stringify(global.P8ArchetypeVisuals));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return json.loads(result.stdout)


def _rendered_identities(format_name: str) -> set[str]:
    identities: set[str] = set()
    for range_name in ("1w", "4w", "12w"):
        document = json.loads(
            (ROOT / f"stats/{format_name}/mtgo/range_{range_name}.json").read_text(
                encoding="utf-8"
            )
        )
        for parent in document["archetypes"]:
            if parent["id"] == "unknown":
                continue
            active = [
                subtype
                for subtype in parent.get("subtypes", [])
                if subtype.get("count", 0) > 0
                or subtype.get("high_score_count", 0) > 0
                or subtype.get("top8_count", 0) > 0
                or subtype.get("avg_points_per_round") is not None
            ]
            if len(active) == 1:
                identities.add(f"{parent['id']}/{active[0]['id']}")
            else:
                identities.add(parent["id"])
                if len(active) >= 2:
                    identities.update(
                        f"{parent['id']}/{subtype['id']}" for subtype in active
                    )
    return identities


def _composition_identities(format_name: str) -> set[str]:
    identities: set[str] = set()
    for range_name in ("1w", "4w", "12w"):
        document = json.loads(
            (ROOT / f"stats/{format_name}/mtgo/range_{range_name}.json").read_text(
                encoding="utf-8"
            )
        )
        identities.update(
            item["id"]
            for item in document["archetypes"]
            if item["id"] != "unknown" and item["high_score_share"] >= 0.03
        )
    return identities


def test_statistics_uses_one_high_score_composition_bar() -> None:
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")
    core = (ROOT / "assets/js/phase8/app-core.js").read_text(encoding="utf-8")
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
    assert "accessibleCompositionSegment({" in chart
    assert "data-composition-identity" in core
    assert "data-tooltip" in core
    assert "top8_share" not in chart
    assert "pie" not in mtgo.lower()
    assert "pie" not in interaction.lower()
    assert ".pie-" not in styles


def test_composition_uses_approved_first_card_without_rendering_card_names() -> None:
    metadata = _visual_metadata()
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")
    interaction = (ROOT / "assets/js/phase8/app.js").read_text(encoding="utf-8")

    expected = {
        "standard": {
            "4-color-tablet": "Inevitable Defeat",
            "azorius-prison": "High Noon",
            "dimir-excruciator": "Doomsday Excruciator",
            "izzet-fling": "Callous Sell-Sword",
            "izzet-prowess": "Boomerang Basics",
            "izzet-spellementals": "Sunderflock",
            "jeskai-lessons": "Jeskai Revelation",
            "mono-green-landfall": "Earthbender Ascension",
            "orzhov-lifegain": "Amalia Benavides Aguirre",
            "selesnya-landfall": "Erode",
            "selesnya-offense": "Practiced Offense",
            "sultai-reanimator": "Bringer of the Last Gift",
        },
        "modern": {
            "affinity": "Mox Opal",
            "boros-energy": "Guide of Souls",
            "boros-land-destruction": "Cleansing Wildfire",
            "broodscale-combo": "Basking Broodscale",
            "chant-control": "Orim's Chant",
            "devoted-druid-combo": "Devoted Druid",
            "dimir-tempo": "Psychic Frog",
            "domain-zoo": "Scion of Draco",
            "eldrazi-tron": "Urza's Tower",
            "esper-blink": "Phelia, Exuberant Shepherd",
            "esper-goryos": "Goryo's Vengeance",
            "esper-ketramose": "Ketramose, the New Dawn",
            "fight-rigging": "Fight Rigging",
            "grixis-persist": "Persist",
            "living-end": "Living End",
            "prowess": "Cori-Steel Cutter",
            "ruby-storm": "Ruby Medallion",
            "simic-neoform": "Neoform",
        },
    }
    for format_name, identities in expected.items():
        assert set(metadata["representativeCards"][format_name]) == set(identities)
        assert set(identities) == _composition_identities(format_name)
        for identity, card_name in identities.items():
            slots = metadata["representativeCards"][format_name][identity]
            assert len(slots) == 2
            assert slots[0]["name"] == card_name
            assert slots[1] is None
            image = slots[0]["image"].removeprefix("../")
            assert (ROOT / "assets" / image).is_file()

    chart = mtgo[mtgo.index("function chartHtml"):mtgo.index("function sortedArchetypes")]
    assert "item.name" in chart
    assert "item.share" in chart
    assert "REPRESENTATIVE_CARDS[state.format]?.[item.id]?.[0]?.image" in chart
    assert "card.name" not in chart
    assert "touchedCompositionIdentity" in interaction
    assert 'matchMedia("(hover: none)")' in interaction
    assert "data-stats-parent" in mtgo


def test_top8_share_remains_in_the_authoritative_table() -> None:
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")

    assert "pct(record.top8_share)" in mtgo
    assert 'sortHeader(t("stats.top8_share"), "top8_share")' in mtgo


def test_mana_identity_covers_every_rendered_identity_without_inference() -> None:
    metadata_source = (ROOT / "assets/js/phase8/archetype-visuals.js").read_text(
        encoding="utf-8"
    )
    metadata = _visual_metadata()
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")

    assert metadata["manaIdentities"]["standard"]["white-sultai-control"] == [
        "w", "u", "b", "g"
    ]
    assert metadata["manaIdentities"]["modern"]["fling-goyf"] == ["r", "g"]
    for format_name in ("standard", "modern"):
        assert set(metadata["manaIdentities"][format_name]) == _rendered_identities(
            format_name
        )
    assert "assets/images/mana/${color}.svg" in mtgo
    assert "MANA_IDENTITIES[state.format]?.[identityId]" in mtgo
    assert "infer" not in metadata_source.lower()

    for symbol in "wubrgc":
        assert (ROOT / f"assets/images/mana/{symbol}.svg").is_file()


def test_product_name_is_not_redefined_by_chart_work() -> None:
    i18n = (ROOT / "assets/js/phase8/i18n.js").read_text(encoding="utf-8")

    assert '"product.stats": "MTGO占比统计"' in i18n
    assert '"chart.title": "高分牌表环境构成"' in i18n
    assert '"chart.threshold"' in i18n
    assert "3%" in i18n
