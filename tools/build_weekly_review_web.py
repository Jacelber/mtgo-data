"""Build a private, read-only weekly review site from existing machine evidence."""
from pathlib import Path
import argparse
import json
import sys
import html
import re
from collections import Counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mtgmeta.weekly_review import build_mtgo_weekly_review
from mtgmeta.mtgo.landing_editorial import build_top8_subject
from mtgmeta.mtgo.publication import require_private_output
from mtgmeta.mtgo.stats import normalize_legacy_card_name


def build_scope(args):
    output = args.output.resolve()
    require_private_output(ROOT, output / 'index.html')
    review = build_mtgo_weekly_review(ROOT, args.format, args.week)
    subject = build_top8_subject(ROOT, args.format, args.week)
    assert set(review['event_ids']) == set(subject['source_event_ids']), 'Classification and Top 8 event scopes differ'
    assert review['classifier']['subject_digest'] == subject['classifier_digest'], 'Classifier subjects differ'
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
    for deck in subject['all_top8']:
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
    registry = yaml.safe_load((ROOT / 'configs/mtgo_weekly_review_completions.yaml').read_text(encoding='utf-8'))
    # Only exact matching stored classification evidence counts as already accepted.
    def accepted_records(value):
        if isinstance(value, dict):
            if value.get('classification_review_digest') == review['classification_review_digest']:
                yield value
            for child in value.values():
                yield from accepted_records(child)
        elif isinstance(value, list):
            for child in value:
                yield from accepted_records(child)
    accepted = list(accepted_records(registry))
    data = {'classification': review, 'subject': subject,
            'accepted_evidence': [{'date': x.get('accepted_on'), 'evidence': x.get('evidence')} for x in accepted],
            'localization': {n: localization[n] for n in used_names if n in localization}}
    output.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    template = Path(__file__).with_name('weekly_review_web.html').read_text(encoding='utf-8')
    if getattr(args, 'multi_scope', False):
        template = template.replace('<nav>', '<nav><a href="../../index.html">返回赛制入口</a>')
    (output / 'index.html').write_text(template.replace('__REVIEW_DATA__', payload), encoding='utf-8')
    (output / 'review-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'events': len(review['events']), 'records': len(review['records']),
                      'priority_records': len(review['machine_priority_records']),
                      'top8': len(subject['all_top8']), 'candidates': len(subject['candidate_evidence']),
                      'classification_already_accepted': bool(accepted)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', action='append', default=[], help='Repeat FORMAT=YYYY-Wnn')
    parser.add_argument('--format')
    parser.add_argument('--week')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--localization', type=Path, required=True)
    args = parser.parse_args()
    if not args.scope:
        if not args.format or not args.week:
            parser.error('provide --scope or both --format and --week')
        return build_scope(args)
    if args.format or args.week:
        parser.error('--scope cannot be combined with --format/--week')
    require_private_output(ROOT, args.output.resolve() / 'index.html')
    cards = []
    labels = {'standard': '标准', 'modern': '摩登', 'pauper': '纯铁'}
    for scope in dict.fromkeys(args.scope):
        if not re.fullmatch(r'[a-z][a-z0-9-]*=\d{4}-W\d{2}', scope):
            parser.error(f'invalid scope: {scope}')
        format_id, week = scope.split('=')
        relative = f'{format_id}/{week}'
        try:
            build_scope(argparse.Namespace(format=format_id, week=week, output=args.output/relative, localization=args.localization, multi_scope=True))
            status = f'<a href="{relative}/index.html">打开完整材料 →</a>'
        except (ValueError, KeyError, AssertionError, OSError) as exc:
            status = f'<p>材料暂不可用：{html.escape(str(exc) or type(exc).__name__)}</p>'
        cards.append(f'<section><h2>{html.escape(labels.get(format_id,format_id))}</h2><p>{week}</p>{status}</section>')
    args.output.mkdir(parents=True, exist_ok=True)
    page = '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每周审阅入口</title><style>body{max-width:1050px;margin:40px auto;padding:20px;background:#f3f5f0;color:#183b39;font:16px/1.7 system-ui}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}section{padding:24px;background:white;border:1px solid #d9e3dc;border-radius:12px}a{color:#126b60}</style><h1>每周审阅</h1><p>按赛制和周次查看完整材料。在对话中选稿与写稿；这里不记录实时选择。</p><main>'+''.join(cards)+'</main></html>'
    (args.output/'index.html').write_text(page,encoding='utf-8')


if __name__ == '__main__':
    main()
