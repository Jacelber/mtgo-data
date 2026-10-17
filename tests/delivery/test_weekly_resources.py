from pathlib import Path

import pytest

from tools.delivery import resources


def test_site_promotion_failure_reuses_completed_build(tmp_path, monkeypatch):
    import build_pages_artifact as builder
    root, work = tmp_path / "root", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    (root / "index.html").write_text("fixed")
    for name in ("names", "images"):
        (work / name).mkdir()
        (work / name / "cache.json").write_text("verified fixture")
    monkeypatch.setattr(resources, "prepare_localization", lambda *a: work / "names")
    monkeypatch.setattr(resources, "prepare_images", lambda *a: work / "images")
    monkeypatch.setattr(builder, "load_config", lambda *a: {"compatibility_manifests": []})
    monkeypatch.setattr(builder, "publication_paths", lambda *a: {"index.html"})
    builds = []
    def build(root, config, site, report, **kwargs):
        builds.append(site)
        site.mkdir()
        (site / "index.html").write_text("fixed")
    monkeypatch.setattr(builder, "build_artifact", build)
    replace = Path.replace
    def interrupted(path, target):
        if path.name == "site" and Path(target) == work / "site":
            raise OSError("interrupted after completed build")
        return replace(path, target)
    record = {"identity": {"root": str(root), "target": "synthetic"}}
    with monkeypatch.context() as fault:
        fault.setattr(Path, "replace", interrupted)
        with pytest.raises(OSError):
            resources.prepare_site(record, work)
    assert (work / "site-complete.json").is_file()
    result = resources.prepare_site(record, work)
    assert (result / "index.html").read_text() == "fixed"
    assert len(builds) == 1
    (result / "index.html").write_text("corrupted")
    with pytest.raises(ValueError, match="no applicable completed build"):
        resources.prepare_site(record, work)
    assert len(builds) == 1


def test_valid_local_name_bundle_does_not_query_remote_cache(tmp_path, monkeypatch):
    local = tmp_path / resources.names.PUBLIC_PREFIX
    local.mkdir(parents=True)
    output = tmp_path / "work"
    output.mkdir()
    calls = []
    monkeypatch.setattr(resources, "complete_localization", lambda *a: True)
    monkeypatch.setattr(resources, "trusted_cache", lambda *a, **k: pytest.fail("Complete local resources must be reused"))
    monkeypatch.setattr(resources, "merge_localization", lambda root, sources, dest: calls.append(sources) or local)
    monkeypatch.setattr(resources.names, "build_bundle", lambda root, dest, **k: dest.mkdir())
    monkeypatch.setattr(resources.names, "verify_bundle", lambda *a: None)
    resources.prepare_localization(tmp_path, output, "synthetic")
    resources.prepare_localization(tmp_path, output, "synthetic")
    assert calls == [[local]]
