"""YAML loading for versioned shared classification rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .rules import RuleSet, RuleValidationFailure, build_rule_set, validate_rule_data


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
