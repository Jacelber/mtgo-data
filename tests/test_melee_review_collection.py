"""Swiss review collection must not silently become final rankings."""

import json
from pathlib import Path

import pytest
import requests
import yaml

from mtgmeta.melee.client import MeleeFetchError, _standings_round, fetch_complete_event
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.stats import MeleeStatisticsError, apply_final_standings

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = [{"source_round_id": "15", "label": "Round 15"},
          {"source_round_id": "18", "label": "Finals"}]


def test_review_source_is_explicit():
    assert _standings_round(ROUNDS, None) == "18"
    assert _standings_round(ROUNDS, "15") == "15"
    for invalid in ("18", "999"):
        with pytest.raises(MeleeFetchError, match="completed Swiss"):
            _standings_round(ROUNDS, invalid)


@pytest.mark.parametrize("review_round,expected", [(None, "18"), ("15", "15")])
def test_empty_standings_stop_before_matches(tmp_path, review_round, expected):
    calls = []

    def send(method, url, **kwargs):
        calls.append((url, kwargs.get("data")))
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if len(calls) == 1:
            response._content = ('<title>Review fixture | Melee</title>' + ''.join(
                f'<button class="round-selector" data-id="{r["source_round_id"]}" '
                f'data-name="{r["label"]}" data-is-completed="True"></button>'
                for r in ROUNDS)).encode()
        else:
            assert url.endswith('/Standing/GetRoundStandings')
            assert f'roundId={expected}'.encode() in kwargs['data']
            response._content = b'{"recordsTotal":0,"data":[]}'
        response._content_consumed = True
        return response

    with pytest.raises(MeleeFetchError, match="empty page"):
        fetch_complete_event("405588", load_melee_event_registry(ROOT / "configs/melee_events.yaml"),
                             tmp_path, request_send=send, request_delay=0,
                             review_standings_round_id=review_round)
    assert len(calls) == 2


def test_swiss_rank_requires_official_supplement(tmp_path):
    event_path = tmp_path / "data/modern/melee/events/405588.json"
    event_path.parent.mkdir(parents=True)
    snapshot = tmp_path / "raw"
    snapshot.mkdir()
    event_path.write_text(json.dumps({"rounds": [{"source_label": "Finals"}],
        "provenance": {"raw_artifacts": [{"path": "raw/tournament.json"}]}}))
    (snapshot / "tournament.json").write_text(json.dumps({"rounds": ROUNDS}))
    records = [{"resource_type": "tournament", "path": "tournament.json"},
               {"resource_type": "standings", "source_round_id": "15"}]
    (snapshot / "manifest.json").write_text(json.dumps({"responses": records}))
    with pytest.raises(MeleeStatisticsError, match="requires official final standings"):
        apply_final_standings({}, event_path, tmp_path)
    records[1]["source_round_id"] = "18"
    (snapshot / "manifest.json").write_text(json.dumps({"responses": records}))
    apply_final_standings({}, event_path, tmp_path)


def test_review_workflow_skips_public_generation():
    workflow = yaml.safe_load((ROOT / ".github/workflows/fetch_melee.yml").read_text())
    steps = {step['name']: step for step in workflow['jobs']['candidate']['steps']}
    for name in ('Build event overview, decks, and quality', 'Build hierarchical matchup statistics',
                 'Package event metadata and catalog', 'Generate format-first consumer catalog'):
        assert steps[name]['if'] == "inputs.review_standings_round_id == ''"
    assert steps['Stage review-only classification']['if'] == "inputs.review_standings_round_id != ''"


def test_source_is_saved_before_normalization_can_fail():
    workflow = yaml.safe_load((ROOT / ".github/workflows/fetch_melee.yml").read_text())
    steps = workflow['jobs']['candidate']['steps']
    names = [step['name'] for step in steps]
    assert names.index('Checkpoint immutable source before normalization') < names.index('Retain normalized event')
    checkpoint = steps[names.index('Checkpoint immutable source before normalization')]['run']
    assert 'git add -- "data_raw/melee/${EVENT_ID}/"\n' in checkpoint
    assert 'git commit' in checkpoint and 'push origin' in checkpoint
    source = steps[names.index('Resolve explicitly selected event source')]['run']
    assert 'glob("*/manifest.json")' in source
    assert 'len(manifests)==1' in source


def test_review_retention_preserves_publication_blocker(tmp_path, monkeypatch):
    from mtgmeta.melee import retention
    from mtgmeta.melee.quality import MeleePublicationBlocked, build_publication_payload

    event = load_melee_event_registry(ROOT / 'configs/melee_events.yaml').require_fetchable('451148')
    source_event = json.loads((ROOT / 'data/modern/melee/events/451148.json').read_bytes())
    snapshot = (ROOT / source_event['provenance']['raw_artifacts'][0]['path']).parent
    normalize = retention.normalize_parsed_snapshot

    def unresolved(*args, **kwargs):
        document = normalize(*args, **kwargs)
        participant = document['participants'][0]
        participant['status'] = 'unknown'
        document['quality']['status'] = 'blocked'
        document['quality']['issues'].append({
            'code': 'unknown_participant_status', 'severity': 'error',
            'entity_type': 'participant', 'entity_id': participant['id'],
            'message': 'Status needs review.', 'blocking': True,
            'source_evidence': ['status_text=Unenrolled (Payment)'],
        })
        return document

    monkeypatch.setattr(retention, 'normalize_parsed_snapshot', unresolved)
    result = retention.retain_normalized_event(event, snapshot, raw_root=ROOT / 'data_raw',
                                               data_root=tmp_path, review_only=True)
    retained = json.loads(result.normalized_path.read_bytes())
    assert result.quality_status == 'blocked'
    assert retained['quality']['publishable'] is False
    assert retained['participants'][0]['status'] == 'unknown'
    assert len(retained['decklists']) == len(source_event['decklists'])
    with pytest.raises(MeleePublicationBlocked, match='unknown_participant_status'):
        build_publication_payload(retained, event)
