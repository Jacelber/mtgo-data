"""Prevent premature editorial review while keeping classification review available."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tools import build_weekly_review_web as web


@pytest.fixture
def scope(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    (root / 'configs').mkdir(parents=True)
    registry_path = root / 'configs/mtgo_weekly_review_completions.yaml'
    registry_path.write_text('{}', encoding='utf-8')
    (root / 'event.json').write_text(json.dumps({'players': [
        {'final_rank': 1, 'player': 'Example', 'main_deck': [], 'sideboard': []}
    ]}), encoding='utf-8')
    cards = tmp_path / 'cards.json'
    cards.write_text('{}', encoding='utf-8')
    review = {'format': 'pauper', 'week': '2026-W37', 'event_ids': ['123'],
              'classifier': {'subject_digest': 'rules-a'}, 'classification_review_digest': 'review-a',
              'events': [{'event_id': '123'}], 'machine_priority_records': [],
              'records': [{'event_id': '123', 'rank': 1, 'player': 'Example',
                           'source_locator': 'event.json#/players/0'}]}
    acceptance = {'week': '2026-W37', 'kind': 'owner_accepted_full_classification',
                  'event_ids': ['123'], 'accepted_classifier_subject': 'rules-a',
                  'classification_review_digest': 'review-a', 'accepted_on': '2026-09-15',
                  'evidence': 'Synthetic Owner classification acceptance'}
    registry = {'data_admissions': {'formats': {'pauper': {'weekly_acceptances': [acceptance]}}}}
    args = argparse.Namespace(format='pauper', week='2026-W37', output=tmp_path / 'output',
                              localization=cards, include_feature=False)
    monkeypatch.setattr(web, 'ROOT', root)
    monkeypatch.setattr(web, 'build_mtgo_weekly_review', lambda *a, **kw: deepcopy(review))
    candidate_path = root / 'statistics/landing/review/candidates_2026-W37.yaml'
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text('machine_fact_digest: current-facts\n', encoding='utf-8')
    monkeypatch.setattr(web, 'load_mtgo_context', lambda *a: SimpleNamespace(paths={'statistics': root / 'statistics'}))
    return SimpleNamespace(args=args, review=review, acceptance=acceptance, registry=registry,
                           registry_path=registry_path, candidate_path=candidate_path)


def test_default_keeps_classification_available_without_generating_feature(scope, monkeypatch):
    monkeypatch.setattr(web, 'build_top8_subject', lambda *a: pytest.fail('Premature Feature generation'))
    web.build_scope(scope.args)
    data = json.loads((scope.args.output / 'review-data.json').read_text(encoding='utf-8'))
    assert data['review_stage'] == 'classification'
    assert data['subject'] is None
    assert len(data['classification']['records']) == 1
    assert 'main_deck' in data['classification']['records'][0]


@pytest.mark.parametrize('change', ['missing', 'other-format', 'other-week', 'rules', 'review', 'events', 'unrelated-digest'])
def test_feature_rejects_missing_or_outdated_acceptance(scope, monkeypatch, change):
    if change == 'missing':
        scope.registry = {}
    elif change == 'other-format':
        scope.registry['data_admissions']['formats']['modern'] = scope.registry['data_admissions']['formats'].pop('pauper')
    elif change == 'other-week':
        scope.acceptance['week'] = '2026-W36'
    elif change == 'rules':
        scope.review['classifier']['subject_digest'] = 'rules-b'
    elif change == 'review':
        scope.review['classification_review_digest'] = 'review-b'
    elif change == 'events':
        scope.review['event_ids'].append('456')
    else:
        scope.registry = {'unrelated': scope.acceptance}
    scope.registry_path.write_text(yaml.safe_dump(scope.registry), encoding='utf-8')
    scope.args.include_feature = True
    monkeypatch.setattr(web, 'build_top8_subject', lambda *a: pytest.fail('Premature Feature generation'))
    scope.args.output.mkdir()
    (scope.args.output / 'index.html').write_text('obsolete Feature snapshot', encoding='utf-8')
    with pytest.raises(web.FeatureReviewUnavailable, match='完整分类验收'):
        web.build_scope(scope.args)
    data = json.loads((scope.args.output / 'review-data.json').read_text(encoding='utf-8'))
    assert data['subject'] is None
    assert data['feature_blocker']
    assert 'obsolete Feature snapshot' not in (scope.args.output / 'index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('candidate', [None, {}, {'machine_fact_digest': 'old-facts'}])
def test_feature_requires_current_candidate_facts(scope, monkeypatch, candidate):
    if candidate is None:
        scope.candidate_path.unlink()
    else:
        scope.candidate_path.write_text(yaml.safe_dump(candidate), encoding='utf-8')
    # Exercise the real consumer's stale-binding rejection with only expensive inputs replaced.
    from mtgmeta.mtgo import landing, landing_editorial as editorial
    monkeypatch.setattr(editorial, 'load_mtgo_context', web.load_mtgo_context)
    monkeypatch.setattr(editorial, 'load_rules_for_format', lambda *a: {})
    monkeypatch.setattr(editorial.stats, 'load_all_events', lambda *a, **kw: [])
    monkeypatch.setattr(landing, 'machine_fact_digest_for_week', lambda *a: 'current-facts')
    with pytest.raises((ValueError, web.MTGOLandingEditorialError)):
        web.feature_subject(scope.review, [scope.acceptance])


def test_accepted_scope_allows_feature_without_weekly_completion(scope, monkeypatch):
    scope.registry_path.write_text(yaml.safe_dump(scope.registry), encoding='utf-8')
    scope.args.include_feature = True
    monkeypatch.setattr(web, 'build_top8_subject', lambda *a: {
        'source_event_ids': ['123'], 'classifier_digest': 'rules-a',
        'all_top8': [], 'candidate_evidence': [], 'machine_fact_digest': 'current-facts'})
    web.build_scope(scope.args)
    data = json.loads((scope.args.output / 'review-data.json').read_text(encoding='utf-8'))
    assert data['review_stage'] == 'feature'
    assert data['subject']['candidate_evidence'] == []  # Empty candidates are a valid result.
    assert data['accepted_evidence'][0]['evidence'] == scope.acceptance['evidence']


def test_initial_acceptance_can_cover_a_larger_historical_scope(scope):
    scope.acceptance['kind'] = 'owner_accepted_initial_public_scope'
    scope.acceptance['event_ids'].append('100')
    registry = {'data_admissions': {'formats': {'pauper': {'initial': scope.acceptance}}}}
    assert web.accepted_classification(registry, scope.review) == [scope.acceptance]


def test_new_week_cannot_overwrite_submitted_web_material(scope):
    scope.args.week = '2026-W38'
    scope.args.output.mkdir()
    page = scope.args.output / 'index.html'
    page.write_text('already submitted')
    with pytest.raises(ValueError, match='不能覆盖'):
        web.build_scope(scope.args)
    assert page.read_text() == 'already submitted'


def test_multi_scope_refusal_keeps_other_scope_and_current_classification_link(scope, monkeypatch):
    scope.registry_path.write_text(yaml.safe_dump(scope.registry), encoding='utf-8')
    def review_for_format(root, format_id, week, **kwargs):
        return {**deepcopy(scope.review), 'format': format_id}
    monkeypatch.setattr(web, 'build_mtgo_weekly_review', review_for_format)
    monkeypatch.setattr(web, 'build_top8_subject', lambda *a: {
        'source_event_ids': ['123'], 'classifier_digest': 'rules-a',
        'all_top8': [], 'candidate_evidence': [], 'machine_fact_digest': 'current-facts'})
    monkeypatch.setattr(web.sys, 'argv', ['build_weekly_review_web.py',
        '--scope', 'standard=2026-W37', '--scope', 'pauper=2026-W37', '--include-feature',
        '--output', str(scope.args.output), '--localization', str(scope.args.localization)])
    with pytest.raises(SystemExit) as stopped:
        web.main()
    assert stopped.value.code == 1
    for format_id, expected in [('standard', 'classification'), ('pauper', 'feature')]:
        data = json.loads((scope.args.output / format_id / '2026-W37/review-data.json').read_text(encoding='utf-8'))
        assert data['review_stage'] == expected
    index = (scope.args.output / 'index.html').read_text(encoding='utf-8')
    assert 'standard/2026-W37/index.html' in index
    assert 'pauper/2026-W37/index.html' in index
