"""Post lands determine the family even when Tower/Nexus also recognize Tron."""
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


def owner_deck():
    event = json.loads((ROOT / "data/legacy/Legacy_Challenge_32_12858119.json").read_text())
    deck = next(d for d in event["players"] if str(d["final_rank"]) == "3")
    return tuple({c["name"]: c["qty"] for c in deck[zone]} for zone in ("main_deck", "sideboard"))


def test_post_precedence_and_owner_name_survive_rule_order(rules):
    main, side = owner_deck()
    for candidate in (rules, reordered_rule_set(rules)):
        result = classify_counts(candidate, main, side)
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified", "multicolor-post", None,
        )
        assert result.archetype_name == "Multi-Color Cloudpost"


def test_tower_nexus_without_post_lands_keeps_the_tron_family(rules):
    main, side = owner_deck()
    main["Urza's Mine"] = main.pop("Cloudpost")
    main["Urza's Power Plant"] = main.pop("Glimmerpost")
    result = classify_counts(rules, main, side)
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified", "tron", "multicolor",
    )
    assert result.subtype_name == "Multi-Color Tron"


def test_post_routing_preserves_a_supported_single_blue_plan(rules):
    main, _ = owner_deck()
    side = {"Tormod's Crypt": 1}
    result = classify_counts(rules, main, side)
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified", "blue-post", "mono-blue",
    )
