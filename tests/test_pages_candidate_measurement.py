from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import build_pages_candidate_measurement as candidate


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _inputs(tmp_path: Path):
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_bytes(b"<h1>site</h1>\n")
    (site / "assets/app.js").write_bytes(b"const ready = true;\n")
    report = tmp_path / "pages-report.json"
    _write_json(
        report,
        {
            "schema_version": "1.0.0",
            "artifact": {"manifest_sha256": "a" * 64},
        },
    )
    localization = tmp_path / "localization-subject.json"
    landing = tmp_path / "landing-subject.json"
    _write_json(localization, {"subject_sha256": "b" * 64})
    _write_json(landing, {"subject_sha256": "c" * 64})
    return site, report, localization, landing


def test_candidate_payload_is_deterministic_and_independently_verifiable(tmp_path: Path):
    site, report, localization, landing = _inputs(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_evidence = candidate.package_candidate(
        ROOT, site, report, localization, landing, first
    )
    second_evidence = candidate.package_candidate(
        ROOT, site, report, localization, landing, second
    )

    assert first_evidence["authority"] == "measurement_only_not_for_publication"
    assert first_evidence["candidate"] == second_evidence["candidate"]
    assert (first / candidate.PAYLOAD_FILE).read_bytes() == (
        second / candidate.PAYLOAD_FILE
    ).read_bytes()
    extracted = tmp_path / "extracted"
    assert candidate.verify_candidate(first, extracted) == first_evidence
    assert (extracted / "index.html").read_bytes() == b"<h1>site</h1>\n"
    assert (extracted / "assets/app.js").read_bytes() == b"const ready = true;\n"


def test_candidate_verifier_rejects_payload_tampering(tmp_path: Path):
    site, report, localization, landing = _inputs(tmp_path)
    output = tmp_path / "candidate"
    candidate.package_candidate(ROOT, site, report, localization, landing, output)
    with (output / candidate.PAYLOAD_FILE).open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(candidate.CandidateMeasurementError, match="digest or size"):
        candidate.verify_candidate(output)


def test_candidate_verifier_rejects_incomplete_source_evidence(tmp_path: Path):
    site, report, localization, landing = _inputs(tmp_path)
    output = tmp_path / "candidate"
    candidate.package_candidate(ROOT, site, report, localization, landing, output)
    evidence_path = output / candidate.EVIDENCE_FILE
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["source"]["checked_out_tree"] = "not-a-tree"
    _write_json(evidence_path, evidence)

    with pytest.raises(candidate.CandidateMeasurementError, match="Git source"):
        candidate.verify_candidate(output)


@pytest.mark.parametrize(
    "path", ["../escape", "/absolute", "folder\\windows", "C:/windows-drive"]
)
def test_candidate_paths_reject_escape_forms(path: str):
    with pytest.raises(candidate.CandidateMeasurementError, match="candidate path"):
        candidate._safe_path(path)


def test_candidate_manifest_rejects_a_symbolic_link(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    try:
        (site / "link.txt").symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable in this environment")

    with pytest.raises(candidate.CandidateMeasurementError, match="symbolic links"):
        candidate.build_file_manifest(site)


def test_candidate_manifest_symlink_rejection_is_portable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    site = tmp_path / "site"
    site.mkdir()
    link = site / "link.txt"
    link.write_text("synthetic link target", encoding="utf-8")
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == link or original(path),
    )

    with pytest.raises(candidate.CandidateMeasurementError, match="symbolic links"):
        candidate.build_file_manifest(site)
