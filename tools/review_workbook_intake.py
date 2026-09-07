"""Read or compare an Owner review XLSX through the raw-OOXML intake gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtgmeta.review_workbook import (  # noqa: E402
    ReviewWorkbookError,
    read_workbook_rows,
    semantic_diff,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_or_print(value: object, output: Path | None) -> None:
    if output is None:
        text = json.dumps(value, ensure_ascii=True, indent=2) + "\n"
        print(text, end="")
        return
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--workbook", required=True, type=Path)
    snapshot.add_argument("--output", type=Path)

    diff = subparsers.add_parser("diff")
    diff.add_argument("--baseline", required=True, type=Path)
    diff.add_argument("--workbook", required=True, type=Path)
    diff.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    try:
        returned = read_workbook_rows(args.workbook)
        if args.command == "snapshot":
            result = {
                "schema_version": "1.0.0",
                "document_type": "owner_review_workbook_snapshot",
                "workbook_sha256": _sha256(args.workbook),
                "sheets": returned,
            }
        else:
            baseline = read_workbook_rows(args.baseline)
            result = {
                "schema_version": "1.0.0",
                "document_type": "owner_review_workbook_semantic_diff",
                "baseline_sha256": _sha256(args.baseline),
                "workbook_sha256": _sha256(args.workbook),
                "changes": semantic_diff(baseline, returned),
            }
        if args.output is not None:
            input_paths = {args.workbook.resolve()}
            if args.command == "diff":
                input_paths.add(args.baseline.resolve())
            if args.output.resolve() in input_paths:
                raise ReviewWorkbookError("output must not overwrite an input workbook")
        _write_or_print(result, args.output)
        return 0
    except (OSError, ReviewWorkbookError) as exc:
        print(f"Review workbook intake ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
