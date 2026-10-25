"""Card notation is resolved by complete registered faces, not slash stripping."""
from dataclasses import asdict, replace
import gzip
import json

import pytest

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_cards import card_facts, classifier_card_name, resolve_card_name
from mtgmeta.deck import deck_to_counts
from mtgmeta.melee.classification import _adapt_decklist
from mtgmeta.mtgo import stats
from test_classifier_shared_semantics import family
from mtgmeta.rules import CardCondition


PAIRS = [
    ("Callous Sell-Sword", "Burn Together", "Callous Sell-Sword"),
    ("Brazen Borrower", "Petty Theft", "Brazen Borrower"),
    ("Fable of the Mirror-Breaker", "Reflection of Kiki-Jiki", "Fable of the Mirror-Breaker"),
    ("Sink into Stupor", "Soporific Springs", "Sink into Stupor"),
    ("Wear", "Tear", "Wear/Tear"),
    ("Roaring Furnace", "Steaming Sauna", "Roaring Furnace/Steaming Sauna"),
]
SEPARATORS = ["/", "//", " / ", " // ", "/ ", " //", "\t/\t", "\n//\t"]


@pytest.mark.parametrize("front,back,key", PAIRS)
@pytest.mark.parametrize("separator", SEPARATORS)
def test_notation_is_shared_by_source_adapters_classification_and_statistics(front, back, key, separator):
    name = f"  {front}{separator}{back}  "
    assert classifier_card_name(name) == key
    adapted, errors = _adapt_decklist({"cards": [
        {"name": name, "quantity": 2, "section": "main"},
        {"name": key, "quantity": 1, "section": "main"},
        {"name": name, "quantity": 1, "section": "sideboard"},
    ]})
    assert not errors
    source = {"main_deck": [{"name": name, "qty": 2}, {"name": key, "qty": 1}],
              "sideboard": [{"name": name, "qty": 1}]}
    assert deck_to_counts(source) == deck_to_counts(adapted) == ({key: 3}, {key: 1})
    assert stats.deck_vector(source) == stats.deck_vector(adapted) == {key: 3}
    # No color restriction: this small rule independently checks identity/counts.
    rules = family(core=(CardCondition(key, "main", min_count=3),), colors=())
    assert asdict(classify_counts(rules, {name: 2, key: 1}, {name: 1})) == asdict(
        classify_counts(rules, {key: 3}, {key: 1}))


def test_all_registered_face_pairs_accept_spacing_without_double_counting():
    facts = card_facts()
    for pair, keys in facts.face_pairs.items():
        if len(keys) != 1:
            continue
        key = next(iter(keys))
        for separator in SEPARATORS:
            spelling = separator.join(pair)
            # Explicit names remain authoritative if a standalone name collides.
            expected = facts.names.get(spelling, key)
            assert classifier_card_name(spelling) == expected, spelling
            assert stats.deck_vector({"main_deck": [{"name": spelling, "qty": 2}]}) == {expected: 2}


@pytest.mark.parametrize("name", [
    "SP//dr, Piloted by Peni", "SP/dr, Piloted by Peni",
    "Unknown // Card", "Callous Sell-Sword/Unrelated Card",
    "Burn Together/Callous Sell-Sword", "Callous Sell-Sword/Callous Sell-Sword",
    "Callous Sell-Sword///Burn Together", "Callous Sell-Sword / / Burn Together",
    "Callous Sell-Sword/Burn Together/Extra Face",
])
def test_literal_slashes_invalid_combinations_and_unknown_entities_are_not_guessed(name):
    assert classifier_card_name(name) == name
    assert stats.deck_vector({"main_deck": [{"name": name, "qty": 2}]}) == {name: 2}


def test_ambiguous_pairs_are_not_guessed_and_explicit_names_win():
    facts = card_facts()
    pair = ("Callous Sell-Sword", "Burn Together")
    spelling = "/".join(pair)
    ambiguous = replace(facts, face_pairs={pair: frozenset({"entity-a", "entity-b"})})
    assert resolve_card_name(spelling, ambiguous) == spelling
    exact = replace(ambiguous, names={spelling: "standalone-entity"})
    assert resolve_card_name(spelling, exact) == "standalone-entity"


def test_separator_inside_a_registered_face_is_literal():
    pair = ("SP//dr, Piloted by Peni", "Another Face")
    facts = replace(card_facts(), face_pairs={pair: frozenset({"synthetic-two-face"})})
    assert resolve_card_name("SP//dr, Piloted by Peni/Another Face", facts) == "synthetic-two-face"
    wrong = "SP/dr, Piloted by Peni/Another Face"
    assert resolve_card_name(wrong, facts) == wrong


def test_offline_fact_selection_uses_same_notation_without_rewriting_snapshot(tmp_path):
    from tools.build_classifier_card_facts import build

    source = tmp_path / "oracle.jsonl.gz"
    card = {
        "name": "Callous Sell-Sword // Burn Together", "oracle_id": "adventure-entity",
        "layout": "adventure", "games": ["mtgo"],
        "card_faces": [
            {"name": "Callous Sell-Sword", "mana_cost": "{1}{B}", "type_line": "Creature", "colors": ["B"]},
            {"name": "Burn Together", "mana_cost": "{R}", "type_line": "Sorcery — Adventure", "colors": ["R"]},
        ],
    }
    with gzip.open(source, "wt") as stream:
        stream.write(json.dumps(card)+"\n")
    expected = build(source, ["Callous Sell-Sword"], "test://oracle")
    assert build(source, ["  Callous Sell-Sword  "], "test://oracle") == expected
    for separator in SEPARATORS:
        assert build(source, [separator.join(["Callous Sell-Sword", "Burn Together"])],
                     "test://oracle") == expected
    with pytest.raises(ValueError, match="unresolved or ambiguous"):
        build(source, ["Callous Sell-Sword/Unrelated Card"], "test://oracle")


@pytest.mark.parametrize("front,back,key", PAIRS)
def test_mixed_notations_do_not_split_presence_mean_core_or_deviation(front, back, key):
    records = [{"main_deck": [{"name": front+separator+back, "qty": 2}]} for separator in SEPARATORS]
    vectors = [stats.deck_vector(record) for record in records]
    mean, rates = stats.mean_vector(vectors), stats.appearance_rates(vectors)
    assert mean == {key: 2.0}
    assert rates == {key: 1.0}
    assert stats.split_core_flex(mean, rates) == ([{"name": key, "mean_qty": 2.0, "rate": 1.0}], [])
    assert all(stats.weighted_l1(vector, mean, rates) == 0 for vector in vectors)
    assert stats.pick_medoid(records, mean, rates) is records[0]
