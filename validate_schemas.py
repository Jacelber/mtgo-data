"""Read-only JSON Schema validation for declared generated JSON outputs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from time import monotonic
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

from mtgmeta.config import load_format_registry
from tools.delivery.gitfacts import InfrastructureError, changed_files


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "schemas" / "manifest.json"


@dataclass(frozen=True)
class ValidationFailure:
    path: str
    location: str
    message: str


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _location(parts: list[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def load_schemas(schema_dir: Path, names: set[str] | None = None) -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    def read(name: str) -> dict:
        if Path(name).name != name or not name.endswith(".schema.json"):
            raise SchemaError(f"invalid local schema name: {name}")
        path = schema_dir / name
        schema = _read_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise SchemaError(f"{path.name} has no non-empty $id")
        return schema
    def retrieve(uri: str) -> Resource:
        # Resolve only referenced local schemas. Never fetch remote schemas or
        # parse unrelated products merely because they share this directory.
        schema = read(urlsplit(uri).path.rsplit("/", 1)[-1])
        if schema["$id"] != uri:
            raise SchemaError(f"schema identity mismatch: {uri}")
        return Resource.from_contents(schema)
    for name in sorted(names if names is not None else {p.name for p in schema_dir.glob("*.schema.json")}):
        schema = read(name)
        schemas[name] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    if not schemas and names is None:
        raise SchemaError(f"no schemas found in {schema_dir}")
    # Preload only the selected schemas' reference closure. Registry retrieval
    # is immutable: a resource retrieved by one validation branch is not saved
    # for its siblings, so lazy retrieval repeats parsing and schema checking.
    registry = Registry().with_resources(resources).crawl()
    pending = [(resource, uri) for uri, resource in resources]
    while pending:
        resource, base = pending.pop()
        base = urljoin(base, resource.id() or "")
        contents = resource.contents
        if isinstance(contents, dict):
            for keyword in ("$ref", "$dynamicRef"):
                ref = contents.get(keyword)
                if not isinstance(ref, str):
                    continue
                uri, _ = urldefrag(urljoin(base, ref))
                if uri != urldefrag(base)[0] and uri not in registry:
                    dependency = retrieve(uri)
                    registry = registry.with_resource(uri, dependency).crawl()
                    pending.append((dependency, uri))
        # Only schema positions are visited; examples/defaults are instance data.
        pending.extend((child, base) for child in resource.subresources())
    return schemas, registry


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    registry: Registry,
    path: str = "<instance>",
) -> list[ValidationFailure]:
    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: (list(error.absolute_path), error.message))
    return [ValidationFailure(path, _location(list(error.absolute_path)), error.message) for error in errors]


def _validate_manifest(
    repository_root: Path,
    manifest_path: Path,
    selected_paths: set[str] | None = None,
) -> tuple[int, list[ValidationFailure]]:
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != "1.0.0":
        raise SchemaError("manifest schema_version must be 1.0.0")
    if manifest.get("output_schema_version_embedded") is not True:
        raise SchemaError("manifest must require embedded output schema versions")
    mappings = manifest.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise SchemaError("manifest mappings must be a non-empty list")
    selected_mappings = []
    for mapping in mappings:
        if not isinstance(mapping, dict) or set(mapping) != {"pattern", "schema"}:
            raise SchemaError("each manifest mapping must contain only pattern and schema")
        pattern, schema_name = mapping["pattern"], mapping["schema"]
        if not isinstance(pattern, str) or not isinstance(schema_name, str):
            raise SchemaError("manifest pattern and schema must be strings")
        matches = [path for path in sorted(repository_root.glob(pattern))
                   if selected_paths is None or path.relative_to(repository_root).as_posix() in selected_paths]
        if not matches and selected_paths is None:
            raise SchemaError(f"manifest pattern matched no files: {pattern}")
        if matches:
            selected_mappings.append((schema_name, matches))
    started = monotonic()
    print("Schema loading references", file=sys.stderr, flush=True)
    schemas, registry = load_schemas(manifest_path.parent, {name for name, _ in selected_mappings})
    print(f"Schema references ready seconds={monotonic()-started:.3f}", file=sys.stderr, flush=True)
    total = sum(len(paths) for _, paths in selected_mappings)
    checked = 0
    failures: list[ValidationFailure] = []
    seen: set[Path] = set()
    formats = None
    for schema_name, matches in selected_mappings:
        for path in matches:
            relative = path.relative_to(repository_root).as_posix()
            file_started = monotonic()
            print(f"Schema start {checked}/{total} {relative}", file=sys.stderr, flush=True)
            if selected_paths is not None and relative not in selected_paths:
                continue
            resolved = path.resolve()
            if resolved in seen:
                raise SchemaError(f"manifest maps a file more than once: {path.relative_to(repository_root)}")
            seen.add(resolved)
            try:
                instance = _read_json(path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                failures.append(ValidationFailure(relative, "$", f"cannot read JSON: {exc}"))
            else:
                failures.extend(validate_instance(instance, schemas[schema_name], registry, relative))
                parts = path.relative_to(repository_root).parts
                format_scoped_output = (
                    len(parts) >= 4
                    and parts[0] in {"stats", "reports"}
                    and parts[2] == "mtgo"
                ) or (
                    len(parts) == 3
                    and parts[0] == "stats"
                    and parts[2] == "archetype_names.json"
                )
                if format_scoped_output:
                    if formats is None:
                        formats = load_format_registry(repository_root / "configs/formats.yaml")
                    try:
                        formats.require_mtgo(parts[1])
                    except ValueError as exc:
                        failures.append(ValidationFailure(relative, "$.format", str(exc)))
                    if not isinstance(instance, dict) or instance.get("format") != parts[1]:
                        failures.append(ValidationFailure(relative, "$.format", "must match the registered output path"))
            checked += 1
            print(f"Schema done {checked}/{total} {relative} seconds={monotonic()-file_started:.3f}", file=sys.stderr, flush=True)
    return checked, failures


# 43 real Standard files took 29.7s after reference reuse; allow a 4x margin.
# Larger operations can override this per call/CLI or with the environment.
DEFAULT_TIMEOUT_SECONDS = 120.0


def schema_timeout_seconds(value: float | None = None) -> float:
    import math
    timeout = float(value if value is not None else
                    os.environ.get("MTGO_SCHEMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("schema timeout must be finite and positive")
    return timeout


def validate_manifest(repository_root: Path, manifest_path: Path,
                      selected_paths: set[str] | None = None, *,
                      timeout_seconds: float | None = None) -> tuple[int, list[ValidationFailure]]:
    """Bound the entire batch, including a stuck schema or single file.

    The worker loads the schema registry once. The supervisor
    terminates its process tree on timeout; temporary IPC is not a persistent cache.
    """
    timeout = schema_timeout_seconds(timeout_seconds)
    with tempfile.TemporaryDirectory(prefix="schema-validation-") as temp:
        request, result = Path(temp)/"request.json", Path(temp)/"result.json"
        request.write_text(json.dumps({"root": str(repository_root.resolve()),
            "manifest": str(manifest_path.resolve()),
            "selected": sorted(selected_paths) if selected_paths is not None else None}), encoding="utf-8")
        # Bypass Windows venv launchers while preserving this interpreter's exact
        # import path. The actual Python worker does not create child processes.
        executable = getattr(sys, "_base_executable", sys.executable)
        bootstrap = "import runpy,sys; sys.path[:]=%r; sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')" % sys.path
        worker = subprocess.Popen([executable, "-B", "-c", bootstrap,
            str(Path(__file__).resolve()), "--worker-request", str(request), str(result)],
            stdout=subprocess.DEVNULL)
        try:
            code = worker.wait(timeout=timeout)
        except BaseException as exc:
            worker.kill()
            worker.wait()
            if isinstance(exc, subprocess.TimeoutExpired):
                raise TimeoutError(f"Schema validation incomplete: exceeded {timeout:g}s; generated files retained") from exc
            raise
        if code:
            raise RuntimeError(f"Schema validation worker failed: {code}")
        value = json.loads(result.read_text(encoding="utf-8"))
        if "error" in value:
            kind = {"SchemaError": SchemaError, "ValueError": ValueError,
                    "FileNotFoundError": FileNotFoundError, "OSError": OSError}.get(value["type"], RuntimeError)
            raise kind(value["error"])
        return value["checked"], [ValidationFailure(**row) for row in value["failures"]]


def _worker(request: str, result: str) -> None:
    args = json.loads(Path(request).read_text(encoding="utf-8"))
    try:
        count, failures = _validate_manifest(Path(args["root"]), Path(args["manifest"]),
            set(args["selected"]) if args["selected"] is not None else None)
        value = {"checked": count, "failures": [vars(row) for row in failures]}
    except Exception as exc:
        value = {"type": type(exc).__name__, "error": str(exc)}
    Path(result).write_text(json.dumps(value), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate declared public JSON files against versioned schemas.")
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: script directory)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="schema mapping manifest")
    parser.add_argument(
        "--changed-from",
        metavar="REF",
        help="validate only mapped public JSON changed from REF",
    )
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        help="validate one mapped repository-relative JSON path (repeatable)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else (root / args.manifest)
    try:
        if args.changed_from and args.paths:
            raise ValueError("--changed-from and --path cannot be combined")
        selected = (
            set(changed_files(root, args.changed_from))
            if args.changed_from
            else set(args.paths) if args.paths else None
        )
        checked, failures = validate_manifest(root, manifest.resolve(), selected, timeout_seconds=args.timeout_seconds)
        if args.paths and checked != len(selected):
            raise SchemaError(
                "one or more requested --path values are not mapped by the selected manifest"
            )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RuntimeError,
        InfrastructureError,
        SchemaError,
        ValueError,
    ) as exc:
        print(f"Schema validation ERROR: {exc}")
        return 2
    if failures:
        print(f"Schema validation FAIL: checked={checked} failures={len(failures)}")
        for failure in failures:
            print(f"{failure.path} {failure.location}: {failure.message}")
        return 1
    profile = _read_json(manifest).get("profile", "unspecified")
    print(f"Schema validation PASS: checked={checked} profile={profile} version=1.0.0 embedded_versions={checked}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker-request":
        _worker(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(main())
