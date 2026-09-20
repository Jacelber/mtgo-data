"""Render shared mana-identity metadata for the public frontend."""

from __future__ import annotations

import argparse
from pathlib import Path

from mtgmeta.mana_identity import write_rendered_mana_identities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    path = write_rendered_mana_identities(args.repository_root)
    print(f"Generated mana identities: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
