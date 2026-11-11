"""Build a fail-closed GitHub Pages artifact from approved repository paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from fnmatch import fnmatchcase
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from tools.delivery.packages import MAX_BYTES, VERSION_MARKER_BYTES
from mtgmeta.catalog import build_catalog
from mtgmeta.config import load_format_registry
from tools.build_landing_card_image_cache import verify_cache_bundle
from tools.build_simple_card_localization import verify_bundle as verify_localization_bundle


CONFIG_KEYS = {
    "schema_version",
    "site_files",
    "site_directories",
    "excluded_patterns",
    "generated_overlays",
    "maximum_artifact_bytes",
}
DATA_TREE_DIRECTORIES = ("data", "data_raw", "reports", "stats")


class PublicationError(ValueError):
    """Indicate that the Pages artifact cannot be built safely."""


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PublicationError(f"{label} must be a non-empty forward-slash path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise PublicationError(f"unsafe {label}: {value!r}")
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"{label} must contain a JSON object: {path}")
    return value


def load_config(root: Path, config_path: Path) -> dict[str, Any]:
    config = _read_json(config_path, "publication config")
    if set(config) != CONFIG_KEYS:
        raise PublicationError(
            "publication config keys must be exactly " + ", ".join(sorted(CONFIG_KEYS))
        )
    if config["schema_version"] != "1.4.0":
        raise PublicationError("unsupported publication config schema_version")
    for key in (
        "site_files",
        "site_directories",
        "excluded_patterns",
    ):
        values = config[key]
        if not isinstance(values, list) or not values:
            raise PublicationError(f"{key} must be a non-empty list")
        normalized = [_safe_relative(value, key) for value in values]
        if len(normalized) != len(set(normalized)):
            raise PublicationError(f"{key} contains duplicate paths")
        config[key] = normalized
    overlays = config["generated_overlays"]
    if not isinstance(overlays, list) or not overlays:
        raise PublicationError("generated_overlays must be a non-empty list")
    overlay_ids: set[str] = set()
    prefixes: set[str] = set()
    for overlay in overlays:
        if not isinstance(overlay, dict) or set(overlay) != {
            "id",
            "manifest",
            "maximum_bytes",
            "public_prefix",
        }:
            raise PublicationError("generated overlay keys are invalid")
        overlay_id = overlay["id"]
        if not isinstance(overlay_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", overlay_id):
            raise PublicationError(f"invalid generated overlay id: {overlay_id!r}")
        if overlay_id in overlay_ids:
            raise PublicationError(f"duplicate generated overlay id: {overlay_id}")
        overlay_ids.add(overlay_id)
        prefix = _safe_relative(overlay["public_prefix"], "generated overlay prefix")
        if prefix in prefixes:
            raise PublicationError(f"duplicate generated overlay prefix: {prefix}")
        prefixes.add(prefix)
        overlay["public_prefix"] = prefix
        overlay["manifest"] = _safe_relative(
            overlay["manifest"], "generated overlay manifest"
        )
        maximum_overlay = overlay["maximum_bytes"]
        if (
            not isinstance(maximum_overlay, int)
            or isinstance(maximum_overlay, bool)
            or maximum_overlay <= 0
        ):
            raise PublicationError("generated overlay maximum_bytes must be positive")
    maximum = config["maximum_artifact_bytes"]
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        raise PublicationError("maximum_artifact_bytes must be a positive integer")
    try:
        config_path.resolve().relative_to(root)
    except ValueError as exc:
        raise PublicationError("publication config must be inside the repository") from exc
    if maximum > MAX_BYTES:
        raise PublicationError(f"maximum_artifact_bytes cannot exceed package limit {MAX_BYTES}")
    if any(Path(p).parts[0] in {"data", "data_raw", "reports", "fetched.txt"}
           for p in config["site_files"] + config["site_directories"]):
        raise PublicationError("retained sources and maintenance files cannot be published")
    return config


def _source_file(root: Path, relative: str) -> Path:
    relative = _safe_relative(relative, "source path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise PublicationError(f"approved path is not a regular file: {relative}")
    return path


def publication_paths(root: Path, config: dict[str, Any]) -> set[str]:
    # Catalog visibility and direct-file publication are the same admission.
    try:
        registry = load_format_registry(root / "configs/formats.yaml")
        expected = build_catalog(root)
    except ValueError as exc:
        raise PublicationError(str(exc)) from exc
    catalog = _read_json(root / "stats/catalog.json", "consumer catalog")
    if catalog.get("formats") != expected["formats"]:
        raise PublicationError("consumer catalog does not match current format admission")
    public_formats = {item.id for item in registry.formats if item.public}

    def admitted(relative: str) -> bool:
        parts = Path(relative).parts
        if parts[0] in {"stats", "reports"} and relative != "stats/catalog.json":
            if len(parts) < 3 or parts[1] not in public_formats:
                return False
        return not any(fnmatchcase(relative, pattern) for pattern in config["excluded_patterns"])

    selected: set[str] = set()
    for relative in config["site_files"]:
        _source_file(root, relative)
        if admitted(relative):
            selected.add(relative)
    for relative in config["site_directories"]:
        directory = root / relative
        if directory.is_symlink() or not directory.is_dir():
            raise PublicationError(f"approved path is not a directory: {relative}")
        found = False
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise PublicationError(
                    f"symbolic links are prohibited: {path.relative_to(root).as_posix()}"
                )
            if path.is_file():
                found = True
                candidate = path.relative_to(root).as_posix()
                if admitted(candidate):
                    selected.add(candidate)
        if not found:
            raise PublicationError(f"approved directory is empty: {relative}")
    if ".nojekyll" in selected:
        raise PublicationError(".nojekyll is generated and must not be a source path")
    return selected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publication_inputs(root: Path, selected: set[str]) -> set[str]:
    """Keep validation/composition inputs even when they are not served by Pages."""
    from mtgmeta.classifier_closure import _protected_input_fingerprints
    paths = selected | {"configs/pages_publication.json"}
    formats = {Path(p).parts[1] for p in selected if p.startswith("stats/") and len(Path(p).parts) > 2}
    for format_id in sorted(formats):
        paths.update(_protected_input_fingerprints(root, format_id))
        meta = root / f"stats/{format_id}/mtgo/meta.json"
        if meta.is_file():
            # These include diagnostic reports bound by the existing product,
            # which remain repository inputs rather than browser resources.
            paths.update(_read_json(meta, "MTGO metadata").get("publication", {}).get("artifacts", {}))
        catalog = root / f"stats/{format_id}/melee/index.json"
        if catalog.is_file():
            for event in _read_json(catalog, "Melee catalog")["events"]:
                for kind in ("classifications", "opportunities"):
                    paths.add(f"data/{format_id}/melee/{kind}/{event['event_id']}.json")
    return {_safe_relative(path, "publication input") for path in paths}


def validate_public_consumers(root: Path, selected: set[str]) -> None:
    """Check the actual catalog/index references, not all provenance paths."""
    def require(relative):
        relative = _safe_relative(relative, "consumer path")
        if relative not in selected:
            raise PublicationError(f"consumer file is absent from artifact: {relative}")
        return _read_json(_source_file(root, relative), "consumer document")

    catalog = require("stats/catalog.json")
    for format_ in catalog["formats"]:
        for product in format_["products"]:
            if product["available"]:
                require(product["path"])
    # Only these fields are fetched by supported browser consumers. In
    # particular, meta.publication.artifacts is a build binding, not a URL list.
    for relative in sorted(selected):
        path = Path(relative)
        if not relative.startswith("stats/") or path.suffix != ".json":
            continue
        if path.name not in {"index.json", "matchup_index.json", "meta.json", "current.json"}:
            continue
        document = _read_json(root / relative, "public index")
        base = path.parent
        if len(path.parts) >= 4 and path.parts[2] == "mtgo":
            for key in ("statistics_catalog", "matchup_catalog", "hierarchy_catalog", "top8_catalog",
                        "completeness_catalog", "pickup_catalog", "landing_document", "landing_feature_catalog"):
                if document.get(key):
                    require((base / _safe_relative(document[key], "MTGO catalog reference")).as_posix())
            for collection in ("ranges", "weeks"):
                for entry in document.get(collection, []):
                    for key in ("file", "decks_file", "comparison_bases_file"):
                        if entry.get(key):
                            require((base / _safe_relative(entry[key], "MTGO index reference")).as_posix())
            for child in document.get("data_files", {}).values():
                require((base / _safe_relative(child, "Landing reference")).as_posix())
        elif len(path.parts) >= 4 and path.parts[2] == "melee" and path.name == "index.json":
            for entry in document["events"]:
                for key in ("meta", "overview", "decks", "matchup", "quality"):
                    require((base / _safe_relative(entry[key], "Melee consumer reference")).as_posix())


def validate_publication(root: Path, config: dict[str, Any], selected: set[str]) -> None:
    from mtgmeta.classifier_closure import validate_current_melee
    from mtgmeta.mtgo.publication import inspect_publication
    validate_public_consumers(root, selected)
    try:
        for relative in sorted(selected):
            parts = Path(relative).parts
            if len(parts) == 4 and parts[0] == "stats":
                if parts[2:] == ("melee", "index.json"):
                    validate_current_melee(root, parts[1])
                elif parts[2:] == ("mtgo", "meta.json"):
                    problems = inspect_publication(root, parts[1])
                    if problems:
                        raise PublicationError(f"MTGO product binding is incomplete: {parts[1]}: {problems}")
    except (ValueError, RuntimeError) as exc:
        raise PublicationError(f"current product/source validation failed: {exc}") from exc


def _tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return sorted(item for item in result.stdout.decode("utf-8").split("\0")
                      if item and (root / item).is_file())
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        raise PublicationError(f"cannot measure tracked repository files: {exc}") from exc


def _git_storage_bytes(root: Path) -> int:
    try:
        result = subprocess.run(
            ["git", "count-objects", "-v"],
            cwd=root,
            check=True,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        values = dict(line.split(": ", 1) for line in result.stdout.splitlines())
        return (int(values["size"]) + int(values["size-pack"])) * 1024
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
        raise PublicationError(f"cannot measure Git object storage: {exc}") from exc


def _tree_bytes(root: Path, paths: set[str]) -> int:
    return sum((root / relative).stat().st_size for relative in paths)


def _manifest_digest(root: Path, paths: set[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(root / relative).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _require_outside(path: Path, base: Path, message: str) -> None:
    try:
        path.relative_to(base)
    except ValueError:
        return
    raise PublicationError(message)


def measure_artifact(root: Path, config: dict[str, Any], *, selected=None, overlays=None, maximum_bytes=None) -> dict[str, Any]:
    """Check the byte budget before copying or freezing a candidate.

    Without resource overlays this is explicitly a lower bound. The builder
    still verifies resource provenance, collisions and the final copied bytes.
    """
    selected = publication_paths(root, config) if selected is None else selected
    source_bytes = _tree_bytes(root, selected)
    overlay_bytes = {}
    configured = {item["id"]: item for item in config["generated_overlays"]}
    if set(overlays or {}) - set(configured):
        raise PublicationError("Unknown generated overlay")
    for identifier, directory in (overlays or {}).items():
        directory = Path(directory)
        if directory.is_symlink() or not directory.is_dir():
            raise PublicationError(f"generated overlay is not a directory: {identifier}")
        paths = list(directory.rglob("*"))
        if any(path.is_symlink() for path in paths):
            raise PublicationError(f"symbolic links are prohibited in overlay: {identifier}")
        size = sum(path.stat().st_size for path in paths if path.is_file())
        if size > configured[identifier]["maximum_bytes"]:
            raise PublicationError(f"generated overlay exceeds maximum_bytes: {identifier}")
        overlay_bytes[identifier] = size
    total = source_bytes + sum(overlay_bytes.values())
    maximum = min(config["maximum_artifact_bytes"], MAX_BYTES,
                  maximum_bytes if maximum_bytes is not None else MAX_BYTES)
    if total + VERSION_MARKER_BYTES > maximum:
        raise PublicationError(f"artifact would exceed maximum_artifact_bytes: {total}")
    return {"source_bytes": source_bytes, "overlay_bytes": overlay_bytes, "bytes": total,
            "packaged_bytes": total + VERSION_MARKER_BYTES, "maximum_bytes": maximum,
            "complete": set(overlay_bytes) == set(configured)}


def _copy_generated_overlays(
    root: Path,
    output: Path,
    config: dict[str, Any],
    overlays: dict[str, Path],
    occupied: set[str],
) -> set[str]:
    configured = {record["id"]: record for record in config["generated_overlays"]}
    if set(overlays) != set(configured):
        raise PublicationError(
            "generated overlays must match configured ids: "
            + ", ".join(sorted(configured))
        )
    copied: set[str] = set()
    for overlay_id, record in configured.items():
        source_root = overlays[overlay_id].resolve()
        _require_outside(
            source_root,
            root,
            f"generated overlay must be outside the repository: {overlay_id}",
        )
        if source_root.is_symlink() or not source_root.is_dir():
            raise PublicationError(f"generated overlay is not a directory: {overlay_id}")
        manifest = source_root / record["manifest"]
        if manifest.is_symlink() or not manifest.is_file():
            raise PublicationError(f"generated overlay manifest is missing: {overlay_id}")
        try:
            if overlay_id == "landing_card_images":
                verify_cache_bundle(root, source_root)
            elif overlay_id == "card_localization":
                verify_localization_bundle(root, source_root)
            else:
                raise PublicationError(f"unsupported generated overlay: {overlay_id}")
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PublicationError(f"generated overlay verification failed: {exc}") from exc

        source_files: list[Path] = []
        for path in source_root.rglob("*"):
            if path.is_symlink():
                raise PublicationError(f"symbolic links are prohibited in overlay: {path}")
            if path.is_file():
                source_files.append(path)
        overlay_bytes = sum(path.stat().st_size for path in source_files)
        if overlay_bytes > record["maximum_bytes"]:
            raise PublicationError(
                f"generated overlay exceeds maximum_bytes: {overlay_id}"
            )
        for source in sorted(source_files):
            child = source.relative_to(source_root).as_posix()
            relative = f"{record['public_prefix']}/{child}"
            _safe_relative(relative, "generated artifact path")
            if relative in occupied or relative in copied:
                raise PublicationError(f"generated overlay path collision: {relative}")
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if _sha256(source) != _sha256(destination):
                raise PublicationError(f"generated overlay byte mismatch: {relative}")
            copied.add(relative)
    return copied


def build_artifact(
    root: Path,
    config_path: Path,
    output: Path,
    report_path: Path,
    *,
    overlays: dict[str, Path] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    report_path = report_path.resolve()
    _require_outside(output, root, "artifact output must be outside the repository")
    _require_outside(report_path, root, "artifact report must be outside the repository")
    _require_outside(report_path, output, "artifact report must be outside the artifact")
    if output.exists():
        raise PublicationError(f"artifact output already exists: {output}")

    config = load_config(root, config_path.resolve())
    selected = publication_paths(root, config)
    from tools.build_archetype_visuals import require_public_representatives
    try:
        require_public_representatives(root, selected)
    except (OSError, ValueError) as exc:
        raise PublicationError(str(exc)) from exc
    inputs = publication_inputs(root, selected)
    before = _manifest_digest(root, inputs)
    validate_publication(root, config, selected)
    measure_artifact(root, config, selected=selected, overlays=overlays)

    output.mkdir(parents=True)
    for relative in sorted(selected):
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)
    (output / ".nojekyll").write_bytes(b"")

    generated = _copy_generated_overlays(
        root, output, config, overlays or {}, selected | {".nojekyll"}
    )
    artifact_paths = selected | generated | {".nojekyll"}
    artifact_bytes = _tree_bytes(output, artifact_paths)
    if artifact_bytes + VERSION_MARKER_BYTES > config["maximum_artifact_bytes"]:
        raise PublicationError(
            f"artifact would exceed maximum_artifact_bytes: {artifact_bytes}"
        )
    for relative in selected:
        if _sha256(root / relative) != _sha256(output / relative):
            raise PublicationError(f"copied artifact byte mismatch: {relative}")

    if publication_inputs(root, selected) != inputs or _manifest_digest(root, inputs) != before:
        raise PublicationError("publication inputs changed while building the artifact")
    tracked = _tracked_files(root)
    tracked_set = set(tracked)
    data_paths = {
        path
        for path in tracked
        if any(path == directory or path.startswith(f"{directory}/") for directory in DATA_TREE_DIRECTORIES)
    }
    report = {
        "schema_version": "1.0.0",
        "repository": {
            "tracked_files": len(tracked),
            "tracked_bytes": _tree_bytes(root, tracked_set),
            "git_object_bytes": _git_storage_bytes(root),
        },
        "data_tree": {
            "files": len(data_paths),
            "bytes": _tree_bytes(root, data_paths),
        },
        "artifact": {
            "files": len(artifact_paths),
            "bytes": artifact_bytes,
            "maximum_bytes": config["maximum_artifact_bytes"],
            "packaged_bytes": artifact_bytes + VERSION_MARKER_BYTES,
            "remaining_bytes": config["maximum_artifact_bytes"] - artifact_bytes - VERSION_MARKER_BYTES,
            "manifest_sha256": _manifest_digest(output, artifact_paths),
        },
        "boundary": {
            "verified_input_files": len(inputs - selected),
            "excluded_tracked_files": len(tracked_set - selected),
            "excluded_tracked_bytes": _tree_bytes(root, tracked_set - selected),
        },
        "generated_overlays": {
            "files": len(generated),
            "bytes": _tree_bytes(output, generated),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def append_summary(path: Path, report: dict[str, Any]) -> None:
    artifact = report["artifact"]
    repository = report["repository"]
    data_tree = report["data_tree"]
    boundary = report["boundary"]
    lines = [
        "## Allowlisted Pages artifact",
        "",
        f"- Repository tracked tree: {repository['tracked_files']} files, {repository['tracked_bytes']} bytes",
        f"- Git object storage: {repository['git_object_bytes']} bytes",
        f"- Data tree: {data_tree['files']} files, {data_tree['bytes']} bytes",
        f"- Pages artifact: {artifact['files']} files, {artifact['bytes']} bytes",
        f"- Generated overlays: {report['generated_overlays']['files']} files, {report['generated_overlays']['bytes']} bytes",
        f"- Artifact manifest SHA-256: `{artifact['manifest_sha256']}`",
        f"- Verified source files: {boundary['verified_input_files']}",
        f"- Excluded tracked paths: {boundary['excluded_tracked_files']} files, {boundary['excluded_tracked_bytes']} bytes",
        "",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/pages_publication.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument(
        "--overlay",
        action="append",
        default=[],
        metavar="ID=PATH",
        help="verified generated overlay outside the repository",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        overlays: dict[str, Path] = {}
        for value in args.overlay:
            overlay_id, separator, path = value.partition("=")
            if not separator or not overlay_id or not path or overlay_id in overlays:
                raise PublicationError(f"invalid --overlay value: {value!r}")
            overlays[overlay_id] = Path(path)
        report = build_artifact(
            root,
            config_path,
            args.output,
            args.report,
            overlays=overlays,
        )
        if args.summary:
            summary = args.summary.resolve()
            _require_outside(summary, root, "artifact summary must be outside the repository")
            _require_outside(
                summary, args.output.resolve(), "artifact summary must be outside the artifact"
            )
            append_summary(summary, report)
    except PublicationError as exc:
        print(f"Pages artifact error: {exc}")
        print("RESULT: FAIL")
        return 1
    print(
        "Pages artifact: "
        f"files={report['artifact']['files']} bytes={report['artifact']['bytes']}"
    )
    print(f"Report: {args.report.resolve()}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
