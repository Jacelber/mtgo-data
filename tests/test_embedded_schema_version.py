import ast
from pathlib import Path

import pytest

from public_contract import PUBLIC_SCHEMA_VERSION, versioned


ROOT = Path(__file__).resolve().parents[1]


def test_versioned_returns_a_new_document_and_rejects_double_versioning():
    source = {"format": "standard"}
    result = versioned(source)
    assert result == {"schema_version": "1.0.0", "format": "standard"}
    assert source == {"format": "standard"}
    assert PUBLIC_SCHEMA_VERSION == "1.0.0"
    with pytest.raises(ValueError, match="already contains"):
        versioned(result)


@pytest.mark.parametrize(
    "path,expected_calls",
    [
        ("src/mtgmeta/mtgo/stats.py", 3),
        ("src/mtgmeta/mtgo/matchup.py", 2),
        ("src/mtgmeta/mtgo/pickup.py", 3),
    ],
)
def test_every_public_json_generator_uses_the_shared_version_helper(path, expected_calls):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "versioned"
    ]
    assert len(calls) == expected_calls
