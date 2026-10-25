import hashlib

from mtgmeta.generation_progress import files


def test_exact_files_and_overlapping_globs_hash_once_without_directory_rescans(tmp_path, monkeypatch):
    for name in ['a.json', 'b.json']:
        (tmp_path / name).write_text(name)
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__/ignored.json').write_text('ignored')
    original_glob, original_read = type(tmp_path).glob, type(tmp_path).read_bytes
    scans, reads = [], []
    def glob(path, pattern):
        scans.append(pattern)
        return original_glob(path, pattern)
    def read(path):
        reads.append(path.name)
        return original_read(path)
    monkeypatch.setattr(type(tmp_path), 'glob', glob)
    monkeypatch.setattr(type(tmp_path), 'read_bytes', read)
    expected = {name: hashlib.sha256(name.encode()).hexdigest() for name in ['a.json', 'b.json']}
    assert files(tmp_path, ['a.json', 'b.json', 'absent.json', '**/*.json']) == expected
    assert scans == ['**/*.json'] and sorted(reads) == ['a.json', 'b.json']


def test_shared_card_logic_change_invalidates_generation_checkpoint(tmp_path):
    from mtgmeta.generation_progress import COMMON, GenerationProgress, implementation

    source = tmp_path / 'src/mtgmeta/classifier_cards.py'
    source.parent.mkdir(parents=True)
    source.write_text('first card logic')
    checkpoint = GenerationProgress(tmp_path / 'progress.json', {'task': 'classifier-test'})
    output = tmp_path / 'classification.json'
    executions = []

    def generate():
        executions.append(source.read_text())
        output.write_text(source.read_text())

    def run():
        checkpoint.run('classification', implementation(tmp_path, COMMON), tmp_path,
                       ['classification.json'], generate)

    run()
    run()
    assert executions == ['first card logic']
    (tmp_path / 'unrelated-page.html').write_text('changed unrelated UI')
    run()
    assert executions == ['first card logic']
    source.write_text('corrected card logic')
    run()
    assert executions == ['first card logic', 'corrected card logic']
    assert output.read_text() == 'corrected card logic'
