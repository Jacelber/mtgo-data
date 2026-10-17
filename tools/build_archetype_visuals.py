"""Inspect and generate the shared statistics/Landing representative bindings."""
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


def inspect_statistics(root: Path, format_id: str, *, weeks=PUBLIC_STATISTICS_RANGES) -> dict:
    """Read the chart's actual visible union, without selecting cards or writing files."""
    required = {}
    for window in weeks:
        path = root / f"stats/{format_id}/mtgo/range_{window}w.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        for row in document["archetypes"]:
            if row["id"] != "unknown" and float(row.get("high_score_share") or 0) >= 0.03:
                required.setdefault(row["id"], []).append(window)
    config_path = root / "configs/mtgo_landing_visuals.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    selected = config.get("formats", {}).get(format_id, {})
    entries = {**selected.get("parents", {}), **selected.get("subtypes", {})}
    for identity in selected.get("allow_parent_fallback_for_subtypes", []):
        entries.setdefault(identity, selected.get("parents", {}).get(identity.split("/")[0], []))
    rows = inspect_cards(root, format_id, {identity: entries.get(identity, []) for identity in required})
    for row in rows:
        row["windows"] = required[row["identity"]]
    return {"format": format_id, "rows": rows, "ready": not any(row["problems"] for row in rows)}


def inspect_cards(root: Path, format_id: str, choices: dict) -> list[dict]:
    """Check the actual shared renderer against independently supplied choices."""
    path = root / "assets/js/phase8/archetype-visuals.js"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    section = text.partition("const representativeCards = Object.freeze({")[2]
    match = re.search(rf"^  {re.escape(format_id)}: Object\.freeze\(\{{\n(.*?)^  \}}\),", section, re.M | re.S)
    groups = dict(re.findall(r'^    "([^"]+)": Object\.freeze\(\[\n(.*?)^    \]\),', match[1], re.M | re.S)) if match else {}
    rows = []
    for identity, cards in sorted(choices.items()):
        rendered = [json.loads(value) for value in re.findall(r'Object\.freeze\((\{[^\n]+\})\)', groups.get(identity, ""))]
        problems, resources = [], []
        if (not isinstance(cards, list) or len(cards) != 2
                or any(not isinstance(card, str) or not card.strip() for card in cards)
                or len(set(cards)) != 2):
            problems.append("two_ordered_cards_required")
        else:
            expected = [{"name": card, "image": f"../images/representative-cards/{format_id}/{image_slug(card)}.jpg"} for card in cards]
            if rendered != expected:
                problems.append("rendered_binding_differs")
            for card, item in zip(cards, expected):
                relative = "assets/" + item["image"][3:]
                resources.append(relative)
                try:
                    require_art_crop_shape(root / relative, format_id=format_id, identity=identity, card=card)
                except (OSError, ValueError) as error:
                    problems.append(str(error))
        rows.append({"identity": identity, "cards": cards,
                     "rendered_cards": rendered, "resources": resources, "problems": problems})
    return rows


def require_public_representatives(root: Path, selected: set[str]) -> None:
    """Validate consumer bindings and both shared images before public packaging."""
    formats = {}
    for relative in sorted(selected):
        match = re.fullmatch(r"stats/([^/]+)/mtgo/range_(1|4|12)w\.json", relative)
        if match:
            formats.setdefault(match[1], []).append(int(match[2]))
    failures = []
    subjects = []
    for format_id, weeks in formats.items():
        subjects.extend((format_id, f"{row['windows']}w", row)
                        for row in inspect_statistics(root, format_id, weeks=weeks)["rows"])
    # A retained Landing can display categories absent from all current ranges.
    # Its accepted names/order, rather than this week's config, are authoritative.
    for relative in sorted(selected):
        match = re.fullmatch(r"stats/([^/]+)/mtgo/landing/current\.json", relative)
        if match:
            page = json.loads((root / relative).read_text(encoding="utf-8"))
            choices = {row["archetype_id"]: [card["name"] for card in row["key_cards"]]
                       for row in page.get("environment", {}).get("rows", [])}
            subjects.extend((match[1], "retained Landing", row)
                            for row in inspect_cards(root, match[1], choices))
    for format_id, consumer, row in subjects:
        problems = row["problems"] + ["image_not_in_public_package: " + p for p in row["resources"] if p not in selected]
        if "assets/js/phase8/archetype-visuals.js" not in selected:
            problems.append("rendered_binding_not_in_public_package")
        if problems:
            failures.append(f"{format_id}/{row['identity']} ({consumer}): " + "; ".join(problems))
    if failures:
        raise ValueError("Shared representatives incomplete before data delivery: " + " | ".join(failures))


def generate(root: Path, format_id: str, *, identities: set[str] | None = None, config_override=None) -> None:
    config = config_override if config_override is not None else yaml.safe_load((root / "configs/mtgo_landing_visuals.yaml").read_text(encoding="utf-8"))
    selected = config["formats"][format_id]
    source = root / "assets/js/phase8/archetype-visuals.js"
    text = source.read_text(encoding="utf-8")
    start = text.index("const representativeCards = Object.freeze({")
    end = text.index("\n});", start)
    block = text[start:end]
    entries = {**selected["parents"], **selected["subtypes"]}
    for identity in selected["allow_parent_fallback_for_subtypes"]:
        entries.setdefault(identity, selected["parents"][identity.split("/")[0]])
    if identities is None:
        require_public_statistics_coverage(root, format_id, set(entries))
    else:
        if not identities <= entries.keys():
            raise ValueError("Selected representative identity is not configured")
        entries = {key: value for key, value in entries.items() if key in identities}
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
    if identities is not None:
        old = re.search(pattern, block, re.M | re.S)
        if old is None:
            raise ValueError("Selected format visual section is absent")
        selected_block = old[0]
        for identity in entries:
            entry_pattern = rf'^    "{re.escape(identity)}": Object\.freeze\(\[\n.*?^    \]\),'
            entry = re.search(entry_pattern, replacement, re.M | re.S)[0]
            if re.search(entry_pattern, selected_block, re.M | re.S):
                selected_block = re.sub(entry_pattern, lambda _: entry, selected_block, flags=re.M | re.S)
            else:
                selected_block = selected_block[:-5] + entry + "\n  }),"
        replacement = selected_block
    if re.search(pattern, block, re.M | re.S):
        block = re.sub(pattern, lambda _: replacement, block, flags=re.M | re.S)
    else:
        block += "\n" + replacement
    temporary = source.with_suffix(".js.new")
    temporary.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")
    temporary.replace(source)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", required=True)
    parser.add_argument("--inspect", action="store_true", help="Read-only 1/4/12-week shared representative inventory")
    parser.add_argument("--identity", action="append", help="Generate only these confirmed changed identities; repeat as needed")
    args = parser.parse_args()
    if args.inspect:
        if args.identity:
            parser.error("--inspect always covers all three public windows; do not filter identities")
        print(json.dumps(inspect_statistics(args.repository_root, args.format), ensure_ascii=False, indent=2))
    else:
        generate(args.repository_root, args.format, identities=set(args.identity) if args.identity else None)
