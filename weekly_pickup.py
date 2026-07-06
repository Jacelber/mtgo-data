# weekly_pickup.py —— 每周 Pickup 牌表：候选生成 + 发布固化
#
# 用法：
#   python weekly_pickup.py candidates   # 生成候选 YAML（给管理者编辑）+ base 比对文件
#   python weekly_pickup.py publish      # 把编辑好的 YAML 转成发布 JSON + 更新索引 + 归档名单
#
# 流程定位（配合每周维护）：
#   抓数据 → 旧规则跑分类 → dump_unknown 审查补规则 → 重跑分类/stats
#   → [本脚本 candidates] → 人工编辑 YAML(删/写解说/approved) → [本脚本 publish]

import os
import sys
import json
import yaml
from datetime import timedelta

from classify_standard import load_rules
from stats_standard import (
    load_all_events, latest_complete_week, build_base_pack,
    process_event, deck_vector, weighted_l1, normalize_dev,
    merge_cards, to_int,
)

# ---------- 常量 ----------
OUT_DIR = os.path.join("stats", "standard", "mtgo", "pickup")
KNOWN_FILE = os.path.join(OUT_DIR, "known_archetypes.json")   # 历史已知套牌名单
INDEX_FILE = os.path.join(OUT_DIR, "index.json")             # 已发布周次索引
INIT_KNOWN_WEEKS = 12   # 首次运行时，用近 N 周出现过的套牌作为初始已知名单


# ---------- 工具 ----------

def iso_week_label(monday):
    """把某周周一日期转成 'YYYY-Www' 标识（ISO 周）。"""
    y, w, _ = monday.isocalendar()
    return f"{y}-W{w:02d}"


def week_records(events, archetypes, end_monday):
    """取最近 1 完整周（end_monday 那周）的全部 records。"""
    start = end_monday
    end_sunday = end_monday + timedelta(days=6)
    recs = []
    for d, ev in events:
        if start <= d <= end_sunday:
            recs.extend(process_event(ev, archetypes)["records"])
    return recs


def archetypes_in_window(events, archetypes, end_monday, n_weeks):
    """返回近 n_weeks 周内出现过（非 Unknown）的套牌名集合。"""
    start = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)
    names = set()
    for d, ev in events:
        if start <= d <= end_sunday:
            for r in process_event(ev, archetypes)["records"]:
                if r["archetype"] != "Unknown":
                    names.add(r["archetype"])
    return names


def load_known():
    """读历史已知套牌名单；不存在返回 None（触发首次初始化）。"""
    if not os.path.exists(KNOWN_FILE):
        return None
    with open(KNOWN_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f).get("known", []))


def deck_deviation(record, base, d99):
    """单副牌相对该套牌 4 周 base 架空平均的偏离度（绝对刻度 0-100）。无 base 返回 None。
    d99 参数保留仅为兼容旧调用签名，实际用 base 的加权总量做分母。
    """
    if not base:
        return None
    from stats_standard import normalize_dev_abs
    vec = deck_vector(record)
    raw = weighted_l1(vec, base["mean"], base["weights"])
    return normalize_dev_abs(raw, base["denom"])



def record_deck_cards(record):
    """取主备牌（合并同名 + 规范卡名），供 YAML/JSON 展示。"""
    return {
        "main_deck": merge_cards(record.get("main_deck", [])),
        "side_deck": merge_cards(record.get("side_deck", [])),
    }


def deck_fingerprint(record):
    """主牌 + 备牌完全相同视为同一副牌（忽略玩家）。返回可哈希指纹。"""
    main = tuple((c["name"], c["qty"]) for c in merge_cards(record.get("main_deck", [])))
    side = tuple((c["name"], c["qty"]) for c in merge_cards(record.get("side_deck", [])))
    return (main, side)


def better_record(a, b):
    """返回战绩更好的 record：final_rank 小 > player_count 多 > starttime 新。"""
    ka = (a["final_rank"], -a["player_count"], a["starttime"])
    kb = (b["final_rank"], -b["player_count"], b["starttime"])
    return a if ka <= kb else b


# ================================================================
#                    动作一：生成候选 YAML
# ================================================================

def generate_candidates():
    archetypes = load_rules()
    events = load_all_events()
    end_monday = latest_complete_week(events)
    if end_monday is None:
        print("没有可用的完整周，终止")
        return

    week_label = iso_week_label(end_monday)
    end_sunday = end_monday + timedelta(days=6)
    print(f"目标周: {week_label}  ({end_monday.isoformat()} ~ {end_sunday.isoformat()})")

    # 4 周 base（复用 stats 的口径）
    base_pack, d99 = build_base_pack(events, archetypes, end_monday)
    print(f"4 周 base: {len(base_pack)} 套牌达标, 全局 D99 = {d99:.3f}")

    # 已知套牌名单（判定新增用）
    known = load_known()
    if known is None:
        known = archetypes_in_window(events, archetypes, end_monday, INIT_KNOWN_WEEKS)
        print(f"⚠️ 首次运行：无历史名单，用近 {INIT_KNOWN_WEEKS} 周出现过的 {len(known)} 个套牌作为初始已知名单。")
        print("   （本周只有连这些里都没有的套牌才算『新增』；本次不写入 known 文件，发布时才归档。）")

    # 本周全部记录
    recs = week_records(events, archetypes, end_monday)
    top8_recs = [r for r in recs if r["is_top8"]]
    print(f"本周牌表 {len(recs)} 副，其中八强以上 {len(top8_recs)} 副")

    # 按「套牌 + 主牌 + 备牌」去重（忽略玩家），同一副牌只保留战绩最好的一条
    dedup = {}
    for r in top8_recs:
        if r["archetype"] == "Unknown":
            continue  # Unknown 走 dump_unknown 流程，不进 pickup
        key = (r["archetype"], deck_fingerprint(r))
        if key not in dedup:
            dedup[key] = r
        else:
            dedup[key] = better_record(dedup[key], r)
    print(f"去重后（主备牌完全相同视为同一副）: {len(dedup)} 副")

    # 第一类：现有套牌 + 八强 + 偏离度
    existing_picks = []
    # 第二类：本周新增套牌 + 八强
    new_picks = []

    for r in dedup.values():
        arch = r["archetype"]
        base = base_pack.get(arch)
        dev = deck_deviation(r, base, d99)
        cards = record_deck_cards(r)
        entry = {
            "archetype": arch,
            "player": r["player"],
            "final_rank": r["final_rank"] if r["final_rank"] != 9999 else None,
            "swiss_score": r["swiss_score"],
            "player_count": r["player_count"],
            "starttime": r["starttime"],
            "deviation": dev,
            "source": None,          # existing / new，下面填
            "approved": False,       # 你确认后改 true
            "comment_zh": "",        # 你写 100-200 字中文解说
            "comment_en": "",        # 预留，英文由对照表就位后补
            "main_deck": cards["main_deck"],
            "side_deck": cards["side_deck"],
        }
        if arch not in known:
            entry["source"] = "new"
            new_picks.append(entry)
        else:
            entry["source"] = "existing"
            existing_picks.append(entry)

    # 第一类按偏离度降序（None 排最后），你从上往下删低的
    existing_picks.sort(key=lambda e: (e["deviation"] is None, -(e["deviation"] or 0)))
    # 第二类按成绩排序（rank 升序）
    new_picks.sort(key=lambda e: (e["final_rank"] is None, e["final_rank"] or 9999))

    doc = {
        "week": week_label,
        "start": end_monday.isoformat(),
        "end": end_sunday.isoformat(),
        "note": "编辑说明：删掉不想 pickup 的条目；保留的把 approved 改为 true 并填 comment_zh；"
                "existing 类已按偏离度从高到低排列，从上往下筛即可。"
                "偏离度可疑时对照同目录 base_reference_*.yaml 逐卡核对。",
        "existing_changes": existing_picks,   # 第一类：现有套牌构筑变化
        "new_archetypes": new_picks,          # 第二类：本周新增套牌
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    cand_file = os.path.join(OUT_DIR, f"candidates_{week_label}.yaml")
    with open(cand_file, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, allow_unicode=True, sort_keys=False, width=1000,
                  default_flow_style=False)

    # ---- 额外输出：所有套牌的 4 周 base（架空平均）供人工比对偏离度 ----
    base_ref = {
        "week": week_label,
        "base_weeks": 4,
        "global_d99": round(d99, 4),
        "note": "每套牌最近 4 周架空平均构筑（Core=常备/Flex=自选），"
                "mean_qty 为均值张数，rate 为出现率（权重）。用于人工核对某副牌偏离度是否合理。",
        "archetypes": {},
    }
    for arch in sorted(base_pack.keys()):
        b = base_pack[arch]
        base_ref["archetypes"][arch] = {
            "sample_size": b["sample_size"],
            "core": b["core"],   # [{name, mean_qty, rate}]
            "flex": b["flex"],
            "medoid": (b["medoid_display"] or {}).get("player") if b["medoid_display"] else None,
        }
    base_ref_file = os.path.join(OUT_DIR, f"base_reference_{week_label}.yaml")
    with open(base_ref_file, "w", encoding="utf-8") as f:
        yaml.dump(base_ref, f, allow_unicode=True, sort_keys=False, width=1000,
                  default_flow_style=False)

    print(f"\n候选写出: {cand_file}")
    print(f"  第一类(现有套牌变化, 八强): {len(existing_picks)} 副")
    print(f"  第二类(本周新增套牌, 八强): {len(new_picks)} 副")
    print(f"base 比对文件: {base_ref_file}  ({len(base_pack)} 套牌)")
    print("请编辑候选 YAML，然后运行: python weekly_pickup.py publish")


# ================================================================
#                    动作二：发布固化 JSON
# ================================================================

def publish():
    archetypes = load_rules()
    events = load_all_events()
    end_monday = latest_complete_week(events)
    if end_monday is None:
        print("没有可用的完整周，终止")
        return
    week_label = iso_week_label(end_monday)

    cand_file = os.path.join(OUT_DIR, f"candidates_{week_label}.yaml")
    if not os.path.exists(cand_file):
        print(f"找不到候选文件 {cand_file}，请先运行 candidates 并编辑。")
        return

    with open(cand_file, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    def approved_of(key):
        picks = []
        for e in doc.get(key, []):
            if not e.get("approved"):
                continue
            picks.append({
                "archetype": e["archetype"],
                "player": e.get("player"),
                "final_rank": e.get("final_rank"),
                "swiss_score": e.get("swiss_score"),
                "player_count": e.get("player_count"),
                "starttime": e.get("starttime"),
                "deviation": e.get("deviation"),
                "source": e.get("source"),
                "comment_zh": (e.get("comment_zh") or "").strip(),
                "comment_en": (e.get("comment_en") or "").strip(),
                "main_deck": e.get("main_deck", []),
                "side_deck": e.get("side_deck", []),
            })
        return picks

    existing = approved_of("existing_changes")
    new_arch = approved_of("new_archetypes")

    if not existing and not new_arch:
        print("⚠️ 没有任何条目被标记 approved: true，未发布。请编辑 YAML 后重试。")
        return

    published = {
        "format": "standard",
        "source": "mtgo",
        "week": week_label,
        "start": doc.get("start"),
        "end": doc.get("end"),
        "existing_changes": existing,
        "new_archetypes": new_arch,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    pub_file = os.path.join(OUT_DIR, f"{week_label}.json")
    with open(pub_file, "w", encoding="utf-8") as f:
        json.dump(published, f, ensure_ascii=False, indent=2)
    print(f"发布写出: {pub_file}  (第一类 {len(existing)} 副, 第二类 {len(new_arch)} 副)")

    # 更新 pickup/index.json（back number 列表，最新在前）
    entries = []
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f).get("weeks", [])
    entries = [e for e in entries if e.get("week") != week_label]  # 覆盖同周
    entries.append({
        "week": week_label,
        "file": f"{week_label}.json",
        "start": doc.get("start"),
        "end": doc.get("end"),
        "existing_count": len(existing),
        "new_count": len(new_arch),
    })
    entries.sort(key=lambda e: e["week"], reverse=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({"format": "standard", "source": "mtgo", "weeks": entries},
                  f, ensure_ascii=False, indent=2)
    print(f"更新索引: {INDEX_FILE}  (共 {len(entries)} 周)")

    # 归档本周出现过的全部套牌名单（供下周判定新增）
    first_run = not os.path.exists(KNOWN_FILE)
    known = load_known() or set()
    this_week_archs = archetypes_in_window(events, archetypes, end_monday, 1)
    # 首次运行时把初始基线也并进来，避免下周误报
    if first_run:
        known |= archetypes_in_window(events, archetypes, end_monday, INIT_KNOWN_WEEKS)
    known |= this_week_archs
    with open(KNOWN_FILE, "w", encoding="utf-8") as f:
        json.dump({"known": sorted(known)}, f, ensure_ascii=False, indent=2)
    print(f"归档已知套牌名单: {KNOWN_FILE}  (共 {len(known)} 个套牌)")


# ---------- 入口 ----------

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "candidates":
        generate_candidates()
    elif action == "publish":
        publish()
    else:
        print("用法:")
        print("  python weekly_pickup.py candidates   # 生成候选 YAML + base 比对文件")
        print("  python weekly_pickup.py publish      # 编辑 YAML 后发布 JSON")
