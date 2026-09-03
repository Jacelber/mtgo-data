"""Compare accepted and candidate rules on the complete retained format corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtgmeta.classifier_impact import compare_classifier_impact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--format", dest="format_id", required=True)
    parser.add_argument("--accepted-rules", type=Path, required=True)
    parser.add_argument("--candidate-rules", type=Path, required=True)
    parser.add_argument("--expected-changes", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = compare_classifier_impact(
            args.repository_root,
            args.format_id,
            args.accepted_rules,
            args.candidate_rules,
            expected_changes_path=args.expected_changes,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Classifier impact ERROR: {exc}")
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    return 0 if result["status"] in {"NO_RULE_CHANGE", "ACCEPTED_CHANGE_SET"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
