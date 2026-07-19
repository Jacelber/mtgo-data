import os
import json
import glob

from classify_standard import load_rules, deck_to_counts, match_archetype
from stats_standard import rounds_from_player_count, high_score_threshold, to_int

DATA_DIR = "data/standard"
OUTPUT_FILE = "unknown_highperf.txt"


def is_unknown(main_counts, side_counts, archetypes):
    return match_archetype(main_counts, side_counts, archetypes) is None


def main():
    archetypes = load_rules()
    records = []  # (排序键, 文本块)

    for event_path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)

        desc = event.get("description", "?")
        starttime = event.get("starttime", "")
        player_count = to_int(event.get("player_count"))
        rounds = rounds_from_player_count(player_count)
        threshold = high_score_threshold(rounds)

        for player in event.get("players", []):
            main_counts, side_counts = deck_to_counts(player)
            if not is_unknown(main_counts, side_counts, archetypes):
                continue

            swiss_score = to_int(player.get("swiss_score"))
            final_rank = to_int(player.get("final_rank"), default=9999)
            is_high = swiss_score >= threshold
            is_top8 = final_rank <= 8
            if not (is_high or is_top8):
                continue

            tag = []
            if is_high: tag.append("高分")
            if is_top8: tag.append(f"八强(rank {final_rank})")
            label = "/".join(tag)

            lines = []
            lines.append("=" * 60)
            lines.append(f"{desc} | {player.get('player','?')} | [{label}]")
            lines.append(f"  赛事人数 {player_count}, {rounds} 轮, 门槛 >={threshold}, "
                         f"swiss_score={swiss_score}, final_rank="
                         f"{final_rank if final_rank != 9999 else '-'}, 日期 {starttime[:10]}")
            lines.append("  --- 主牌 ---")
            main_total = 0
            for name in sorted(main_counts.keys()):
                q = main_counts[name]
                lines.append(f"    {q:>2} {name}")
                main_total += q
            lines.append(f"  主牌合计: {main_total} 张")
            lines.append("  --- 备牌 ---")
            side_total = 0
            for name in sorted(side_counts.keys()):
                q = side_counts[name]
                lines.append(f"    {q:>2} {name}")
                side_total += q
            lines.append(f"  备牌合计: {side_total} 张")

            # 排序键: 先八强(rank小的在前)、再高分(score大的在前)
            sort_key = (final_rank, -swiss_score)
            records.append((sort_key, "\n".join(lines)))

    records.sort(key=lambda r: r[0])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"高分/八强 Unknown 牌表，共 {len(records)} 副\n")
        f.write("（按 final_rank 升序、swiss_score 降序排列，战绩最好的在最上）\n\n")
        for _, block in records:
            f.write(block + "\n\n")

    print(f"共导出 {len(records)} 副高分/八强 Unknown 牌表到 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
