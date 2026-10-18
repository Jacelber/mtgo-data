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
