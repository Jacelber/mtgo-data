"""Shared mana-identity metadata and public coverage validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Mapping

import yaml


DEFAULT_CONFIG = Path("configs/archetype_mana_identities.yaml")
DEFAULT_RENDERED = Path("assets/js/phase8/archetype-visuals.js")
ALLOWED_COLORS = ("w", "u", "b", "r", "g", "c")


@dataclass(frozen=True)
class ManaIdentityEntry:
    colors: tuple[str, ...]
    status: str
    basis: str | None = None


def _validated_colors(value: object, identity_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            f"mana identity {identity_id!r} must contain at least one indicator"
        )
    colors = tuple(value)
    if any(not isinstance(color, str) or color not in ALLOWED_COLORS for color in colors):
        raise ValueError(f"mana identity {identity_id!r} contains an invalid indicator")
    if len(colors) != len(set(colors)):
        raise ValueError(f"mana identity {identity_id!r} contains duplicate indicators")
    if colors == ("c",):
        return colors
    if "c" in colors:
        raise ValueError(
            f"mana identity {identity_id!r} cannot combine colorless with colors"
        )
    expected = tuple(color for color in ALLOWED_COLORS if color in colors)
    if colors != expected:
        raise ValueError(
            f"mana identity {identity_id!r} must use canonical WUBRG order"
        )
    return colors


def load_mana_identities(
    repository_root: str | Path,
    *,
    config_path: str | Path | None = None,
) -> dict[str, dict[str, ManaIdentityEntry]]:
    root = Path(repository_root).resolve()
    path = Path(config_path) if config_path else root / DEFAULT_CONFIG
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise ValueError("Unsupported mana identity config")
    formats = document.get("formats")
    if not isinstance(formats, dict):
        raise ValueError("Mana identity config requires formats")

    result: dict[str, dict[str, ManaIdentityEntry]] = {}
    for format_id, format_value in formats.items():
        if not isinstance(format_id, str) or not isinstance(format_value, dict):
            raise ValueError("Invalid mana identity format entry")
        entries: dict[str, ManaIdentityEntry] = {}
        approved = format_value.get("approved", {})
        candidates = format_value.get("candidates", {})
        if not isinstance(approved, dict) or not isinstance(candidates, dict):
            raise ValueError(f"Invalid mana identity groups: {format_id}")
        for identity_id, colors in approved.items():
            if not isinstance(identity_id, str):
                raise ValueError(f"Invalid mana identity key: {format_id}")
            entries[identity_id] = ManaIdentityEntry(
                _validated_colors(colors, identity_id), "approved"
            )
        for identity_id, candidate in candidates.items():
            if identity_id in entries:
                raise ValueError(f"Duplicate mana identity: {format_id}/{identity_id}")
            if not isinstance(identity_id, str) or not isinstance(candidate, dict):
                raise ValueError(f"Invalid mana identity candidate: {format_id}")
            basis = candidate.get("basis")
            if basis is not None and not isinstance(basis, str):
                raise ValueError(f"Invalid mana identity basis: {format_id}/{identity_id}")
            entries[identity_id] = ManaIdentityEntry(
                _validated_colors(candidate.get("colors"), identity_id),
                "candidate",
                basis,
            )
        result[format_id] = entries
    return result


def required_mana_identity_ids(
    repository_root: str | Path,
    format_id: str,
) -> frozenset[str]:
    root = Path(repository_root).resolve()
    path = root / "stats" / format_id / "mtgo" / "archetype_hierarchy.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(
        item["id"]
        for group in (document.get("parents", []), document.get("leaves", []))
        for item in group
        if item.get("id")
    )


def rendered_mana_identities(
    repository_root: str | Path,
    format_id: str,
) -> dict[str, tuple[str, ...]]:
    root = Path(repository_root).resolve()
    text = (root / DEFAULT_RENDERED).read_text(encoding="utf-8")
    section = text.split("const manaIdentities = Object.freeze({", 1)[1].split(
        "\n});", 1
    )[0]
    match = re.search(
        rf"^  {re.escape(format_id)}: Object\.freeze\(\{{\n(.*?)^  \}}\),",
        section,
        re.M | re.S,
    )
    if not match:
        raise ValueError(f"Missing rendered mana identity map: {format_id}")
    result = {}
    for line in match[1].splitlines():
        item = re.fullmatch(
            r'\s*"([^"]+)": Object\.freeze\((\[[^\n]*\])\),\s*', line
        )
        if line.strip() and not item:
            raise ValueError("Rendered mana identity map is not a generated literal")
        if item:
            result[item[1]] = _validated_colors(json.loads(item[2]), item[1])
    return result


def require_complete_mana_identities(
    repository_root: str | Path,
    format_id: str,
) -> None:
    root = Path(repository_root).resolve()
    formats = load_mana_identities(root)
    if format_id not in formats:
        raise ValueError(f"Missing mana identity format: {format_id}")
    entries = formats[format_id]
    required = required_mana_identity_ids(root, format_id)
    missing = sorted(required - entries.keys())
    if missing:
        raise ValueError(
            f"public format {format_id!r} is missing mana identities: "
            + ", ".join(missing)
        )
    pending = sorted(
        identity_id
        for identity_id in required
        if entries[identity_id].status != "approved"
    )
    if pending:
        raise ValueError(
            f"public format {format_id!r} has unreviewed mana identities: "
            + ", ".join(pending)
        )
    expected = {
        identity_id: entries[identity_id].colors for identity_id in sorted(required)
    }
    rendered = rendered_mana_identities(root, format_id)
    actual = {identity_id: rendered.get(identity_id) for identity_id in sorted(required)}
    if actual != expected:
        raise ValueError(f"public format {format_id!r} has stale rendered mana identities")


def render_mana_identity_block(
    formats: Mapping[str, Mapping[str, ManaIdentityEntry]],
) -> str:
    lines = ["const manaIdentities = Object.freeze({"]
    for format_id, entries in formats.items():
        lines.append(f"  {format_id}: Object.freeze({{")
        for identity_id, entry in entries.items():
            colors = json.dumps(list(entry.colors))
            lines.append(
                f"    {json.dumps(identity_id)}: Object.freeze({colors}),"
            )
        lines.append("  }),")
    lines.append("});")
    return "\n".join(lines)


def write_rendered_mana_identities(repository_root: str | Path) -> Path:
    root = Path(repository_root).resolve()
    source = root / DEFAULT_RENDERED
    text = source.read_text(encoding="utf-8")
    start = text.index("const manaIdentities = Object.freeze({")
    end = text.index("\n});", start) + len("\n});")
    replacement = render_mana_identity_block(load_mana_identities(root))
    source.write_text(
        text[:start] + replacement + text[end:], encoding="utf-8", newline="\n"
    )
    return source
