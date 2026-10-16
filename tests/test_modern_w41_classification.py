from copy import deepcopy
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.mtgo.landing_editorial import build_public_name_contract


ROOT = Path(__file__).resolve().parents[1]


def retained(event, rank):
    paths = list((ROOT / 'data/modern').glob(f'*_{event}.json'))
    assert len(paths) == 1
    event = json.loads(paths[0].read_text(encoding='utf-8'))
    return next(p for p in event['players'] if int(p['final_rank']) == rank)


@pytest.fixture(scope='module')
def rules():
    return load_rule_set(ROOT / 'my_archetypes/modern.yaml')


@pytest.mark.parametrize(('event', 'rank', 'parent', 'subtype'), [
    ('12855500', 7, 'living-end', 'sultai'),
    ('12855507', 10, 'phoenix-prowess', None),
    ('12855508', 26, 'mono-white-tron', None),
    ('12856334', 16, 'dimir-unearth', None),
    ('12856334', 20, 'mardu-goryos', None),
    ('12856339', 32, 'omnath-midrange', None),
    ('12856172', 30, 'sphinx-approach', None),
])
def test_modern_w41_owner_corrections(rules, event, rank, parent, subtype):
    result = classify_deck(rules, retained(event, rank))
    assert (result.status, result.archetype_id, result.subtype_id) == ('classified', parent, subtype)


def test_chant_scepter_pair_does_not_make_a_white_tron_azorius(rules):
    deck = deepcopy(retained('12855508', 26))
    result = classify_deck(rules, deck)
    assert 'chant-control-azorius' not in {m.rule_id for m in result.matched_rules}
    deck['main_deck'] = [c for c in deck['main_deck'] if not c['name'].startswith("Urza's ")]
    result = classify_deck(rules, deck)
    assert 'chant-control-azorius' not in {m.rule_id for m in result.matched_rules}


def test_one_plains_does_not_make_classic_eldrazi_tron_mono_white(rules):
    event = json.loads((ROOT / 'data/modern/melee/events/405588.json').read_text(encoding='utf-8'))
    deck = event['decklists'][348]
    assert any(c['name'] == 'Plains' and c['quantity'] == 1 for c in deck['cards'])
    result = classify_deck(rules, {
        'main_deck': [{'name': c['name'], 'qty': c['quantity']} for c in deck['cards'] if c['section'] == 'main'],
        'sideboard': [{'name': c['name'], 'qty': c['quantity']} for c in deck['cards'] if c['section'] == 'sideboard'],
    })
    assert (result.archetype_id, result.subtype_id) == ('eldrazi-tron', 'colorless')


def test_real_azorius_chant_requires_both_mana_sources(rules):
    deck = {'main_deck': [{'name': n, 'qty': 4} for n in (
        "Orim's Chant", 'Isochron Scepter', 'Hallowed Fountain', 'Counterspell',
    )], 'sideboard': []}
    result = classify_deck(rules, deck)
    assert (result.archetype_id, result.subtype_id) == ('chant-control', 'azorius')


def test_selesnya_eldrazi_without_talisman_is_not_azorius_chant(rules):
    event = json.loads((ROOT / 'data/modern/melee/events/471573.json').read_text(encoding='utf-8'))
    deck = next(d for d in event['decklists'] if d['participant_id'] ==
                'participant-2a50ab2590e1db8215f2b7cbf3d7f6cca43911d8d48bd155a97c31cb2466057b')
    assert not any(c['name'] == 'Talisman of Unity' for c in deck['cards'])
    result = classify_deck(rules, {
        'main_deck': [{'name': c['name'], 'qty': c['quantity']} for c in deck['cards'] if c['section'] == 'main'],
        'sideboard': [{'name': c['name'], 'qty': c['quantity']} for c in deck['cards'] if c['section'] == 'sideboard'],
    })
    assert (result.archetype_id, result.subtype_id) == ('eldrazi-ramp', 'selesnya')
    assert 'chant-control-azorius' not in {m.rule_id for m in result.matched_rules}


def test_sphinx_approach_preserves_more_than_four_copies(rules):
    deck = deepcopy(retained('12856172', 30))
    assert sum(c['qty'] for c in deck['main_deck'] if c['name'] == "Sphinx's Approach") == 12
    result = classify_deck(rules, deck)
    assert (result.status, result.archetype_id) == ('classified', 'sphinx-approach')
    for c in deck['main_deck']:
        if c['name'] == "Sphinx's Approach":
            c['qty'] = 4
    assert classify_deck(rules, deck).archetype_id != 'sphinx-approach'


def test_phoenix_prowess_requires_both_engines(rules):
    deck = deepcopy(retained('12855507', 10))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Arclight Phoenix']
    assert classify_deck(rules, deck).archetype_id != 'phoenix-prowess'


def test_corrected_references_do_not_change_the_burn_and_eldrazi_decks(rules):
    burn = classify_deck(rules, retained('12856334', 30))
    tron = classify_deck(rules, retained('12856334', 32))
    assert (burn.archetype_id, burn.subtype_id) == ('burn', 'mono-red')
    assert (tron.archetype_id, tron.subtype_id) == ('eldrazi-tron', 'colorless')


def test_public_hollowvine_subtype_names_keep_the_confirmed_parent_wording():
    names = {n['identity_id']: n['display']['zh'] for n in build_public_name_contract(ROOT, 'modern')['names']}
    assert names['hollowvine'] == '藤蔓石椁'
    assert {sub: names['hollowvine/' + sub] for sub in ('boros', 'rakdos', 'mardu')} == {
        'boros': '红白藤蔓石椁', 'rakdos': '红黑藤蔓石椁', 'mardu': '玛尔都藤蔓石椁',
    }
