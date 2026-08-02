"""Native Node.js frontend test-suite contract."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
NODE_TEST = ROOT / "tests" / "js" / "phase8-matchup-model.test.js"


def test_native_node_frontend_suite_passes() -> None:
    result = subprocess.run(
        ["node", "--test", str(NODE_TEST)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
