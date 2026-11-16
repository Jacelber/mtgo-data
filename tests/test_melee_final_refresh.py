"""Refresh only official ranks, preserving Swiss data and unranked DQ facts."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mtgmeta.melee.stats import apply_final_standings, MeleeStatisticsError, statistics_document_bytes
from validate_schemas import load_schemas, validate_instance

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('final_refresh', ROOT / 'tools/refresh_melee_final_standings.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def test_refresh_discovers_fresh_completed_final_and_persists_minimized_source(tmp_path, monkeypatch):
    path = tmp_path / 'data/modern/melee/events/900001.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'participants': [
        {'source_id': '1', 'id': 'a', 'status': 'active'},
        {'source_id': '2', 'id': 'b', 'status': 'dropped'},
        {'source_id': '3', 'id': 'dq', 'status': 'disqualified'}],
        'standings': [{'participant_id': 'a', 'rank': 1}, {'participant_id': 'b', 'rank': 2}, {'participant_id': 'dq', 'rank': None}],
        'rounds': [{'source_label': 'Round 14'}], 'matches': ['preserved'], 'decklists': ['preserved']}))
    original = path.read_bytes()
    definition = SimpleNamespace(format='modern', url='https://melee.gg/Tournament/View/900001')
    monkeypatch.setattr(refresh, 'load_melee_event_registry', lambda p: SimpleNamespace(require_fetchable=lambda e: definition))
    calls = []
    def send(request, **kwargs):
        calls.append(request)
        if request.get_method() == 'GET':
            return BytesIO(b'<title>Fixture | Melee</title><button class="round-selector" data-id="18" data-name="Finals" data-is-completed="True"></button>')
        assert b'roundId=18' in request.data
        return BytesIO(json.dumps({'recordsTotal': 2, 'data': [
            {'ID': 100 + rank, 'Rank': rank, 'Points': 3, 'Team': {'Players': [
                {'ID': pid, 'DisplayName': str(pid), 'Username': 'private-account'}]}}
            for rank, pid in ((1, 2), (2, 1))]}).encode())
    monkeypatch.setattr(refresh.urllib.request, 'urlopen', send)
    result = refresh.refresh(tmp_path, '900001')
    final = json.load(open(result['path']))
    assert len(calls) == 2 and final['source_round_id'] == '18'
    assert final['ranks'] == {'a': 2, 'b': 1} and final['unranked_participant_ids'] == ['dq']
    assert path.read_bytes() == original
    for artifact in final['raw_artifacts']:
        body = (tmp_path / artifact['path']).read_bytes()
        assert sha256(body).hexdigest() == artifact['sha256']
        assert b'private-account' not in body


def test_unranked_dq_statistics_and_bound_final_ranks(tmp_path):
    from melee_synthetic import source_fixture, derived, write_json
    _, event, path, _ = source_fixture(tmp_path, dq=True)
    dq = next(p['id'] for p in event['participants'] if p['status'] == 'disqualified')
    standing = next(s for s in event['standings'] if s['participant_id'] == dq)
    standing.update(rank=None, match_points=None)
    write_json(path, event)
    _, _, statistics, _ = derived(tmp_path, event, path)
    decks = json.loads(statistics_document_bytes(statistics['decks']));before = deepcopy(decks)
    assert decks['decks'][-1]['participant_id'] == dq
    ranks = {d['participant_id']: i for i, d in enumerate(decks['decks'], 1) if d['participant_id'] != dq}
    final = {'event_id': decks['event_id'], 'event_sha256': sha256(path.read_bytes()).hexdigest(),
             'ranks': ranks, 'unranked_participant_ids': [dq]}
    target = path.parent.parent / 'final_standings' / path.name
    write_json(target, final)
    apply_final_standings(decks, path, tmp_path)
    actual = next(d for d in decks['decks'] if d['participant_id'] == dq)
    assert actual['final_rank'] is None and actual['overall_event_match_points'] is None
    assert actual['statistics_eligibility']['played_match_metrics_excluded']
    schemas, registry = load_schemas(ROOT / 'schemas', {'melee-event-decks.schema.json'})
    assert not validate_instance(decks, schemas['melee-event-decks.schema.json'], registry)
    active = next(d for d in decks['decks'] if d['participant_id'] != dq)
    active['final_rank'] = None
    assert validate_instance(decks, schemas['melee-event-decks.schema.json'], registry)
    for altered in ({**final, 'unranked_participant_ids': []},
                    {**final, 'ranks': {}},
                    {**final, 'ranks': {**ranks, dq: 4}}):
        write_json(target, altered)
        with pytest.raises(MeleeStatisticsError, match='match retained'):
            apply_final_standings(deepcopy(before), path, tmp_path)
