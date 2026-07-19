"""P2-08 regression coverage for hash-independent generated ordering."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stats_matchup import build_window_output
from stats_standard import deck_diff, weighted_l1


def cell(wins, losses=0, draws=0):
    return {"wins": wins, "losses": losses, "draws": draws}


def test_tied_generated_rows_use_stable_name_order():
    diff = deck_diff(
        {"Zulu": 0, "Alpha": 0, "Mike": 2, "Bravo": 2},
        {"Zulu": 1, "Alpha": 1, "Mike": 1, "Bravo": 1},
        top=2,
    )
    assert [item["name"] for item in diff["fewer"]] == ["Alpha", "Zulu"]
    assert [item["name"] for item in diff["more"]] == ["Bravo", "Mike"]

    order, _, _ = build_window_output(
        {},
        {},
        {"Zulu": cell(2), "Alpha": cell(2), "Beta": cell(3)},
    )
    assert order == ["Beta", "Alpha", "Zulu"]


def test_weighted_distance_uses_stable_high_precision_sum():
    value = weighted_l1(
        {"Huge": 1, "Small A": 1, "Small B": 1},
        {},
        {"Huge": 10**16, "Small A": 1, "Small B": 1},
    )
    assert value == 10000000000000002


HASH_SEED_PROBE = r"""
import json
from stats_matchup import build_window_output
from stats_standard import deck_diff, weighted_l1

def cell(wins):
    return {"wins": wins, "losses": 0, "draws": 0}

distance = weighted_l1(
    {"Huge": 1, "Small A": 1, "Small B": 1}, {},
    {"Huge": 10**16, "Small A": 1, "Small B": 1},
)
diff = deck_diff(
    {"Zulu": 0, "Alpha": 0, "Mike": 2, "Bravo": 2},
    {"Zulu": 1, "Alpha": 1, "Mike": 1, "Bravo": 1},
    top=2,
)
order, _, _ = build_window_output(
    {}, {}, {"Zulu": cell(2), "Alpha": cell(2), "Beta": cell(3)},
)
print(json.dumps({"distance": distance, "diff": diff, "order": order}, sort_keys=True))
"""


def test_generated_tie_behavior_is_independent_of_python_hash_seed():
    outputs = []
    for seed in ("1", "2", "17", "101"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-B", "-c", HASH_SEED_PROBE],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outputs.append(json.loads(result.stdout))
    assert outputs == [outputs[0]] * len(outputs)
