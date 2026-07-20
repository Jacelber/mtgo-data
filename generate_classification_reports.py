"""Generate sanitized MTGO classification diagnostic reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtgmeta.config import load_rule_set
from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.reports import (
    build_classification_reports,
    find_identity_fields,
    has_blocking_diagnostics,
    load_events,
    write_classification_reports,
)


FORMAT_ID = "standard"


def _resolve_override(root: Path, value: str | Path | None, default: Path) -> Path:
    if value is None:
        return default
    path = Path(value)
    return path if path.is_absolute() else root / path


def generate_reports(
    repository_root: str | Path,
    format_id: str,
    *,
    data_directory: str | Path | None = None,
    rules_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    registry_path: str | Path | None = None,
):
    """Generate reports only after explicit format and path authorization."""

    root = Path(repository_root).resolve()
    context = load_mtgo_context(
        root,
        format_id,
        "classification",
        registry_path=registry_path,
    )
    data_dir = _resolve_override(root, data_directory, context.paths["events"])
    rules = _resolve_override(root, rules_path, context.paths["rules"])
    output_dir = _resolve_override(root, output_directory, context.paths["reports"])
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise ValueError(f"no event files found in {data_dir}")
    reports = build_classification_reports(
        load_events(paths, root),
        load_rule_set(rules),
        format_id=format_id,
        source="mtgo",
    )
    identity_fields = find_identity_fields(reports)
    if identity_fields:
        raise ValueError("forbidden identity fields found: " + ", ".join(identity_fields))
    write_classification_reports(reports, output_dir)
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--format", dest="format_id", default=FORMAT_ID)
    parser.add_argument("--registry", type=Path, help="format registry override")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--rules", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail on conflicts or invalid decks")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    registry = args.registry
    if registry is not None and not registry.is_absolute():
        registry = root / registry
    try:
        reports = generate_reports(
            root,
            args.format_id,
            data_directory=args.data_dir,
            rules_path=args.rules,
            output_directory=args.output_dir,
            registry_path=registry,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Classification report generation ERROR: {exc}")
        return 2

    summary = reports["index"]["summary"]
    print(
        "Classification reports generated: "
        f"format={args.format_id} decks={summary['total_decks']} unknown={summary['unknown']} "
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
