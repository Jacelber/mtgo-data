import json

import pytest

from tools.delivery import packages
from tools import review_submission as cli
from mtgmeta.mtgo import review_submission as review


def test_four_formats_share_one_retained_extraction(tmp_path, monkeypatch):
    site = tmp_path / 'site'
    for rel in packages.PROBES:
        path = site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}')
    envelopes = []
    for fmt in ['standard', 'modern', 'pioneer', 'pauper']:
        packet = review.make_packet('preview', fmt, '2026-W41', {'final_page': {'copy': fmt}}, bindings={})
        receipt = review.record_decision(packet, None, ['final_page'], evidence='isolated fixture',
            accepted_on='2026-10-12', entrypoint='http://localhost/fixture')
        envelopes.append({'submission': packet, 'decisions': receipt})
    candidate = tmp_path / 'package'
    manifest = packages.prepare(site, candidate, target='Jacelber/mtgo-data', source='fixture')
    state = {'current': {'operation': 'isolated', 'package': manifest['id'], 'health': 'passed'}, 'pending': None}
    packets = {e['submission']['format']: e['submission'] for e in envelopes}
    def preview(root, fmt):
        assert (root / 'index.html').read_text() == '{}'
        return packets[fmt]
    monkeypatch.setattr(review, 'preview_packet', preview)
    extracts, original = [], packages.extract
    def counted(*args, **kwargs):
        extracts.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(packages, 'extract', counted)
    results = cli.confirmed_completions(envelopes, candidate, state)
    assert set(results) == set(packets) and len(extracts) == 1
    assert cli.confirmed_completions(envelopes, candidate, state) == results
    assert len(extracts) == 1
    # Rechecking a single format uses the same real package/resources too.
    assert cli.confirmed_completion(envelopes[0], candidate, state) == results['standard']
    assert len(extracts) == 1
    extracted = candidate.with_name('package-completion-site')
    (extracted / 'index.html').write_text('tampered')
    with pytest.raises(ValueError, match='extraction changed'):
        cli.confirmed_completions(envelopes, candidate, state)
    with (candidate / 'product.tar.gz').open('ab') as handle: handle.write(b'changed')
    with pytest.raises(ValueError, match='package bytes'):
        cli.confirmed_completions(envelopes, candidate, state)
