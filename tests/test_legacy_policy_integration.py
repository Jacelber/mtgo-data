"""Accepted card-only examples and integration failure modes; no private labels."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_counts, classify_deck, classifier_digest
from mtgmeta.classifier_shadow_audit import reordered_rule_set
from mtgmeta.config import load_rule_set, parse_rule_text, RuleConfigError
from mtgmeta.consumer import identity_display_name
from mtgmeta.legacy_policy import identities, structural_rules
from mtgmeta.legacy_policy.colors import audit
from mtgmeta.mtgo.stats import _classify_identity
from mtgmeta.mtgo.landing_editorial import _display_english
from mtgmeta.rules import ArchetypeDefinition, CardCondition, ClassificationRule

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "tests/fixtures/legacy/accepted_integration.json").read_text(
        encoding="utf8"
    )
)


@pytest.fixture(scope="module")
def rules():
    return load_rule_set(ROOT / "my_archetypes/legacy.yaml")


def deck(case):
    return {
        "main_deck": [{"name": n, "qty": q} for n, q in case["main"].items()],
        "sideboard": [{"name": n, "qty": q} for n, q in case["side"].items()],
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case"])
def test_accepted_counts_normalized_deck_and_statistics_agree(rules, case):
    result = classify_counts(rules, case["main"], case["side"])
    normalized = classify_deck(rules, deck(case))
    reordered = classify_counts(reordered_rule_set(rules), case["main"], case["side"])
    for value in [result, normalized, reordered]:
        assert (value.status, value.archetype_id, value.subtype_id) == (
            "classified",
            case["parent"],
            case["subtype"],
        )
    assert _classify_identity(deck(case), rules)[::2] == (
        case["parent"],
        case["subtype"],
    )


def test_reanimator_sideboard_transformations_do_not_split_black_main(rules):
    base = next(c for c in CASES if c["case"] == "black-main-side-transformation")
    for side in [
        {"Show and Tell": 4, "Underground Sea": 1},
        {"Stronghold Gambit": 4, "Badlands": 1},
        {"Serenity": 4, "Scrubland": 1},
    ]:
        r = classify_counts(rules, base["main"], side)
        assert (r.archetype_id, r.subtype_id) == ("mono-black-reanimator", None)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case"])
def test_mite_does_not_create_a_new_color(rules, case):
    result = classify_counts(rules, case["main"], {**case["side"], "Haywire Mite": 1})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        case["parent"],
        case["subtype"],
    )


def test_artifact_tempo_requires_the_spell_engine(rules):
    c = next(c for c in CASES if c["case"] == "artifact-tempo-nexus")
    for card in ["Emry, Lurker of the Loch", "Retrofitter Foundry", "Flame of Anor"]:
        r = classify_counts(
            rules, {n: q for n, q in c["main"].items() if n != card}, c["side"]
        )
        assert r.archetype_id != "izzet-artifacts"


def test_hogaak_branch_remains_open_to_green_but_mite_is_neutral(rules):
    c = next(c for c in CASES if c["case"] == "hogaak-blue-black")
    r = classify_counts(rules, c["main"], {**c["side"], "Haywire Mite": 1})
    assert r.subtype_id == "hogaak"
    r = classify_counts(
        rules, {**c["main"], "Bayou": 1}, {**c["side"], "Reverent Silence": 1}
    )
    assert r.subtype_id == "hogaak-g"


def test_chaos_exception_does_not_escape_painter():
    for label, pid, colors in [
        ("painter-welded-chaos", "painter-combo", set()),
        ("tron-castable-chaos", "mono-blue-tron", {"B", "R"}),
    ]:
        c = next(c for c in CASES if c["case"] == label)
        a = audit({"main": c["main"], "side": c["side"], "candidate": {"parent": pid}})
        assert {
            e["color"] for e in a["evidence"] if e["card"] == "Chaos Defiler"
        } == colors


def test_output_names_are_complete_for_statistics_and_landing():
    for row in identities().values():
        if row["subtype_id"]:
            assert (
                identity_display_name(row["parent_name"], row["english"])
                == row["english"]
            )
            assert (
                _display_english(row["parent_name"], row["english"]) == row["english"]
            )
    assert identity_display_name("Burn", "Mono-Red") == "Mono-Red Burn"


def test_beanstalk_merge_keeps_the_same_colors_without_yorion(rules):
    case = next(
        c for c in CASES
        if c["case"] == "yorion-beanstalk-enchantment-engine-without-brainstorm"
    )
    result = classify_counts(
        rules,
        case["main"],
        {n: q for n, q in case["side"].items() if n != "Yorion, Sky Nomad"},
    )
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "multicolor-beanstalk-control",
        "wubg",
    )
    assert not any(pid == "bant-beanstalk" for pid, _ in identities())


def test_policy_does_not_resolve_real_parent_conflicts(rules):
    def parent(pid):
        return ArchetypeDefinition(
            pid,
            pid,
            10,
            (),
            (ClassificationRule(pid, 10, None, (CardCondition("Island"),)),),
        )

    source = (parent("one"), parent("two"))
    r = classify_counts(
        replace(rules, recognition_archetypes=source), {"Island": 1}, {}
    )
    assert r.status == "conflict" and {m.archetype_id for m in r.conflict_matches} == {
        "one",
        "two",
    }


def test_policy_cannot_be_attached_to_another_format():
    text = (
        (ROOT / "my_archetypes/legacy.yaml")
        .read_text(encoding="utf8")
        .replace("format: legacy", "format: modern", 1)
    )
    with pytest.raises(RuleConfigError, match="identity_policy"):
        parse_rule_text(text)


def test_digest_covers_structure_and_is_order_independent(rules):
    assert classifier_digest(rules) == classifier_digest(reordered_rule_set(rules))
    assert classifier_digest(rules) != classifier_digest(structural_rules(rules))
    source = list(rules.recognition_archetypes)
    source[0] = replace(source[0], priority=source[0].priority + 1)
    assert classifier_digest(rules) != classifier_digest(
        replace(rules, recognition_archetypes=tuple(source))
    )


def test_policy_digest_is_portable_across_checkout_line_endings(tmp_path, monkeypatch):
    import mtgmeta.legacy_policy as policy

    monkeypatch.setattr(policy, "ROOT", tmp_path)
    code = tmp_path / "policy.py"
    data = tmp_path / "facts.json"
    code.write_bytes(b"x = 1\n")
    data.write_bytes(b'{"b":2,"a":1}\n')
    before = policy.policy_subject()
    code.write_bytes(b"x = 1\r\n")
    data.write_bytes(b'{\r\n "a":1, "b":2\r\n}\r\n')
    assert policy.policy_subject() == before
    data.write_bytes(b'{"a":1,"b":3}')
    assert policy.policy_subject() != before


def test_unreviewed_payment_role_and_invalid_input_do_not_guess(rules):
    c = next(c for c in CASES if c["case"] == "ninja-annex-room-alias")
    r = classify_counts(rules, c["main"], {**c["side"], "Unknown Future Tool": 1})
    assert r.status == "unknown" and any("legacy_identity:" in e for e in r.errors)
    assert classify_counts(rules, {"Island": -1}, {}).status == "invalid_deck"
