"""Build an offline classifier fact snapshot from a pinned Scryfall Oracle export.

No network lookup occurs here or during classification. The required-name list
contains card names only; it can be collected from retained source inputs/rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from mtgmeta.classifier_fact_builder import build


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--oracle-gzip", type=Path, required=True)
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument("--complete", action="store_true", help="Import the complete constructed card library")
    p.add_argument("--preserve-facts", type=Path, help="Keep existing reviewed entities unchanged during initial expansion")
    selection.add_argument("--required-names", type=Path,
                           help="JSON list of names to cover, including newly observed names")
    selection.add_argument("--existing-facts", type=Path,
                           help="Reproduce an existing snapshot's entity coverage")
    p.add_argument("--source-uri", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    required = (json.loads(args.required_names.read_text()) if args.required_names
                else [card["key"] for card in json.loads(args.existing_facts.read_text())["cards"]] if args.existing_facts else None)
    result = build(args.oracle_gzip, required, args.source_uri,
                   existing=json.loads(args.preserve_facts.read_bytes()) if args.preserve_facts else None)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(result['cards'])} cards written to {args.output}")


if __name__ == "__main__":
    main()
