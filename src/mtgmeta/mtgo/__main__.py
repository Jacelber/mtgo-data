"""Explicit format-aware command line interface for the MTGO production pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from mtgmeta.config import FormatConfigError, load_format_registry

from . import DEFAULT_REGISTRY_PATH
from . import fetch, matchup, pickup, stats


DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def _month(value: str) -> tuple[int, int]:
    try:
        year_text, month_text = value.split("-", 1)
        year, month = int(year_text), int(month_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("month must use YYYY-MM") from exc
    if year < 2000 or month not in range(1, 13):
        raise argparse.ArgumentTypeError("month must use YYYY-MM")
    return year, month


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    parser.add_argument("--registry", type=Path, help="format registry override")
    parser.add_argument("--format", dest="format_id", required=True, help="explicit MTGO format ID")
    commands = parser.add_subparsers(dest="command", required=True)

    event_parser = commands.add_parser("fetch-events", help="fetch official MTGO events")
    event_parser.add_argument(
        "--month",
        action="append",
        type=_month,
        dest="months",
        help="calendar month in YYYY-MM; repeat for multiple months",
    )

    match_parser = commands.add_parser("fetch-matches", help="fetch Videre match records")
    match_parser.add_argument("event_ids", nargs="*", help="optional numeric event IDs")
    match_parser.add_argument("--force", action="store_true", help="replace existing event files")

    commands.add_parser("build-statistics", help="build rolling MTGO statistics")
    commands.add_parser("build-matchups", help="build Videre matchup statistics")

    pickup_parser = commands.add_parser("pickup", help="manage Weekly Pickup")
    pickup_commands = pickup_parser.add_subparsers(dest="pickup_command", required=True)
    candidate_parser = pickup_commands.add_parser("candidates", help="generate review candidates")
    candidate_parser.add_argument(
        "--if-absent",
        action="store_true",
        help="preserve an existing candidate file for the latest complete week",
    )
    pickup_commands.add_parser("publish", help="publish manually approved candidates")

    commands.add_parser("generate-metadata", help="generate MTGO metadata")
    report_parser = commands.add_parser(
        "classification-reports",
        help="generate de-identified classification diagnostics",
    )
    report_parser.add_argument("--strict", action="store_true", help="fail on blocking diagnostics")
    return parser


def _registry_path(root: Path, value: Path | None) -> Path:
    if value is None:
        return root / DEFAULT_REGISTRY_PATH
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def _run_fetch_events(args: argparse.Namespace, root: Path, registry: Path) -> int:
    summary = fetch.fetch_event_months(
        root,
        args.format_id,
        months=args.months,
        registry_path=registry,
    )
    print(
        "MTGO events: "
        f"format={args.format_id} candidates={summary['candidates']} fetched={summary['fetched']} "
        f"skipped={summary['skipped']} excluded={summary['excluded_no_playoff']} "
        f"failed={summary['failed']}"
    )
    for source, message in summary["errors"]:
        print(f"ERROR {source}: {message}", file=sys.stderr)
    return 1 if summary["failed"] else 0


def _run_fetch_matches(args: argparse.Namespace, root: Path, registry: Path) -> int:
    event_ids = args.event_ids or None
    summary = matchup.fetch_and_store_matches(
        root,
        args.format_id,
        event_ids=event_ids,
        force=args.force,
        registry_path=registry,
    )
    print(
        "Videre matches: "
        f"format={args.format_id} requested={summary['requested']} fetched={summary['fetched']} "
        f"skipped={summary['skipped']} not_found={summary['not_found']} failed={summary['failed']}"
    )
    for event_id, message in summary["errors"]:
        print(f"ERROR {event_id}: {message}", file=sys.stderr)
    return 1 if summary["failed"] else 0


def _run_statistics(args: argparse.Namespace, root: Path, registry: Path) -> int:
    written = stats.build_all_stats(root, args.format_id, registry_path=registry)
    if not written:
        print(f"No complete MTGO event week is available for {args.format_id}.")
        return 0
    print(f"MTGO statistics: format={args.format_id} output={written['index.json'].parent}")
    return 0


def _run_matchups(args: argparse.Namespace, root: Path, registry: Path) -> int:
    written, statistics = matchup.build_all_matchups(root, args.format_id, registry_path=registry)
    if not written:
        print(f"No complete MTGO event week is available for {args.format_id}.")
        return 0
    counts = ", ".join(f"{weeks}w={values['counted']}" for weeks, values in statistics.items())
    print(f"MTGO matchups: format={args.format_id} output={written['matchup_index.json'].parent} {counts}")
    return 0


def _run_pickup(args: argparse.Namespace, root: Path, registry: Path) -> int:
    if args.pickup_command == "candidates":
        result = pickup.generate_candidates(
            root,
            args.format_id,
            registry_path=registry,
            preserve_existing=args.if_absent,
        )
        if result is None:
            print(f"No complete MTGO event week is available for {args.format_id}.")
        elif result["skipped_existing"]:
            print(f"Weekly Pickup candidates preserved: {result['candidate_path']}")
        else:
            print(f"Weekly Pickup candidates written: {result['candidate_path']}")
        return 0
    result = pickup.publish(root, args.format_id, registry_path=registry)
    if result is None:
        print("No manually approved Weekly Pickup candidates are available.")
    else:
        print(f"Weekly Pickup published: {result['published_path']}")
    return 0


def _run_metadata(args: argparse.Namespace, root: Path, registry: Path) -> int:
    destination = pickup.generate_metadata(root, args.format_id, registry_path=registry)
    print(f"MTGO metadata: format={args.format_id} output={destination}")
    return 0


def _run_reports(args: argparse.Namespace, root: Path, registry: Path) -> int:
    from generate_classification_reports import generate_reports
    from mtgmeta.reports import has_blocking_diagnostics

    reports = generate_reports(root, args.format_id, registry_path=registry)
    summary = reports["index"]["summary"]
    print(
        "Classification reports: "
        f"format={args.format_id} decks={summary['total_decks']} unknown={summary['unknown']} "
        f"conflicts={summary['conflicts']} invalid={summary['invalid_decks']}"
    )
    if args.strict and has_blocking_diagnostics(reports):
        print("Classification report strict validation FAIL: blocking diagnostics found")
        return 1
    print("Classification report validation PASS")
    return 0


RUNNERS = {
    "fetch-events": _run_fetch_events,
    "fetch-matches": _run_fetch_matches,
    "build-statistics": _run_statistics,
    "build-matchups": _run_matchups,
    "pickup": _run_pickup,
    "generate-metadata": _run_metadata,
    "classification-reports": _run_reports,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    registry = _registry_path(root, args.registry)
    try:
        # Every command validates the explicit format before its runner can access
        # a network client or create an output directory.
        format_registry = load_format_registry(registry)
        if args.command == "fetch-events":
            format_registry.require_mtgo_event_collection(args.format_id)
        else:
            format_registry.require_mtgo(args.format_id)
        return RUNNERS[args.command](args, root, registry)
    except (
        FormatConfigError,
        fetch.MTGOFetchError,
        fetch.MTGOParseError,
        fetch.MTGOStorageError,
        matchup.MTGOMatchupError,
        pickup.MTGOPickupError,
        stats.MTGOStatisticsError,
        OSError,
        ValueError,
    ) as exc:
        print(f"MTGO command ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
