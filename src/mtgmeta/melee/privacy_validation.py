"""Validation boundary for persisted Melee v3 resource documents."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "melee-minimized-resource.schema.json"

# Exact source keys found by P10-01/P10-03 to be unnecessary for the persisted
# statistical contract. Values are intentionally not scanned: a display name or
# card name may legitimately contain the same text.
PROHIBITED_RESOURCE_KEYS = frozenset({
    "CollectorNumber",
    "Components",
    "DecklistName",
    "DisplayName",
    "DisplayNameLastFirst",
    "Language",
    "LanguageDescription",
    "LinkToCards",
    "PlayerId",
    "ProfileImageVersion",
    "PronounsDescription",
    "ScreenName",
    "SetCode",
    "TeamId",
    "Treatment",
    "Username",
    "source_participant_id",
})


class MeleeResourceValidationError(ValueError):
    """Raised when a minimized resource cannot cross the persistence boundary."""


def _json_path(parts: tuple[Any, ...]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


@lru_cache(maxsize=4)
def _validator(schema_path: Path) -> Draft202012Validator:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        raise MeleeResourceValidationError(
            f"cannot load minimized-resource Schema {schema_path}: {exc}"
        ) from exc
    return Draft202012Validator(schema)


def scan_prohibited_resource_keys(document: Any) -> tuple[str, ...]:
    """Return prohibited JSON-key paths in one already-scoped v3 resource."""

    findings: list[str] = []

    def visit(value: Any, path: tuple[Any, ...]) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = (*path, key)
                if key in PROHIBITED_RESOURCE_KEYS:
                    findings.append(_json_path(child_path))
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, index))

    visit(document, ())
    return tuple(findings)


def validate_minimized_resource(
    document: Any,
    *,
    context: str = "minimized resource",
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> None:
    """Apply the authoritative Schema and supplemental prohibited-key scan."""

    validator = _validator(Path(schema_path).resolve())
    errors = sorted(
        validator.iter_errors(document),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        error = errors[0]
        raise MeleeResourceValidationError(
            f"{context}: Schema validation failed at "
            f"{_json_path(tuple(error.absolute_path))}: {error.message}"
        )
    findings = scan_prohibited_resource_keys(document)
    if findings:
        raise MeleeResourceValidationError(
            f"{context}: prohibited persisted key at {findings[0]}"
        )


__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "MeleeResourceValidationError",
    "PROHIBITED_RESOURCE_KEYS",
    "scan_prohibited_resource_keys",
    "validate_minimized_resource",
]
