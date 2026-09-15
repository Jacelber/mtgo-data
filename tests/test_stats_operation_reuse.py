import json
from collections import Counter
from mtgmeta.mtgo import stats
from test_mtgo_third_format import repository, THIRD, TODAY, NOW


def test_stats_cache_is_per_operation_and_not_shared_across_input_or_rules(tmp_path, monkeypatch):
    repository(tmp_path,'private_executable')
    calls=Counter();original=stats.process_event
    def process(event,rules):
        calls[event['event_id']]+=1
        return original(event,rules)
    monkeypatch.setattr(stats,'process_event',process)
    def run():
        calls.clear()
        files=stats.build_all_stats(tmp_path,THIRD,today=TODAY,generated_at=NOW)
        assert calls=={'100':1,'200':1}
        return json.loads(files['range_4w.json'].read_text(encoding='utf-8'))
    first=run();assert first['total_decks']==16
    assert run()==first
    rule=tmp_path/f'my_archetypes/{THIRD}.yaml'
    rule.write_text(rule.read_text().replace('Signal Card','Different Card'))
    changed=run();assert changed!=first
    rule.write_text(rule.read_text().replace('Different Card','Signal Card'))
    event=tmp_path/f'data/{THIRD}/200.json';value=json.loads(event.read_text());value['players'].pop();event.write_text(json.dumps(value))
    assert run()['total_decks']==15


def test_public_loader_reads_once_and_still_rejects_unadmitted_bad_input(tmp_path,monkeypatch):
    from pathlib import Path
    import pytest
    from mtgmeta.mtgo.publication import PublicationError
    repository(tmp_path,'complete_public')
    counts=Counter();original=Path.read_text
    def read(path,*args,**kwargs):
        if path.parent==tmp_path/f'data/{THIRD}':counts[path.name]+=1
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    events=stats.load_events_from_directory(tmp_path/f'data/{THIRD}',repository_root=tmp_path,format_id=THIRD,public=True)
    assert len(events)==1 and counts=={'100.json':1,'200.json':1}
    p=tmp_path/f'data/{THIRD}/200.json';value=json.loads(p.read_text());value['format']='CMODERN';p.write_text(json.dumps(value))
    with pytest.raises(PublicationError,match='cross-format'):
        stats.load_events_from_directory(p.parent,repository_root=tmp_path,format_id=THIRD,public=True)
