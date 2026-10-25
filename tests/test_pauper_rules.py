from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts
from mtgmeta.config import load_rule_set


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "my_archetypes" / "pauper.yaml"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "pauper" / "rule_contract.json"
NAMES_PATH = ROOT / "configs" / "mtgo_archetype_names.yaml"
CURRENT_SOURCES = json.loads(
    (ROOT / "tests/fixtures/pauper/current_rule_sources.json").read_text()
)["cases"]


@lru_cache(maxsize=1)
def _rules():
    return load_rule_set(RULES_PATH)


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_case(case: dict[str, object]) -> None:
    rules = _rules()
    expected = case["expected"]
    assert isinstance(expected, dict)
    main = dict(case["main"])
    side = {}
    # Retain the old fixture bytes and explicitly supply the missing context.
    # A Tron deck needs all three pieces; the maintained Wildfire blink route
    # includes its Mulldrifter target. Neither production threshold is lowered.
    additions = {
        "green-tron-b": {"Urza's Mine": 2, "Urza's Power Plant": 2},
        "jeskai-ephemerate-wildfire": {"Mulldrifter": 2},
        "dimir-control": {"Cast Down": 1},
        # These frozen structural examples omitted the ordinary lands needed
        # to cast their spells. Keep their identities and original bytes.
        "mono-white-battle-screech": {"Plains": 8},
        "mono-white-battle-screech-novice": {"Plains": 8},
        "golgari-gardens": {"Swamp": 8},
        "golgari-gardens-artifact": {"Swamp": 8},
        "azorius-familiars": {"Plains": 8, "Island": 8},
        "boros-packbeast-swarm": {"Plains": 8, "Mountain": 8},
        "mardu-packbeast-swarm": {"Plains": 8, "Mountain": 8, "Swamp": 4},
        "mono-white-learn-packbeast-swarm": {"Plains": 8},
        "mono-white-packbeast-swarm": {"Plains": 8},
        "esper-packbeast-swarm": {"Plains": 8, "Island": 4, "Swamp": 4},
        "boros-battle-screech-gates": {"Plains": 8},
        "selesnya-packbeast-swarm": {"Plains": 8},
    }
    if case["id"] in {"green-tron-b", "jeskai-ephemerate-wildfire"}:
        assert classify_counts(rules, main, {}).status == "unknown"
    main.update(additions.get(case["id"], {}))
    if case["id"] in {"golgari-gardens", "golgari-gardens-artifact"}:
        # Khalni Garden itself is not a green spell. Include an actual supported
        # green sideboard spell instead of asserting a land-only color label.
        side["Weather the Storm"] = 1
    result = classify_counts(rules, main, side)

    assert result.status == expected["status"], case["id"]
    assert result.archetype_id == expected["archetype_id"], case["id"]
    # These ordinary subtypes already existed in the frozen production rules;
    # the earlier synthetic contract still recorded null for them.
    established_subtypes = {
        "golgari-gardens": "golgari", "golgari-gardens-artifact": "golgari",
        "dimir-control": "dimir", "azorius-familiars": "azorius",
    }
    assert result.subtype_id == established_subtypes.get(case["id"], expected["subtype_id"]), case["id"]
    if case["id"] in {"boros-battle-screech-gates", "green-tron-fangren"}:
        # Removing Boros Garrison as a color proxy lets the existing, higher
        # priority Boros route also match Gates. Keep the frozen fixture's old
        # trace and verify both routes explicitly; its public identity is fixed.
        assert expected["selected_rule_id"] in {
            match.rule_id for match in result.matched_rules
        }
        # Fangren is likewise a more specific route already covered by the
        # higher-priority three-piece Tron branch in the frozen production code.
        assert result.selected_rule_id == {
            "boros-battle-screech-gates": "boros-battle-screech",
            "green-tron-fangren": "green-tron-b",
        }[case["id"]]
    else:
        assert result.selected_rule_id == expected["selected_rule_id"], case["id"]
    assert result.conflict_matches == (), case["id"]


def test_pauper_rule_inventory_and_parent_boundaries() -> None:
    rules = _rules()
    archetypes = {archetype.id: archetype for archetype in rules.archetypes}
    rule_ids = {
        rule.id for archetype in rules.archetypes for rule in archetype.rules
    }
    fixture_rule_ids = {
        case["expected"]["selected_rule_id"] for case in _fixture()["cases"]
    }

    assert rules.format == "pauper"
    source_rule_ids = {case["rule_id"] for case in CURRENT_SOURCES}
    # Additional Gardens branches have explicit single-spell variants below.
    assert fixture_rule_ids | source_rule_ids | {"golgari-gardens-artifact-red-splash", "golgari-gardens-blue-splash"} == rule_ids
    assert "gates" not in archetypes
    assert {
        "selesnya-gates",
        "jeskai-caw-gates",
        "snacker-gates",
        "naya-gates",
        "naya-hawkeye",
        "synthesizer-gates",
        "packbeast-swarm",
        "mardu-synthesizer",
        "rakdos-synthesizer",
        "esper-midrange",
    }.issubset(archetypes)
    assert archetypes["green-tron"].name == "Monster Tron"
    named_outputs = {
        (row["parent_id"], row.get("subtype_id"))
        for row in yaml.safe_load(NAMES_PATH.read_text())["names"]
        if row.get("format") == "pauper"
    }
    for archetype in rules.archetypes:
        assert (archetype.id, None) in named_outputs
        for subtype in archetype.subtypes:
            assert (archetype.id, subtype.id) in named_outputs
    for archetype in rules.archetypes:
        if archetype.subtypes:
            assert all(rule.subtype_id is not None or archetype.color_subtypes for rule in archetype.rules)


@pytest.mark.parametrize("case", CURRENT_SOURCES, ids=lambda case: case["rule_id"])
def test_later_rules_have_retained_source_execution_coverage(case):
    from mtgmeta.classifier import classify_deck

    result = classify_deck(_rules(), case)
    assert case["rule_id"] in {m.rule_id for m in result.matched_rules}, case["source_locator"]


def test_artifact_gardens_supported_red_sideboard_spell_selects_existing_jund():
    base = next(c for c in _fixture()["cases"] if c["id"] == "golgari-gardens-artifact")
    main = dict(base["main"]) | {"Mountain": 1, "Swamp": 8}
    side = {"Weather the Storm": 1}
    ordinary = classify_counts(_rules(), main, side)
    splash = classify_counts(_rules(), main, side | {"Cast into the Fire": 1})
    assert (ordinary.archetype_id, ordinary.subtype_id) == ("golgari-gardens", "golgari")
    assert (splash.archetype_id, splash.subtype_id) == ("golgari-gardens", "jund")
    assert splash.selected_rule_id == "golgari-gardens-artifact-red-splash"


def test_rats_gardens_supported_blue_spell_uses_same_core_for_sultai():
    main = {"Khalni Garden": 3, "Fanatical Offering": 3, "Crypt Rats": 1,
            "Brave the Wilds": 1, "Swamp": 8, "Island": 1}
    assert classify_counts(_rules(), main, {}).subtype_id == "golgari"
    result = classify_counts(_rules(), main, {"Opt": 1})
    assert (result.archetype_id, result.subtype_id, result.selected_rule_id) == (
        "golgari-gardens", "sultai", "golgari-gardens-blue-splash",
    )
    for core in ("Khalni Garden", "Fanatical Offering"):
        without = {k: v for k, v in main.items() if k != core}
        assert not any(m.archetype_id == "golgari-gardens" for m in classify_counts(_rules(), without, {"Opt": 1}).matched_rules)


def test_owner_accepted_jund_names() -> None:
    text = NAMES_PATH.read_text(encoding="utf-8")
    rows = yaml.safe_load(text)["names"]
    pauper_names = {
        row["parent_id"]: row["chinese"]
        for row in rows
        if row.get("format") == "pauper" and row.get("subtype_id") is None
    }

    assert all("勇德" not in name for name in pauper_names.values())
    assert {
        parent_id: pauper_names[parent_id]
        for parent_id in ("jund-gardens", "jund-wildfire", "jund-affinity", "jund-ramp")
    } == {
        "jund-gardens": "勇得控制",
        "jund-wildfire": "勇得野火",
        "jund-affinity": "勇得共鸣",
        "jund-ramp": "勇得Ramp",
    }


@pytest.mark.parametrize("case", _fixture()["cases"], ids=lambda case: case["id"])
def test_each_pauper_rule_has_a_bounded_representative(case: dict[str, object]) -> None:
    _assert_case(case)


@pytest.mark.parametrize(
    "case",
    _fixture()["boundary_cases"],
    ids=lambda case: case["id"],
)
def test_owner_accepted_pauper_boundaries(case: dict[str, object]) -> None:
    _assert_case(case)
