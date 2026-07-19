"""P2-02 tests for shared card-name and deck normalization."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from classify_standard import match_archetype
from mtgmeta.card_names import CARD_ALIASES, normalize_card_name
from mtgmeta.deck import count_card, deck_to_counts


ALIAS_PATH = SRC / "mtgmeta" / "data" / "om1_spm_aliases.json"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
RULE_PATH = ROOT / "my_archetypes" / "standard.yaml"
LEGACY_ALIASES = {
    "Kavaero, Mind-Bitten": "Superior Spider-Man",
    "Leyline Weaver": "Spider Manifestation",
}


def test_om1_spm_alias_artifact_is_complete_unique_and_traceable():
    artifact = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    mappings = artifact["mappings"]
    assert artifact["source"] == {
        "project": "MTGJSON",
        "set_code": "OM1",
        "url": "https://mtgjson.com/api/v5/OM1.json",
        "license": "MIT",
        "license_url": "https://github.com/mtgjson/mtgjson/blob/main/LICENSE",
        "retrieved_on": "2026-07-19",
        "data_version": "5.3.0+20260718",
        "data_date": "2026-07-18",
    }
    assert artifact["mapping_count"] == len(mappings) == len(CARD_ALIASES) == 158
    assert artifact["canonical_name_count"] == len({item["canonical_name"] for item in mappings}) == 153
    assert len({item["alias"] for item in mappings}) == 158
    assert all(item["oracle_id"] and item["collector_number"] for item in mappings)


def test_representative_single_and_double_faced_om1_names_normalize_to_spm_names():
    assert normalize_card_name(" Kavaero, Mind-Bitten ") == "Superior Spider-Man"
    assert normalize_card_name("Leyline Weaver") == "Spider Manifestation"
    assert normalize_card_name("Surris, Silk-Tech Vanguard") == "Peter Parker // Amazing Spider-Man"
    assert normalize_card_name("Surris, Spidersilk Innovator") == "Peter Parker // Amazing Spider-Man"
    assert normalize_card_name("Lightning Bolt") == "Lightning Bolt"


def test_deck_normalization_merges_aliases_duplicates_and_zones_without_mutation():
    deck = {
        "main_deck": [
            {"name": "Kavaero, Mind-Bitten", "qty": "2"},
            {"name": " Superior Spider-Man ", "qty": 1},
        ],
        "sideboard": [
            {"name": "Leyline Weaver", "qty": 2},
            {"name": "Spider Manifestation", "qty": "1"},
        ],
    }
    original = json.loads(json.dumps(deck))
    main, side = deck_to_counts(deck)
    assert main == {"Superior Spider-Man": 3}
    assert side == {"Spider Manifestation": 3}
    assert count_card("Superior Spider-Man", "main", main, side) == 3
    assert count_card("Spider Manifestation", "side", main, side) == 3
    assert count_card("Spider Manifestation", "any", main, side) == 3
    assert count_card("Spider Manifestation", "legacy-default", main, side) == 3
    assert deck == original
    assert deck_to_counts({}) == ({}, {})


def test_full_om1_mapping_improves_normalization_without_changing_3936_parent_results():
    records = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["records"]
    rules = yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))["archetypes"]
    changed_decks = 0
    changed_alias_names = set()
    parent_differences = []

    for record in records:
        deck = {
            "main_deck": [{"name": name, "qty": qty} for name, qty in record["main"]],
            "sideboard": [{"name": name, "qty": qty} for name, qty in record["side"]],
        }
        shared_main, shared_side = deck_to_counts(deck)

        legacy_main = {}
        legacy_side = {}
        for source, destination in ((record["main"], legacy_main), (record["side"], legacy_side)):
            for name, qty in source:
                normalized = LEGACY_ALIASES.get(name.strip(), name.strip())
                destination[normalized] = destination.get(normalized, 0) + int(qty)

        if (shared_main, shared_side) != (legacy_main, legacy_side):
            changed_decks += 1
            changed_alias_names.update((set(legacy_main) | set(legacy_side)) & set(CARD_ALIASES))

        selected = match_archetype(shared_main, shared_side, rules) or "Unknown"
        if selected != record["expected"]:
            parent_differences.append((record["id"], record["expected"], selected))

    assert len(records) == 3936
    assert changed_decks == 567
    assert len(changed_alias_names) == 25
    assert parent_differences == []
