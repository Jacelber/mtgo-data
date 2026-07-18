"""Read-only validation for legacy archetype rule YAML files."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ValidationFailure:
    path: str
    message: str


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
COPY_KEYS = ("minCopies", "maxCopies", "exactCopies")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_data(data: Any) -> list[ValidationFailure]:
    failures: list[ValidationFailure] = []
    if not isinstance(data, dict):
        return [ValidationFailure("root", "must be a mapping")]
    if not _nonempty_string(data.get("format")):
        failures.append(ValidationFailure("format", "must be a non-empty string"))
    if "date" in data and not isinstance(data["date"], str):
        failures.append(ValidationFailure("date", "must be a legacy string scalar"))
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, list) or not archetypes:
        failures.append(ValidationFailure("archetypes", "must be a non-empty list"))
        return failures
    for i, archetype in enumerate(archetypes):
        ap = f"archetypes[{i}]"
        if not isinstance(archetype, dict):
            failures.append(ValidationFailure(ap, "must be a mapping")); continue
        if not _nonempty_string(archetype.get("name")):
            failures.append(ValidationFailure(f"{ap}.name", "must be a non-empty string"))
        cards = archetype.get("signatureCards")
        if not isinstance(cards, list) or not cards:
            failures.append(ValidationFailure(f"{ap}.signatureCards", "must be a non-empty list")); continue
        for j, card in enumerate(cards):
            cp = f"{ap}.signatureCards[{j}]"
            if not isinstance(card, dict):
                failures.append(ValidationFailure(cp, "must be a mapping")); continue
            if not card:
                failures.append(ValidationFailure(cp, "must not be empty")); continue
            if not _nonempty_string(card.get("name")):
                failures.append(ValidationFailure(f"{cp}.name", "must be a non-empty string"))
            if "zone" in card and card["zone"] not in ("any", "main", "side"):
                failures.append(ValidationFailure(f"{cp}.zone", "must be one of any, main, side"))
            present = [key for key in COPY_KEYS if key in card]
            if len(present) > 1:
                failures.append(ValidationFailure(cp, "copy-count conditions are mutually exclusive"))
            for key in present:
                value = card[key]
                if isinstance(value, bool) or not isinstance(value, int):
                    failures.append(ValidationFailure(f"{cp}.{key}", "must be an integer"))
                elif value < 0:
                    failures.append(ValidationFailure(f"{cp}.{key}", "must not be negative"))
    return failures


def validate_text(text: str) -> list[ValidationFailure]:
    try:
        data = yaml.load(text, Loader=DuplicateKeyLoader)
    except yaml.YAMLError as exc:
        return [ValidationFailure("YAML", str(exc).splitlines()[0])]
    return validate_data(data)


def validate_path(path: str | Path) -> list[ValidationFailure]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return [ValidationFailure(str(path), f"cannot read input: {exc.strerror or type(exc).__name__}")]
    return validate_text(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate legacy archetype rule YAML.")
    parser.add_argument("path", nargs="?", default="my_archetypes/standard.yaml")
    args = parser.parse_args(argv)
    failures = validate_path(args.path)
    if failures:
        print(f"Rule validation FAIL: {args.path}")
        for failure in failures:
            print(f"{failure.path}: {failure.message}")
        return 1
    print(f"Rule validation PASS: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
