"""Build a private, read-only weekly review site from existing machine evidence."""
from pathlib import Path
import argparse
import json
import sys
import html
import re
from collections import Counter
from copy import deepcopy

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mtgmeta.weekly_review import build_mtgo_weekly_review
from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo.landing_editorial import build_top8_subject, MTGOLandingEditorialError
from mtgmeta.mtgo.publication import require_private_output
from mtgmeta.mtgo.stats import normalize_legacy_card_name


class FeatureReviewUnavailable(ValueError):
    """Requested Feature review was replaced with current classification material."""


def accepted_classification(registry, review):
    """Use scoped business evidence, never an unrelated nested digest or completion flag."""
    scope = registry.get('data_admissions', {}).get('formats', {}).get(review['format'], {})
    candidates = [scope.get('initial', {}), *scope.get('weekly_acceptances', [])]
    accepted = []
    for item in candidates:
        if (item.get('kind') in {'owner_accepted_initial_public_scope', 'owner_accepted_full_classification'}
                and item.get('week') == review['week']
                and item.get('classification_review_digest') == review.get('classification_review_digest')
                and item.get('accepted_classifier_subject') == review['classifier']['subject_digest']
                and set(review['event_ids']).issubset(set(item.get('event_ids', [])))
                and item.get('evidence') and item.get('accepted_on')):
            accepted.append(item)
    return accepted


def feature_subject(review, accepted):
    if not accepted:
        raise ValueError('Feature 尚不可审阅：先完成当前赛事与分类版本的完整分类验收。')
    context = load_mtgo_context(ROOT, review['format'], 'landing_generation')
    candidate_path = context.paths['statistics'] / 'landing' / 'review' / f"candidates_{review['week']}.yaml"
    if not candidate_path.is_file():
        raise ValueError('Feature 尚不可审阅：先生成当前分类下的统计与机械候选。')
    candidate = yaml.safe_load(candidate_path.read_text(encoding='utf-8'))
    if not isinstance(candidate, dict) or not candidate.get('machine_fact_digest'):
        raise ValueError('Feature 候选缺少统计版本依据，请重新生成。')
    # This consumer recomputes current machine facts and rejects stale candidate digests.
    subject = build_top8_subject(ROOT, review['format'], review['week'])
    assert set(review['event_ids']) == set(subject['source_event_ids']), 'Classification and Top 8 event scopes differ'
    assert review['classifier']['subject_digest'] == subject['classifier_digest'], 'Classifier subjects differ'
    return subject


def build_scope(args):
    output = args.output.resolve()
    require_private_output(ROOT, output / 'index.html')
    bootstrap = getattr(args, 'name_review_bootstrap', False)
    if bootstrap and output.is_relative_to(ROOT):
        raise ValueError('name review bootstrap output must be outside the repository')
    review = build_mtgo_weekly_review(ROOT, args.format, args.week, name_review_bootstrap=bootstrap)
    source_review = deepcopy(review) if bootstrap else review
    registry = yaml.safe_load((ROOT / 'configs/mtgo_weekly_review_completions.yaml').read_text(encoding='utf-8'))
    accepted = [] if bootstrap else accepted_classification(registry, review)
    include_feature = getattr(args, 'include_feature', False)
    if bootstrap and include_feature:
        raise ValueError('首次分类审阅不能同时包含 Feature。')
    subject, feature_error = None, None
    if include_feature:
        try:
            subject = feature_subject(review, accepted)
        except (ValueError, AssertionError, OSError, MTGOLandingEditorialError) as exc:
            feature_error = str(exc)
    localization = json.loads(args.localization.read_text(encoding='utf-8'))
    used_names = set()
    for row in review['records']:
        file, locator = row['source_locator'].split('#')
        raw = json.loads((ROOT / file).read_text(encoding='utf-8'))
        player = raw['players'][int(locator.split('/')[-1])]
        assert int(player['final_rank']) == row['rank']
        assert (player.get('player') or player.get('name')) == row['player']
        row['main_deck'] = player['main_deck']
        row['sideboard'] = player.get('sideboard', [])
        row['reference'] = f"{args.week}-{args.format}-{row['event_id']}-{row['rank']:02d}"
        used_names.update(c['name'] for zone in ('main_deck', 'sideboard') for c in row[zone])
    by_key = {(r['event_id'], r['rank']): r for r in review['records']}
    for deck in subject['all_top8'] if subject is not None else []:
        row = by_key[(deck['event_id'], deck['final_rank'])]
        assert row['player'] == deck['player']
        def quantities(cards):
            result = Counter()
            for card in cards:
                result[normalize_legacy_card_name(card['name'])] += int(card['qty'])
            return result
        assert quantities(row['main_deck']) == quantities(deck['main_deck']), (row['reference'], quantities(row['main_deck']), quantities(deck['main_deck']))
        assert quantities(row['sideboard']) == quantities(deck['side_deck']), (row['reference'], quantities(row['sideboard']), quantities(deck['side_deck']))
        deck['reference'] = row['reference']
    data = {'classification': source_review, 'subject': subject,
            'review_stage': 'feature' if subject is not None else 'classification',
            'feature_blocker': feature_error,
            'accepted_evidence': [{'date': x.get('accepted_on'), 'evidence': x.get('evidence')} for x in accepted],
            'localization': {n: localization[n] for n in used_names if n in localization}}
    if bootstrap:
        data['deck_details'] = {f"{r['event_id']}-{r['rank']}": {key: r[key] for key in ('main_deck', 'sideboard', 'reference')} for r in review['records']}
        proposals = getattr(args, 'name_proposals', None)
        data['name_proposals'] = json.loads(proposals.read_text(encoding='utf-8')) if proposals else {}
        data['rule_candidates'] = yaml.safe_load((ROOT / review['classifier']['rules_path']).read_text(encoding='utf-8'))['archetypes']
    reference = getattr(args, 'reference_comparison', None)
    if reference:
        comparison = json.loads(reference.read_text(encoding='utf-8'))
        if comparison['summary']['classifier_digest'] != review['classifier']['subject_digest']:
            raise ValueError('reference comparison and weekly review use different classifier inputs')
        data['reference_comparison'] = comparison
    addendum = getattr(args, 'classification_addendum', None)
    if addendum:
        comparison = json.loads(addendum.read_text(encoding='utf-8'))
        if comparison['summary']['candidate_digest'] != review['classifier']['subject_digest']:
            raise ValueError('classification addendum and weekly review use different classifier inputs')
        data['classification_addendum'] = comparison
    output.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    template = Path(__file__).with_name('weekly_review_web.html').read_text(encoding='utf-8')
    if getattr(args, 'multi_scope', False):
        template = template.replace('<nav>', '<nav><a href="../../index.html">返回赛制入口</a>')
    (output / 'index.html').write_text(template.replace('__REVIEW_DATA__', payload), encoding='utf-8')
    (output / 'review-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'events': len(review['events']), 'records': len(review['records']),
                      'priority_records': len(review['machine_priority_records']),
                      'top8': len(subject['all_top8']) if subject is not None else None,
                      'candidates': len(subject['candidate_evidence']) if subject is not None else None,
                      'classification_already_accepted': bool(accepted)}, ensure_ascii=False))
    if feature_error:
        # Replace any old Feature snapshot at this URL before reporting the refusal.
        raise FeatureReviewUnavailable(feature_error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', action='append', default=[], help='Repeat FORMAT=YYYY-Wnn')
    parser.add_argument('--format')
    parser.add_argument('--week')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--localization', type=Path, required=True)
    parser.add_argument('--include-feature', action='store_true', help='After classification acceptance and statistics refresh, include Feature review')
    parser.add_argument('--name-review-bootstrap', action='store_true', help='Private first classification/name review, without Landing screening')
    parser.add_argument('--name-proposals', type=Path, help='Optional display-only Chinese proposals keyed by taxonomy identity_key')
    parser.add_argument('--reference-comparison', type=Path, help='Private reference comparison with explanations and the same classifier digest')
    parser.add_argument('--classification-addendum', type=Path, help='Private grouped classification additions with the same classifier digest')
    args = parser.parse_args()
    if args.name_proposals and not args.name_review_bootstrap:
        parser.error('--name-proposals requires --name-review-bootstrap')
    if args.reference_comparison and not args.name_review_bootstrap:
        parser.error('--reference-comparison requires --name-review-bootstrap')
    if args.classification_addendum and not args.name_review_bootstrap:
        parser.error('--classification-addendum requires --name-review-bootstrap')
    if args.classification_addendum and args.reference_comparison:
        parser.error('select one private comparison view')
    if not args.scope:
        if not args.format or not args.week:
            parser.error('provide --scope or both --format and --week')
        return build_scope(args)
    if args.format or args.week:
        parser.error('--scope cannot be combined with --format/--week')
    require_private_output(ROOT, args.output.resolve() / 'index.html')
    cards = []
    failed = False
    labels = {'standard': '标准', 'modern': '摩登', 'pauper': '纯铁', 'pioneer': '先驱'}
    for scope in dict.fromkeys(args.scope):
        if not re.fullmatch(r'[a-z][a-z0-9-]*=\d{4}-W\d{2}', scope):
            parser.error(f'invalid scope: {scope}')
        format_id, week = scope.split('=')
        relative = f'{format_id}/{week}'
        try:
            build_scope(argparse.Namespace(format=format_id, week=week, output=args.output/relative, localization=args.localization, multi_scope=True, name_review_bootstrap=args.name_review_bootstrap, name_proposals=args.name_proposals, include_feature=args.include_feature))
            status = f'<a href="{relative}/index.html">打开完整材料 →</a>'
        except FeatureReviewUnavailable as exc:
            failed = True
            status = f'<p>{html.escape(str(exc))}</p><a href="{relative}/index.html">打开当前分类材料 →</a>'
        except (ValueError, KeyError, AssertionError, OSError, MTGOLandingEditorialError) as exc:
            failed = True
            status = f'<p>材料暂不可用：{html.escape(str(exc) or type(exc).__name__)}</p>'
        cards.append(f'<section><h2>{html.escape(labels.get(format_id,format_id))}</h2><p>{week}</p>{status}</section>')
    args.output.mkdir(parents=True, exist_ok=True)
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每周审阅入口</title><style>body{max-width:1050px;margin:40px auto;padding:20px;background:#f3f5f0;color:#183b39;font:16px/1.7 system-ui}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}section{padding:24px;background:white;border:1px solid #d9e3dc;border-radius:12px}a{color:#126b60}</style><h1>每周审阅</h1><p>按赛制和周次查看材料。先完成分类与统计更新，再选 Feature 和写稿；这里不记录实时选择。</p><main>'+''.join(cards)+'</main></html>'
    (args.output/'index.html').write_text(page,encoding='utf-8')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
