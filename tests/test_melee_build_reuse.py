from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from mtgmeta.melee.matchup import MeleeMatchupError, build_event_matchup_from_statistics
from mtgmeta.melee import matchup
from mtgmeta.generation_progress import GenerationProgress, files
from test_melee_missing_decklist_contract import _documents


def test_reuse_preserves_matrix_and_rejects_changed_ledger(tmp_path):
    ledger, statistics, expected = _documents()
    path = tmp_path / 'ledger.json'
    path.write_text(json.dumps(ledger))
    digest = sha256(path.read_bytes()).hexdigest()
    statistics['overview']['input']['opportunity_sha256'] = digest
    expected['input']['opportunity_sha256'] = digest
    original = deepcopy(statistics)
    assert build_event_matchup_from_statistics(statistics, path) == expected
    assert statistics == original
    path.write_text(json.dumps({**ledger, 'event_id': '999999'}))
    with pytest.raises(MeleeMatchupError, match='changed during generation'):
        build_event_matchup_from_statistics(statistics, path)


def test_standalone_matchup_rebuilds_statistics_before_reuse(tmp_path, monkeypatch):
    ledger, statistics, expected = _documents()
    path = tmp_path / 'ledger.json'
    path.write_text(json.dumps(ledger))
    digest = sha256(path.read_bytes()).hexdigest()
    statistics['overview']['input']['opportunity_sha256'] = digest
    expected['input']['opportunity_sha256'] = digest
    calls = []
    def generate(*args):
        calls.append(args)
        return statistics
    monkeypatch.setattr(matchup, 'build_event_statistics_from_paths', generate)
    args = [tmp_path/'event.json', tmp_path/'classification.json', path, tmp_path/'rules.yaml', tmp_path]
    assert matchup.build_event_matchup_from_paths(*args) == expected
    assert calls == [tuple(args)]


def test_checkpoint_resume_checks_outputs_and_rebuilds_corruption(tmp_path):
    source, output = tmp_path/'source.json', tmp_path/'matchup.json'
    source.write_text('original')
    calls = []
    def produce():
        calls.append(source.read_text())
        output.write_text(source.read_text())
    def run():
        progress = GenerationProgress(tmp_path/'progress.json', {'event': 'test'})
        progress.run('matchup', files(tmp_path, ['source.json']), tmp_path, ['matchup.json'], produce)
        return progress
    run()
    assert run().reused == ['matchup']
    output.write_text('damaged')
    assert run().executed == ['matchup']
    source.write_text('new input')
    assert run().executed == ['matchup']
    assert calls == ['original', 'original', 'new input']
