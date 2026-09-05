"""Generate the format-first public product availability catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

from mtgmeta.public_contract import versioned

from .config import (
    REQUIRED_MTGO_PRODUCT_CAPABILITIES,
    FormatDefinition,
    load_format_registry,
)


PRODUCTS = (
    ("mtgo-statistics", "mtgo", "meta.json"),
    ("mtgo-matchups", "mtgo", "matchup_index.json"),
    ("mtgo-top8", "mtgo", "top8/index.json"),
    ("mtgo-landing", "mtgo", "landing/current.json"),
    ("tabletop-major-events", "melee", "index.json"),
)
DEFAULT_MTGO_PRODUCT_ID = "mtgo-landing"
REQUIRED_MTGO_PRODUCT_IDS = frozenset(
    product_id for product_id, source, _suffix in PRODUCTS if source == "mtgo"
)


def _product_path(format_id: str, source: str, suffix: str) -> Path:
    return Path("stats") / format_id / source / Path(suffix)


def require_complete_public_format(
    repository_root: str | Path,
    definition: FormatDefinition,
) -> FormatDefinition:
    """Resolve complete-public eligibility from registry state and product files."""

    root = Path(repository_root).resolve()
    if not definition.public:
        raise ValueError(
            f"format {definition.id!r} is not a complete public MTGO format: "
            "registry public is false"
        )
    if definition.state != "executable" or not definition.mtgo.enabled:
        raise ValueError(f"public format {definition.id!r} must be executable")
    if not REQUIRED_MTGO_PRODUCT_CAPABILITIES <= definition.mtgo.capabilities:
        raise ValueError(
            f"public format {definition.id!r} is missing required MTGO capabilities"
        )
    missing = sorted(
        product_id
        for product_id, source, suffix in PRODUCTS
        if product_id in REQUIRED_MTGO_PRODUCT_IDS
        and not (root / _product_path(definition.id, source, suffix)).is_file()
    )
    if missing:
        raise ValueError(
            f"public format {definition.id!r} is missing required MTGO products: "
            + ", ".join(missing)
        )
    return definition


def resolve_complete_public_format(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
) -> FormatDefinition:
    root = Path(repository_root).resolve()
    registry = load_format_registry(
        registry_path or root / "configs" / "formats.yaml"
    )
    return require_complete_public_format(root, registry.get(format_id))


def complete_public_formats(
    repository_root: str | Path,
    *,
    registry_path: str | Path | None = None,
) -> tuple[FormatDefinition, ...]:
    root = Path(repository_root).resolve()
    registry = load_format_registry(
        registry_path or root / "configs" / "formats.yaml"
    )
    return tuple(
        require_complete_public_format(root, definition)
        for definition in registry.formats
        if definition.public
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
        if definition.public:
            require_complete_public_format(root, definition)
        products = []
        for product_id, source, suffix in PRODUCTS:
            relative = _product_path(definition.id, source, suffix)
            available = definition.public and (root / relative).is_file()
            products.append(
                {
                    "id": product_id,
                    "available": available,
                    "path": relative.as_posix() if available else None,
                }
            )
        available_ids = [item["id"] for item in products if item["available"]]
        default_product_id = (
            DEFAULT_MTGO_PRODUCT_ID
            if DEFAULT_MTGO_PRODUCT_ID in available_ids
            else (available_ids[0] if available_ids else None)
        )
        formats.append(
            {
                "id": definition.id,
                "display_name": definition.display_name,
                "state": definition.state,
                "default_product_id": default_product_id,
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
