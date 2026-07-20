"""Legacy Standard command for format-aware MTGO Weekly Pickup."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent
SHARED_SRC = REPOSITORY_ROOT / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.mtgo import load_mtgo_context
from mtgmeta.mtgo import pickup as _shared
from classify_standard import load_rules
from stats_standard import (
    build_base_pack,
    deck_vector,
    latest_complete_week,
    load_all_events,
    merge_cards,
    normalize_dev,
    normalize_dev_abs,
    process_event,
    to_int,
    weighted_l1,
)


FORMAT_ID = "standard"
_CONTEXT = load_mtgo_context(REPOSITORY_ROOT, FORMAT_ID, "weekly_pickup")
OUT_DIR = str(_CONTEXT.paths["statistics"] / "pickup")
KNOWN_FILE = str(Path(OUT_DIR) / "known_archetypes.json")
INDEX_FILE = str(Path(OUT_DIR) / "index.json")
INIT_KNOWN_WEEKS = _shared.INITIAL_KNOWN_WEEKS

iso_week_label = _shared.iso_week_label
week_records = _shared.week_records
archetypes_in_window = _shared.archetypes_in_window
deck_deviation = _shared.deck_deviation
record_deck_cards = _shared.record_deck_cards
deck_fingerprint = _shared.deck_fingerprint
better_record = _shared.better_record


def load_known():
    return _shared.load_known(KNOWN_FILE)


def generate_candidates():
    result = _shared.generate_candidates(REPOSITORY_ROOT, FORMAT_ID)
    if result is None:
        print("没有可用的完整周，终止。")
        return None
    print(f"目标周: {result['week']}")
    print(f"候选写出: {result['candidate_path']}")
    print(
        f"现有套牌变化: {result['existing_count']} 副；"
        f"本周新增套牌: {result['new_count']} 副"
    )
    print(f"base 比对文件: {result['base_reference_path']}")
    print("请编辑候选 YAML，然后运行: python weekly_pickup.py publish")
    return result


def publish():
    result = _shared.publish(REPOSITORY_ROOT, FORMAT_ID)
    if result is None:
        print("没有可发布的已批准候选；请先生成并编辑候选 YAML。")
        return None
    print(
        f"发布写出: {result['published_path']} "
        f"(现有变化 {result['existing_count']} 副；新增 {result['new_count']} 副)"
    )
    print(f"更新索引: {result['index_path']}")
    print(f"归档已知套牌名单: {result['known_path']}")
    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    action = args[0] if args else ""
    if action == "candidates":
        generate_candidates()
        return 0
    if action == "publish":
        publish()
        return 0
    print("用法:")
    print("  python weekly_pickup.py candidates   # 生成候选 YAML + base 比对文件")
    print("  python weekly_pickup.py publish      # 编辑 YAML 后发布 JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
