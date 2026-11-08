"""Accepted pending builds and the existing-result protection boundary."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck, ClassificationResult
from mtgmeta.classifier_cards import use_card_facts
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set
from mtgmeta.legacy_policy import policy_counts
from mtgmeta.legacy_policy.reviewed_extensions import resolve_unclassified

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/legacy/accepted_remaining74.json").read_text(
        encoding="utf8"
    )
)


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case"])
def test_accepted_rows_through_normal_entrypoints(rules, case):
    expected = ("classified", case["parent"], case["subtype"])
    deck = {
        "main_deck": [{"name": n, "qty": q} for n, q in case["main"].items()],
        "sideboard": [{"name": n, "qty": q} for n, q in case["side"].items()],
    }
    for r in [
        classify_counts(rules, case["main"], case["side"]),
        classify_deck(rules, deck),
        classify_counts(reordered_rule_set(rules), case["main"], case["side"]),
    ]:
        assert (r.status, r.archetype_id, r.subtype_id) == expected


def unknown():
    return ClassificationResult(
        "unknown", None, None, None, None, None, None, (), (), (), (), None, False
    )


def test_fallback_preserves_existing_results_and_unrelated_conflicts(rules):
    c = next(c for c in CASES if c["case"] == "Q082")
    with use_card_facts(rules.facts):
        m, s = policy_counts(c["main"]), policy_counts(c["side"])
        accepted = classify_counts(rules, m, s)
        assert resolve_unclassified(m, s, accepted) is accepted
        conflict = replace(
            unknown(), status="conflict", conflict_kind="parent_archetype"
        )
        assert resolve_unclassified(m, s, conflict) is conflict
        invalid = replace(unknown(), status="invalid_deck")
        assert resolve_unclassified(m, s, invalid) is invalid


def test_low_cantrip_extension_does_not_drop_daze_requirement(rules):
    c = next(c for c in CASES if c["case"] == "Q020")
    with use_card_facts(rules.facts):
        m, s = policy_counts(c["main"]), policy_counts(c["side"])
        m["Daze"] = 3
        assert resolve_unclassified(m, s, unknown()).status == "unknown"


def test_new_core_is_required_not_just_shared_acceleration(rules):
    for ref, card in [
        ("Q003", "Vengevine"),
        ("Q006", "Amulet of Vigor"),
        ("Q042", "Mesmeric Orb"),
        ("Q052", "Metalwork Colossus"),
        ("Q083", "Price of Freedom"),
        ("Q021", "Mystic Forge"),
    ]:
        c = next(c for c in CASES if c["case"] == ref)
        with use_card_facts(rules.facts):
            m, s = policy_counts(c["main"]), policy_counts(c["side"])
            m.pop(card)
            assert resolve_unclassified(m, s, unknown()).archetype_id != c["parent"]


def test_free_tools_do_not_create_colors_in_extensions(rules):
    c = next(c for c in CASES if c["case"] == "Q025")
    with use_card_facts(rules.facts):
        r = resolve_unclassified(
            policy_counts(c["main"]),
            policy_counts({**c["side"], "Haywire Mite": 1}),
            unknown(),
        )
        assert r.archetype_id == "mono-red-prowess"


def test_new_color_evidence_cannot_be_silently_ignored(rules):
    c = next(c for c in CASES if c["case"] == "Q025")
    with use_card_facts(rules.facts):
        m = policy_counts({**c["main"], "Taiga": 1})
        s = policy_counts({**c["side"], "Veil of Summer": 1})
        assert resolve_unclassified(m, s, unknown()).status == "unknown"


def test_overlapping_extension_targets_remain_a_conflict(rules, monkeypatch):
    from mtgmeta.legacy_policy import reviewed_extensions

    definitions = [
        {"id": "test-burn", "parent": "burn", "main_min": {"Lightning Bolt": 4}},
        {
            "id": "test-prowess",
            "parent": "mono-red-prowess",
            "main_min": {"Lightning Bolt": 4},
        },
    ]
    with use_card_facts(rules.facts):
        for order in [definitions, list(reversed(definitions))]:
            monkeypatch.setattr(reviewed_extensions, "definitions", lambda: order)
            result = resolve_unclassified({"Lightning Bolt": 4}, {}, unknown())
            assert result.status == "conflict"
            assert {m.archetype_id for m in result.conflict_matches} == {
                "burn",
                "mono-red-prowess",
            }
