"""Validate value-independent invariants on generated MTGO output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _rounded_share(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def validate_range_document(document: dict[str, Any], label: str) -> list[str]:
    failures: list[str] = []
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        return [f"{label}: archetypes is not a list"]

    fields = (
        ("count", "total_decks", None),
        ("high_score_count", "total_high_score", "high_score_share"),
        ("top8_count", "total_top8", "top8_share"),
    )
    for count_key, total_key, share_key in fields:
        total = document.get(total_key)
        counts = [item.get(count_key) for item in archetypes if isinstance(item, dict)]
        if (
            not isinstance(total, int)
            or total < 0
            or len(counts) != len(archetypes)
            or any(not isinstance(value, int) or value < 0 for value in counts)
        ):
            failures.append(f"{label}: {count_key}/{total_key} is not non-negative integer data")
            continue
        if sum(counts) != total:
            failures.append(
                f"{label}: sum({count_key})={sum(counts)} does not equal {total_key}={total}"
            )
        if share_key:
            for item, count in zip(archetypes, counts, strict=True):
                share = item.get(share_key)
                expected = _rounded_share(count, total)
                if not isinstance(share, (int, float)) or abs(share - expected) > 0.00005:
                    failures.append(
                        f"{label}: {item.get('id', '<unknown>')} {share_key}={share!r}; expected {expected}"
                    )
    return failures


def _validate_matrix(matrix: Any, label: str) -> list[str]:
    if not isinstance(matrix, dict):
        return [f"{label}: matrix is not an object"]
    failures: list[str] = []
    for left, row in matrix.items():
        if not isinstance(row, dict):
            failures.append(f"{label}: row {left!r} is not an object")
            continue
        for right, cell in row.items():
            cell_label = f"{label}[{left!r}][{right!r}]"
            if not isinstance(cell, dict):
                failures.append(f"{cell_label}: cell is not an object")
                continue
            values = tuple(cell.get(key) for key in ("wins", "losses", "draws", "matches"))
            if any(not isinstance(value, int) or value < 0 for value in values):
                failures.append(f"{cell_label}: record fields are not non-negative integers")
                continue
            wins, losses, draws, matches = values
            if matches != wins + losses + draws:
                failures.append(f"{cell_label}: matches does not equal wins + losses + draws")
            inverse = matrix.get(right, {}).get(left)
            if not isinstance(inverse, dict) or (
                wins,
                losses,
                draws,
                matches,
            ) != (
                inverse.get("losses"),
                inverse.get("wins"),
                inverse.get("draws"),
                inverse.get("matches"),
            ):
                failures.append(f"{cell_label}: inverse record is missing or asymmetric")
            literal = cell.get("literal_record")
            if not isinstance(literal, dict):
                failures.append(f"{cell_label}: literal_record is missing")
                continue
            if any(literal.get(key) != cell.get(key) for key in ("wins", "losses", "draws", "matches")):
                failures.append(f"{cell_label}: literal_record disagrees with matrix cell")
            rate = literal.get("win_rate")
            interval = literal.get("confidence_interval_95")
            if matches == 0:
                if rate is not None or interval is not None:
                    failures.append(f"{cell_label}: missing sample must not be encoded as zero")
            elif not (
                isinstance(rate, (int, float))
                and isinstance(interval, dict)
                and isinstance(interval.get("lower"), (int, float))
                and isinstance(interval.get("upper"), (int, float))
                and interval["lower"] <= rate <= interval["upper"]
            ):
                failures.append(f"{cell_label}: confidence interval does not contain win rate")
    return failures


def validate_matchup_document(document: dict[str, Any], label: str) -> list[str]:
    failures: list[str] = []
    for level in ("parent", "leaf"):
        failures.extend(_validate_matrix(document.get(f"{level}_matrix"), f"{label}:{level}"))
    return failures


def validate_repository_output(root: Path) -> list[str]:
    failures: list[str] = []
    for path in sorted(root.glob("stats/*/mtgo/range_*w.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        failures.extend(validate_range_document(document, path.as_posix()))
    for path in sorted(root.glob("stats/*/mtgo/matchup_*w.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        failures.extend(validate_matchup_document(document, path.as_posix()))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    failures = validate_repository_output(args.root)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print("Generated MTGO output invariants are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
