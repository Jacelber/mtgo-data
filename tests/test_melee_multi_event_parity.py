from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from mtgmeta.melee.multi_event_contract import (
    MultiEventContractError,
    build_multi_event_matchup_contract,
)
from mtgmeta.melee.multi_event_matchup import MultiEventMatchupError


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "melee" / "multi_event_matchup_parity.json"
)


@pytest.fixture(scope="module")
def parity_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _apply_operation(target: dict[str, Any], operation: dict[str, Any]) -> None:
    parent: Any = target
    for segment in operation["path"][:-1]:
        parent = parent[segment]
    key = operation["path"][-1]
    if operation["op"] == "set":
        parent[key] = deepcopy(operation["value"])
        return
    if operation["op"] == "delete":
        del parent[key]
        return
    if operation["op"] == "truncate":
        del parent[key][operation["length"] :]
        return
    raise AssertionError(f"unsupported fixture operation: {operation['op']}")


def test_python_contract_owns_the_shared_success_fixture(
    parity_fixture: dict[str, Any],
) -> None:
    result = build_multi_event_matchup_contract(
        deepcopy(parity_fixture["event_inputs"]),
        canonical_hierarchy=deepcopy(parity_fixture["canonical_hierarchy"]),
        catalog=deepcopy(parity_fixture["catalog"]),
    )

    assert result == parity_fixture["expected"]


def test_python_contract_owns_shared_rejection_codes(
    parity_fixture: dict[str, Any],
) -> None:
    for rejection in parity_fixture["rejections"]:
        candidate = deepcopy(
            {
                "event_inputs": parity_fixture["event_inputs"],
                "catalog": parity_fixture["catalog"],
            }
        )
        for operation in rejection["operations"]:
            _apply_operation(candidate, operation)

        with pytest.raises((MultiEventContractError, MultiEventMatchupError)) as caught:
            build_multi_event_matchup_contract(
                candidate["event_inputs"],
                canonical_hierarchy=deepcopy(parity_fixture["canonical_hierarchy"]),
                catalog=candidate["catalog"],
            )

        assert caught.value.code == rejection["error_code"], rejection["name"]
