"""P10-07 allowlisted Pages artifact contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import build_pages_artifact as pages


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pages_publication.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _minimal_repository(root: Path) -> Path:
    files = {
        "index.html": b"<html>site</html>\n",
        "fetched.txt": b"2026-08-01\n",
        "assets/app.js": b"console.log('site');\n",
        "data/exact.json": b'{"schema_version":"1.0.0"}\n',
        "data_raw/melee/1/snapshot/response.json": b'{"public":true}\n',
        "melee/index.html": b"<html>tabletop</html>\n",
        "reports/report.json": b"{}\n",
        "stats/catalog.json": b'{"schema_version":"1.0.0"}\n',
        "stats/event.json": b'{"schema_version":"1.0.0"}\n',
    }
    for relative, data in files.items():
        _write(root / relative, data)
    raw_manifest = {
        "responses": [
            {
                "path": "response.json",
                "bytes": len(files["data_raw/melee/1/snapshot/response.json"]),
                "sha256": _sha256(files["data_raw/melee/1/snapshot/response.json"]),
            }
        ]
    }
    raw_manifest_bytes = (json.dumps(raw_manifest) + "\n").encode()
    _write(root / "data_raw/melee/1/snapshot/manifest.json", raw_manifest_bytes)
    compatibility = {
        "immutable_snapshot": {
            "manifest": {
                "path": "data_raw/melee/1/snapshot/manifest.json",
                "bytes": len(raw_manifest_bytes),
                "sha256": _sha256(raw_manifest_bytes),
            },
            "response_count": 1,
        },
        "exact_files": [
            {
                "path": "data/exact.json",
                "bytes": len(files["data/exact.json"]),
                "sha256": _sha256(files["data/exact.json"]),
            },
            {
                "path": "stats/event.json",
                "bytes": len(files["stats/event.json"]),
                "sha256": _sha256(files["stats/event.json"]),
            },
        ],
        "catalog_projections": [{"path": "stats/catalog.json"}],
    }
    compatibility_path = root / "tests/compatibility.json"
    _write(compatibility_path, (json.dumps(compatibility) + "\n").encode())
    config = {
        "schema_version": "1.0.0",
        "site_files": ["index.html", "fetched.txt"],
        "site_directories": [
            "assets",
            "data",
            "data_raw",
            "melee",
            "reports",
            "stats",
        ],
        "compatibility_manifests": ["tests/compatibility.json"],
        "maximum_artifact_bytes": 100000,
    }
    config_path = root / "configs/pages_publication.json"
    _write(config_path, (json.dumps(config) + "\n").encode())
    _write(root / "unlisted-sentinel.txt", b"must not publish\n")
    _write(root / "src/private.py", b"SECRET = False\n")
    return config_path


def test_real_publication_plan_preserves_products_and_434455_bytes() -> None:
    config = pages.load_config(ROOT, CONFIG)
    selected = pages.publication_paths(ROOT, config)
    protected = pages.validate_compatibility(ROOT, config, selected)
    assert {
        "index.html",
        "melee/index.html",
        "assets/js/phase8/app-core.js",
        "assets/js/phase8/app-mtgo.js",
        "assets/js/phase8/app-tabletop.js",
        "assets/js/phase8/app.js",
        "stats/catalog.json",
        "data/modern/melee/events/434455.json",
        "data_raw/melee/434455/20260724T092458Z-01/manifest.json",
        "reports/standard/mtgo/classification_conflicts.json",
    } <= selected
    assert len(protected) == 494
    assert "build_pages_artifact.py" not in selected
    assert "docs/STATUS.yaml" not in selected
    assert "tests/test_pages_artifact.py" not in selected
    assert ".github/workflows/pages.yml" not in selected


def test_fresh_artifact_excludes_unlisted_paths_and_reports_sizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    config_path = _minimal_repository(root)
    tracked = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    monkeypatch.setattr(pages, "_tracked_files", lambda unused_root: tracked)
    monkeypatch.setattr(pages, "_git_storage_bytes", lambda unused_root: 4096)
    output = tmp_path / "site"
    report_path = tmp_path / "report.json"
    report = pages.build_artifact(root, config_path, output, report_path)
    assert (output / "index.html").read_bytes() == b"<html>site</html>\n"
    assert (output / ".nojekyll").read_bytes() == b""
    assert not (output / "unlisted-sentinel.txt").exists()
    assert not (output / "src/private.py").exists()
    assert report["artifact"]["files"] == 11
    assert report["boundary"]["protected_files"] == 5
    assert report["boundary"]["excluded_tracked_files"] == 4
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_protected_byte_change_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    config_path = _minimal_repository(root)
    (root / "data/exact.json").write_text("{}\n", encoding="utf-8")
    config = pages.load_config(root, config_path)
    selected = pages.publication_paths(root, config)
    with pytest.raises(pages.PublicationError, match="protected byte count changed"):
        pages.validate_compatibility(root, config, selected)


def test_output_must_be_new_and_outside_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    config_path = _minimal_repository(root)
    monkeypatch.setattr(pages, "_tracked_files", lambda unused_root: [])
    monkeypatch.setattr(pages, "_git_storage_bytes", lambda unused_root: 0)
    with pytest.raises(pages.PublicationError, match="outside the repository"):
        pages.build_artifact(
            root, config_path, root / "site", tmp_path / "inside-report.json"
        )
    with pytest.raises(pages.PublicationError, match="report must be outside"):
        pages.build_artifact(
            root, config_path, tmp_path / "site", root / "report.json"
        )
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(pages.PublicationError, match="already exists"):
        pages.build_artifact(root, config_path, output, tmp_path / "report.json")
