"""Export complete weekly classification review evidence from retained inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtgmeta.weekly_review import (  # noqa: E402
    build_melee_review,
    build_mtgo_weekly_review,
    build_v2_completion_record,
    melee_record_detail,
    mtgo_record_detail,
)


def _write_or_print(value: object, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if output is None:
        print(text, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    mtgo = subparsers.add_parser("mtgo")
    mtgo.add_argument("--week", required=True)
    mtgo.add_argument("--format", dest="format_id", required=True)
    mtgo.add_argument("--output", type=Path)

    melee = subparsers.add_parser("melee")
    melee.add_argument("--format", dest="format_id", required=True)
    melee.add_argument("--event-id", required=True)
    melee.add_argument("--output", type=Path)

    detail = subparsers.add_parser("mtgo-detail")
    detail.add_argument("--format", dest="format_id", required=True)
    detail.add_argument("--event-id", required=True)
    detail.add_argument("--rank", required=True, type=int)
    detail.add_argument("--output", type=Path)

    melee_detail = subparsers.add_parser("melee-detail")
    melee_detail.add_argument("--format", dest="format_id", required=True)
    melee_detail.add_argument("--event-id", required=True)
    melee_detail.add_argument("--participant-id", required=True)
    melee_detail.add_argument("--output", type=Path)

    completion = subparsers.add_parser("completion")
    completion.add_argument("--week", required=True)
    completion.add_argument("--standard-review", required=True, type=Path)
    completion.add_argument("--modern-review", required=True, type=Path)
    completion.add_argument("--standard-landing-digest", required=True)
    completion.add_argument("--modern-landing-digest", required=True)
    completion.add_argument("--completed-on", required=True)
    completion.add_argument("--evidence", required=True)
    completion.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    try:
        if args.command == "mtgo":
            value = build_mtgo_weekly_review(root, args.format_id, args.week)
        elif args.command == "melee":
            value = build_melee_review(root, args.format_id, args.event_id)
        elif args.command == "mtgo-detail":
            value = mtgo_record_detail(root, args.format_id, args.event_id, args.rank)
        elif args.command == "melee-detail":
            value = melee_record_detail(
                root,
                args.format_id,
                args.event_id,
                args.participant_id,
            )
        else:
            reviews = [
                json.loads(args.standard_review.read_text(encoding="utf-8")),
                json.loads(args.modern_review.read_text(encoding="utf-8")),
            ]
            value = build_v2_completion_record(
                reviews,
                week_id=args.week,
                completed_on=args.completed_on,
                evidence=args.evidence,
                landing_content_digests={
                    "standard": args.standard_landing_digest,
                    "modern": args.modern_landing_digest,
                },
            )
        _write_or_print(value, args.output)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Weekly classification review ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
