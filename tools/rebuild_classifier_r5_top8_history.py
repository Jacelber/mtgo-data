"""Reclassify only already-indexed MTGO Top 8 history for R5."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

from mtgmeta.config import load_rule_set
from mtgmeta.mtgo import stats, top8


ROOT = Path(__file__).resolve().parents[1]


def _load_index(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("weeks"), list):
        raise ValueError(f"{path}: invalid Top 8 index")
    return value


def rebuild_format(format_id: str) -> list[str]:
    output = ROOT / "stats" / format_id / "mtgo" / "top8"
    index = _load_index(output / "index.json")
    rules = load_rule_set(ROOT / "my_archetypes" / f"{format_id}.yaml")
    events = stats.load_all_events(ROOT, format_id)
    written: list[str] = []
    for entry in index["weeks"]:
        monday = date.fromisoformat(entry["start"])
        week, bases = top8._build_week_documents(
            events,
            rules,
            monday,
            format_id=format_id,
        )
        if len(week["events"]) != entry["event_count"]:
            raise ValueError(f"{format_id} {entry['file']}: event count changed")
        for filename, document in {
            entry["file"]: week,
            entry["comparison_bases_file"]: bases,
        }.items():
            (output / filename).write_bytes(top8._document_bytes(document))
            written.append((output / filename).relative_to(ROOT).as_posix())
    return written


def main() -> int:
    for format_id in ("standard", "modern"):
        for path in rebuild_format(format_id):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
