"""Observed W38 failure sequence and the nearby concurrency/privacy boundaries."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import ANY, Mock, patch

import pytest
import yaml

from tools import pages_writer
from tools.delivery import commands, state


TARGET = 'Jacelber/mtgo-data-governance-verification'


@pytest.fixture
def delivery():
    saved = state.initial()
    saved['current'] = {'operation': 'A', 'package': 'A', 'health': 'passed',
                        'remote': {'deployment_id': '1'}}
    saved['packages'] = {key: {'complete': True, 'target': TARGET, 'eligible': key == 'A'}
                         for key in ('A', 'B', 'C')}
    saved = state.claim(saved, operation='B', package='B', base='A')
    saved = state.bind_remote(state.sending(saved, 'B'), 'B', {'pages_id': 'original'})
    saved['pending'].update(run='7', attempt='1')
    archive, pages = Mock(), Mock()
    def save(updated, sha):
        nonlocal saved
        assert sha == 'sha'
        saved = deepcopy(updated)
        return 'sha'
    archive.load_state.side_effect = lambda: (deepcopy(saved), 'sha')
    archive.save_state.side_effect = save
    archive.retrieve.return_value = {'id': 'B', 'probes': {}}
    pages.client.api.return_value = {'status': 'completed', 'id': 7}
    pages.query.return_value = {'status': 'updating_pages'}
    pages.operation_record.return_value = '2'
    with patch.object(commands, 'context', return_value=(archive, pages)), \
            patch.object(pages_writer, 'observe_content', return_value={'state': 'matching', 'mismatches': []}) as observe:
        yield archive, pages, observe


def test_timeout_then_next_preparation_reconciles_same_operation(delivery):
    archive, pages, _ = delivery
    assert commands.preflight(TARGET)['state'] == 'waiting'
    archive.retrieve.assert_not_called()  # Still running needs no product download.
    archive.save_state.assert_not_called()
    pages.query.return_value = {'status': 'succeed'}
    result = commands.preflight(TARGET)
    assert (result['state'], result['base']) == ('ready', 'B')
    assert result['current']['health'] == 'passed'
    assert archive.load_state()[0]['pending'] is None
    assert [call.args[0] for call in pages.query.call_args_list] == ['original', 'original']
    archive.retrieve.assert_called_once_with('B', ANY, target=TARGET)
    pages.create.assert_not_called()
    pages.cancel.assert_not_called()


def test_running_workflow_and_query_failure_never_clear_pending(delivery):
    archive, pages, _ = delivery
    pages.client.api.return_value = {'status': 'in_progress', 'id': 7}
    assert commands.preflight(TARGET)['state'] == 'waiting'
    pages.query.assert_not_called()
    pages.client.api.return_value = {'status': 'completed', 'id': 7}
    pages.query.side_effect = RuntimeError('query unavailable')
    with pytest.raises(RuntimeError, match='query unavailable'):
        commands.preflight(TARGET)
    assert archive.load_state()[0]['pending']['operation'] == 'B'
    archive.save_state.assert_not_called()


@pytest.mark.parametrize('platform', ['succeed', 'deployment_failed', 'cancelled'])
def test_completed_write_is_not_automatically_a_healthy_product(delivery, platform):
    archive, pages, observe = delivery
    pages.query.return_value = {'status': platform}
    observe.return_value = {'state': 'unconfirmed', 'mismatches': ['index.html']}
    result = commands.preflight(TARGET)
    assert result['base'] == 'B'
    assert result['current']['health'] == 'unknown'
    assert result['observation']['write_completed'] is True
    saved = archive.load_state()[0]
    assert saved['previous']['package'] == 'A'
    assert saved['pending'] is None
    assert saved['recovery'] is None
    assert saved['packages']['B']['eligible'] is False
    pages.create.assert_not_called()


def test_external_write_and_control_race_do_not_overwrite_facts(delivery):
    archive, pages, observe = delivery
    pages.query.return_value = {'status': 'succeed'}
    pages.current.side_effect = state.Conflict('external deployment')
    with pytest.raises(state.Conflict):
        commands.preflight(TARGET)
    archive.save_state.assert_not_called()
    pages.current.side_effect = None
    def race(*args):
        changed, _ = archive.load_state()
        changed['recovery'] = {'id': 'restore', 'package': 'A'}
        archive.load_state.side_effect = lambda: (changed, 'changed-sha')
        return {'state': 'matching', 'mismatches': []}
    observe.side_effect = race
    with pytest.raises(state.Conflict, match='state changed'):
        commands.preflight(TARGET)
    archive.save_state.assert_not_called()


def test_archived_result_is_discoverable_and_stale_base_is_not_rewritten(delivery):
    archive, pages, _ = delivery
    commands.remember_candidate(TARGET, 'prepare-C', 'C', 'A')
    pages.query.return_value = {'status': 'succeed'}
    with pytest.raises(state.Conflict, match='stale combination'):
        commands.preflight(TARGET, 'prepare-C')
    with pytest.raises(state.Conflict, match='retained'):
        commands.dispatch(TARGET, 'prepare-C', 'C', 'A', 'publish')
    with pytest.raises(state.Conflict, match='cannot be changed'):
        commands.remember_candidate(TARGET, 'prepare-C', 'C', 'B')
    assert archive.load_state()[0]['packages']['C']['preparations']['prepare-C'] == 'A'
    pages.create.assert_not_called()


def test_recovery_remains_actionable_without_releasing_pause(delivery):
    archive, pages, observe = delivery
    saved, _ = archive.load_state()
    saved['recovery'] = {'id': 'restore', 'package': 'A', 'failed_operation': 'B'}
    saved['automatic_publication_pause'] = {'recovery': 'restore'}
    archive.save_state(saved, 'sha')
    pages.query.return_value = {'status': 'succeed'}
    result = commands.preflight(TARGET)
    assert result['state'] == 'recovery_required'
    assert archive.load_state()[0]['automatic_publication_pause'] == {'recovery': 'restore'}
    pages.create.assert_not_called()


def test_never_sent_attempt_settles_but_unknown_send_is_not_replayed(delivery):
    archive, pages, _ = delivery
    saved, _ = archive.load_state()
    saved['pending'].update(phase='claimed', remote=None)
    archive.save_state(saved, 'sha')
    pages.attempt_never_sent.return_value = False
    assert commands.preflight(TARGET)['state'] == 'waiting'
    pages.attempt_never_sent.return_value = True
    result = commands.preflight(TARGET)
    assert (result['base'], result['observation']['state']) == ('A', 'not_sent')
    assert archive.load_state()[0]['pending'] is None
    pages.create.assert_not_called()


def test_same_archived_package_dispatches_after_no_send_without_building(delivery):
    archive, pages, _ = delivery
    saved, _ = archive.load_state()
    saved['pending'].update(phase='claimed', remote=None)
    archive.save_state(saved, 'sha')
    commands.remember_candidate(TARGET, 'candidate-C', 'C', 'A')
    pages.attempt_never_sent.return_value = True
    result = commands.preflight(TARGET, 'candidate-C')
    assert (result['package'], result['candidate_base'], result['base']) == ('C', 'A', 'A')
    pages.client.api.return_value = {'workflow_runs': []}
    result = commands.dispatch(TARGET, 'candidate-C', 'C', 'A', 'publish')
    assert result['state'] == 'submitted'
    assert pages.client.api.call_args.kwargs['body']['inputs']['package'] == 'C'
    archive.retrieve.assert_not_called()
    pages.create.assert_not_called()


def test_product_confirmation_can_converge_on_next_preflight(delivery):
    archive, pages, observe = delivery
    pages.query.return_value = {'status': 'succeed'}
    observe.return_value = {'state': 'unconfirmed', 'mismatches': ['index.html']}
    assert commands.preflight(TARGET)['current']['health'] == 'unknown'
    observe.return_value = {'state': 'matching', 'mismatches': []}
    assert commands.preflight(TARGET)['current']['health'] == 'passed'
    pages.create.assert_not_called()


@pytest.mark.parametrize('outcome', ['ready', 'waiting', 'stale', 'forged', 'missing', 'multiple'])
@pytest.mark.parametrize('explicit', [False, True])
def test_real_workflow_preparation_entry_reuses_or_stops_before_source_build(tmp_path, delivery, outcome, explicit):
    archive, pages, _ = delivery
    saved, _ = archive.load_state()
    saved['pending'] = None
    saved['packages']['C']['preparations'] = {'C': 'A'}
    for info in saved['packages'].values():
        info['target'] = 'Jacelber/mtgo-data'
    if outcome in ('stale', 'forged'):
        saved['current']['operation'] = 'B'
    elif outcome == 'missing':
        saved['packages']['C'].pop('preparations')
    elif outcome == 'multiple':
        saved['packages']['C']['preparations']['another'] = 'A'
    elif outcome == 'waiting':
        saved['pending'] = {'operation': 'B', 'run': '7'}
        pages.client.api.return_value = {'status': 'in_progress', 'id': 7}
    archive.save_state(saved, 'sha')
    workflow = yaml.safe_load((Path(__file__).resolve().parents[2] / '.github/workflows/prepare-pages.yml').read_text(encoding='utf-8'))
    entry = next(step for step in workflow['jobs']['base']['steps'] if step.get('id') == 'base')['run']
    code = entry.split("python - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    output = tmp_path / 'outputs'
    # Missing automatic discovery legitimately prepares a new candidate; this
    # test targets the old-package fast path, so missing requires explicit input.
    explicit = explicit or outcome == 'missing'
    blocked = outcome in ('waiting', 'stale', 'missing') or (explicit and outcome in ('forged', 'multiple')) or (not explicit and outcome == 'forged')
    with patch('tools.delivery.gitfacts.preparation_source', side_effect=AssertionError('Do not prepare source')), \
            patch.dict('os.environ', {'PREPARATION': 'C', 'ARCHIVED_PACKAGE': 'C' if explicit else '',
                                    'ARCHIVED_BASE': 'B' if outcome == 'forged' else 'A',
                                    'ARCHIVED_PREPARATION': '', 'GITHUB_OUTPUT': str(output)}):
        if blocked:
            with pytest.raises((RuntimeError, state.Conflict)):
                exec(compile(code, 'preparation-entry', 'exec'), {})
            assert not output.exists()
        else:
            with pytest.raises(SystemExit) as stopped:
                exec(compile(code, 'preparation-entry', 'exec'), {})
            assert stopped.value.code == 0
            assert output.read_text() == 'operation=A\npackage=C\npreparation=C\n'
    pages.create.assert_not_called()
    archive.retrieve.assert_not_called()
    for name in ('localization-cache', 'build', 'archive'):
        assert workflow['jobs'][name]['if'] == "needs.base.outputs.package == ''"
    assert workflow['jobs']['reuse']['needs'] == 'base'
    reuse = next(step for step in workflow['jobs']['reuse']['steps'] if 'run' in step and 'dispatch(' in step['run'])
    assert reuse['env']['PREPARATION'] == '${{ needs.base.outputs.preparation }}'
    assert "preparation=os.environ['PREPARATION']" in reuse['run']
    writer = yaml.safe_load((Path(__file__).resolve().parents[2] / '.github/workflows/pages.yml').read_text(encoding='utf-8'))
    for job, command in [('request', 'request'), ('deploy', 'claim')]:
        step = next(step for step in writer['jobs'][job]['steps'] if f' {command} --package' in step.get('run', ''))
        assert '--preparation "$PREPARATION"' in step['run']
        assert step.get('env', writer['jobs'][job].get('env', {}))['PREPARATION'] == '${{ inputs.preparation }}'


@pytest.mark.parametrize('supplied,current,error', [('B','B','supplied base'), ('A','B','retained'), ('A','A',None)])
def test_direct_dispatch_checks_trusted_base_before_any_post(delivery, supplied, current, error):
    archive, pages, _ = delivery
    saved, _ = archive.load_state()
    saved['pending'] = None
    saved['current']['operation'] = current
    saved['packages']['C']['preparations'] = {'original-C': 'A'}
    archive.save_state(saved, 'sha')
    pages.client.api.return_value = {'workflow_runs': []}
    if error:
        with pytest.raises(state.Conflict, match=error):
            commands.dispatch(TARGET, 'new-operation', 'C', supplied, 'publish', preparation='original-C')
        pages.client.api.assert_not_called()
    else:
        assert commands.dispatch(TARGET, 'new-operation', 'C', supplied, 'publish', preparation='original-C')['state'] == 'submitted'
        assert pages.client.api.call_args.kwargs['body']['inputs']['preparation'] == 'original-C'
    assert archive.load_state()[0]['packages']['C']['preparations'] == {'original-C': 'A'}
    archive.retrieve.assert_not_called()


def test_multiple_records_require_exact_selection_even_when_bases_equal():
    saved = state.initial()
    saved['packages']['C'] = {'complete': True, 'preparations': {'one': 'A', 'two': 'A'}}
    with pytest.raises(state.Conflict, match='exact preparation'):
        state.archived_preparation(saved, 'C', 'A')
    assert state.archived_preparation(saved, 'C', 'A', 'two')['preparation'] == 'two'
    with pytest.raises(state.Conflict, match='does not belong'):
        state.archived_preparation(saved, 'C', 'A', 'other')


@pytest.mark.parametrize('entry', ['request', 'claim'])
def test_direct_writer_cannot_bypass_preparation_check(delivery, tmp_path, entry):
    import io
    archive, pages, _ = delivery
    saved, _ = archive.load_state()
    saved['pending'] = None
    saved['current']['operation'] = 'B'
    saved['packages']['C']['preparations'] = {'original-C': 'A'}
    archive.save_state(saved, 'sha')
    archive.save_state.reset_mock()
    argv = ['writer', '--target', TARGET, '--operation', 'new-operation', entry,
            '--package', 'C', '--base', 'B', '--preparation', 'original-C']
    if entry == 'claim':
        argv += ['--output', str(tmp_path / 'unused')]
    with patch.object(pages_writer, 'context', return_value=(archive, pages)), \
            patch('sys.argv', argv), patch('sys.stdout', new_callable=io.StringIO) as report:
        assert pages_writer.main() == 2
    assert 'supplied base' in report.getvalue()
    archive.save_state.assert_not_called()
    archive.retrieve.assert_not_called()
    pages.create.assert_not_called()
