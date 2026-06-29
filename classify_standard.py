import os
import json
import glob
import yaml

# === 配置 ===
RULES_FILE = "my_archetypes/standard.yaml"   # j6e 格式的规则库
DATA_DIR = "data/standard"                     # 你抓取的 standard 赛事数据
UNKNOWN_OUTPUT = "unknown_decks.txt"           # 归不了类的牌表导出到这里


# ---------- 1. 加载 YAML 规则 ----------
def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    archetypes = data.get("archetypes", [])
    print(f"  已加载 {len(archetypes)} 条规则（来自 {RULES_FILE}）")
    return archetypes


# ---------- 2. 把一副牌整理成「卡名 -> 张数」的字典 ----------
def deck_to_counts(player):
    """返回 (主牌计数字典, 备牌计数字典)，键是卡名，值是张数"""
    main_counts = {}
    side_counts = {}
    for c in player.get("main_deck", []):
        name = c["name"].strip()
        main_counts[name] = main_counts.get(name, 0) + int(c["qty"])
    for c in player.get("sideboard", []):
        name = c["name"].strip()
        side_counts[name] = side_counts.get(name, 0) + int(c["qty"])
    return main_counts, side_counts


# ---------- 3. 数某张卡在指定区域有几张 ----------
def count_card(card_name, zone, main_counts, side_counts):
    """根据 zone 决定在哪里数这张卡的张数"""
    if zone == "main":
        return main_counts.get(card_name, 0)
    elif zone == "side":
        return side_counts.get(card_name, 0)
    else:  # "any" 或没写 zone：主备合计
        return main_counts.get(card_name, 0) + side_counts.get(card_name, 0)


# ---------- 4. 判断一张签名卡的条件是否满足 ----------
def signature_card_met(sig, main_counts, side_counts):
    name = sig["name"]
    zone = sig.get("zone", "any")   # 默认 any（主备合计）
    actual = count_card(name, zone, main_counts, side_counts)

    # exactCopies：必须恰好等于（常用 0 表示「不能有这张卡」）
    if "exactCopies" in sig:
        return actual == sig["exactCopies"]
    # minCopies：必须 >= 指定张数
    if "minCopies" in sig:
        return actual >= sig["minCopies"]
    # 既没写 exactCopies 也没写 minCopies：只要有这张卡就算（>=1）
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
