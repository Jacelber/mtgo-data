from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier_shadow import (
    EQUIPMENT_MARKER,
    ShadowFeatureError,
    augment_shadow_counts,
    classify_shadow_counts,
    load_shadow_feature_manifest,
    mana_source_marker,
    spell_marker,
)
from mtgmeta.classifier_shadow_audit import rule_inventory
from mtgmeta.config import load_rule_set
from mtgmeta.rules import ClassificationRule, RuleSet
from tools.build_classifier_r2_shadow_rules import build_shadow_rules


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "docs" / "audits" / "classifier-r2"
RESULTS_ROOT = AUDIT_ROOT / "results"
MANIFEST = load_shadow_feature_manifest(AUDIT_ROOT / "semantic_card_features.yaml")
MODERN = load_rule_set(AUDIT_ROOT / "shadow_rules" / "modern.yaml")
STANDARD = load_rule_set(AUDIT_ROOT / "shadow_rules" / "standard.yaml")

PROTECTED_HASHES = {
    "docs/audits/classifier-r2/baseline_rules/modern.yaml": "3DF393EF3CBEBD655D6BE68BFAC8012E488673D52CBF663706906297378FE411",
    "docs/audits/classifier-r2/baseline_rules/standard.yaml": "DCEE23F09920290E16532C01A8AF5B7CA7106C73F5ED3F9626DE03200C6C063C",
    "data/modern/melee/events/434455.json": "0B4296A9573A4FACF4CFDE1CE98569156F78FDE6F5D2A1D3D662B54E2889E710",
    "docs/audits/classifier-r2/baseline_pickup/modern_known_archetypes.json": "6C3868B160E61F61F5FBF509EB6E56AA4E8EFB61AB26D4EA5E0D467A10D2F178",
    "docs/audits/classifier-r2/baseline_pickup/standard_known_archetypes.json": "311E102E971D6E5B12DBBBF8E50D8DF1D34D44EC4AA6E15684C1F6C340156032",
}

FEATURE_REPRESENTATIVES = {
    EQUIPMENT_MARKER: "Batterskull",
    mana_source_marker("white"): "Plains",
    mana_source_marker("blue"): "Island",
    mana_source_marker("black"): "Swamp",
    mana_source_marker("red"): "Mountain",
    mana_source_marker("green"): "Forest",
    spell_marker("white"): "Bandage",
    spell_marker("blue"): "Preordain",
    spell_marker("black"): "Feed the Swarm",
    spell_marker("red"): "Fire Magic",
    spell_marker("green"): "Heritage Reclamation",
}

MODERN_TARGET_PARENTS = {
    "grixis-persist",
    "agadeem-persist",
    "esper-persist",
    "cremator-goryos",
    "esper-goryos",
    "grixis-goryos",
    "dimir-tempo",
    "esper-ketramose",
    "esper-blink",
    "azorius-blink",
    "jeskai-stoneforge",
    "jeskai-blink",
    "mardu-blink",
    "orzhov-blink",
    "eldrazi-ramp-chant",
    "omnath-midrange",
    "chant-control",
    "azorius-control",
    "hollowvine",
    "rakdos-hollow-one",
    "living-end",
    "steel-cutter",
    "rakdos-steel-cutter",
    "mono-red-artifact",
    "prowess",
    "deaths-shadow",
    "mono-blue-tron",
}

STANDARD_TARGET_PARENTS = {
    "izzet-aggro",
    "azorius-prison",
    "boros-manufacturing",
    "kona-omniscience",
    "dark-jeskai-control",
    "white-sultai-control",
    "leyline-aggro",
}


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def _rules_by_id(rule_set: RuleSet) -> dict[str, tuple[str, ClassificationRule]]:
    return {
        rule.id: (archetype.id, rule)
        for archetype in rule_set.archetypes
        for rule in archetype.rules
    }


def _minimal_deck(rule: ClassificationRule) -> tuple[dict[str, int], dict[str, int]]:
    main: dict[str, int] = {}
    side: dict[str, int] = {}
    for item in rule.conditions:
        quantity = item.exact_count if item.exact_count is not None else item.min_count
        if not quantity:
            continue
        name = FEATURE_REPRESENTATIVES.get(item.card, item.card)
        target = side if item.zone == "side" else main
        target[name] = max(target.get(name, 0), quantity)
    return main, side


def _classify(
    rule_set: RuleSet,
    main: Mapping[str, int],
    side: Mapping[str, int] | None = None,
):
    return classify_shadow_counts(rule_set, main, side or {}, MANIFEST)


def _target_cases() -> list[tuple[str, RuleSet, str, str]]:
    cases = []
    for format_id, rule_set, parents in (
        ("modern", MODERN, MODERN_TARGET_PARENTS),
        ("standard", STANDARD, STANDARD_TARGET_PARENTS),
    ):
        for rule_id, (parent_id, _) in _rules_by_id(rule_set).items():
            if parent_id in parents:
                cases.append((format_id, rule_set, rule_id, parent_id))
    cases.extend(
        [
            ("modern", MODERN, "broodscale-combo-simic", "broodscale-combo"),
            ("modern", MODERN, "jeskai-control-primary", "jeskai-control"),
            ("standard", STANDARD, "sultai-control-bargain", "sultai-control"),
            ("standard", STANDARD, "dimir-deceit-primary", "dimir-deceit"),
        ]
    )
    return sorted(cases, key=lambda item: (item[0], item[2]))


def test_generated_shadow_rules_are_reproducible_and_valid() -> None:
    for format_id, rule_set, expected in (
        ("modern", MODERN, (70, 54, 119)),
        ("standard", STANDARD, (72, 11, 82)),
    ):
        path = AUDIT_ROOT / "shadow_rules" / f"{format_id}.yaml"
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == build_shadow_rules(
            format_id
        )
        inventory = rule_inventory(rule_set)
        assert (
            inventory["parent_count"],
            inventory["subtype_count"],
            inventory["rule_count"],
        ) == expected
        assert inventory["rule_ids_unique"] is True
        assert inventory["numeric_priorities_globally_unique"] is True
        assert inventory["priority_collisions"] == []


def test_r2_baseline_rules_pickup_state_and_event_are_byte_preserved() -> None:
    assert {
        path: _sha256(ROOT / path) for path in PROTECTED_HASHES
    } == PROTECTED_HASHES


def test_shadow_feature_adapter_is_explicit_immutable_and_fail_closed() -> None:
    main = {"Plains": 2, "Apostle's Blessing": 3, "Batterskull": 1}
    side = {"Fire Magic": 1}
    augmented_main, augmented_side = augment_shadow_counts(main, side, MANIFEST)
    assert main == {"Plains": 2, "Apostle's Blessing": 3, "Batterskull": 1}
    assert side == {"Fire Magic": 1}
    assert augmented_main[mana_source_marker("white")] == 2
    assert augmented_main[EQUIPMENT_MARKER] == 1
    assert spell_marker("white") not in augmented_main
    assert augmented_side[spell_marker("red")] == 1
    with pytest.raises(ShadowFeatureError, match="reserved"):
        augment_shadow_counts({mana_source_marker("white"): 1}, {}, MANIFEST)


@pytest.mark.parametrize(
    ("format_id", "rule_set", "rule_id", "parent_id"),
    _target_cases(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_every_r1_target_rule_has_an_executable_positive_case(
    format_id: str, rule_set: RuleSet, rule_id: str, parent_id: str
) -> None:
    del format_id
    _, rule = _rules_by_id(rule_set)[rule_id]
    main, side = _minimal_deck(rule)
    result = _classify(rule_set, main, side)
    assert result.status == "classified"
    assert (result.archetype_id, result.selected_rule_id) == (parent_id, rule_id)


@pytest.mark.parametrize(
    ("main", "expected_parent", "expected_subtype"),
    [
        (
            {
                "Goblin Charbelcher": 4,
                "Tameshi, Reality Architect": 4,
                "Orim's Chant": 4,
            },
            "mono-blue-belcher",
            None,
        ),
        (
            {
                "Cori-Steel Cutter": 4,
                "Lava Dart": 4,
                "Dragon's Rage Channeler": 4,
                "Monastery Swiftspear": 4,
                "Apostle's Blessing": 4,
            },
            "prowess",
            "mono-red",
        ),
        (
            {
                "Phelia, Exuberant Shepherd": 4,
                "Quantum Riddler": 4,
                "Solitude": 4,
                "Ephemerate": 2,
                "Hallowed Fountain": 1,
                "Guide of Souls": 4,
                "Ocelot Pride": 4,
            },
            "azorius-energy",
            None,
        ),
    ],
)
def test_modern_precedence_boundaries(
    main: dict[str, int], expected_parent: str, expected_subtype: str | None
) -> None:
    result = _classify(MODERN, main)
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        expected_parent,
        expected_subtype,
    )


@pytest.mark.parametrize(
    "main",
    [
        {
            "Goryo's Vengeance": 4,
            "Faithless Looting": 4,
            "Psychic Frog": 2,
        },
        {
            "Goryo's Vengeance": 4,
            "Faithless Looting": 4,
            "Psychic Frog": 4,
            "Ephemerate": 1,
        },
        {"Fatal Push": 4, "Psychic Frog": 2, "Watery Grave": 2},
        {"Living End": 4},
    ],
)
def test_modern_unsupported_structures_remain_unknown(main: dict[str, int]) -> None:
    assert _classify(MODERN, main).status == "unknown"


def test_standard_intersection_and_threshold_boundaries() -> None:
    kona_intersection = {
        "Kona, Rescue Beastie": 4,
        "Omniscience": 4,
        "Uthros, Titanic Godcore": 3,
        "Ashling, Rekindled": 1,
        "Hallowed Fountain": 1,
    }
    unsupported_leyline = {
        "Leyline of Resonance": 4,
        "Slickshot Show-Off": 4,
        "Island": 1,
        "Forest": 1,
    }
    white_subthreshold = {
        "Rakshasa's Bargain": 2,
        "Aang, Swift Savior": 1,
        "Three Steps Ahead": 2,
        "Emeritus of Abundance": 2,
    }
    for main in (kona_intersection, unsupported_leyline, white_subthreshold):
        assert _classify(STANDARD, main).status == "unknown"

    _, deceit_rule = _rules_by_id(STANDARD)["dimir-deceit-primary"]
    deceit_main, deceit_side = _minimal_deck(deceit_rule)
    assert _classify(STANDARD, deceit_main, deceit_side).archetype_id == "dimir-deceit"
    deceit_main["Requiting Hex"] = 1
    assert _classify(STANDARD, deceit_main, deceit_side).status == "unknown"


def test_committed_corpus_audit_outputs_match_the_accepted_shadow() -> None:
    summary = json.loads((RESULTS_ROOT / "summary.json").read_text(encoding="utf-8"))
    modern = summary["formats"]["modern"]
    standard = summary["formats"]["standard"]

    assert (modern["record_count"], standard["record_count"]) == (5792, 3936)
    assert modern["shadow_summary"]["statuses"] == {
        "classified": 5650,
        "unknown": 142,
    }
    assert standard["shadow_summary"]["statuses"] == {
        "classified": 3868,
        "unknown": 68,
    }
    for item in (modern, standard):
        assert item["order_independence_mismatches"] == 0
        assert item["shadow_summary"]["conflict"] == 0
        assert item["shadow_summary"]["residual_subtype"] == 0
        assert item["rule_inventory"]["numeric_priorities_globally_unique"] is True
        assert item["rule_inventory"]["rule_ids_unique"] is True

    assert modern["diagnostic_delta"] == {
        "classified": -14,
        "conflict": 0,
        "invalid_deck": 0,
        "multiple_matches": -495,
        "residual_subtype": 0,
        "same_parent_multiple_subtype_matches": -90,
        "unknown": 14,
    }
    assert standard["diagnostic_delta"] == {
        "classified": 3,
        "conflict": 0,
        "invalid_deck": 0,
        "multiple_matches": -86,
        "residual_subtype": 0,
        "same_parent_multiple_subtype_matches": -21,
        "unknown": -3,
    }
    assert summary["event_434455"]["event_bytes_unchanged"] is True
    assert summary["event_434455"]["participant_identifiers_retained"] is False
    assert summary["pickup_dry_run"]["status"] == "dry_run_not_applied"
    assert all(
        item["source_bytes_unchanged"]
        for item in summary["pickup_dry_run"]["formats"].values()
    )


def test_deck_transition_report_is_complete_and_deidentified() -> None:
    path = RESULTS_ROOT / "deck_transitions.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5792 + 3936
    assert all(
        forbidden not in path.read_text(encoding="utf-8").lower()
        for forbidden in ('"player', '"participant', '"username', '"account')
    )
    assert all(len(json.loads(line)["deck_id"]) == 20 for line in lines)


def test_production_modules_do_not_import_the_r2_shadow_path() -> None:
    shadow_modules = {"classifier_shadow.py", "classifier_shadow_audit.py"}
    for path in (ROOT / "src" / "mtgmeta").rglob("*.py"):
        if path.name in shadow_modules:
            continue
        assert "classifier_shadow" not in path.read_text(encoding="utf-8")
