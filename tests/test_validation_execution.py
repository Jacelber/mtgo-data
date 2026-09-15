import subprocess
from pathlib import Path
import pytest
import validate_schemas as v

@pytest.mark.parametrize('phase', ['load_schemas', 'validate_instance'])
def test_timeout_interrupts_stuck_phase_and_reaps_worker(tmp_path, monkeypatch, capfd, phase):
    import json, os, time
    monkeypatch.setenv("PYTHONPATH", str(Path(v.__file__).parent) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    (tmp_path/'selected.json').write_text('3')
    schemas=tmp_path/'schemas';schemas.mkdir()
    (schemas/'manifest.json').write_text(json.dumps({'schema_version':'1.0.0','output_schema_version_embedded':True,'mappings':[{'pattern':'selected.json','schema':'value.schema.json'}]}))
    (schemas/'value.schema.json').write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://example.test/value.schema.json','type':'integer'}))
    source=Path(v.__file__).read_text(encoding='utf-8')
    marker='    schemas: dict[str, dict[str, Any]] = {}' if phase=='load_schemas' else '    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())'
    source=source.replace(marker, '    print("STUCK '+phase+'", file=sys.stderr, flush=True)\n    __import__("time").sleep(60)\n'+marker,1)
    script=tmp_path/'validator.py';script.write_text(source,encoding='utf-8');monkeypatch.setattr(v,'__file__',str(script))
    children=[];original=subprocess.Popen
    def spawn(*args,**kwargs):
        child=original(*args,**kwargs);children.append(child);return child
    monkeypatch.setattr(subprocess,'Popen',spawn)
    started = time.monotonic()
    with pytest.raises(TimeoutError,match='incomplete'):
        v.validate_manifest(tmp_path,schemas/'manifest.json',{'selected.json'},timeout_seconds=3)
    assert time.monotonic() - started < 8
    assert children and all(child.poll() is not None for child in children)
    assert 'STUCK '+phase in capfd.readouterr().err
    assert (tmp_path/'selected.json').read_text()=='3'
    # Repair just the validator and retry the same preserved output.
    monkeypatch.undo()
    checked,errors=v.validate_manifest(tmp_path,schemas/'manifest.json',{'selected.json'},timeout_seconds=10)
    assert checked==1 and not errors


def test_resume_stage_skips_generation_and_rejects_changed_sources(tmp_path,monkeypatch):
    from mtgmeta import classifier_closure as c
    root=tmp_path/'root';stage=tmp_path/'stage'
    for base in (root,stage):
        (base/'src').mkdir(parents=True)
        (base/'src/generator.py').write_text('unchanged')
        (base/'validate_schemas.py').write_text('# validator')
        (base/'stats').mkdir()
    (root/'stats/result.json').write_text('old');(stage/'stats/result.json').write_text('new')
    monkeypatch.setattr(c,'_protected_input_fingerprints',lambda *a:{'input':'same'})
    monkeypatch.setattr(c,'inspect_format',lambda base,fmt:{'state':c.CURRENT if (base/'stats/result.json').read_text()=='new' else c.STALE})
    monkeypatch.setattr(c,'_changed_tree_paths',lambda *a:['stats/result.json'])
    monkeypatch.setattr(c,'_allowed_refreshed_artifacts',lambda *a:{'stats/result.json'})
    monkeypatch.setattr(c,'_build_staged_format',lambda *a:pytest.fail('must not regenerate'))
    monkeypatch.setattr(c,'_validate_staged_schemas',lambda *a:(_ for _ in ()).throw(c.SchemaExecutionError('timeout')))
    failed=c.converge_format(root,'standard',execute=True,resume_stage=stage)
    assert failed['state']=='EXECUTION_FAILED' and stage.exists()
    assert (root/'stats/result.json').read_text()=='old'
    (root/'schemas').mkdir();(root/'schemas/fixed.schema.json').write_text('{}')
    monkeypatch.setattr(c,'_validate_staged_schemas',lambda *a:None)
    assert c.converge_format(root,'standard',execute=True,resume_stage=stage)['state']==c.CURRENT
    assert (root/'stats/result.json').read_text()=='new'
    assert (stage/'schemas/fixed.schema.json').read_text()=='{}'
    (root/'stats/result.json').write_text('old');(root/'src/generator.py').write_text('changed')
    with pytest.raises(c.ClassifierClosureError,match='inputs changed'):
        c.converge_format(root,'standard',execute=True,resume_stage=stage)

def test_publication_resume_preserves_stage_and_does_not_generate(tmp_path,monkeypatch):
    import shutil,subprocess
    from test_mtgo_reviewed_publication import _repository,_generate
    from mtgmeta.mtgo import publication,stats
    from mtgmeta import classifier_closure as closure
    root=tmp_path/'root';root.mkdir();_repository(root)
    for fmt in ('standard','modern'):_generate(root,fmt)
    stage=tmp_path/'stage';shutil.copytree(root,stage)
    for base in (root,stage):(base/'validate_schemas.py').write_text('# validation implementation')
    monkeypatch.setattr(closure,'inspect_format',lambda *a:{'state':'CURRENT'})
    monkeypatch.setattr(stats,'build_all_stats',lambda *a,**k:pytest.fail('resume must not regenerate'))
    retained = {p.relative_to(stage): p.read_bytes() for directory in ('stats','reports') for p in (stage/directory).rglob('*.json')}
    commands=[]
    def failed(args,**kwargs):
        commands.append(args)
        if any('validate_output_invariants.py' in str(arg) for arg in args):
            raise subprocess.CalledProcessError(2,args)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(subprocess,'run',failed)
    with pytest.raises(subprocess.CalledProcessError):
        publication.stage_publication(root,'standard',resume_stage=stage)
    assert stage.is_dir()
    monkeypatch.setattr(subprocess,'run',lambda args,**kwargs:subprocess.CompletedProcess(args,0))
    result=publication.stage_publication(root,'standard',resume_stage=stage)
    assert result['stage']==str(stage) and not result['executed']
    assert {p: (stage/p).read_bytes() for p in retained} == retained
    extra=stage/'stats/standard/mtgo/unrelated.json';extra.write_text('{}')
    with pytest.raises(publication.PublicationError,match='invalid staged publication'):
        publication.stage_publication(root,'standard',resume_stage=stage)
    extra.unlink()
    victim=stage/'stats/standard/mtgo/range_1w.json';victim.write_text('{}')
    with pytest.raises(publication.PublicationError,match='invalid staged publication'):
        publication.stage_publication(root,'standard',resume_stage=stage)
