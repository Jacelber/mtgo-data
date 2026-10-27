"""Compose accepted Landing bytes over current data without regenerating either."""
from pathlib import Path
import shutil

from mtgmeta.generation_progress import GenerationProgress, files, implementation
from mtgmeta.resource_progress import save
from tools.delivery import verification


def editorial_paths(formats, week):
    result = set()
    for fmt in formats:
        base = f'stats/{fmt}/mtgo/landing'
        result.update({f'{base}/current.json', f'{base}/features/{week}.json', f'{base}/features/index.json'})
        result.update(f'{base}/weeks/{week}/{part}.json' for part in
                      ('range', 'completeness', 'environment_decks', 'feature_decks'))
    return result


def retain_reviewed_entry(preview, stage):
    """Keep approved cache versions only when every renderer byte is identical."""
    from tools.delivery.packages import sha256
    from mtgmeta.mtgo.preview_resources import ENTRY, select, versioned_entry_equivalent
    before, after = preview / ENTRY, stage / ENTRY
    if before.read_bytes() == after.read_bytes():
        return False
    approved = {name: sha256(preview / name) for name in select(preview)}
    current = {name: sha256(stage / name) for name in select(stage)}
    proof = {'before_html': before.read_bytes().decode('utf-8'),
             'after_html': after.read_bytes().decode('utf-8')}
    if (set(approved) != set(current)
            or any(approved[name] != current[name] for name in approved if name != ENTRY)
            or not versioned_entry_equivalent(proof, approved, current)):
        raise ValueError('Accepted entry differs beyond identical-renderer cache versions')
    shutil.copyfile(before, after)
    return True


def compose(root, preview, scope, envelopes, work):
    """Private, local-only composition. Missing resources fail without network."""
    import json
    from build_pages_artifact import load_config, publication_paths, _copy_generated_overlays, validate_compatibility
    from mtgmeta.mtgo import metadata, publication, review_submission as review
    from tools.delivery import resources
    from tools import build_landing_card_image_cache as images, build_simple_card_localization as names
    from tools.build_archetype_visuals import require_public_representatives
    root, preview, work = Path(root).resolve(), Path(preview).resolve(), Path(work).resolve()
    if work == root or work.is_relative_to(root) or work == preview or work.is_relative_to(preview):
        raise ValueError('Composition needs an external private work directory')
    config = load_config(root, root / 'configs/pages_publication.json')
    material = verification.material_snapshot(root, scope)
    # Copy only declared public material and the private inputs needed to verify
    # it. No whole-repository clone, generated resources, Git or credentials.
    paths = set(material['files'])
    for value in material['inputs'].values():
        paths.update(value)
    paths.update(files(root, ['configs/*.yaml', 'my_archetypes/*.yaml', 'schemas/*.json']))
    # Old closeout workspaces may contain downloaded overlays. They are seeds,
    # not source products; the generated-overlay verifier installs them once.
    prefixes = tuple(item['public_prefix'] + '/' for item in config['generated_overlays'])
    paths = {p for p in paths if not p.startswith(prefixes)}
    identity = {'root': str(root), 'preview': str(preview), 'scope': scope,
                'source_files': files(root, sorted(paths)), 'preview_files': files(preview, ['**/*']),
                'acceptances': envelopes}
    work.mkdir(parents=True, exist_ok=True)
    progress = GenerationProgress(work / 'composition.json', identity)
    stage, site = work / 'source', work / 'site'
    editorial = editorial_paths(scope['mtgo_formats'], scope['week'])

    def copy_file(source, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.is_file() or source.read_bytes() != dest.read_bytes():
            shutil.copyfile(source, dest)

    def source():
        for fmt in scope['mtgo_formats']:
            if publication.inspect_publication(root, fmt):
                raise ValueError('Current data binding is stale: ' + fmt)
        for relative in sorted(paths):
            copy_file(root / relative, stage / relative)
        for relative in sorted(editorial):
            # Archive growth in another week must survive this composition.
            if relative.endswith('/features/index.json'):
                before = json.loads((root / relative).read_text(encoding='utf-8'))
                after = json.loads((preview / relative).read_text(encoding='utf-8'))
                entries = [v for v in after['weeks'] if v['week'] == scope['week']]
                if len(entries) != 1:
                    raise ValueError('Accepted Feature index lacks selected week')
                before['weeks'] = sorted([v for v in before['weeks'] if v['week'] != scope['week']] + entries,
                                         key=lambda v: v['week'], reverse=True)
                save(stage / relative, before)
            elif (preview / relative).is_file():
                copy_file(preview / relative, stage / relative)
            elif '/weeks/' not in relative or json.loads((preview / relative.split('/weeks/')[0] / 'current.json').read_text(encoding='utf-8')).get('data_files'):
                raise ValueError('Accepted Landing dependency is missing: ' + relative)
        entry_retained = retain_reviewed_entry(preview, stage)
        for fmt in scope['mtgo_formats']:
            old = json.loads((root / f'stats/{fmt}/mtgo/meta.json').read_text(encoding='utf-8'))
            # Existing metadata generator binds the new editorial bytes only;
            # keep the data/rules timestamps and all underlying statistics.
            metadata.generate_metadata(stage, fmt, rules_updated=old['rules_updated'], data_updated=old['data_updated'])
            if publication.inspect_publication(stage, fmt):
                raise ValueError('Composed data binding is stale: ' + fmt)
        allowed = editorial | {f'stats/{fmt}/mtgo/meta.json' for fmt in scope['mtgo_formats']}
        if entry_retained:
            allowed.add('index.html')
        if any((stage / p).read_bytes() != (root / p).read_bytes() for p in paths - allowed):
            raise ValueError('Composition changed material outside accepted content')
    import inspect
    def basis(producer, dependencies, **inputs):
        return {'inputs': identity, 'producer': inspect.getsource(producer), 'copy': inspect.getsource(copy_file),
                'implementation': implementation(root, dependencies), **inputs}
    progress.run('source', basis(source, ['src/mtgmeta/mtgo/metadata.py', 'src/mtgmeta/mtgo/publication.py'],
                 reviewed_entry=inspect.getsource(retain_reviewed_entry)),
                 work, ['source/**/*'], source)

    def local_resources():
        local = [p / names.PUBLIC_PREFIX for p in (preview, root) if (p / names.PUBLIC_PREFIX).is_dir()]
        seed = resources.merge_localization(stage, local, work / 'localization-seed')
        bundle = seed / names.SEED_BUNDLE_DIRECTORY
        # The existing seed exporter trims obsolete demand without new queries.
        # Ordinary untranslated card names retain the existing English fallback;
        # actual selected Landing resources are checked against accepted previews.
        names.verify_bundle(stage, bundle)
        seeds = [p / images.CACHE_PUBLIC_PREFIX for p in (preview, root) if (p / images.CACHE_PUBLIC_PREFIX).is_dir()]
        retained = [images.verify_cache_bundle(stage, seed, exact=False) for seed in seeds]
        needed = {card['name'] for card in images.cache_subject(stage)['cards']}
        if not needed <= {card['name'] for manifest in retained for card in manifest['cards']}:
            raise ValueError('Retained Feature images are incomplete; prepare only the missing resources')
        output = work / 'images'
        if not output.exists():
            images.build_cache_bundle(stage, output, seeds=tuple(seeds))
        images.verify_cache_bundle(stage, output)
        save(work / 'overlays.json', {'card_localization': str(bundle), 'landing_card_images': str(output)})
    progress.run('resources', basis(local_resources, ['tools/delivery/resources.py', 'tools/build_landing_card_image_cache.py',
                 'tools/build_simple_card_localization.py'],
                 source=progress.state['steps']['source']['outputs'],
                 retained_resources=files(root, [names.PUBLIC_PREFIX + '/**/*', images.CACHE_PUBLIC_PREFIX + '/**/*'])), work,
                 ['images/**/*', 'localization-seed/**/*', 'overlays.json'], local_resources)

    def public_site():
        current = publication_paths(stage, config)
        require_public_representatives(stage, current)
        validate_compatibility(stage, config, current)
        for relative in sorted(current):
            copy_file(stage / relative, site / relative)
        (site / '.nojekyll').write_bytes(b'')
        overlays = {key: Path(value) for key, value in json.loads((work / 'overlays.json').read_text()).items()}
        _copy_generated_overlays(stage, site, config, overlays, current | {'.nojekyll'})
        for envelope in envelopes:
            packet = envelope['submission']
            review.require_accepted(packet, envelope['decisions'], current=review.preview_packet(site, packet['format']))
    progress.run('site', basis(public_site, ['build_pages_artifact.py', 'src/mtgmeta/mtgo/review_submission.py'],
                 source=progress.state['steps']['source']['outputs'], resources=progress.state['steps']['resources']['outputs']),
                 work, ['site/**/*'], public_site)
    progress.validated()
    return {'root': stage, 'site': site, 'reused': progress.reused, 'executed': progress.executed}
