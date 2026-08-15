from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_shadow_audit import (
    _event_decks,
    diagnostic_flags,
    identity_signature,
    reordered_rule_set,
)
from mtgmeta.config import load_rule_set
from mtgmeta.deck import deck_to_counts
from mtgmeta.mtgo import stats


ROOT = Path(__file__).resolve().parents[1]
FROZEN_MANIFEST = (
    ROOT
    / "docs"
    / "audits"
    / "classifier-r4"
    / "baseline_unknown_inputs"
    / "configs"
    / "classifier_semantic_features.yaml"
)


def _top8_deck(format_id: str, event_id: str, player: str) -> dict[str, object]:
    document = json.loads(
        (
            ROOT
            / "stats"
            / format_id
            / "mtgo"
            / "top8"
            / "2026-W32.json"
        ).read_text(encoding="utf-8")
    )
    event = next(item for item in document["events"] if item["event_id"] == event_id)
    placement = next(
        item
        for item in event["placements"]
        if item["exact_deck"]["player"] == player
    )
    return placement["exact_deck"]


@pytest.mark.parametrize(
    ("format_id", "event_id", "player", "parent_id", "subtype_id", "rule_id"),
    [
        (
            "standard",
            "12850815",
            "itstime",
            "izzet-fling",
            None,
            "izzet-fling-primary",
        ),
        (
            "standard",
            "12850613",
            "MacIsaac",
            "leyline-aggro",
            "izzet",
            "leyline-aggro-izzet",
        ),
        (
            "modern",
            "12851108",
            "manohito",
            "broodscale-combo",
            "gruul",
            "broodscale-combo-gruul",
        ),
    ],
)
def test_reviewed_w32_exact_decks_select_owner_corrected_identity(
    format_id: str,
    event_id: str,
    player: str,
    parent_id: str,
    subtype_id: str,
    rule_id: str,
) -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
    deck = _top8_deck(format_id, event_id, player)
    main, side = deck_to_counts(deck)

    assert sum(main.values()) == 60
    assert sum(side.values()) == 15
    result = classify_counts(rules, main, side)
    reordered = classify_counts(reordered_rule_set(rules), main, side)

    assert result.status == "classified"
    assert result.archetype_id == parent_id
    assert result.subtype_id == subtype_id
    assert result.selected_rule_id == rule_id
    assert identity_signature(result) == identity_signature(reordered)


@pytest.mark.parametrize("leyline_count", [0, 1])
def test_standard_at_most_one_leyline_remains_izzet_fling(
    leyline_count: int,
) -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / "standard.yaml")
    result = classify_counts(
        rules,
        {
            "Callous Sell-Sword": 3,
            "Stormchaser's Talent": 4,
            "Spirebluff Canal": 4,
            "Leyline of Resonance": leyline_count,
        },
        {},
    )

    assert result.archetype_id == "izzet-fling"
    assert result.subtype_id is None
    assert result.selected_rule_id == "izzet-fling-primary"


def test_standard_two_leylines_cannot_select_izzet_fling() -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / "standard.yaml")
    result = classify_counts(
        rules,
        {
            "Callous Sell-Sword": 3,
            "Stormchaser's Talent": 4,
            "Spirebluff Canal": 4,
            "Leyline of Resonance": 2,
        },
        {},
    )

    assert result.selected_rule_id != "izzet-fling-primary"


@pytest.mark.parametrize("event_id", ["12842468", "12842882"])
def test_reviewed_single_leyline_lists_remain_izzet_fling(event_id: str) -> None:
    event_path = next((ROOT / "data" / "standard").glob(f"*_{event_id}.json"))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    deck = next(player for player in event["players"] if player["player"] == "Arcbound_Papi")
    main, side = deck_to_counts(deck)
    rules = load_rule_set(ROOT / "my_archetypes" / "standard.yaml")
    result = classify_counts(rules, main, side)

    assert main["Leyline of Resonance"] == 1
    assert result.archetype_id == "izzet-fling"
    assert result.selected_rule_id == "izzet-fling-primary"


def test_standard_leyline_rules_keep_original_priority_and_no_talent_shell() -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / "standard.yaml")
    fling = next(item for item in rules.archetypes if item.id == "izzet-fling")
    leyline = next(item for item in rules.archetypes if item.id == "leyline-aggro")

    priorities = {rule.id: rule.priority for rule in leyline.rules}
    assert fling.priority == 53000
    assert leyline.priority == 27040
    assert priorities == {
        "leyline-aggro-izzet": 27040,
        "leyline-aggro-gruul": 27030,
        "leyline-aggro-boros": 27020,
        "leyline-aggro-rakdos": 27010,
        "leyline-aggro-mono-red": 27000,
    }


@pytest.mark.parametrize(
    "red_source",
    ["Copperline Gorge", "Grove of the Burnwillows", "Karplusan Forest"],
)
def test_each_reviewed_main_red_source_selects_gruul_broodscale(
    red_source: str,
) -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    result = classify_counts(
        rules,
        {
            "Basking Broodscale": 4,
            "Blade of the Bloodchief": 4,
            "Forest": 2,
            red_source: 1,
        },
        {},
    )

    assert result.archetype_id == "broodscale-combo"
    assert result.subtype_id == "gruul"
    assert result.selected_rule_id == "broodscale-combo-gruul"


def test_sideboard_only_red_source_does_not_change_mono_green_broodscale() -> None:
    rules = load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    result = classify_counts(
        rules,
        {
            "Basking Broodscale": 4,
            "Blade of the Bloodchief": 4,
            "Forest": 2,
        },
        {"Copperline Gorge": 4},
    )

    assert result.archetype_id == "broodscale-combo"
    assert result.subtype_id == "mono-green"
    assert result.selected_rule_id == "broodscale-combo-mono-green"


def _baseline_rules(tmp_path: Path, format_id: str):
    document = yaml.safe_load(
        (
            ROOT
            / "docs"
            / "audits"
            / "classifier-r4"
            / "shadow_rules"
            / f"{format_id}.yaml"
        ).read_text(encoding="utf-8")
    )
    if format_id == "standard":
        spellementals = next(
            item
            for item in document["archetypes"]
            if item["id"] == "izzet-spellementals"
        )
        rule = next(
            item
            for item in spellementals["rules"]
            if item["id"] == "izzet-spellementals-primary"
        )
        rule["conditions"]["all"].append(
            {
                "card": "Stormchaser's Talent",
                "zone": "main",
                "exact_count": 0,
            }
        )

    root = tmp_path / format_id
    rules_dir = root / "my_archetypes"
    manifest_dir = root / "configs"
    rules_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "classifier_semantic_features.yaml").write_bytes(
        FROZEN_MANIFEST.read_bytes()
    )
    rule_path = rules_dir / f"{format_id}.yaml"
    rule_path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    return load_rule_set(rule_path)


def _identity(result) -> tuple[str, str | None, str | None]:
    return result.status, result.archetype_id, result.subtype_id


def _audit_records(
    baseline_rules,
    candidate_rules,
    records,
) -> tuple[Counter[tuple[object, ...]], Counter[str]]:
    reordered = reordered_rule_set(candidate_rules)
    transitions: Counter[tuple[object, ...]] = Counter()
    diagnostics: Counter[str] = Counter()
    for main, side in records:
        baseline = classify_counts(baseline_rules, main, side)
        candidate = classify_counts(candidate_rules, main, side)
        reordered_candidate = classify_counts(reordered, main, side)
        assert identity_signature(candidate) == identity_signature(reordered_candidate)
        flags = diagnostic_flags(candidate, candidate_rules)
        diagnostics.update(name for name, enabled in flags.items() if enabled)
        if _identity(baseline) != _identity(candidate):
            transitions[
                (
                    baseline.archetype_id,
                    baseline.subtype_id,
                    candidate.archetype_id,
                    candidate.subtype_id,
                    candidate.selected_rule_id,
                )
            ] += 1
    return transitions, diagnostics


def _current_mtgo_records(format_id: str):
    for _day, event in stats.load_all_events(ROOT, format_id):
        for player in event.get("players", []):
            yield deck_to_counts(player)


def _frozen_records(format_id: str):
    fixture = (
        ROOT
        / "tests"
        / "fixtures"
        / format_id
        / (
            "frozen_j6e_corpus.json"
            if format_id == "modern"
            else "frozen_legacy_corpus.json"
        )
    )
    for record in json.loads(fixture.read_text(encoding="utf-8"))["records"]:
        yield dict(record["main"]), dict(record["side"])


@pytest.mark.committed_baseline
def test_complete_classifier_impact_is_limited_to_owner_corrections(
    tmp_path: Path,
) -> None:
    expected_transitions = {
        "standard": {
            ("izzet-fling", None, "izzet-prowess", None),
            ("izzet-fling", None, "leyline-aggro", "izzet"),
        },
        "modern": {
            (
                "broodscale-combo",
                "mono-green",
                "broodscale-combo",
                "gruul",
            ),
        },
    }
    audit = {}
    for format_id in ("standard", "modern"):
        baseline = _baseline_rules(tmp_path, format_id)
        candidate = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
        current_transitions, current_diagnostics = _audit_records(
            baseline, candidate, _current_mtgo_records(format_id)
        )
        frozen_transitions, frozen_diagnostics = _audit_records(
            baseline, candidate, _frozen_records(format_id)
        )

        observed = {
            transition[:4]
            for transition in (*current_transitions, *frozen_transitions)
        }
        assert observed <= expected_transitions[format_id]
        assert current_diagnostics["conflict"] == 0
        assert current_diagnostics["invalid_deck"] == 0
        assert current_diagnostics["residual_subtype"] == 0
        assert frozen_diagnostics["conflict"] == 0
        assert frozen_diagnostics["invalid_deck"] == 0
        assert frozen_diagnostics["residual_subtype"] == 0
        audit[format_id] = {
            "current": {str(key): value for key, value in current_transitions.items()},
            "frozen": {str(key): value for key, value in frozen_transitions.items()},
        }

    baseline_modern = _baseline_rules(tmp_path / "tabletop", "modern")
    candidate_modern = load_rule_set(ROOT / "my_archetypes" / "modern.yaml")
    tabletop_path = ROOT / "data" / "modern" / "melee" / "events" / "434455.json"
    tabletop_transitions, tabletop_diagnostics = _audit_records(
        baseline_modern,
        candidate_modern,
        _event_decks(json.loads(tabletop_path.read_text(encoding="utf-8"))),
    )
    assert {
        transition[:4] for transition in tabletop_transitions
    } <= expected_transitions["modern"]
    assert tabletop_diagnostics["conflict"] == 0
    assert tabletop_diagnostics["invalid_deck"] == 0
    assert tabletop_diagnostics["residual_subtype"] == 0
    audit["modern_tabletop_434455"] = {
        str(key): value for key, value in tabletop_transitions.items()
    }

    print(json.dumps(audit, ensure_ascii=False, sort_keys=True))
