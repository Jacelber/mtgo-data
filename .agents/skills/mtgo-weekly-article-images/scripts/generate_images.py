"""Local MTGO article tables. Uses project classification and scoring unchanged."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys


def event_suffix(name, format_id):
    """Article labels preserve ordinary Challenge headers and mark special events."""
    from mtgmeta.mtgo.top8 import event_display_name
    import re
    compact = event_display_name(name, format_id)
    if re.fullmatch(r'C\d+', compact):
        return ''
    if compact == 'RCSQ':
        return 'SQ'
    return compact


def share(count, total):
    return Fraction(count, total) if total else None


def summarize(periods):
    """Periods are current week, previous week, and pooled previous four weeks."""
    counters = []
    totals = []
    for records in periods:
        high, top = Counter(), Counter()
        for record in records:
            key = (record['archetype_id'], record['subtype_id'])
            high[key] += int(record['is_high_score'])
            top[key] += int(record['is_top8'])
        counters.append((high, top))
        totals.append((sum(high.values()), sum(top.values())))
    if not totals[0][0] or not totals[2][0]:
        raise ValueError('Current and previous-four-week high-score populations are required')
    identities = set().union(*(set(h) | set(t) for h, t in counters))
    selected = [k for k in identities if
                share(counters[0][0][k], totals[0][0]) >= Fraction(2, 100)
                or share(counters[2][0][k], totals[2][0]) >= Fraction(2, 100)]
    selected.sort(key=lambda k: (-share(counters[0][0][k], totals[0][0]),
                                -share(counters[2][0][k], totals[2][0]),
                                k[0], k[1] or ''))
    other = identities - set(selected)
    def values(keys):
        return [[sum(counter[k] for k in keys) for counter in pair] for pair in counters]
    return [(k, values([k])) for k in selected] + [(None, values(other))], totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--format', required=True)
    parser.add_argument('--week', required=True, help='ISO week, e.g. 2026-W42')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--draft-note', default='', help='Known gaps or provisional classification; saved outside the images')
    parser.add_argument('--code-root', type=Path, help='Project Python source when --repo is a frozen input tree')
    parser.add_argument('--expected-current-events', type=int, required=True)
    parser.add_argument('--font', type=Path, default=Path('C:/Windows/Fonts/msyh.ttc'))
    parser.add_argument('--bold-font', type=Path, default=Path('C:/Windows/Fonts/msyhbd.ttc'))
    parser.add_argument('--events-per-block', type=int, default=7)
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    if args.expected_current_events < 1 or args.events_per_block < 1:
        parser.error('expected-current-events and events-per-block must be positive')
    if out.exists():
        raise ValueError('Use a new output directory to preserve the previous input snapshot')
    if out.is_relative_to(root / 'stats') or out.is_relative_to(root / 'data'):
        raise ValueError('Article images and private inputs belong outside public data trees')
    code_root = (args.code_root or root).resolve()
    sys.path.insert(0, str(code_root / 'src'))
    for dependency_root in dict.fromkeys([code_root, root]):
        packages = dependency_root / '.venv/Lib/site-packages'
        if packages.exists():
            sys.path.append(str(packages))
    import yaml
    from PIL import Image, ImageDraw, ImageFont
    from mtgmeta.mtgo import load_mtgo_context
    from mtgmeta.mtgo.normalize import load_rules_for_format
    from mtgmeta.mtgo.stats import process_event, parse_event_date
    from mtgmeta.classifier import classifier_digest
    from mtgmeta.mtgo.publication import require_private_output

    require_private_output(code_root, out)
    require_private_output(root, out)

    year, week = map(int, args.week.split('-W'))
    monday = date.fromisocalendar(year, week, 1)
    end = monday + timedelta(days=7)
    if end > datetime.now(timezone(timedelta(hours=9))).date():
        raise ValueError('Only complete natural weeks can be rendered')
    start = monday - timedelta(weeks=4)
    ctx = load_mtgo_context(root, args.format, 'event_statistics')
    snapshot = out / 'inputs'
    frozen = {}
    def preserve(relative, content):
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        frozen[relative.as_posix()] = sha256(content).hexdigest()
    rule_document = yaml.safe_load(ctx.paths['rules'].read_text('utf-8'))
    input_paths = [Path('configs/formats.yaml'), Path('configs/mtgo_archetype_names.yaml'),
                   ctx.paths['rules'].relative_to(root)]
    if rule_document.get('semantic_features'):
        semantic_path = Path(rule_document['semantic_features']['manifest_path'])
        if not (root / semantic_path).resolve().is_relative_to(root):
            raise ValueError('Semantic feature path escapes input repository')
        input_paths.append(semantic_path)
    for relative in input_paths:
        preserve(relative, (root / relative).read_bytes())
    events = []
    for path in sorted(ctx.paths['events'].glob('*.json')):
        raw = path.read_bytes()
        event = json.loads(raw)
        event_date = parse_event_date(event.get('starttime'))
        if event_date is None:
            raise ValueError(f'Invalid event date: {path.name}')
        if not start <= event_date < end:
            continue
        if event.get('format') != 'C' + args.format.upper():
            raise ValueError(f'Cross-format input: {path.name}')
        preserve(path.relative_to(root), raw)
        events.append((event_date, event))
    ids = [str(e['event_id']) for _, e in events]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate event identity')
    rules = load_rules_for_format(snapshot, args.format)
    names_data = yaml.safe_load((snapshot / 'configs/mtgo_archetype_names.yaml').read_text('utf-8'))
    names = {(r['parent_id'], r.get('subtype_id')): r['chinese']
             for r in names_data['names'] if r['format'] == args.format
             and r.get('review_status') == 'approved' and r.get('chinese')}
    names[('unknown', None)] = '未分类'
    def name(key):
        if key not in names:
            raise ValueError(f'Missing approved Chinese leaf name: {key}')
        return names[key]
    processed = [(d, process_event(e, rules)) for d, e in events]
    current_events = sorted([(d, e) for d, e in processed if monday <= d < end],
                            key=lambda pair: (pair[1]['starttime'], pair[1]['event_id']))
    if not current_events:
        raise ValueError('No current-week events; never fall back to another week')
    if len(current_events) > args.expected_current_events:
        raise ValueError('Expected event count is below retained current events')
    if len(current_events) < args.expected_current_events and not args.draft_note.strip():
        raise ValueError('Missing expected events: provide --draft-note for an authorized trial')
    for i in range(1, 5):
        w = monday - timedelta(weeks=i)
        if not any(w <= d < w + timedelta(days=7) for d, _ in processed):
            raise ValueError(f'No retained reference events for {w}; confirm empty week separately')
    periods = [[r for d, e in processed if lower <= d < upper for r in e['records']]
               for lower, upper in [(monday, end), (monday-timedelta(weeks=1), monday), (start, monday)]]
    rows, totals = summarize(periods)
    rendered_rows = []
    for key, values in rows:
        rendered_rows.append({'identity': list(key) if key else None,
                              'name': name(key) if key else '其他', 'counts': values,
                              'shares': [[float(share(v, n)) if n else None for v, n in zip(pair, denom)]
                                         for pair, denom in zip(values, totals)]})
    event_table = []
    for d, event in current_events:
        by_rank = {}
        for r in event['records']:
            rank = r['final_rank']
            if rank <= 8:
                if rank in by_rank:
                    raise ValueError(f'Duplicate final rank: {event["event_id"]}/{rank}')
                by_rank[rank] = r
        placements = []
        for rank in range(1, 9):
            r = by_rank.get(rank)
            key = (r['archetype_id'], r['subtype_id']) if r and r['main_deck'] else None
            placements.append({'rank': rank, 'identity': list(key) if key else None,
                               'name': name(key) if key else '牌表缺失'})
        event_table.append({'date': d.isoformat(), 'event_id': event['event_id'],
                            'name': event['event_name'], 'players': event['player_count'],
                            'header_suffix': event_suffix(event['event_name'], args.format),
                            'placements': placements})
    for i, denom in enumerate(totals):
        assert [sum(row['counts'][i][j] for row in rendered_rows) for j in range(2)] == list(denom)
    report = {'format': args.format, 'week': args.week, 'current_period': [monday.isoformat(), (end-timedelta(days=1)).isoformat()],
              'four_week_period': [start.isoformat(), (monday-timedelta(days=1)).isoformat()],
              'four_week_method': 'pooled_raw_counts_excluding_current_week',
              'draft_note': args.draft_note, 'expected_current_events': args.expected_current_events,
              'image_style': 'table_only', 'events_per_block': args.events_per_block,
              'classifier_digest': classifier_digest(rules), 'input_sha256': frozen,
              'totals': totals, 'reference_weeks': [
                  {'monday': (monday-timedelta(weeks=i)).isoformat(),
                   'events': sum(monday-timedelta(weeks=i) <= d < monday-timedelta(weeks=i-1) for d, _ in processed)}
                  for i in range(1, 5)], 'events': event_table, 'rows': rendered_rows}
    (out / 'table-data.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    scale = 2
    def font(size, bold=False):
        return ImageFont.truetype(str(args.bold_font if bold else args.font), round(size*scale))
    def canvas(w, h):
        im = Image.new('RGB', (w*scale+1, h*scale+1), 'white')
        return im, ImageDraw.Draw(im)
    def text(draw, box, value, size=24, bold=False, fill='#111111', align='center'):
        x1, y1, x2, y2 = [v*scale for v in box]
        while size >= 13:
            f = font(size, bold)
            if all(draw.textlength(line, font=f) <= x2-x1-16*scale for line in value.split('\n')):
                break
            size -= 1
        if size < 13:
            raise ValueError(f'Text too wide: {value}')
        bounds = draw.multiline_textbbox((0, 0), value, font=f, spacing=4*scale, align=align)
        height = bounds[3]-bounds[1]
        if height > y2-y1-6*scale:
            raise ValueError(f'Text too tall: {value}')
        width = bounds[2]-bounds[0]
        x = x1+10*scale if align == 'left' else (x1+x2-width)/2
        draw.multiline_text((x, (y1+y2-height)/2-bounds[1]), value, font=f,
                            fill=fill, spacing=4*scale, align=align)
    def cell(draw, box, value, size=24, bold=False, shade=False):
        draw.rectangle(tuple(round(v*scale) for v in box), fill='#cccccc' if shade else 'white', outline='#171717', width=2)
        text(draw, box, value, size, bold)
    blocks = [event_table[i:i+args.events_per_block] for i in range(0, len(event_table), args.events_per_block)]
    cols = min(len(event_table), args.events_per_block)
    width = max(1200, 68+cols*190)
    rank_w, header_h, row_h, gap = 68, 90, 62, 16
    block_height = header_h+8*row_h
    im, draw = canvas(width, len(blocks)*block_height+(len(blocks)-1)*gap)
    for block_index, block in enumerate(blocks):
        x0, y0 = 0, block_index*(block_height+gap)
        cw = (width-rank_w)/len(block)
        cell(draw, (x0,y0,x0+rank_w,y0+header_h), '排名', 23, True, True)
        for j, event in enumerate(block):
            x = x0+rank_w+j*cw
            d = date.fromisoformat(event['date'])
            cell(draw, (x,y0,x+cw,y0+header_h), f'{d.month}月{d.day}日{event["header_suffix"]}\n（{event["players"]}人）', 24, True, True)
            for i, entry in enumerate(event['placements']):
                y = y0+header_h+i*row_h
                cell(draw, (x,y,x+cw,y+row_h), entry['name'], 24)
        for i in range(8):
            y = y0+header_h+i*row_h
            cell(draw, (x0,y,x0+rank_w,y+row_h), str(i+1), 24, True)
    im.save(out / f'{args.format}-{args.week}-top8.png')
    width, y0, row_h = 1360, 0, 58
    height = 108+row_h*len(rendered_rows)
    im, draw = canvas(width, height)
    xs = [0, 76, 420, 576, 732, 888, 1044, 1200, 1360]
    cell(draw, (xs[0],y0,xs[1],y0+108), '排名', 24, True, True)
    cell(draw, (xs[1],y0,xs[2],y0+108), '套牌', 27, True, True)
    for j, label in enumerate(['本周', '上周', '近4周平均']):
        k = 2+j*2
        cell(draw, (xs[k],y0,xs[k+2],y0+54), label, 27, True, True)
        for z, metric in enumerate(['高分','八强']):
            cell(draw, (xs[k+z],y0+54,xs[k+z+1],y0+108), metric, 25, True, True)
    for i, row in enumerate(rendered_rows):
        y = y0+108+i*row_h
        vals = [str(i+1) if row['identity'] else '—', row['name']]
        vals += ['—' if value is None else f'{value*100:.1f}%' for pair in row['shares'] for value in pair]
        for j, value in enumerate(vals):
            cell(draw, (xs[j],y,xs[j+1],y+row_h), value, 27 if j != 1 else 28, j == 0)
    im.save(out / f'{args.format}-{args.week}-shares.png')
    print(json.dumps({'output': str(out), 'events': len(event_table), 'totals': totals,
                      'rows': len(rendered_rows), 'classifier_digest': report['classifier_digest']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
