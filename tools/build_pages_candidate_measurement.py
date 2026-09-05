"""Package and verify a deterministic, measurement-only Pages candidate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_FILE = "pages-candidate.tar.gz"
MANIFEST_FILE = "pages-candidate-manifest.json"
EVIDENCE_FILE = "pages-candidate-evidence.json"
MANIFEST_SCHEMA_VERSION = "1.0.0"
EVIDENCE_SCHEMA_VERSION = "1.0.0"
PAGES_WORKFLOW_PATH = ".github/workflows/pages.yml"
TRUST_INPUT_PATHS = (
    ".github/workflows/pages.yml",
    "build_pages_artifact.py",
    "configs/formats.yaml",
    "configs/pages_publication.json",
    "requirements.txt",
    "schemas/landing-card-image-cache.schema.json",
    "src/mtgmeta/card_names.py",
    "src/mtgmeta/catalog.py",
    "src/mtgmeta/config.py",
    "src/mtgmeta/data/om1_spm_aliases.json",
    "tests/fixtures/melee/434455_compatibility_manifest.json",
    "tools/build_landing_card_image_cache.py",
    "tools/build_pages_candidate_measurement.py",
    "tools/build_simple_card_localization.py",
    "tools/select_trusted_pages_artifact.py",
)


class CandidateMeasurementError(ValueError):
    """Indicate that a measurement candidate is incomplete or unsafe."""


def _is_hex_digest(value: object, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(
        rf"[0-9a-f]{{{length}}}", value
    ) is not None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateMeasurementError(f"cannot read {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateMeasurementError(f"{label} is not an object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_path(value: str) -> PurePosixPath:
    if "\\" in value:
        raise CandidateMeasurementError(f"candidate path uses a backslash: {value!r}")
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:", value)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise CandidateMeasurementError(f"unsafe candidate path: {value!r}")
    return path


def build_file_manifest(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if site.is_symlink() or not site.is_dir():
        raise CandidateMeasurementError("Pages candidate site is not a directory")
    files = []
    for path in sorted(site.rglob("*")):
        if path.is_symlink():
            raise CandidateMeasurementError(f"symbolic links are prohibited: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(site).as_posix()
        _safe_path(relative)
        files.append(
            {
                "path": relative,
                "object_type": "regular_file",
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    if not files:
        raise CandidateMeasurementError("Pages candidate site is empty")
    return {"schema_version": MANIFEST_SCHEMA_VERSION, "files": files}


def write_deterministic_payload(site: Path, manifest: dict[str, Any], output: Path) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for record in manifest["files"]:
                    source = site / Path(*PurePosixPath(record["path"]).parts)
                    info = tarfile.TarInfo(record["path"])
                    info.size = record["bytes"]
                    info.mode = 0o644
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    with source.open("rb") as handle:
                        archive.addfile(info, handle)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise CandidateMeasurementError(f"git {' '.join(args)} failed")
    return result.stdout.strip()


def collect_source_evidence(root: Path) -> dict[str, Any]:
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    parents = _git(root, "show", "-s", "--format=%P", "HEAD").split()
    if (
        not _is_hex_digest(commit, 40)
        or not _is_hex_digest(tree, 40)
        or any(not _is_hex_digest(parent, 40) for parent in parents)
    ):
        raise CandidateMeasurementError("Git source identity is malformed")
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha and github_sha != commit:
        raise CandidateMeasurementError("GITHUB_SHA does not match the checked-out commit")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "local_measurement")
    pr_number = None
    pr_head = None
    observed_base = None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_name == "pull_request":
        if not event_path:
            raise CandidateMeasurementError("pull_request evidence lacks GITHUB_EVENT_PATH")
        event = _read_json(Path(event_path), "GitHub event")
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise CandidateMeasurementError("GitHub event lacks pull_request evidence")
        head = pull_request.get("head")
        base = pull_request.get("base")
        pr_number = pull_request.get("number")
        pr_head = head.get("sha") if isinstance(head, dict) else None
        observed_base = base.get("sha") if isinstance(base, dict) else None
        if (
            not isinstance(pr_number, int)
            or isinstance(pr_number, bool)
            or not _is_hex_digest(pr_head, 40)
            or not _is_hex_digest(observed_base, 40)
        ):
            raise CandidateMeasurementError("pull_request identity is incomplete")
        if parents != [observed_base, pr_head]:
            raise CandidateMeasurementError(
                "checked-out pull_request merge parents do not match base and head"
            )
        repository = os.environ.get("GITHUB_REPOSITORY")
        workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF")
        workflow_sha = os.environ.get("GITHUB_WORKFLOW_SHA")
        run_id = os.environ.get("GITHUB_RUN_ID")
        run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
        if (
            not repository
            or not workflow_ref
            or not workflow_ref.startswith(
                f"{repository}/{PAGES_WORKFLOW_PATH}@"
            )
            or not workflow_sha
            or not _is_hex_digest(workflow_sha, 40)
            or not run_id
            or not run_id.isdigit()
            or not run_attempt
            or not run_attempt.isdigit()
        ):
            raise CandidateMeasurementError("pull_request workflow identity is incomplete")
    return {
        "repository": os.environ.get("GITHUB_REPOSITORY", "local"),
        "event": event_name,
        "pr_number": pr_number,
        "checked_out_commit": commit,
        "checked_out_tree": tree,
        "checked_out_parents": parents,
        "pr_head": pr_head,
        "observed_base": observed_base,
        "workflow": os.environ.get("GITHUB_WORKFLOW"),
        "workflow_path": PAGES_WORKFLOW_PATH if event_name == "pull_request" else None,
        "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
        "workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }


def _trust_inputs(root: Path) -> list[dict[str, Any]]:
    records = []
    for relative in TRUST_INPUT_PATHS:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise CandidateMeasurementError(f"candidate trust input is missing: {relative}")
        records.append({"path": relative, "sha256": _sha256_file(path)})
    return records


def package_candidate(
    root: Path,
    site: Path,
    pages_report: Path,
    localization_subject: Path,
    landing_subject: Path,
    output: Path,
) -> dict[str, Any]:
    root = root.resolve()
    site = site.resolve()
    output = output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise CandidateMeasurementError("candidate output must be outside the repository")
    try:
        site.relative_to(root)
    except ValueError:
        pass
    else:
        raise CandidateMeasurementError("candidate site must be outside the repository")
    if output.exists():
        raise CandidateMeasurementError(f"candidate output already exists: {output}")
    report = _read_json(pages_report, "Pages report")
    localization = _read_json(localization_subject, "localization subject")
    landing = _read_json(landing_subject, "Landing cache subject")
    report_digest = report.get("artifact", {}).get("manifest_sha256")
    localization_digest = localization.get("subject_sha256")
    landing_digest = landing.get("subject_sha256")
    if any(
        not _is_hex_digest(value, 64)
        for value in (report_digest, localization_digest, landing_digest)
    ):
        raise CandidateMeasurementError("candidate source digest evidence is incomplete")
    manifest = build_file_manifest(site)
    output.mkdir(parents=True)
    manifest_path = output / MANIFEST_FILE
    payload_path = output / PAYLOAD_FILE
    _write_json(manifest_path, manifest)
    write_deterministic_payload(site, manifest, payload_path)
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "authority": "measurement_only_not_for_publication",
        "source": collect_source_evidence(root),
        "candidate": {
            "payload": PAYLOAD_FILE,
            "payload_bytes": payload_path.stat().st_size,
            "payload_sha256": _sha256_file(payload_path),
            "manifest": MANIFEST_FILE,
            "manifest_sha256": _sha256_file(manifest_path),
            "site_files": len(manifest["files"]),
            "site_bytes": sum(record["bytes"] for record in manifest["files"]),
        },
        "publication_selection": {
            "pages_report_schema_version": report.get("schema_version"),
            "artifact_manifest_sha256": report_digest,
            "compatibility_verified": True,
        },
        "localization_subject_sha256": localization_digest,
        "landing_cache_subject_sha256": landing_digest,
        "runtime": {
            "python": sys.version.split()[0],
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "runner_environment": os.environ.get("RUNNER_ENVIRONMENT"),
            "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
        },
        "trust_inputs": _trust_inputs(root),
    }
    evidence["trust_inputs_sha256"] = _canonical_sha256(evidence["trust_inputs"])
    _write_json(output / EVIDENCE_FILE, evidence)
    verify_candidate(output)
    return evidence


def _manifest_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if set(manifest) != {"schema_version", "files"}:
        raise CandidateMeasurementError("candidate manifest has unsupported fields")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CandidateMeasurementError("candidate manifest schema is incompatible")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise CandidateMeasurementError("candidate manifest files are missing")
    paths: set[str] = set()
    for record in files:
        if not isinstance(record, dict) or set(record) != {
            "path",
            "object_type",
            "bytes",
            "sha256",
        }:
            raise CandidateMeasurementError("candidate manifest record is malformed")
        path = record["path"]
        if not isinstance(path, str):
            raise CandidateMeasurementError("candidate manifest path is not a string")
        _safe_path(path)
        if path in paths:
            raise CandidateMeasurementError(f"duplicate candidate path: {path}")
        paths.add(path)
        if (
            record["object_type"] != "regular_file"
            or not isinstance(record["bytes"], int)
            or record["bytes"] < 0
            or not isinstance(record["sha256"], str)
            or not _is_hex_digest(record["sha256"], 64)
        ):
            raise CandidateMeasurementError(f"candidate manifest metadata is invalid: {path}")
    return files


def _verify_source_evidence(source: object) -> None:
    expected_keys = {
        "repository",
        "event",
        "pr_number",
        "checked_out_commit",
        "checked_out_tree",
        "checked_out_parents",
        "pr_head",
        "observed_base",
        "workflow",
        "workflow_path",
        "workflow_ref",
        "workflow_sha",
        "run_id",
        "run_attempt",
    }
    if not isinstance(source, dict) or set(source) != expected_keys:
        raise CandidateMeasurementError("candidate source evidence is malformed")
    parents = source["checked_out_parents"]
    if (
        not isinstance(source["repository"], str)
        or not source["repository"]
        or not _is_hex_digest(source["checked_out_commit"], 40)
        or not _is_hex_digest(source["checked_out_tree"], 40)
        or not isinstance(parents, list)
        or any(not _is_hex_digest(parent, 40) for parent in parents)
    ):
        raise CandidateMeasurementError("candidate Git source evidence is invalid")
    if source["event"] == "local_measurement":
        return
    if source["event"] != "pull_request":
        raise CandidateMeasurementError("candidate event evidence is invalid")
    repository = source["repository"]
    workflow_ref = source["workflow_ref"]
    if (
        not isinstance(source["pr_number"], int)
        or isinstance(source["pr_number"], bool)
        or source["pr_number"] < 1
        or not _is_hex_digest(source["pr_head"], 40)
        or not _is_hex_digest(source["observed_base"], 40)
        or parents != [source["observed_base"], source["pr_head"]]
        or not isinstance(source["workflow"], str)
        or not source["workflow"]
        or source["workflow_path"] != PAGES_WORKFLOW_PATH
        or not isinstance(workflow_ref, str)
        or not workflow_ref.startswith(f"{repository}/{PAGES_WORKFLOW_PATH}@")
        or not _is_hex_digest(source["workflow_sha"], 40)
        or not isinstance(source["run_id"], str)
        or not source["run_id"].isdigit()
        or int(source["run_id"]) < 1
        or not isinstance(source["run_attempt"], str)
        or not source["run_attempt"].isdigit()
        or int(source["run_attempt"]) < 1
    ):
        raise CandidateMeasurementError("candidate pull-request evidence is invalid")


def verify_candidate(input_directory: Path, extract: Path | None = None) -> dict[str, Any]:
    input_directory = input_directory.resolve()
    manifest_path = input_directory / MANIFEST_FILE
    payload_path = input_directory / PAYLOAD_FILE
    evidence_path = input_directory / EVIDENCE_FILE
    manifest = _read_json(manifest_path, "candidate manifest")
    records = _manifest_records(manifest)
    evidence = _read_json(evidence_path, "candidate evidence")
    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise CandidateMeasurementError("candidate evidence schema is incompatible")
    if evidence.get("authority") != "measurement_only_not_for_publication":
        raise CandidateMeasurementError("candidate evidence authority is invalid")
    _verify_source_evidence(evidence.get("source"))
    actual_control_files = {path.name for path in input_directory.iterdir()}
    if actual_control_files != {PAYLOAD_FILE, MANIFEST_FILE, EVIDENCE_FILE}:
        raise CandidateMeasurementError("candidate measurement contains undeclared files")
    trust_inputs = evidence.get("trust_inputs")
    if (
        not isinstance(trust_inputs, list)
        or evidence.get("trust_inputs_sha256") != _canonical_sha256(trust_inputs)
        or any(
            not isinstance(record, dict)
            or set(record) != {"path", "sha256"}
            or record.get("path") not in TRUST_INPUT_PATHS
            or not _is_hex_digest(record.get("sha256"), 64)
            for record in trust_inputs
        )
        or [record["path"] for record in trust_inputs] != list(TRUST_INPUT_PATHS)
    ):
        raise CandidateMeasurementError("candidate trust-input evidence is invalid")
    publication = evidence.get("publication_selection")
    if (
        not isinstance(publication, dict)
        or publication.get("compatibility_verified") is not True
        or not _is_hex_digest(publication.get("artifact_manifest_sha256"), 64)
        or any(
            not _is_hex_digest(evidence.get(key), 64)
            for key in (
                "localization_subject_sha256",
                "landing_cache_subject_sha256",
            )
        )
    ):
        raise CandidateMeasurementError("candidate publication evidence is invalid")
    candidate = evidence.get("candidate")
    if not isinstance(candidate, dict):
        raise CandidateMeasurementError("candidate evidence payload is missing")
    if (
        candidate.get("payload") != PAYLOAD_FILE
        or candidate.get("manifest") != MANIFEST_FILE
        or candidate.get("payload_bytes") != payload_path.stat().st_size
        or candidate.get("payload_sha256") != _sha256_file(payload_path)
        or candidate.get("manifest_sha256") != _sha256_file(manifest_path)
        or candidate.get("site_files") != len(records)
        or candidate.get("site_bytes") != sum(record["bytes"] for record in records)
    ):
        raise CandidateMeasurementError("candidate evidence digest or size mismatch")
    destination = extract.resolve() if extract else None
    if destination:
        if destination.exists():
            raise CandidateMeasurementError(f"candidate extraction path exists: {destination}")
        destination.mkdir(parents=True)
    seen: set[str] = set()
    expected = {record["path"]: record for record in records}
    try:
        with tarfile.open(payload_path, mode="r:gz") as archive:
            for member in archive:
                path = member.name
                _safe_path(path)
                if path in seen:
                    raise CandidateMeasurementError(f"duplicate payload path: {path}")
                seen.add(path)
                record = expected.get(path)
                if record is None or not member.isfile():
                    raise CandidateMeasurementError(f"undeclared payload member: {path}")
                handle = archive.extractfile(member)
                if handle is None:
                    raise CandidateMeasurementError(f"cannot read payload member: {path}")
                payload = handle.read()
                if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    raise CandidateMeasurementError(f"payload member digest mismatch: {path}")
                if destination:
                    target = destination / Path(*PurePosixPath(path).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
        if seen != set(expected):
            missing = sorted(set(expected) - seen)
            raise CandidateMeasurementError(
                "payload is missing declared files: " + ", ".join(missing)
            )
    except Exception:
        if destination:
            shutil.rmtree(destination, ignore_errors=True)
        raise
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("--root", type=Path, default=ROOT)
    package_parser.add_argument("--site", type=Path, required=True)
    package_parser.add_argument("--pages-report", type=Path, required=True)
    package_parser.add_argument("--localization-subject", type=Path, required=True)
    package_parser.add_argument("--landing-subject", type=Path, required=True)
    package_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--input", type=Path, required=True)
    verify_parser.add_argument("--extract", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            evidence = package_candidate(
                args.root,
                args.site,
                args.pages_report,
                args.localization_subject,
                args.landing_subject,
                args.output,
            )
        else:
            evidence = verify_candidate(args.input, args.extract)
    except (CandidateMeasurementError, OSError, tarfile.TarError) as exc:
        parser.error(str(exc))
    candidate = evidence["candidate"]
    print(
        "Pages candidate measurement: "
        f"files={candidate['site_files']} bytes={candidate['site_bytes']} "
        f"payload_bytes={candidate['payload_bytes']} "
        f"payload_sha256={candidate['payload_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
