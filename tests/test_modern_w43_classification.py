"""Owner's W43 decisions, with the adjacent families kept separate."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.mtgo.landing_editorial import build_public_name_contract

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = [
    ('12856628', 22, 'boros-land-destruction', '红白炸地'),
    ('12856973', 4, 'titan-canopy-ramp', '泰坦树冠Ramp'),
    ('12856973', 10, 'izzet-storm', '红蓝风暴'),
    ('12856973', 20, 'grixis-control', '格利极控制'),
    ('12856979', 8, 'selesnya-energy', '白绿能量'),
    ('12856984', 32, 'gruul-prowess', '红绿灵技'),
]


def retained(event, rank):
    path, = (ROOT / 'data/modern').glob(f'*_{event}.json')
    return next(p for p in json.loads(path.read_text(encoding='utf-8'))['players']
                if int(p['final_rank']) == rank)


@pytest.fixture(scope='module')
def rules():
    return load_rule_set(ROOT / 'my_archetypes/modern.yaml')


@pytest.mark.parametrize('event,rank,parent,chinese', DECISIONS)
def test_complete_retained_lists_follow_owner_decisions(rules, event, rank, parent, chinese):
    result = classify_deck(rules, retained(event, rank))
    assert (result.status, result.archetype_id, result.subtype_id) == ('classified', parent, None)
    names = build_public_name_contract(ROOT, 'modern')['names']
    entry = next(n for n in names if n['identity_id'] == parent)
    assert entry['display']['zh'] == chinese


def test_red_white_land_destruction_cannot_match_the_azorius_rule(rules):
    result = classify_deck(rules, retained('12856628', 22))
    assert 'azorius-land-denial' not in {m.archetype_id for m in result.matched_rules}
    assert dict(result.color_diagnostics)['azorius-land-denial'].colors == {'white', 'red'}


def test_gifts_is_a_real_core_requirement_for_the_new_storm_route(rules):
    deck = deepcopy(retained('12856973', 10))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Gifts Ungiven']
    assert classify_deck(rules, deck).archetype_id != 'izzet-storm'


def test_canopy_route_does_not_take_amulet_titan(rules):
    deck = deepcopy(retained('12856973', 4))
    deck['main_deck'].append({'name': 'Amulet of Vigor', 'qty': 4})
    result = classify_deck(rules, deck)
    assert result.archetype_id == 'amulet-titan'


def test_grixis_control_keeps_the_channeler_tempo_boundary(rules):
    deck = deepcopy(retained('12856973', 20))
    deck['main_deck'].append({'name': "Dragon's Rage Channeler", 'qty': 4})
    assert classify_deck(rules, deck).archetype_id != 'grixis-control'


def test_owner_confirmed_retained_white_land_control_without_orchid(rules):
    event = json.loads((ROOT / 'data/modern/melee/events/441441.json').read_text(encoding='utf-8'))
    participant = 'participant-10f62d54a05adb22175f85815d2c3128242e03fe8b928caa8f6dd857eff67108'
    cards = next(d['cards'] for d in event['decklists'] if d['participant_id'] == participant)
    deck = {zone: [{'name': c['name'], 'qty': c['quantity']}
                   for c in cards if c['section'] == section]
            for zone, section in [('main_deck', 'main'), ('sideboard', 'sideboard')]}
    assert all(c['name'] != 'White Orchid Phantom' for c in deck['main_deck'])
    result = classify_deck(rules, deck)
    assert (result.status, result.archetype_id) == ('classified', 'mono-white-ponza')
    assert 'azorius-land-denial' not in {m.archetype_id for m in result.matched_rules}
