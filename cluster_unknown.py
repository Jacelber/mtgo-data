import os
import json
import glob

# 直接复用分类脚本的核心逻辑，保证 Unknown 判定完全一致（含别名表）
from classify_standard import load_rules, deck_to_counts, signature_card_met

# === 配置 ===
DATA_DIR = "data/standard"
SIMILARITY_THRESHOLD = 0.60
MIN_GROUP_SIZE = 3



def is_unknown(main_counts, side_counts, archetypes):
    for arch in archetypes:
        sigs = arch.get("signatureCards", [])
        if sigs and all(signature_card_met(s, main_counts, side_counts) for s in sigs):
            return False   # 匹配到某个套牌，不是 Unknown
    return True


# ---------- 把一副牌变成「全部卡名的集合」（主备合计），用于比较重合度 ----------
def deck_to_cardset(main_counts, side_counts):
    return set(main_counts.keys()) | set(side_counts.keys())


def similarity(set_a, set_b):
    """两副牌卡名的重合度（交集 / 并集，即 Jaccard 相似度）"""
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union


# ---------- 主流程 ----------
def main():
    archetypes = load_rules()

    # 1. 收集所有 Unknown 牌表
    unknowns = []   # 每个元素: (赛事名, 牌手名, 卡名集合, 带张数的卡列表)
    for event_path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        for player in event.get("players", []):
            main_counts, side_counts = deck_to_counts(player)
            if is_unknown(main_counts, side_counts, archetypes):
                cardset = deck_to_cardset(main_counts, side_counts)
                # 带张数的卡列表（主牌），方便看代表牌表
                card_list = sorted(f"{q} {n}" for n, q in main_counts.items())
                unknowns.append((event.get("description", "?"),
                                 player.get("player", "?"),
                                 cardset, card_list))

    print(f"共有 {len(unknowns)} 副 Unknown 牌表，开始聚类...\n")

    # 2. 简单贪心聚类：每副牌和已有的组比较，重合度够高就并入，否则自立一组
    groups = []   # 每个组是一个 list，里面是 unknowns 的索引
    group_repr = []  # 每个组的代表卡名集合（用第一副牌当代表）

    for idx, (_, _, cardset, _) in enumerate(unknowns):
        placed = False
        for g_i, rep in enumerate(group_repr):
            if similarity(cardset, rep) >= SIMILARITY_THRESHOLD:
                groups[g_i].append(idx)
                placed = True
                break
        if not placed:
            groups.append([idx])
            group_repr.append(cardset)

    # 3. 按组大小排序，输出大组
    groups_sorted = sorted(groups, key=len, reverse=True)

    print("=" * 60)
    print(f"聚类完成：共分出 {len(groups_sorted)} 组")
    big_groups = [g for g in groups_sorted if len(g) >= MIN_GROUP_SIZE]
    print(f"其中 {len(big_groups)} 个大组（>= {MIN_GROUP_SIZE} 副），"
          f"覆盖 {sum(len(g) for g in big_groups)} 副")
    print(f"剩下 {len(unknowns) - sum(len(g) for g in big_groups)} 副是小组/单例")
    print("=" * 60)

    # 4. 把详细结果写到文件
    with open("unknown_clusters.txt", "w", encoding="utf-8") as f:
        for rank, g in enumerate(groups_sorted, 1):
            if len(g) < MIN_GROUP_SIZE:
                continue
            f.write(f"\n{'='*60}\n")
            f.write(f"组 {rank}：{len(g)} 副\n")
            f.write(f"{'='*60}\n")
            # 列出这一组里有哪些牌手（看看是不是同一人重复）
            sample_players = [f"{unknowns[i][0]} | {unknowns[i][1]}" for i in g[:8]]
            f.write("部分牌手：\n")
            for sp in sample_players:
                f.write(f"  - {sp}\n")
            # 用第一副当代表，列出完整主牌
            f.write(f"\n代表牌表（主牌，来自第一副）：\n")
            for card in unknowns[g[0]][3]:
                f.write(f"  {card}\n")

            # 同时在终端打印大组的简要信息
            if rank <= 15:
                print(f"组 {rank}: {len(g):>3} 副")

    print(f"\n详细聚类结果（含每组代表牌表）已写入 unknown_clusters.txt")


if __name__ == "__main__":
    main()
