import os, json
from classify_standard import load_rules, deck_to_counts, normalize_name, signature_card_met

DATA_DIR = "data/standard"

# 在这里填你要分析的那场赛事的文件名
TARGET_FILE = "Standard_Challenge_32_12845647.json"   # ← 改成你的目标文件

def match_archetype(main_counts, side_counts, archetypes):
    for arch in archetypes:
        sigs = arch.get("signatureCards", [])
        if sigs and all(signature_card_met(s, main_counts, side_counts) for s in sigs):
            return arch.get("name", "Unnamed")
    return "Unknown"

def to_int(v):
    # 把可能是字符串/None 的排名值安全转成整数；无效值返回一个很大的数排到最后
    if v is None or v == "":
        return 9999
    try:
        return int(v)
    except (ValueError, TypeError):
        return 9999

def sort_key(player):
    fr = to_int(player.get("final_rank"))
    sr = to_int(player.get("swiss_rank"))
    # 有有效 final_rank（不是兜底的 9999）的排前面，按 final_rank 升序；
    # 没有的按 swiss_rank 升序排在后面
    if fr != 9999:
        return (0, fr)
    return (1, sr)


def fmt_deck(card_list):
    # card_list 是 [{"name":..., "qty":...}, ...]
    lines = []
    for c in sorted(card_list, key=lambda x: x["name"]):
        lines.append(f"    {c['qty']} {c['name']}")
    return "\n".join(lines) if lines else "    (无)"

def main():
    archetypes = load_rules()
    path = os.path.join(DATA_DIR, TARGET_FILE)
    with open(path, "r", encoding="utf-8") as f:
        event = json.load(f)

    players = event.get("players", [])
    players_sorted = sorted(players, key=sort_key)

    out_lines = []
    header = f"赛事: {event.get('description','?')}  (event_id={event.get('event_id','?')}, starttime={event.get('starttime','?')})"
    out_lines.append(header)
    out_lines.append("=" * 70)

    for i, p in enumerate(players_sorted, 1):
        main_counts, side_counts = deck_to_counts(p)
        arch = match_archetype(main_counts, side_counts, archetypes)
        fr = p.get("final_rank")
        sr = p.get("swiss_rank")
        rank_str = f"final={fr}" if fr is not None else f"swiss={sr}"
        out_lines.append(f"\n#{i}  [{rank_str}]  {p.get('player','?')}  ->  【{arch}】")
        out_lines.append("  主牌:")
        out_lines.append(fmt_deck(p.get("main_deck", [])))
        out_lines.append("  备牌:")
        out_lines.append(fmt_deck(p.get("sideboard", [])))

    text = "\n".join(out_lines)
    print(text)
    out_path = "event_classify_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n\n已导出到 {out_path}")

if __name__ == "__main__":
    main()
