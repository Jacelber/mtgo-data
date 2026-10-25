"""Lightweight retained-input notice; no classification, statistics or acceptance.

Full review packets remain the responsibility of the existing weekly-maintenance
entry points. This notice never marks a week completed or a product published.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

import jsonschema
import yaml
from mtgmeta.config import load_format_registry
import validate_production_candidate as validation


def monday(week: str) -> date:
    value = date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    if value.strftime('%G-W%V') != week:
        raise ValueError('Invalid review week: ' + week)
    return value


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def build(root: Path, *, retained_sha: str, source_sha: str, run_id: str,
          run_attempt: str, today: date | None = None) -> dict:
    if any(not re.fullmatch(r'[0-9a-f]{40}', s) for s in (retained_sha, source_sha)):
        raise ValueError('Collection notice requires exact retained/source commits')
    if not run_id.isdigit() or not run_attempt.isdigit():
        raise ValueError('Invalid collection run identity')
    today = today or datetime.now(timezone.utc).date()
    registry = load_format_registry(root / 'configs/formats.yaml')
    maintenance = yaml.safe_load((root / 'configs/mtgo_weekly_review_completions.yaml').read_text())
    settings = maintenance['weekly_maintenance']
    admissions = maintenance['data_admissions']['formats']
    results = []
    for fmt, config in settings.items():
        registry.require_mtgo_event_collection(fmt)
        if set(config) != {'start_week'}:
            raise ValueError('Collection notice requires an explicit maintenance start_week')
        start = monday(config['start_week'])
        # Only list recorded membership; do not infer its current acceptance or
        # publication validity. The weekly review still verifies those facts.
        admission = admissions[fmt]
        recorded_ids = set(map(str, admission['initial']['event_ids']))
        for item in admission['weekly_acceptances']:
            recorded_ids.update(map(str, item['event_ids']))
        weeks = defaultdict(list)
        retained_count = 0
        for path in sorted((root / 'data' / fmt).glob('*.json')):
            value = json.loads(path.read_text())
            errors = validation._validate_event_document(path.relative_to(root).as_posix(), value)
            if errors:
                raise ValueError('\n'.join(errors))
            retained_count += 1
            day = date.fromisoformat(value['starttime'][:10])
            week = day.strftime('%G-W%V')
            if monday(week) < start or monday(week) + timedelta(days=7) > today:
                continue
            event_id = str(value['event_id'])
            weeks[week].append({'event_id': event_id, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        pending = []
        for week, events in sorted(weeks.items()):
            unadmitted = sorted({e['event_id'] for e in events} - recorded_ids, key=int)
            if unadmitted:
                pending.append({'week': week, 'retained_event_count': len(events),
                                'unadmitted_event_ids': unadmitted, 'source_digest': digest(events)})
        discovery_path = root / 'data' / fmt / 'mtgo/discovery.json'
        deferred = []
        if discovery_path.is_file():
            discovery = json.loads(discovery_path.read_text())
            errors = validation._validate_discovery_document(discovery_path.relative_to(root).as_posix(), discovery)
            if errors:
                raise ValueError('\n'.join(errors))
            deferred = [{'link': e['link'], 'event_date': e['event_date'], 'status': e['status']}
                        for e in discovery['events'] if e['status'] in {'discovered', 'deferred_incomplete'}]
        results.append({'format': fmt, 'pending_weeks': pending,
                        'retained_event_count': retained_count,
                        'match_file_count': len(list((root / 'data' / fmt / 'mtgo/matches').glob('*.json'))),
                        'deferred_sources': deferred})
    return {'schema_version': '1.9.0', 'document_type': 'weekly_maintenance_readiness',
            'purpose': 'collection_notice', 'status': 'inputs_retained',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'readiness_digest': digest(results),
            'collection': {'retained_sha': retained_sha, 'source_sha': source_sha,
                           'run_id': run_id, 'run_attempt': run_attempt},
            'formats': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--retained-sha', required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-attempt', required=True)
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    document = build(root, retained_sha=args.retained_sha, source_sha=args.source_sha,
                     run_id=args.run_id, run_attempt=args.run_attempt)
    schema = json.loads((root / 'schemas/weekly-maintenance-readiness.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
    if args.github_output:
        with args.github_output.open('a') as stream:
            stream.write(f'readiness-digest={document["readiness_digest"]}\nstatus=inputs_retained\n')
            stream.write(f'artifact-name=weekly-maintenance-readiness-{args.run_id}\n')
    print('Retained-input notice created; classification and public generation were not run.')


if __name__ == '__main__':
    main()
