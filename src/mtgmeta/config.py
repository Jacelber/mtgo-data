"""Validated YAML loading for shared rules and the MTGO format registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml

from .rules import RuleSet, RuleValidationFailure, build_rule_set, validate_rule_data


FORMAT_REGISTRY_SCHEMA_VERSION = "1.0.0"
FORMAT_STATES = frozenset({"executable", "planned", "decision_gated"})
MTGO_CAPABILITIES = frozenset(
    {
        "event_fetching",
        "raw_event_storage",
        "normalization",
        "classification",
        "event_statistics",
        "range_statistics",
        "matchup_statistics",
        "weekly_pickup",
        "metadata_generation",
        "catalog_generation",
    }
)
FORMAT_PATH_KEYS = (
    "events",
    "matches",
    "rules",
    "statistics",
    "reports",
)


class DuplicateKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: DuplicateKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


class RuleConfigError(ValueError):
    def __init__(self, failures: list[RuleValidationFailure]):
        self.failures = tuple(failures)
        super().__init__("; ".join(f"{item.path}: {item.message}" for item in failures))


class FormatConfigError(ValueError):
    """Raised when the manually maintained format registry is invalid."""


class UnknownFormatError(FormatConfigError):
    """Raised when a caller requests a format that is absent from the registry."""


class DisabledFormatError(FormatConfigError):
    """Raised when a known format cannot yet run an MTGO operation."""


@dataclass(frozen=True)
class FormatPaths:
    events: str
    matches: str
    rules: str
    statistics: str
    reports: str

    def resolve(self, repository_root: str | Path) -> dict[str, Path]:
        return {
            key: resolve_repository_path(repository_root, getattr(self, key))
            for key in FORMAT_PATH_KEYS
        }


@dataclass(frozen=True)
class MTGOFormat:
    enabled: bool
    capabilities: frozenset[str]
    paths: FormatPaths


@dataclass(frozen=True)
class FormatDefinition:
    id: str
    display_name: str
    state: str
    public: bool
    mtgo: MTGOFormat


@dataclass(frozen=True)
class FormatRegistry:
    schema_version: str
    formats: tuple[FormatDefinition, ...]

    def get(self, format_id: str) -> FormatDefinition:
        for definition in self.formats:
            if definition.id == format_id:
                return definition
        raise UnknownFormatError(f"unknown format {format_id!r}")

    def require_mtgo(self, format_id: str) -> FormatDefinition:
        definition = self.get(format_id)
        if not definition.mtgo.enabled:
            state_note = "is decision-gated" if definition.state == "decision_gated" else "is not enabled"
            raise DisabledFormatError(f"MTGO format {format_id!r} {state_note}")
        return definition


def parse_rule_text(text: str) -> RuleSet:
    try:
        data = yaml.load(text, Loader=DuplicateKeyLoader)
    except yaml.YAMLError as exc:
        raise RuleConfigError([RuleValidationFailure("YAML", str(exc).splitlines()[0])]) from exc
    failures = validate_rule_data(data)
    if failures:
        raise RuleConfigError(failures)
    return build_rule_set(data)


def load_rule_set(path: str | Path) -> RuleSet:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuleConfigError([RuleValidationFailure(str(source), f"cannot read input: {exc}")]) from exc
    return parse_rule_text(text)


def _load_yaml_mapping(text: str, label: str) -> dict[str, Any]:
    try:
        data = yaml.load(text, Loader=DuplicateKeyLoader)
    except yaml.YAMLError as exc:
        raise FormatConfigError(f"{label}: {str(exc).splitlines()[0]}") from exc
    if not isinstance(data, dict):
        raise FormatConfigError(f"{label}: expected a mapping")
    return data


def _format_error(path: str, message: str) -> FormatConfigError:
    return FormatConfigError(f"{path}: {message}")


def _require_string(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _format_error(f"{path}.{key}", "must be a non-empty string")
    return value


def _validate_relative_path(value: str, path: str) -> str:
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise _format_error(path, "must be a safe repository-relative path using forward slashes")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise _format_error(path, "must be a safe repository-relative path")
    return candidate.as_posix()


def parse_format_text(text: str) -> FormatRegistry:
    """Parse the registry without selecting or defaulting a format."""
    data = _load_yaml_mapping(text, "formats")
    if set(data) != {"schema_version", "formats"}:
        raise _format_error("formats", "must contain only schema_version and formats")
    if data["schema_version"] != FORMAT_REGISTRY_SCHEMA_VERSION:
        raise _format_error("schema_version", f"must be {FORMAT_REGISTRY_SCHEMA_VERSION!r}")
    entries = data["formats"]
    if not isinstance(entries, list) or not entries:
        raise _format_error("formats", "must be a non-empty list")

    definitions: list[FormatDefinition] = []
    seen_ids: set[str] = set()
    expected_entry_keys = {"id", "display_name", "state", "public", "mtgo"}
    expected_mtgo_keys = {"enabled", "capabilities", "paths"}
    for index, entry in enumerate(entries):
        path = f"formats[{index}]"
        if not isinstance(entry, dict) or set(entry) != expected_entry_keys:
            raise _format_error(path, "has unsupported, missing, or malformed fields")
        format_id = _require_string(entry, "id", path)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", format_id):
            raise _format_error(f"{path}.id", "must be a lowercase stable identifier")
        if format_id in seen_ids:
            raise _format_error(f"{path}.id", f"duplicates {format_id!r}")
        seen_ids.add(format_id)
        display_name = _require_string(entry, "display_name", path)
        state = _require_string(entry, "state", path)
        if state not in FORMAT_STATES:
            raise _format_error(f"{path}.state", "must be executable, planned, or decision_gated")
        public = entry["public"]
        if not isinstance(public, bool):
            raise _format_error(f"{path}.public", "must be a boolean")
        mtgo_data = entry["mtgo"]
        if not isinstance(mtgo_data, dict) or set(mtgo_data) != expected_mtgo_keys:
            raise _format_error(f"{path}.mtgo", "has unsupported, missing, or malformed fields")
        enabled = mtgo_data["enabled"]
        if not isinstance(enabled, bool):
            raise _format_error(f"{path}.mtgo.enabled", "must be a boolean")
        if enabled != (state == "executable"):
            raise _format_error(f"{path}.mtgo.enabled", "must match executable state")
        capabilities = mtgo_data["capabilities"]
        if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
            raise _format_error(f"{path}.mtgo.capabilities", "must be a list of strings")
        if len(capabilities) != len(set(capabilities)) or any(item not in MTGO_CAPABILITIES for item in capabilities):
            raise _format_error(f"{path}.mtgo.capabilities", "contains duplicate or unsupported capability")
        if not enabled and capabilities:
            raise _format_error(f"{path}.mtgo.capabilities", "must be empty while MTGO is disabled")
        paths = mtgo_data["paths"]
        if not isinstance(paths, dict) or set(paths) != set(FORMAT_PATH_KEYS):
            raise _format_error(f"{path}.mtgo.paths", "must declare every MTGO path exactly once")
        normalized_paths = {
            key: _validate_relative_path(_require_string(paths, key, f"{path}.mtgo.paths"), f"{path}.mtgo.paths.{key}")
            for key in FORMAT_PATH_KEYS
        }
        if any(f"/{format_id}" not in value and not value.endswith(format_id) for value in normalized_paths.values()):
            raise _format_error(f"{path}.mtgo.paths", "must remain format-specific")
        definitions.append(
            FormatDefinition(
                id=format_id,
                display_name=display_name,
                state=state,
                public=public,
                mtgo=MTGOFormat(
                    enabled=enabled,
                    capabilities=frozenset(capabilities),
                    paths=FormatPaths(**normalized_paths),
                ),
            )
        )
    return FormatRegistry(schema_version=FORMAT_REGISTRY_SCHEMA_VERSION, formats=tuple(definitions))


def load_format_registry(path: str | Path) -> FormatRegistry:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FormatConfigError(f"{source}: cannot read input: {exc}") from exc
    return parse_format_text(text)


def resolve_repository_path(repository_root: str | Path, relative_path: str) -> Path:
    """Resolve a validated registry path without permitting a repository escape."""
    normalized = _validate_relative_path(relative_path, "path")
    root = Path(repository_root).resolve()
    resolved = (root / Path(*PurePosixPath(normalized).parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FormatConfigError(f"path: escapes repository root: {relative_path!r}") from exc
    return resolved
