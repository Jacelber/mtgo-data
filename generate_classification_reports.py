"""Generate sanitized Standard MTGO classification diagnostic reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import load_rule_set
from mtgmeta.reports import (
    build_classification_reports,
    find_identity_fields,
    has_blocking_diagnostics,
    load_events,
    write_classification_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--data-dir", type=Path, default=Path("data/standard"))
    parser.add_argument("--rules", type=Path, default=Path("my_archetypes/standard.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/standard/mtgo"))
    parser.add_argument("--strict", action="store_true", help="fail on conflicts or invalid decks")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    data_dir = args.data_dir if args.data_dir.is_absolute() else root / args.data_dir
    rules_path = args.rules if args.rules.is_absolute() else root / args.rules
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    try:
        paths = sorted(data_dir.glob("*.json"))
        if not paths:
            raise ValueError(f"no event files found in {data_dir}")
        reports = build_classification_reports(load_events(paths, root), load_rule_set(rules_path))
        identity_fields = find_identity_fields(reports)
        if identity_fields:
            raise ValueError("forbidden identity fields found: " + ", ".join(identity_fields))
        write_classification_reports(reports, output_dir)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Classification report generation ERROR: {exc}")
        return 2

    summary = reports["index"]["summary"]
    print(
        "Classification reports generated: "
        f"decks={summary['total_decks']} unknown={summary['unknown']} "
        f"multiple={summary['multiple_matches']} conflicts={summary['conflicts']} "
        f"invalid={summary['invalid_decks']} subtypes={summary['selected_subtypes']}"
    )
    if args.strict and has_blocking_diagnostics(reports):
        print("Classification report strict validation FAIL: blocking diagnostics found")
        return 1
    print("Classification report validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
