"""Exercise the real combine/resume entry with small isolated product inputs."""
import json
from pathlib import Path
import shutil

import pytest

from tools import weekly_maintenance as workflow
from tools.delivery import verification, content
from mtgmeta.generation_progress import files
from mtgmeta.mtgo import review_submission as review


@pytest.mark.parametrize('difference', ['versions', 'markup', 'renderer', 'invalid_version'])
def test_reviewed_entry_preserves_only_cache_versions(tmp_path, difference):
    from hashlib import sha256
    preview, stage = tmp_path / 'preview', tmp_path / 'stage'
    script = b'window.approvedRenderer = true;'
    version = sha256(script).hexdigest()[:12]
    for directory in (preview, stage):
        (directory / 'assets').mkdir(parents=True)
        (directory / 'assets/app.js').write_bytes(script)
    html = '<h1>Approved page</h1><script src="assets/app.js{}"></script>'
    (preview / 'index.html').write_text(html.format('?v=' + version), encoding='utf-8')
    (stage / 'index.html').write_text(html.format(''), encoding='utf-8')
    if difference == 'markup':
        (stage / 'index.html').write_text(html.replace('Approved page', 'Changed page').format(''), encoding='utf-8')
    elif difference == 'renderer':
        (stage / 'assets/app.js').write_bytes(b'window.unapprovedRenderer = true;')
    elif difference == 'invalid_version':
        (preview / 'index.html').write_text(html.format('?v=' + '0' * 12), encoding='utf-8')
    if difference == 'versions':
        assert content.retain_reviewed_entry(preview, stage)
        assert (stage / 'index.html').read_bytes() == (preview / 'index.html').read_bytes()
        assert (stage / 'assets/app.js').read_bytes() == script
    else:
        before = (stage / 'index.html').read_bytes()
        with pytest.raises(ValueError):
            content.retain_reviewed_entry(preview, stage)
        assert (stage / 'index.html').read_bytes() == before


def test_current_data_and_four_acceptances_survive_interrupted_composition(tmp_path, monkeypatch):
    import build_pages_artifact as builder
    from tools import build_archetype_visuals as visuals
    from mtgmeta.mtgo import publication, metadata
    from tools.delivery import resources
    from tools import build_landing_card_image_cache as images, build_simple_card_localization as names
    root, preview = tmp_path / 'root', tmp_path / 'preview'
    formats = ['standard', 'pioneer', 'modern', 'pauper']
    week = '2026-W41'
    selected = {'index.html', 'stats/catalog.json', 'assets/card-cache/v1/manifest.json'}
    for fmt in formats:
        selected |= content.editorial_paths([fmt], week)
        selected |= {f'stats/{fmt}/mtgo/meta.json', f'stats/{fmt}/mtgo/range_1w.json',
                     f'stats/{fmt}/mtgo/landing/features/2026-W40.json'}
    for rel in selected | {'configs/pages_publication.json'}:
        workflow.write(root / rel, {'value': 'latest data', 'rules_updated': 'fixed', 'data_updated': 'fixed'})
    for fmt in formats:
        workflow.write(root / f'stats/{fmt}/mtgo/landing/features/index.json', {'weeks': [
            {'week':'2026-W40'}, {'week':'2026-W42'}]})
    shutil.copytree(root, preview)
    for fmt in formats:
        workflow.write(preview / f'stats/{fmt}/mtgo/range_1w.json', {'value': 'stale preview data'})
        workflow.write(preview / f'stats/{fmt}/mtgo/landing/current.json', {'copy': fmt + ' accepted'})
        workflow.write(preview / f'stats/{fmt}/mtgo/landing/features/index.json', {'weeks': [
            {'week':week}, {'week':'2026-W40'}]})
    config = {'generated_overlays': [{'public_prefix':'assets/card-cache/v1'}], 'compatibility_manifests': []}
    monkeypatch.setattr(builder, 'load_config', lambda *a: config)
    monkeypatch.setattr(builder, 'publication_paths', lambda r, *a: {p for p in selected if (r / p).is_file()})
    monkeypatch.setattr(builder, 'validate_compatibility', lambda *a: None)
    monkeypatch.setattr(visuals, 'require_public_representatives', lambda *a: None)
    monkeypatch.setattr(verification, 'material_snapshot', lambda r, s: {'files': files(r, sorted(selected | {'configs/pages_publication.json'})), 'inputs': {}})
    monkeypatch.setattr(publication, 'inspect_publication', lambda *a: [])
    generated = []
    def metadata_only(stage, fmt, **kwargs):
        generated.append(fmt)
        workflow.write(stage / f'stats/{fmt}/mtgo/meta.json', {'binding': 'accepted', **kwargs})
    monkeypatch.setattr(metadata, 'generate_metadata', metadata_only)
    monkeypatch.setattr(resources, 'complete_localization', lambda *a: True)
    monkeypatch.setattr(resources, 'merge_localization', lambda r, s, d: d)
    monkeypatch.setattr(names, 'verify_bundle', lambda *a: {})
    monkeypatch.setattr(images, 'verify_cache_bundle', lambda *a, **k: {'cards': []})
    monkeypatch.setattr(images, 'cache_subject', lambda *a: {'cards': []})
    built = []
    def image_bundle(stage, output, **kwargs):
        built.append(1)
        workflow.write(output / 'manifest.json', {'cards': []})
    monkeypatch.setattr(images, 'build_cache_bundle', image_bundle)
    def packet(site, fmt):
        return review.make_packet('preview', fmt, week, {'final_page': workflow.read(site / f'stats/{fmt}/mtgo/landing/current.json')}, bindings={})
    monkeypatch.setattr(review, 'preview_packet', packet)
    paths = []
    for fmt in formats:
        submitted = packet(preview, fmt)
        decisions = review.record_decision(submitted, None, ['final_page'], evidence='isolated existing acceptance', accepted_on='2026-10-12', entrypoint='http://localhost/test')
        accepted = tmp_path / (fmt + '.accepted.json')
        workflow.write(accepted, {'submission': submitted, 'decisions': decisions})
        record = tmp_path / (fmt + '.delivery.json')
        from tools.delivery import weekly
        weekly.create_record(record, kind='landing_content', root=root, site=preview,
            scope={'week':week,'mtgo_formats':[fmt]}, references=[accepted], source='isolated')
        paths.append(record)
    originals = files(root, ['**/*'])
    def interrupted(*a): raise OSError('site copy interrupted after completed resources')
    monkeypatch.setattr(builder, '_copy_generated_overlays', interrupted)
    output = tmp_path / 'batch.delivery.json'
    with pytest.raises(OSError, match='interrupted'):
        workflow.combine_content_records(root, preview, paths, output, compose=True)
    assert not output.exists() and len(generated) == 4 and built == [1]
    monkeypatch.setattr(builder, '_copy_generated_overlays', lambda *a: set())
    result = workflow.combine_content_records(root, preview, paths, output, compose=True)
    assert result['composition']['reused'] == ['source', 'resources']
    assert result['composition']['executed'] == ['site']
    assert len(generated) == 4 and built == [1] and files(root, ['**/*']) == originals
    site = Path(result['composition']['site'])
    assert not (Path(result['composition']['root']) / 'assets/card-cache/v1').exists()
    assert (root / 'assets/card-cache/v1/manifest.json').is_file()
    for fmt in formats:
        assert workflow.read(site / f'stats/{fmt}/mtgo/range_1w.json')['value'] == 'latest data'
        assert packet(site, fmt) == packet(preview, fmt)
        index = workflow.read(site / f'stats/{fmt}/mtgo/landing/features/index.json')
        assert [e['week'] for e in index['weeks']] == ['2026-W42', '2026-W41', '2026-W40']
    assert workflow.find_delivery(tmp_path)['state'] == 'located'
    # A byte change cannot silently reuse the composition or invent acceptance.
    workflow.write(preview / 'stats/modern/mtgo/landing/current.json', {'copy':'unaccepted'})
    with pytest.raises(ValueError):
        workflow.combine_content_records(root, preview, paths, output, compose=True)
