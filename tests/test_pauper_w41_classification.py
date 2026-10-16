from copy import deepcopy
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set


ROOT = Path(__file__).resolve().parents[1]


def retained(event_id, rank):
    paths = list((ROOT / 'data/pauper').glob(f'*_{event_id}.json'))
    assert len(paths) == 1
    event = json.loads(paths[0].read_text(encoding='utf-8'))
    return next(p for p in event['players'] if int(p['final_rank']) == rank)


@pytest.fixture(scope='module')
def rules():
    return load_rule_set(ROOT / 'my_archetypes/pauper.yaml')


@pytest.mark.parametrize(('event_id', 'rank', 'parent'), [
    ('12855502', 13, 'grixis-faeries'),
    ('12856155', 11, 'grixis-faeries'),
    ('12855509', 12, 'boros-snacker'),
    ('12855517', 31, 'boros-snacker'),
    ('12856180', 23, 'boros-snacker'),
    ('12855517', 20, 'esper-ephemerate'),
    ('12855502', 24, 'boros-snacker'),
    ('12856189', 24, 'boros-snacker'),
    ('12840528', 19, 'boros-snacker'),
    ('12855509', 16, 'grixis-faeries'),
])
def test_owner_confirmed_pauper_corrections_and_controls(rules, event_id, rank, parent):
    result = classify_deck(rules, retained(event_id, rank))
    assert (result.status, result.archetype_id, result.subtype_id) == ('classified', parent, None)


def test_grixis_faeries_accepts_the_red_land_in_either_zone(rules):
    deck = deepcopy(retained('12855509', 16))
    land = next(c for c in deck['main_deck'] if c['name'] == 'Molten Tributary')
    deck['main_deck'].remove(land)
    deck['sideboard'].append(land)
    assert classify_deck(rules, deck).archetype_id == 'grixis-faeries'


def test_sideboard_land_alone_does_not_change_dimir_faeries(rules):
    deck = deepcopy(retained('12855502', 13))
    deck['sideboard'] = [c for c in deck['sideboard'] if c['name'] != 'Vandalblast']
    assert classify_deck(rules, deck).archetype_id == 'dimir-faeries'


@pytest.mark.parametrize('missing', ['Sneaky Snacker', 'Pursue the Past'])
def test_boros_snacker_requires_its_recursion_engine(rules, missing):
    deck = deepcopy(retained('12856180', 23))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != missing]
    assert classify_deck(rules, deck).archetype_id == 'boros-synthesizer'


def test_boros_snacker_does_not_absorb_the_gate_branch(rules):
    deck = deepcopy(retained('12856180', 23))
    deck['main_deck'].append({'name': 'Basilisk Gate', 'qty': 1})
    assert classify_deck(rules, deck).archetype_id != 'boros-snacker'


def test_esper_ephemerate_keeps_its_blink_engine(rules):
    deck = deepcopy(retained('12855517', 20))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Ephemerate']
    assert classify_deck(rules, deck).archetype_id != 'esper-ephemerate'
