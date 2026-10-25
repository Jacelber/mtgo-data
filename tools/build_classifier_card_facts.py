"""Build an offline classifier fact snapshot from a pinned Scryfall Oracle export.

No network lookup occurs here or during classification. The required-name list
contains card names only; it can be collected from retained source inputs/rules.
"""

from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mtgmeta.card_names import CARD_ALIASES, normalize_card_name
from mtgmeta.classifier_cards import matching_face_entities


def spellings(card: dict) -> set[str]:
    names = {card["name"]}
    faces = card.get("card_faces", [])
    if faces:
        names.update(face["name"] for face in faces)
        if card["layout"] == "split":
            names.add("/".join(face["name"] for face in faces))
    return names


def build(source: Path, required: list[str], source_uri: str) -> dict:
    index: dict[str, list[dict]] = {}
    by_oracle = {}
    with gzip.open(source, "rt", encoding="utf-8") as stream:
        for line in stream:
            card = json.loads(line)
            if not card.get("oracle_id") or card.get("layout") in {
                "art_series",
                "token",
                "double_faced_token",
                "emblem",
                "front_card",
            }:
                continue
            by_oracle[card["oracle_id"]] = card
            for name in spellings(card):
                index.setdefault(name, []).append(card)
    # A back/prepared face can share a standalone card's name. Prefer the
    # standalone entity; for duplicate paper-only variants prefer MTGO facts.
    for name, choices in index.items():
        exact = [
            c
            for c in choices
            if c["name"] == name or c.get("card_faces", [{}])[0].get("name") == name
        ]
        choices = exact or choices
        online = [c for c in choices if "mtgo" in c.get("games", [])]
        index[name] = online or choices
    alias_artifact = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "src/mtgmeta/data/om1_spm_aliases.json"
        ).read_text()
    )
    for item in alias_artifact["mappings"]:
        card = by_oracle.get(item.get("oracle_id"))
        if card:
            for name in [item["alias"], item["canonical_name"]]:
                index[name] = [card]
    # Selection accepts the same complete-face notation as runtime, without
    # expanding the stored snapshot's names or guessing from a single face.
    pairs = {}
    for spelling, choices in index.items():
        for card in choices:
            faces = card.get("card_faces", [])
            if spelling == card["name"] and len(faces) == 2:
                pair = tuple(normalize_card_name(face["name"]) for face in faces)
                pairs.setdefault(pair, set()).add(card["oracle_id"])
    pairs = {pair: frozenset(ids) for pair, ids in pairs.items()}
    selected = {}
    unresolved = []
    for name in required:
        choices = index.get(name.strip(), index.get(normalize_card_name(name), []))
        if not choices:
            choices = [by_oracle[oracle] for oracle in matching_face_entities(name, pairs)]
        if len(choices) != 1:
            unresolved.append(name)
        else:
            card = choices[0]
            selected[card["oracle_id"]] = card
    if unresolved:
        raise ValueError(f"unresolved or ambiguous required names: {unresolved}")
    fields = ("name", "mana_cost", "type_line", "oracle_text", "colors")
    alias_names = set(CARD_ALIASES) | set(CARD_ALIASES.values())
    names_by_oracle = {}
    for name in alias_names:
        choices = index.get(name, [])
        if len(choices) == 1:
            names_by_oracle.setdefault(choices[0]["oracle_id"], set()).add(name)
    cards = []
    for card in sorted(selected.values(), key=lambda c: c["name"]):
        row = {k: card[k] for k in ("oracle_id", "name", "layout")}
        row.update({k: card.get(k, []) for k in ("produced_mana",)})
        row["faces"] = [
            {k: face.get(k, [] if k == "colors" else "") for k in fields}
            for face in card.get("card_faces", [card])
        ]
        # Existing rule spellings stay readable; the oracle identity owns all faces.
        row["key"] = (
            "/".join(f["name"] for f in row["faces"])
            if card["layout"] == "split"
            else row["faces"][0]["name"]
        )
        row["key"] = CARD_ALIASES.get(row["key"], row["key"])
        row["names"] = sorted(
            name
            for name in spellings(card)
            if len(index.get(name, [])) == 1
            and index[name][0]["oracle_id"] == card["oracle_id"]
        )
        row["names"] = sorted(
            set(row["names"])
            | {row["key"]}
            | names_by_oracle.get(card["oracle_id"], set())
        )
        cards.append(row)
    return {
        "schema_version": "1.0.0",
        "source": {
            "provider": "Scryfall Oracle Cards",
            "uri": source_uri,
            "sha256": sha256(source.read_bytes()).hexdigest(),
        },
        "cards": cards,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--oracle-gzip", type=Path, required=True)
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument("--required-names", type=Path,
                           help="JSON list of names to cover, including newly observed names")
    selection.add_argument("--existing-facts", type=Path,
                           help="Reproduce an existing snapshot's entity coverage")
    p.add_argument("--source-uri", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    required = (json.loads(args.required_names.read_text()) if args.required_names
                else [card["key"] for card in json.loads(args.existing_facts.read_text())["cards"]])
    result = build(args.oracle_gzip, required, args.source_uri)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(result['cards'])} cards written to {args.output}")


if __name__ == "__main__":
    main()
