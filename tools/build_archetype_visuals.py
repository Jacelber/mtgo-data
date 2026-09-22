"""Generate representative-card bindings from the maintained Landing selections."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata

import yaml


PUBLIC_STATISTICS_RANGES = (1, 4, 12)
JPEG_START_OF_FRAME_MARKERS = frozenset(
    (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)
)


def image_slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower().replace("'", "")).strip("-")


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"Representative image is not a JPEG: {path.as_posix()}")
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            raise ValueError(f"Invalid representative JPEG: {path.as_posix()}")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0x01, *range(0xD0, 0xDA)):
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in JPEG_START_OF_FRAME_MARKERS:
            if length < 7:
                break
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            if width and height:
                return width, height
            break
        offset += length
    raise ValueError(f"Cannot read representative JPEG dimensions: {path.as_posix()}")


def require_art_crop_shape(
    path: Path,
    *,
    format_id: str,
    identity: str,
    card: str,
) -> None:
    width, height = jpeg_dimensions(path)
    ratio = width / height
    if 0.65 <= ratio <= 0.8:
        raise ValueError(
            "Representative image must use an art crop, not a full-card portrait: "
            f"{format_id}/{identity} ({card}) {path.as_posix()} ({width}x{height})"
        )


def require_public_statistics_coverage(
    root: Path,
    format_id: str,
    identities: set[str],
) -> None:
    missing_by_range: list[str] = []
    for weeks in PUBLIC_STATISTICS_RANGES:
        path = root / f"stats/{format_id}/mtgo/range_{weeks}w.json"
        if not path.is_file():
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(
            str(row["id"])
            for row in document.get("archetypes", [])
            if row.get("id") != "unknown"
            and float(row.get("high_score_share") or 0) >= 0.03
            and row.get("id") not in identities
        )
        if missing:
            missing_by_range.append(f"{weeks}w={','.join(missing)}")
    if missing_by_range:
        raise ValueError(
            "Missing representative images for public statistics: "
            f"{format_id}; {'; '.join(missing_by_range)}"
        )


def generate(root: Path, format_id: str) -> None:
    config = yaml.safe_load((root / "configs/mtgo_landing_visuals.yaml").read_text(encoding="utf-8"))
    selected = config["formats"][format_id]
    source = root / "assets/js/phase8/archetype-visuals.js"
    text = source.read_text(encoding="utf-8")
    start = text.index("const representativeCards = Object.freeze({")
    end = text.index("\n});", start)
    block = text[start:end]
    entries = {**selected["parents"], **selected["subtypes"]}
    for identity in selected["allow_parent_fallback_for_subtypes"]:
        entries.setdefault(identity, selected["parents"][identity.split("/")[0]])
    require_public_statistics_coverage(root, format_id, set(entries))
    lines = [f"  {format_id}: Object.freeze({{"]
    for identity, cards in entries.items():
        lines.append(f"    {json.dumps(identity)}: Object.freeze([")
        for card in cards:
            relative = f"images/representative-cards/{format_id}/{image_slug(card)}.jpg"
            image_path = root / "assets" / relative
            if not image_path.is_file():
                raise ValueError(f"Missing representative image: assets/{relative}")
            require_art_crop_shape(
                image_path,
                format_id=format_id,
                identity=identity,
                card=card,
            )
            lines.append("      Object.freeze(" + json.dumps(
                {"name": card, "image": "../" + relative}, ensure_ascii=False) + "),")
        lines.append("    ]),")
    lines.append("  }),")
    replacement = "\n".join(lines)
    pattern = rf"^  {re.escape(format_id)}: Object\.freeze\(\{{\n.*?^  \}}\),"
    if re.search(pattern, block, re.M | re.S):
        block = re.sub(pattern, lambda _: replacement, block, flags=re.M | re.S)
    else:
        block += "\n" + replacement
    source.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", required=True)
    args = parser.parse_args()
    generate(args.repository_root, args.format)
