"""Collection persistence must not depend on classification or public generation."""
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import jsonschema
import pytest
import yaml

import validate_production_candidate as validation
from tools import generate_mtgo_collection_readiness as notice
from tools import integrate_mtgo_collection as collection

ROOT = Path(__file__).resolve().parents[1]


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value) if not isinstance(value, str) else value)
    return target


def event(number=1, day='2026-09-08'):
    return {'event_id': str(number), 'format': 'CSTANDARD', 'description': 'Synthetic Challenge',
            'starttime': day + 'T12:00:00Z', 'player_count': 8, 'inplayoffs': 1,
            'players': [{'loginid': '1', 'player': 'Synthetic Player', 'swiss_rank': 1,
                         'swiss_score': 12, 'final_rank': 1,
                         'main_deck': [{'name': 'Unclassified future card', 'qty': 60}], 'sideboard': []}]}


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    collection.git(root, 'init')
    collection.git(root, 'config', 'user.name', 'Synthetic collection test')
    collection.git(root, 'config', 'user.email', 'test@example.invalid')
    write(root, 'configs/formats.yaml', (ROOT / 'configs/formats.yaml').read_text())
    write(root, 'data/standard/1.json', event())
    write(root, 'fetched.txt', '/decklist/standard-challenge-2026-09-081\n')
    # No generated statistics, names or classifier rules exist in this checkout.
    collection.git(root, 'add', '.')
    collection.git(root, 'commit', '-m', 'synthetic retained inputs')
    return root


def baseline(root):
    return validation.snapshot_state(root, require_public_products=False)


def candidate(root, tmp_path):
    before = baseline(root)
    write(root, 'data/standard/2.json', event(2))
    write(root, 'data/standard/mtgo/matches/2.json', {'event_id': '2', 'matches': []})
    with (root / 'fetched.txt').open('a') as stream:
        stream.write('/decklist/standard-challenge-2026-09-082\n')
    artifact = tmp_path / 'candidate'
    result = collection.export(root, artifact, before)
    assert result['changed']
    assert result['sha256'] == hashlib.sha256((artifact / 'collection.patch').read_bytes()).hexdigest()
    collection.git(root, 'reset', '--hard', 'HEAD')
    return artifact


def commit(root):
    collection.git(root, 'add', '.')
    collection.git(root, 'commit', '-m', 'unrelated delivery')


def test_raw_retention_survives_other_deliveries_and_lost_push_response(repository, tmp_path):
    root = repository
    artifact = candidate(root, tmp_path)
    write(root, 'README.md', 'later documentation')
    write(root, 'my_archetypes/standard.yaml', 'later rules that need not run during collection')
    write(root, 'stats/standard/mtgo/landing/current.json', {'accepted': 'unchanged'})
    write(root, 'data/modern/3.json', {**event(3), 'format': 'CMODERN'})
    commit(root)
    before = (root / 'stats/standard/mtgo/landing/current.json').read_bytes()
    result = collection.integrate(root, artifact, 'HEAD', '100')
    assert result['status'] == 'prepared'
    assert json.loads((root / 'data/standard/2.json').read_text()) == event(2)
    assert (root / 'data/standard/mtgo/matches/2.json').exists()
    assert (root / 'data/modern/3.json').exists()
    assert (root / 'stats/standard/mtgo/landing/current.json').read_bytes() == before
    assert collection.text(root, 'status', '--porcelain') == ''
    head = collection.text(root, 'rev-parse', 'HEAD')
    retry = collection.integrate(root, artifact, 'HEAD', '100')
    assert retry['reused'] and retry['commit'] == head
    assert collection.text(root, 'rev-parse', 'HEAD') == head


def test_overlap_keeps_original_candidate_without_overwriting(repository, tmp_path):
    artifact = candidate(repository, tmp_path)
    write(repository, 'fetched.txt', '/decklist/standard-challenge-2026-09-081\n/decklist/another-source\n')
    commit(repository)
    head = collection.text(repository, 'rev-parse', 'HEAD')
    with pytest.raises(subprocess.CalledProcessError):
        collection.integrate(repository, artifact, 'HEAD', '101')
    assert collection.text(repository, 'status', '--porcelain') == ''
    assert collection.text(repository, 'rev-parse', 'HEAD') == head
    assert (artifact / 'collection.patch').exists()
    assert not (repository / 'data/standard/2.json').exists()


def test_post_apply_failure_rolls_back_and_retains_patch(repository, tmp_path):
    artifact = candidate(repository, tmp_path)
    # An invalid transferred document can pass git apply, but not source validation.
    path = artifact / 'collection.patch'
    path.write_text(path.read_text().replace('CSTANDARD', 'CMODERN'))
    with pytest.raises(ValueError, match='format'):
        collection.integrate(repository, artifact, 'HEAD', '102')
    assert collection.text(repository, 'status', '--porcelain') == ''
    assert not (repository / 'data/standard/2.json').exists()
    assert path.exists()


def test_no_change_has_no_commit_and_public_validation_stays_strict(repository, tmp_path):
    head = collection.text(repository, 'rev-parse', 'HEAD')
    artifact = tmp_path / 'candidate'
    assert not collection.export(repository, artifact, baseline(repository))['changed']
    result = collection.integrate(repository, artifact, 'HEAD', '103')
    assert result['status'] == 'unchanged' and result['commit'] == head
    with pytest.raises(validation.CandidateValidationError, match='missing required.*products'):
        validation._configured_formats(repository)


@pytest.mark.parametrize('mutation,error', [
    ('product', 'Outside collection scope'), ('rule', 'Outside collection scope'),
    ('delete', 'deletion'), ('ledger', 'discard fetched'),
    ('format', 'format'), ('symlink', 'symlinks'), ('discovery', 'discard discovered'),
])
def test_rejects_loss_invalid_source_and_out_of_scope_writes(repository, tmp_path, mutation, error):
    root = repository
    if mutation == 'discovery':
        write(root, 'data/standard/mtgo/discovery.json', {
            'schema_version': '1.0.0', 'source': 'mtgo', 'format': 'standard',
            'events': [{'link': '/decklist/original', 'event_date': '2026-09-08', 'status': 'retained'}]})
        commit(root)
    before = baseline(root)
    if mutation == 'product': write(root, 'stats/catalog.json', {})
    if mutation == 'rule': write(root, 'my_archetypes/standard.yaml', {})
    if mutation == 'delete': (root / 'data/standard/1.json').unlink()
    if mutation == 'ledger': write(root, 'fetched.txt', '/decklist/replacement\n')
    if mutation == 'format': write(root, 'data/standard/2.json', {**event(2), 'format': 'MODERN'})
    if mutation == 'symlink': (root / 'data/standard/2.json').symlink_to(root / 'data/standard/1.json')
    if mutation == 'discovery':
        path = root / 'data/standard/mtgo/discovery.json'
        path.write_text(path.read_text().replace('/decklist/original', '/decklist/replacement'))
    with pytest.raises(ValueError, match=error):
        collection.export(root, tmp_path / 'candidate', before)


def test_cli_collection_baseline_works_without_products(repository, tmp_path):
    target = tmp_path / 'baseline.json'
    assert validation.main(['--root', str(repository), 'snapshot', '--collection-only', '--output', str(target)]) == 0
    assert json.loads(target.read_text())['event_files']['standard'] == 1
    assert validation.main(['--root', str(repository), 'formats', '--collection-only', '--kind', 'product']) == 0


def test_pending_notice_needs_no_rules_stats_or_acceptance_verification(repository):
    root = repository
    write(root, 'configs/mtgo_weekly_review_completions.yaml', {
        'weekly_maintenance': {'standard': {'start_week': '2026-W37'}},
        'data_admissions': {'formats': {'standard': {
            'initial': {'event_ids': ['1']}, 'weekly_acceptances': []}}}})
    write(root, 'data/standard/2.json', event(2, '2026-09-09'))  # Late source in previously admitted week.
    write(root, 'data/standard/3.json', event(3, '2026-09-15'))
    write(root, 'data/standard/4.json', event(4, '2026-09-21'))  # Current week is not complete.
    write(root, 'data/standard/5.json', event(5, '2026-09-01'))  # Before maintenance start.
    write(root, 'data/standard/mtgo/discovery.json', {
        'schema_version': '1.0.0', 'source': 'mtgo', 'format': 'standard', 'events': [
            {'link': '/decklist/a', 'event_date': '2026-09-20', 'status': 'deferred_incomplete'},
            {'link': '/decklist/b', 'event_date': '2026-09-20', 'status': 'discovered'},
            {'link': '/decklist/c', 'event_date': '2026-09-20', 'status': 'excluded_no_playoff'}]})
    args = dict(retained_sha='a'*40, source_sha='b'*40, run_id='1', run_attempt='1', today=date(2026, 9, 21))
    value = notice.build(root, **args)
    schema = json.loads((ROOT / 'schemas/weekly-maintenance-readiness.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(value)
    row = value['formats'][0]
    assert [(p['week'], p['unadmitted_event_ids']) for p in row['pending_weeks']] == [
        ('2026-W37', ['2']), ('2026-W38', ['3'])]
    assert len(row['deferred_sources']) == 2
    assert 'completed_reviews' not in row and 'data_admission' not in row
    assert value['readiness_digest'] == notice.build(root, **{**args, 'run_id': '2'})['readiness_digest']
    write(root, 'data/standard/2.json', {**event(2), 'description': 'corrected source'})
    assert value['readiness_digest'] != notice.build(root, **args)['readiness_digest']


def test_daily_workflow_only_retains_inputs_and_keeps_recovery():
    workflow = yaml.safe_load((ROOT / '.github/workflows/update.yml').read_text())
    jobs = workflow['jobs']
    assert 'build' not in jobs and 'publish' not in jobs
    assert jobs['retain']['needs'] == 'fetch'
    assert jobs['weekly-readiness']['needs'] == 'retain'
    scripts = '\n'.join(s.get('run', '') + s.get('with', {}).get('script', '')
                        for j in jobs.values() for s in j['steps'])
    for forbidden in ('build-statistics', 'build-matchups', 'build-top8', 'build-landing',
                      'build-completeness', 'classification-reports', 'createWorkflowDispatch',
                      'generate_weekly_maintenance_readiness.py'):
        assert forbidden not in scripts
    fetch = jobs['fetch']['steps']
    names = [s['name'] for s in fetch]
    assert names.index('Package resumable fetch checkpoint') > names.index('Upload immutable collected inputs')
    artifact = next(s for s in fetch if s['name'] == 'Upload immutable collected inputs')['with']
    assert artifact['retention-days'] == 30
    assert '/collection.patch\n' not in artifact['path'] and 'collection.patch.gz.cms' in artifact['path']
    assert jobs['retain']['permissions']['actions'] == 'read'


def test_collection_notice_does_not_close_or_downgrade_weekly_reviews(tmp_path):
    node = shutil.which('node')
    if not node: pytest.skip('Node required to verify actual notification JavaScript')
    workflow = yaml.safe_load((ROOT / '.github/workflows/update.yml').read_text())
    script = next(s['with']['script'] for s in workflow['jobs']['weekly-readiness-notify']['steps']
                  if s['name'] == 'Create or update the deduplicated readiness issue')
    path = tmp_path / 'script.json'
    path.write_text(json.dumps(script))
    harness = r'''
const assert=require('assert');
const script=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));
const run=new (Object.getPrototypeOf(async function(){}).constructor)('require','core','github','context','process',script);
(async()=>{
 for(const kind of ['new','update','identical','empty','empty_existing']) {
  const calls=[];
  const data={schema_version:'1.9.0',readiness_digest:'new',collection:{retained_sha:'abc'},formats:[{
   format:'standard',pending_weeks:kind.startsWith('empty')?[]:[{week:'2026-W38',unadmitted_event_ids:['2']}],deferred_sources:[]}]};
  const issues=[{number:1,state:'open',body:'<!-- weekly-maintenance:standard:2026-W38 -->'},
                {number:2,state:'closed',body:'<!-- weekly-maintenance:modern:2026-W38 -->'}];
  if(['update','identical','empty_existing'].includes(kind)) issues.push({number:3,state:'open',body:
   '<!-- mtgo-retained-inputs -->'+(kind==='identical'?'<!-- collection-digest:new -->':'')});
  const github={paginate:async()=>issues,rest:{issues:{listForRepo(){},
   create:async x=>{calls.push(x);return{data:{number:4}}},update:async x=>calls.push(x),
   createComment:async()=>{throw Error('no daily comment spam')}}}};
  const summary={addRaw(){return this},addEOL(){return this},async write(){}};
  await run(n=>n==='fs'?{readFileSync:()=>JSON.stringify(data)}:require(n),{summary},github,
   {repo:{owner:'example',repo:'example'},serverUrl:'https://example.test',runId:1},
   {env:{READINESS_RESULT:'success',READINESS_PATH:'unused'}});
  assert(!calls.some(x=>x.issue_number===1||x.issue_number===2||x.state==='closed'));
  assert.strictEqual(calls.length,['identical','empty'].includes(kind)?0:1);
 }
})().catch(e=>{console.error(e);process.exit(1)});
'''
    result = subprocess.run([node, '-e', harness, str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_transferred_patch_cannot_write_products(repository, tmp_path):
    root = repository
    artifact = tmp_path / 'candidate'
    artifact.mkdir()
    (artifact / 'source.txt').write_text(collection.text(root, 'rev-parse', 'HEAD'))
    write(root, 'stats/catalog.json', {'unaccepted': True})
    collection.git(root, 'add', '.')
    (artifact / 'collection.patch').write_bytes(collection.git(root, 'diff', '--cached', '--binary', 'HEAD'))
    collection.git(root, 'reset', '--hard', 'HEAD')
    with pytest.raises(ValueError, match='escaped collection scope'):
        collection.integrate(root, artifact, 'HEAD', '104')
    assert not (root / 'stats/catalog.json').exists()
    assert collection.text(root, 'status', '--porcelain') == ''


def test_same_run_cannot_silently_retain_different_inputs(repository, tmp_path):
    artifact = candidate(repository, tmp_path)
    collection.integrate(repository, artifact, 'HEAD', '105')
    path = artifact / 'collection.patch'
    path.write_text(path.read_text() + '\n')
    head = collection.text(repository, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match='already retained different'):
        collection.integrate(repository, artifact, 'HEAD', '105')
    assert collection.text(repository, 'rev-parse', 'HEAD') == head
    assert collection.text(repository, 'status', '--porcelain') == ''


@pytest.mark.parametrize('payload', [b'', b'synthetic collected patch\n'])
def test_actual_workflow_handoff_handles_empty_and_nonempty_patches(tmp_path, payload):
    import os
    if not shutil.which('openssl'): pytest.skip('OpenSSL required for actual handoff check')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(tmp_path / 'synthetic-key'), '-out', str(tmp_path / 'cert'),
                    '-subj', '/CN=local-collection-test', '-days', '1'], check=True, capture_output=True)
    workflow = yaml.safe_load((ROOT / '.github/workflows/update.yml').read_text())
    encrypt = next(s['run'] for s in workflow['jobs']['fetch']['steps']
                   if s['name'] == 'Encrypt collected inputs for retention')
    decrypt = next(s['run'] for s in workflow['jobs']['retain']['steps']
                   if s['name'] == 'Decrypt the existing output in the trusted integration job')
    patch = write(tmp_path, 'mtgo-collection-candidate/collection.patch', payload.decode())
    env = {**os.environ, 'RUNNER_TEMP': str(tmp_path),
           'CERTIFICATE': (tmp_path / 'cert').read_text(),
           'HANDOFF_KEY': (tmp_path / 'synthetic-key').read_text()}
    subprocess.run(['bash', '-e', '-c', encrypt], env=env, check=True, capture_output=True)
    patch.unlink()
    # Only ciphertext crosses jobs; the original gzip is not available to decryption.
    patch.with_suffix('.patch.gz').unlink()
    subprocess.run(['bash', '-e', '-c', decrypt], env=env, check=True, capture_output=True)
    assert patch.read_bytes() == payload
    assert not (tmp_path / 'mtgo-output-key.pem').exists()
