"""Read-only JSON Schema validation for declared generated JSON outputs."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


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


def load_schemas(schema_dir: Path) -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = _read_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise SchemaError(f"{path.name} has no non-empty $id")
        schemas[path.name] = schema
        resources.append((schema_id, Resource.from_contents(schema)))
    if not schemas:
        raise SchemaError(f"no schemas found in {schema_dir}")
    return schemas, Registry().with_resources(resources)


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    registry: Registry,
    path: str = "<instance>",
) -> list[ValidationFailure]:
    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: (list(error.absolute_path), error.message))
    return [ValidationFailure(path, _location(list(error.absolute_path)), error.message) for error in errors]


def validate_manifest(repository_root: Path, manifest_path: Path) -> tuple[int, list[ValidationFailure]]:
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != "1.0.0":
        raise SchemaError("manifest schema_version must be 1.0.0")
    if manifest.get("output_schema_version_embedded") is not True:
        raise SchemaError("manifest must require embedded output schema versions")
    mappings = manifest.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise SchemaError("manifest mappings must be a non-empty list")
    schemas, registry = load_schemas(manifest_path.parent)
    checked = 0
    failures: list[ValidationFailure] = []
    seen: set[Path] = set()
    for mapping in mappings:
        if not isinstance(mapping, dict) or set(mapping) != {"pattern", "schema"}:
            raise SchemaError("each manifest mapping must contain only pattern and schema")
        pattern, schema_name = mapping["pattern"], mapping["schema"]
        if not isinstance(pattern, str) or not isinstance(schema_name, str):
            raise SchemaError("manifest pattern and schema must be strings")
        if schema_name not in schemas:
            raise SchemaError(f"manifest references missing schema {schema_name}")
        matches = sorted(repository_root.glob(pattern))
        if not matches:
            raise SchemaError(f"manifest pattern matched no files: {pattern}")
        for path in matches:
            resolved = path.resolve()
            if resolved in seen:
                raise SchemaError(f"manifest maps a file more than once: {path.relative_to(repository_root)}")
            seen.add(resolved)
            relative = path.relative_to(repository_root).as_posix()
            try:
                instance = _read_json(path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                failures.append(ValidationFailure(relative, "$", f"cannot read JSON: {exc}"))
            else:
                failures.extend(validate_instance(instance, schemas[schema_name], registry, relative))
            checked += 1
    return checked, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate declared public JSON files against versioned schemas.")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: script directory)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="schema mapping manifest")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else (root / args.manifest)
    try:
        checked, failures = validate_manifest(root, manifest.resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError, ValueError) as exc:
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
    raise SystemExit(main())
