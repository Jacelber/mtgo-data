from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set


ROOT = Path(__file__).resolve().parents[1]


def retained(event, rank):
    paths = list((ROOT / 'data/pioneer').glob(f'*_{event}.json'))
    assert len(paths) == 1
    document = json.loads(paths[0].read_text(encoding='utf-8'))
    return next(p for p in document['players'] if int(p['final_rank']) == rank)


@pytest.fixture(scope='module')
def rules():
    return load_rule_set(ROOT / 'my_archetypes/pioneer.yaml')


@pytest.mark.parametrize(('event', 'rank', 'parent'), [
    ('12855505', 7, 'mono-black-phoenix'),
    ('12855505', 22, 'bant-airbending'),
    ('12856150', 5, 'jund-sacrifice'),
    ('12856150', 19, 'orzhov-midrange'),
    ('12856150', 21, 'mono-black-phoenix'),
    ('12856171', 5, 'boros-discard'),
    ('12856181', 2, 'mono-green-landfall'),
    ('12856181', 8, 'boros-discard'),
    ('12856171', 25, 'mono-black-phoenix'),
    ('12856171', 12, 'jund-sacrifice'),
    ('12856181', 7, 'jund-sacrifice'),
    ('12856181', 19, 'jund-sacrifice'),
])
def test_pioneer_w41_owner_corrections(rules, event, rank, parent):
    result = classify_deck(rules, retained(event, rank))
    assert (result.status, result.archetype_id, result.subtype_id) == ('classified', parent, None)


@pytest.mark.parametrize(('event', 'rank'), [('12856171', 12), ('12856181', 7), ('12856181', 19)])
def test_hybrid_sacrifice_has_same_main_and_ignores_sideboard_variation(rules, event, rank):
    def counts(deck):
        total = Counter()
        for c in deck['main_deck']:
            total[c['name']] += c['qty']
        return total
    assert counts(retained(event, rank)) == counts(retained('12856150', 5))
    deck = deepcopy(retained(event, rank))
    deck['sideboard'] = []
    assert classify_deck(rules, deck).archetype_id == 'jund-sacrifice'
    assert not next(a for a in rules.archetypes if a.id == 'jund-sacrifice').subtypes


def test_hybrid_sacrifice_requires_cat_oven_core(rules):
    deck = deepcopy(retained('12856150', 5))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Cauldron Familiar']
    assert classify_deck(rules, deck).archetype_id != 'jund-sacrifice'


def test_orzhov_fallback_keeps_established_control_identity(rules):
    deck = {'main_deck': [{'name': n, 'qty': 2} for n in (
        'The Wandering Emperor', 'Godless Shrine', 'Pest Control', 'Thoughtseize', 'Fatal Push',
    )], 'sideboard': []}
    result = classify_deck(rules, deck)
    assert result.archetype_id == 'orzhov-control'
    assert 'orzhov-midrange-primary' in {m.rule_id for m in result.overridden_matches}


def test_phoenix_with_red_mana_is_not_mono_black(rules):
    deck = deepcopy(retained('12855505', 7))
    deck['main_deck'].append({'name': 'Blood Crypt', 'qty': 2})
    assert classify_deck(rules, deck).archetype_id != 'mono-black-phoenix'


def test_landfall_requires_the_landfall_engine(rules):
    deck = deepcopy(retained('12856181', 2))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Earthbender Ascension']
    assert classify_deck(rules, deck).archetype_id != 'mono-green-landfall'
