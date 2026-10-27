"""Owner's retained Dimir Self-Bounce list and its local boundaries."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from mtgmeta.classifier import classify_counts, classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.mtgo.landing_editorial import build_public_name_contract

ROOT = Path(__file__).resolve().parents[1]


def subject():
    event = json.loads((ROOT / 'data/pauper/Pauper_Challenge_32_12856992.json').read_text(
        encoding='utf-8'))
    deck = next(p for p in event['players'] if int(p['final_rank']) == 23)
    return load_rule_set(ROOT / 'my_archetypes/pauper.yaml'), deck


def test_complete_owner_list_uses_the_new_independent_parent():
    rules, deck = subject()
    result = classify_deck(rules, deck)
    assert (result.status, result.archetype_id, result.subtype_id) == (
        'classified', 'dimir-self-bounce', None)
    entry = next(n for n in build_public_name_contract(ROOT, 'pauper')['names']
                 if n['identity_id'] == 'dimir-self-bounce')
    assert entry['display'] == {'en': 'Dimir Self-Bounce', 'zh': '蓝黑回手'}


def test_value_permanents_without_self_bounce_are_not_the_new_family():
    rules, original = subject()
    deck = deepcopy(original)
    deck['main_deck'] = [c for c in deck['main_deck']
                         if c['name'] not in {'Dream Stalker', 'Geistwave'}]
    assert classify_deck(rules, deck).archetype_id != 'dimir-self-bounce'


def test_new_dimir_parent_does_not_accept_supported_normal_red_spells():
    rules, deck = subject()
    main, side = Counter(), Counter()
    for cards, counts in [(deck['main_deck'], main), (deck['sideboard'], side)]:
        for card in cards:
            counts[card['name']] += card['qty']
    main['Mountain'] += 1
    side['Lightning Bolt'] += 1
    result = classify_counts(rules, main, side)
    assert result.archetype_id != 'dimir-self-bounce'
    assert dict(result.color_diagnostics)['dimir-self-bounce'].colors == {'blue', 'black', 'red'}
