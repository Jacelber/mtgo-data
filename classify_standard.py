import os
import json
import glob
import sys
from pathlib import Path
import yaml

SHARED_SRC = Path(__file__).resolve().parent / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.deck import count_card as shared_count_card
from mtgmeta.deck import deck_to_counts as shared_deck_to_counts

# === 配置 ===
RULES_FILE = "my_archetypes/standard.yaml"   # j6e 格式的规则库
DATA_DIR = "data/standard"                     # 你抓取的 standard 赛事数据
UNKNOWN_OUTPUT = "unknown_decks.txt"           # 归不了类的牌表导出到这里

# MTGO 版权改名卡 -> j6e 规则使用的标准卡名
# 仅覆盖 2025年末蜘蛛侠系列 ~ 2026年6月漫威系列 窗口期内高频改名卡
# 漫威系列发售后线上获得版权，新数据已用正名，此表把两个时期的数据归一
CARD_ALIASES = {
    "Kavaero, Mind-Bitten": "Superior Spider-Man",
    "Leyline Weaver": "Spider Manifestation",
}


def normalize_name(name):
    """Preserve the legacy public-output alias behavior during migration."""
    name = name.strip()
    return CARD_ALIASES.get(name, name)

# ---------- 1. 加载 YAML 规则 ----------
def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    archetypes = data.get("archetypes", [])
    print(f"  已加载 {len(archetypes)} 条规则（来自 {RULES_FILE}）")
    return archetypes


# ---------- 2. 把一副牌整理成「卡名 -> 张数」的字典 ----------
def deck_to_counts(player):
    return shared_deck_to_counts(player)


# ---------- 3. 数某张卡在指定区域有几张 ----------
def count_card(card_name, zone, main_counts, side_counts):
    """根据 zone 决定在哪里数这张卡的张数"""
    return shared_count_card(card_name, zone, main_counts, side_counts)


# ---------- 4. 判断一张签名卡的条件是否满足 ----------
def signature_card_met(sig, main_counts, side_counts):
    name = sig["name"]
    zone = sig.get("zone", "any")
    actual = count_card(name, zone, main_counts, side_counts)
    if "exactCopies" in sig:
        return actual == sig["exactCopies"]
    if "minCopies" in sig:
        return actual >= sig["minCopies"]
    if "maxCopies" in sig:
        return actual <= sig["maxCopies"]
    return actual >= 1



# ---------- 5. 尝试匹配一个套牌 ----------
def match_archetype(main_counts, side_counts, archetypes):
    for arch in archetypes:
        sigs = arch.get("signatureCards", [])
        if sigs and all(signature_card_met(s, main_counts, side_counts) for s in sigs):
            return arch.get("name", "Unnamed")
    return None


# ---------- 6. 主流程 ----------
def main():
    archetypes = load_rules()

    counts = {}            # 每个分类结果的牌表数量
    total = 0
    unknown_decks = []     # 收集归不了类的牌表

    event_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    print(f"  找到 {len(event_files)} 个 standard 赛事文件\n")

    for event_path in event_files:
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        for player in event.get("players", []):
            total += 1
            main_counts, side_counts = deck_to_counts(player)

            result = match_archetype(main_counts, side_counts, archetypes)
            if result is None:
                result = "Unknown"
                # 记录 Unknown 牌表（带张数，方便后续审查）
                main_list = sorted(f"{qty} {name}" for name, qty in main_counts.items())
                unknown_decks.append((event.get("description", "?"),
                                      player.get("player", "?"),
                                      main_list))

            counts[result] = counts.get(result, 0) + 1

    # ---------- 输出报告 ----------
    print("=" * 50)
    print(f"总牌表数: {total}")
    print("=" * 50)
    for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100 if total else 0
        print(f"  {cnt:>4} ({pct:4.1f}%)  {name}")

    unknown_count = counts.get("Unknown", 0)
    matched = total - unknown_count
    print("=" * 50)
    if total:
        print(f"成功分类: {matched} / {total}  ({matched/total*100:.1f}%)")
    print(f"完全归不了类 (Unknown): {unknown_count}")

    # 导出 Unknown 牌表
    with open(UNKNOWN_OUTPUT, "w", encoding="utf-8") as f:
        for desc, pname, cards in unknown_decks:
            f.write(f"=== {desc} | {pname} ===\n")
            for card in cards:
                f.write(f"  {card}\n")
            f.write("\n")
    print(f"\nUnknown 牌表已导出到 {UNKNOWN_OUTPUT}")


if __name__ == "__main__":
    main()
