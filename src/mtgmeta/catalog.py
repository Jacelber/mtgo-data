"""Generate the format-first public product availability catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

from mtgmeta.public_contract import versioned

from .config import load_format_registry


PRODUCTS = (
    ("mtgo-statistics", "mtgo", "meta.json"),
    ("mtgo-matchups", "mtgo", "matchup_index.json"),
    ("mtgo-top8", "mtgo", "top8/index.json"),
    ("mtgo-landing", "mtgo", "landing/current.json"),
    ("tabletop-major-events", "melee", "index.json"),
    ("weekly-pickup", "mtgo", "pickup/index.json"),
)


def build_catalog(
    repository_root: str | Path,
    *,
    generated_at: datetime | str | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    registry = load_format_registry(
        registry_path or root / "configs" / "formats.yaml"
    )
    if generated_at is None:
        generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elif isinstance(generated_at, datetime):
        generated = generated_at.isoformat(timespec="seconds")
    else:
        generated = generated_at
    formats = []
    for definition in registry.formats:
        products = []
        for product_id, source, suffix in PRODUCTS:
            relative = Path("stats") / definition.id / source / Path(suffix)
            available = definition.public and (root / relative).is_file()
            products.append(
                {
                    "id": product_id,
                    "available": available,
                    "path": relative.as_posix() if available else None,
                }
            )
        available_ids = [item["id"] for item in products if item["available"]]
        formats.append(
            {
                "id": definition.id,
                "display_name": definition.display_name,
                "state": definition.state,
                "default_product_id": available_ids[0] if available_ids else None,
                "products": products,
            }
        )
    return versioned(
        {
            "document_type": "consumer_catalog",
            "generated": generated,
            "formats": formats,
        }
    )


def write_catalog(
    repository_root: str | Path,
    *,
    generated_at: datetime | str | None = None,
    registry_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    root = Path(repository_root).resolve()
    destination = Path(output_path) if output_path else root / "stats" / "catalog.json"
    document = build_catalog(
        root,
        generated_at=generated_at,
        registry_path=registry_path,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    destination = write_catalog(args.root, output_path=args.output)
    print(f"Generated consumer catalog: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
