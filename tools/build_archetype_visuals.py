"""Generate representative-card bindings from the maintained Landing selections."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata

import yaml


def image_slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower().replace("'", "")).strip("-")


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
    lines = [f"  {format_id}: Object.freeze({{"]
    for identity, cards in entries.items():
        lines.append(f"    {json.dumps(identity)}: Object.freeze([")
        for card in cards:
            relative = f"images/representative-cards/{format_id}/{image_slug(card)}.jpg"
            if not (root / "assets" / relative).is_file():
                raise ValueError(f"Missing representative image: assets/{relative}")
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
