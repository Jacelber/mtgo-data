"""Scoped, owner-approved Absolute Virtue copying use in Standard Spider-Man."""

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.classifier_cards import deck_colors
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.rules import validate_rule_data

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_spider_copy.json").read_text())["cases"]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/standard.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["record_id"])
def test_reviewed_copy_targets_keep_dimir_without_erasing_other_white(rules, case):
    result = classify_deck(rules, case)
    assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "dimir-spider-man", "dimir")
    colors = dict(result.color_diagnostics)["dimir-spider-man"]
    target = next(c for c in colors.contributions if c.card == "Absolute Virtue")
    assert target.colors == ()
    assert target.reason == "standard-spider-man:noncast-target"
    main, side = deck_to_counts(case)
    assert "white" in deck_colors(main, side).colors
    with_white = classify_counts(rules, main, side | {"Rest in Peace": 1})
    assert dict(with_white.color_diagnostics)["dimir-spider-man"].colors == {"white", "blue", "black"}
    assert not any(m.archetype_id == "dimir-spider-man" for m in with_white.matched_rules)


def test_copy_profile_needs_copy_source_and_respects_explicit_normal_cast():
    main = {"Superior Spider-Man": 4, "Watery Grave": 4, "Bleachbone Verge": 1, "Opt": 4, "Duress": 1}
    side = {"Absolute Virtue": 2}
    profile = "standard-spider-man"
    assert deck_colors(main, side, profile=profile).colors == {"blue", "black"}
    assert deck_colors(main | side, {}, profile=profile).colors == {"blue", "black"}
    no_source = {k: v for k, v in main.items() if k != "Superior Spider-Man"}
    assert deck_colors(no_source, side, profile=profile).colors == {"white", "blue", "black"}
    assert deck_colors(main, side, profile=profile, uses={"Absolute Virtue": "normal_cast"}).colors == {"white", "blue", "black"}
    assert deck_colors(main, side | {"Rest in Peace": 1}, profile=profile).colors == {"white", "blue", "black"}
    # An unrelated potential copy target is not automatically excluded.
    assert deck_colors(main, {"Solitude": 1}, profile=profile).colors == {"white", "blue", "black"}


def test_copy_profile_is_standard_only():
    data = yaml.safe_load((ROOT / "my_archetypes/standard.yaml").read_text())
    data["archetypes"] = [a for a in data["archetypes"] if a["id"] == "dimir-spider-man"]
    assert not validate_rule_data(data)
    for fmt in ("modern", "pioneer", "pauper"):
        assert any(f.message == "profile is Standard-only" for f in validate_rule_data(data | {"format": fmt}))


def test_approved_grixis_sources_and_unrelated_red_spell(rules):
    from mtgmeta.mana_identity import require_complete_mana_identities, rendered_mana_identities

    cases = json.loads((ROOT / "tests/fixtures/classifier_round1_standard_grixis_spider.json").read_text())["cases"]
    assert len(cases) == 7
    for case in cases:
        result = classify_deck(rules, case)
        assert (result.status, result.archetype_id, result.subtype_id) == ("classified", "dimir-spider-man", "grixis")
        main, side = deck_to_counts(case)
        # Replace the observed payoff; neither Ashling nor a named red land
        # defines this color child.
        red = {"Ashling, Rekindled", "Traumatic Critique", "Pyroclasm", "Ajani Unrelenting", "Thor, God of Thunder"}
        main = {k: v for k, v in main.items() if k not in red}
        side = {k: v for k, v in side.items() if k not in red}
        assert classify_counts(rules, main, side).subtype_id == "dimir"
        assert classify_counts(rules, main, side | {"Abrade": 1}).subtype_id == "grixis"
    # Color alone cannot bypass all of the family's structural routes.
    unrelated = {"Island": 8, "Swamp": 8, "Mountain": 8, "Opt": 4, "Duress": 4, "Abrade": 4}
    assert not any(m.archetype_id == "dimir-spider-man" for m in classify_counts(rules, unrelated, {}).matched_rules)
    names = yaml.safe_load((ROOT / "configs/mtgo_archetype_names.yaml").read_text())["names"]
    row = next(n for n in names if n["identity_key"] == "standard|dimir-spider-man|grixis")
    assert (row["english"], row["chinese"]) == ("Grixis Spider-Man", "格利极蜘蛛侠")
    require_complete_mana_identities(ROOT, "standard")
    assert rendered_mana_identities(ROOT, "standard")["dimir-spider-man/grixis"] == ("u", "b", "r")
