"""Explicit format-aware command line interface for the MTGO production pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from mtgmeta.config import DisabledFormatError, FormatConfigError, load_format_registry

from . import DEFAULT_REGISTRY_PATH
from . import (
    completeness,
    fetch,
    landing,
    landing_editorial,
    landing_screening,
    matchup,
    metadata,
    stats,
    top8,
)


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
TRANSIENT_FAILURE_EXIT_CODE = 75


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
    refresh_parser = commands.add_parser(
        "refresh-event",
        help="replace one retained official event after identity verification",
    )
    refresh_parser.add_argument("url", help="official MTGO decklist URL")

    match_parser = commands.add_parser("fetch-matches", help="fetch Videre match records")
    match_parser.add_argument("event_ids", nargs="*", help="optional numeric event IDs")
    match_parser.add_argument("--force", action="store_true", help="replace existing event files")

    commands.add_parser("build-statistics", help="build rolling MTGO statistics")
    commands.add_parser(
        "build-top8",
        help="build retained complete-week MTGO Top 8 data",
    )
    commands.add_parser("build-matchups", help="build Videre matchup statistics")
    commands.add_parser(
        "build-completeness",
        help="build range-specific MTGO source-completeness data",
    )
    landing_parser = commands.add_parser(
        "build-landing",
        help="build the latest-only MTGO Landing document",
    )
    landing_parser.add_argument("--week", help="explicit closed review week")
    landing_parser.add_argument(
        "--private-output",
        type=Path,
        help="build a private format into an external directory",
    )
    landing_parser.add_argument("--review-directory", type=Path)
    landing_parser.add_argument("--name-catalog", type=Path)
    landing_parser.add_argument("--visuals", type=Path)
    review_parser = commands.add_parser(
        "landing-review",
        help="manage the private Landing editorial review source",
    )
    review_commands = review_parser.add_subparsers(
        dest="landing_review_command", required=True
    )
    prepare_parser = review_commands.add_parser(
        "prepare", help="prepare private Landing screening candidates"
    )
    prepare_parser.add_argument(
        "--if-absent",
        action="store_true",
        help="preserve an existing candidate for the latest complete week",
    )
    prepare_parser.add_argument("--week", help="explicit closed review week")
    validate_parser = review_commands.add_parser(
        "validate-xlsx",
        help="validate a Landing workbook stage without importing it",
    )
    validate_parser.add_argument("workbook", type=Path, help="XLSX review carrier")
    validate_parser.add_argument(
        "--stage",
        required=True,
        choices=("chinese", "bilingual"),
        help="content stage whose machine contract must be complete",
    )
    validate_parser.add_argument(
        "--expected-sha256",
        required=True,
        help="immutable workbook SHA-256 submitted for this stage",
    )
    import_parser = review_commands.add_parser(
        "import-xlsx", help="import an explicitly approved Landing workbook"
    )
    import_parser.add_argument("workbook", type=Path, help="accepted XLSX carrier")
    import_parser.add_argument(
        "--expected-sha256",
        required=True,
        help="accepted immutable workbook SHA-256",
    )

    commands.add_parser("generate-metadata", help="generate MTGO metadata")
    commands.add_parser(
        "generate-hierarchy",
        help="generate the maintained archetype hierarchy catalog",
    )
    report_parser = commands.add_parser(
        "classification-reports",
        help="generate de-identified classification diagnostics",
    )
    report_parser.add_argument(
        "--output-dir",
        type=Path,
        help="write reports to a disposable or alternate directory",
    )
    report_parser.add_argument("--strict", action="store_true", help="fail on blocking diagnostics")
    publication_parser = commands.add_parser("publication", help="inspect or prepare the Owner-reviewed MTGO boundary")
    publication_commands = publication_parser.add_subparsers(dest="publication_command", required=True)
    publication_commands.add_parser("inspect", help="read public and pending event membership")
    prepare = publication_commands.add_parser("prepare-review", help="write private full classification material")
    prepare.add_argument("--week", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    accept = publication_commands.add_parser("admission-record", help="prepare a data-admission record after exact Owner acceptance; never marks completion")
    accept.add_argument("--week", required=True)
    accept.add_argument("--expected-review-digest", required=True)
    accept.add_argument("--accepted-on", required=True)
    accept.add_argument("--evidence", required=True)
    accept.add_argument("--output", type=Path, required=True)
    stage = publication_commands.add_parser("stage", help="generate and validate a format in isolation; default is no materialization")
    stage.add_argument("--include-landing", action="store_true")
    stage.add_argument("--execute", action="store_true")
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
        f"deferred={summary['deferred_incomplete']} "
        f"failed={summary['failed']} transient={summary['transient_failed']}"
    )
    for source, message in summary["warnings"]:
        print(f"DEFERRED {source}: {message}", file=sys.stderr)
    for source, message in summary["errors"]:
        print(f"ERROR {source}: {message}", file=sys.stderr)
    if not summary["failed"]:
        return 0
    if summary["failed"] == summary["transient_failed"]:
        return TRANSIENT_FAILURE_EXIT_CODE
    return 1


def _run_refresh_event(args: argparse.Namespace, root: Path, registry: Path) -> int:
    destination = fetch.refresh_existing_event(
        root,
        args.format_id,
        args.url,
        registry_path=registry,
    )
    print(f"MTGO event refreshed: format={args.format_id} output={destination}")
    return 0


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
        f"skipped={summary['skipped']} not_found={summary['not_found']} "
        f"source_unavailable={summary['source_unavailable']} failed={summary['failed']}"
    )
    for event_id, message in summary["warnings"]:
        print(f"SOURCE UNAVAILABLE {event_id}: {message}", file=sys.stderr)
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


def _run_top8(args: argparse.Namespace, root: Path, registry: Path) -> int:
    written = top8.build_all_top8(root, args.format_id, registry_path=registry)
    print(
        f"MTGO Top 8: format={args.format_id} "
        f"output={written['index.json'].parent}"
    )
    return 0


def _run_completeness(
    args: argparse.Namespace,
    root: Path,
    registry: Path,
) -> int:
    written = completeness.build_all_completeness(
        root,
        args.format_id,
        registry_path=registry,
    )
    if not written:
        print(f"No complete MTGO event week is available for {args.format_id}.")
        return 0
    print(
        f"MTGO completeness: format={args.format_id} "
        f"output={written['index.json'].parent}"
    )
    return 0


def _run_landing(args: argparse.Namespace, root: Path, registry: Path) -> int:
    result = landing.generate(
        root,
        args.format_id,
        registry_path=registry,
        review_directory=args.review_directory,
        name_catalog_path=args.name_catalog,
        output_directory=args.private_output,
        visuals_path=args.visuals,
        private=args.private_output is not None,
        review_week=args.week,
    )
    if result["status"] in {"stale_review_required", "summary_review_required"}:
        reason = (
            "explicit summary review"
            if result["status"] == "summary_review_required"
            else "explicit re-review"
        )
        print(
            f"MTGO Landing preserved for {reason}: "
            f"format={args.format_id} output={result['path']}"
        )
    else:
        print(
            "MTGO Landing: "
            f"format={args.format_id} week={result['week']} "
            f"features={result['feature_count']} summary={result['summary_count']} "
            f"output={result['path']}"
        )
    return 0


def _run_landing_review(args: argparse.Namespace, root: Path, registry: Path) -> int:
    if args.landing_review_command == "prepare":
        result = landing_screening.prepare_candidates(
            root,
            args.format_id,
            registry_path=registry,
            preserve_existing=args.if_absent,
            week=args.week,
        )
        if result is None:
            print(f"No complete MTGO event week is available for {args.format_id}.")
        elif result.get("review_required"):
            print(
                "Landing screening candidates need review after source events changed: "
                f"{result['candidate_path']}"
            )
        elif result["skipped_existing"]:
            print(f"Landing screening candidates preserved: {result['candidate_path']}")
        else:
            print(f"Landing screening candidates written: {result['candidate_path']}")
        return 0

    workbook = (
        args.workbook.resolve()
        if args.workbook.is_absolute()
        else (root / args.workbook).resolve()
    )
    if args.landing_review_command == "validate-xlsx":
        result = landing_editorial.validate_review_workbook(
            root,
            workbook,
            stage=args.stage,
            expected_sha256=args.expected_sha256,
            formats={args.format_id},
        )
        print(
            "MTGO Landing review validated: "
            f"format={args.format_id} stage={result['stage']} "
            f"reviews={result['review_count']} features={result['feature_count']} "
            f"copy={result['copy_count']} names={result['name_count']}"
        )
        return 0
    result = landing_editorial.import_review_workbook(
        root,
        workbook,
        expected_sha256=args.expected_sha256,
        formats={args.format_id},
    )
    print(
        "MTGO Landing review imported: "
        f"format={args.format_id} reviews={result['review_count']} "
        f"features={result['feature_count']} copy={result['copy_count']} "
        f"names={result['name_count']}"
    )
    return 0


def _run_metadata(args: argparse.Namespace, root: Path, registry: Path) -> int:
    destination = metadata.generate_metadata(root, args.format_id, registry_path=registry)
    print(f"MTGO metadata: format={args.format_id} output={destination}")
    return 0


def _run_hierarchy(args: argparse.Namespace, root: Path, registry: Path) -> int:
    destination = metadata.generate_hierarchy_catalog(
        root,
        args.format_id,
        registry_path=registry,
    )
    names_destination = landing_editorial.generate_public_name_contract(
        root,
        args.format_id,
    )
    print(f"MTGO hierarchy: format={args.format_id} output={destination}")
    print(f"Classifier names: format={args.format_id} output={names_destination}")
    return 0


def _run_reports(args: argparse.Namespace, root: Path, registry: Path) -> int:
    from mtgmeta.classification_reports_cli import generate_reports
    from mtgmeta.reports import has_blocking_diagnostics

    reports = generate_reports(
        root,
        args.format_id,
        output_directory=args.output_dir,
        registry_path=registry,
    )
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


def _run_publication(args: argparse.Namespace, root: Path, registry: Path) -> int:
    import json
    from . import publication
    if args.publication_command == "inspect":
        print(json.dumps(publication.inspect(root, args.format_id), indent=2))
    elif args.publication_command == "stage":
        print(json.dumps(publication.stage_publication(root, args.format_id,
            include_landing=args.include_landing, execute=args.execute), indent=2))
    elif args.publication_command == "prepare-review":
        print(publication.prepare_review(root, args.format_id, args.week, args.output))
    else:
        publication.require_private_output(root, args.output)
        record = publication.acceptance_record(root, args.format_id, args.week,
            expected_review_digest=args.expected_review_digest,
            accepted_on=args.accepted_on, evidence=args.evidence)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(args.output)
    return 0


RUNNERS = {
    "publication": _run_publication,
    "fetch-events": _run_fetch_events,
    "refresh-event": _run_refresh_event,
    "fetch-matches": _run_fetch_matches,
    "build-statistics": _run_statistics,
    "build-top8": _run_top8,
    "build-completeness": _run_completeness,
    "build-landing": _run_landing,
    "landing-review": _run_landing_review,
    "build-matchups": _run_matchups,
    "generate-metadata": _run_metadata,
    "generate-hierarchy": _run_hierarchy,
    "classification-reports": _run_reports,
}

COMMAND_CAPABILITIES = {
    "publication": "classification",
    "fetch-matches": "matchup_statistics",
    "build-statistics": "event_statistics",
    "build-top8": "weekly_top8",
    "build-completeness": "completeness_reporting",
    "build-landing": "landing_generation",
    "landing-review": "landing_generation",
    "build-matchups": "matchup_statistics",
    "generate-metadata": "metadata_generation",
    "generate-hierarchy": "catalog_generation",
    "classification-reports": "classification",
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    registry = _registry_path(root, args.registry)
    try:
        # Every command validates the explicit format before its runner can access
        # a network client or create an output directory.
        format_registry = load_format_registry(registry)
        if args.command in {"fetch-events", "refresh-event"}:
            format_registry.require_mtgo_event_collection(args.format_id)
        else:
            definition = format_registry.require_mtgo(args.format_id)
            capability = COMMAND_CAPABILITIES[args.command]
            if capability not in definition.mtgo.capabilities:
                raise DisabledFormatError(
                    f"MTGO format {args.format_id!r} does not support {capability!r}"
                )
        return RUNNERS[args.command](args, root, registry)
    except (
        FormatConfigError,
        fetch.MTGOFetchError,
        fetch.MTGOParseError,
        fetch.MTGOStorageError,
        completeness.MTGOCompletenessError,
        landing.MTGOLandingError,
        landing_editorial.MTGOLandingEditorialError,
        matchup.MTGOMatchupError,
        landing_screening.MTGOLandingScreeningError,
        stats.MTGOStatisticsError,
        top8.MTGOTop8Error,
        OSError,
        ValueError,
    ) as exc:
        print(f"MTGO command ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
