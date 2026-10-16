from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set


ROOT = Path(__file__).resolve().parents[1]


def retained(event_id: str, rank: int) -> dict:
    paths = list((ROOT / 'data/standard').glob(f'*_{event_id}.json'))
    assert len(paths) == 1
    event = json.loads(paths[0].read_text(encoding='utf-8'))
    return next(p for p in event['players'] if int(p['final_rank']) == rank)


@pytest.fixture(scope='module')
def rules():
    return load_rule_set(ROOT / 'my_archetypes/standard.yaml')


@pytest.mark.parametrize(('event', 'rank', 'parent', 'subtype'), [
    ('12855542', 6, 'boros-superfriends', None),
    ('12855542', 16, 'azorius-control', 'traditional'),
    ('12856121', 21, 'azorius-control', 'traditional'),
    ('12856121', 25, 'mono-white-swarm-aggro', None),
    ('12856121', 31, 'boros-superfriends', None),
    ('12856130', 9, 'azorius-control', 'traditional'),
    ('12856130', 20, 'boros-superfriends', None),
    ('12855544', 5, 'azorius-control', 'traditional'),
    ('12855544', 20, 'simic-landfall', None),
    ('12855544', 26, 'simic-landfall', None),
    ('12856141', 7, 'azorius-control', 'traditional'),
    ('12856141', 23, 'golgari-self-mill', None),
    ('12856143', 7, 'simic-landfall', None),
    ('12856143', 9, 'azorius-control', 'traditional'),
    ('12856143', 21, 'azorius-control', 'traditional'),
    ('12856143', 28, 'grixis-artifact-sacrifice', None),
    ('12856154', 5, 'lifegain', 'abzan'),
    ('12856154', 18, 'izzet-looting', None),
    ('12856137', 17, 'selesnya-landfall', None),
    ('12856183', 15, 'golgari-self-mill', None),
    ('12856183', 21, 'azorius-control', 'traditional'),
    ('12856183', 23, 'sultai-demon', None),
    ('12856183', 27, 'mono-white-angels', None),
    ('12856183', 31, 'jund-midrange', None),
])
def test_owner_w41_corrections(rules, event, rank, parent, subtype):
    result = classify_deck(rules, retained(event, rank))
    assert (result.status, result.archetype_id, result.subtype_id) == ('classified', parent, subtype)


def test_spider_man_union_combines_dimir_and_preserves_sultai(rules):
    parent = next(a for a in rules.archetypes if a.id == 'dimir-spider-man')
    assert [s.id for s in parent.subtypes] == ['dimir', 'sultai']
    assert not {'dimir-deceit', 'dimir-excruciator', 'sultai-excruciator'} & {a.id for a in rules.archetypes}
    result = classify_deck(rules, retained('12855542', 2))
    assert (result.archetype_id, result.subtype_id) == ('dimir-spider-man', 'dimir')


def test_sultai_spider_man_retains_green_build_under_shared_parent(rules):
    deck = {'main_deck': [{'name': name, 'qty': qty} for name, qty in (
        ('Doomsday Excruciator', 2), ('Superior Spider-Man', 4), ('Deceit', 4),
        ('Wistfulness', 2), ('Overgrown Tomb', 4),
    )], 'sideboard': []}
    result = classify_deck(rules, deck)
    assert (result.archetype_id, result.subtype_id) == ('dimir-spider-man', 'sultai')
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Wistfulness']
    result = classify_deck(rules, deck)
    assert (result.archetype_id, result.subtype_id) == ('dimir-spider-man', 'dimir')


def test_professor_in_sideboard_does_not_make_lifegain_abzan(rules):
    deck = deepcopy(retained('12856154', 5))
    professor = [c for c in deck['main_deck'] if c['name'] == 'Professor Dellian Fel']
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != 'Professor Dellian Fel']
    deck['sideboard'].extend(professor)
    result = classify_deck(rules, deck)
    assert (result.archetype_id, result.subtype_id) == ('lifegain', 'orzhov')


def test_sideboard_white_landfall_requires_the_white_package(rules):
    deck = deepcopy(retained('12856137', 17))
    deck['sideboard'] = [c for c in deck['sideboard'] if c['name'] not in {'Plains', 'Sheltered by Ghosts', 'Seam Rip'}]
    assert classify_deck(rules, deck).archetype_id != 'selesnya-landfall'


@pytest.mark.parametrize(('event', 'rank'), [('12842913', 29), ('12844853', 20), ('12854491', 7)])
def test_blue_mana_alone_does_not_move_other_demon_builds(rules, event, rank):
    assert classify_deck(rules, retained(event, rank)).archetype_id == 'golgari-demon'


@pytest.mark.parametrize(('event', 'rank', 'core', 'parent'), [
    ('12856121', 25, 'Warden of the Inner Sky', 'mono-white-swarm-aggro'),
    ('12856143', 28, 'Obsessive Pursuit', 'grixis-artifact-sacrifice'),
    ('12856183', 27, 'Giada, Font of Hope', 'mono-white-angels'),
])
def test_new_families_require_their_engine(rules, event, rank, core, parent):
    deck = deepcopy(retained(event, rank))
    deck['main_deck'] = [c for c in deck['main_deck'] if c['name'] != core]
    assert classify_deck(rules, deck).archetype_id != parent
