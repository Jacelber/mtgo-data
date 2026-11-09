"""Accepted historical mapping and the stock/tool versus blue-engine boundary."""
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set
from mtgmeta.legacy_policy.tron import output_identity

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/legacy/accepted_tron_mapping.json").read_text(encoding="utf8"))


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case"])
def test_accepted_mapping_and_rule_order(rules, case):
    for r in (rules, reordered_rule_set(rules)):
        result = classify_counts(r, case["main"], case["side"])
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified", case["parent"], case["subtype"],
        )


def test_stock_and_single_force_do_not_define_blue_parent():
    for extra in ({}, {"Force of Will": 1}):
        assert output_identity("mono-blue-tron", "mono-blue", {"Stock Up": 4, **extra}) == ("tron", "mono-blue")


def test_transmute_core_needs_no_force_and_preserves_actual_colors():
    main = {"Transmute Artifact": 3, "Coveted Jewel": 2, "Relic of Sauron": 3, "Grim Monolith": 4}
    assert output_identity("non-white-tron", None, main) == ("blue-tron", "non-white")
    assert output_identity("forge-combo", None, main) == ("forge-combo", None)


def test_unvalidated_colorless_recognition_still_defers_to_extensions():
    assert output_identity("colorless-tron", None, {"Stock Up": 4}) == ("colorless-tron", None)


def test_four_color_blue_engine_keeps_non_red_payment_subtype():
    main = {"Force of Will": 4, "Force of Negation": 3, "Stock Up": 4}
    assert output_identity("non-red-tron", None, main) == ("blue-tron", "non-red")


def test_reviewed_artifact_tools_do_not_hide_a_colored_spell_plan(rules):
    from mtgmeta.legacy_policy.nexus_colors import audit_color
    main = {
        "Planar Nexus": 4, "Urza's Tower": 4, "Urza's Mine": 2,
        "Urza's Power Plant": 2, "Karn, the Great Creator": 4,
        "Grim Monolith": 4, "The One Ring": 4, "Kozilek's Command": 4,
        "Lich's Relic": 1, "Portable Hole": 1, "Perilous Snare": 1, "Mishra's Research Desk": 1,
    }
    tools = audit_color(rules, "colorless-tron", main, {"Mindbreak Trap": 2})
    assert tools["subtype"] == "colorless" and not tools["issues"]
    assert set(tools["excluded"]) >= {"Lich's Relic", "Portable Hole", "Mindbreak Trap"}
    colored = audit_color(rules, "colorless-tron", {**main, "Thoughtseize": 4}, {})
    assert colored["subtype"] != "colorless"
