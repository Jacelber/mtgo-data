# -*- coding: utf-8 -*-
"""
stats_matchup.py —— Standard 对阵矩阵统计（分时间窗口版）

数据链路：
  官方赛事 JSON (data/standard/Standard_Challenge_32_<event_id>.json)
    -> deck_to_counts + match_archetype 得到 {玩家名 -> archetype}
  Videre 对局 JSON (data/standard/mtgo/matches/<event_id>.json)
    -> 每条非轮空对局映射双方 archetype，任一方无法映射则整场丢弃
    -> 每场物理对局只计一次（视角无关去重），跨 archetype 对称写入，镜像单列

时间窗口：复用 stats_standard 的自然周口径（周一~周日）与滚动窗口。
  终点 = latest_complete_week（最近一个已结束完整周的周一）
  第 n 档窗口 = [end_monday-(n-1)周, end_monday+6天]
  档位 1/4/12/36 周；每档输出独立文件 matchup_<n>w.json。

胜率口径（MTGO/melee 通用）：win_rate = wins/(wins+losses+draws)，平局计入分母。
置信度：Wilson 95% 区间半宽 ci_half（0-1 小数），样本越大越窄。
"""

import os
import glob
import json
import math
from datetime import datetime, timedelta

from classify_standard import load_rules, deck_to_counts, match_archetype
from stats_standard import parse_event_date, week_monday, latest_complete_week
from public_contract import versioned

# === 配置 ===
OFFICIAL_DIR = "data/standard"
MATCHES_DIR = "data/standard/mtgo/matches"
OUT_DIR = "stats/standard/mtgo"
RANGES = [1, 4, 12, 36]        # 后端全生成；前端上线时先显示 1/4/12
MIN_MATCHUP_SAMPLE = 20        # 低置信提示阈值（不过滤，仅记录）
WILSON_Z = 1.96               # 95% 置信

# ---------- Wilson 区间半宽 ----------
def wilson_half_width(wins, total, z=WILSON_Z):
    """返回 Wilson 95% 置信区间的半宽（0-1 小数）。total=0 返回 None。"""
    if total <= 0:
        return None
    p = wins / total
    n = total
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return margin  # 半宽（对称近似，围绕 Wilson 中心）

# ---------- 三元组工具 ----------
def _blank_cell():
    return {"wins": 0, "losses": 0, "draws": 0}

def _win_rate(cell):
    total = cell["wins"] + cell["losses"] + cell["draws"]
    return cell["wins"] / total if total else None

# ---------- 加载官方赛事：日期 + 分类映射 ----------
def load_official_events(archetypes):
    """返回 [(event_date, event_id, {player:archetype}, {all_names}), ...]。"""
    out = []
    for path in sorted(glob.glob(os.path.join(OFFICIAL_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            event = json.load(f)
        d = parse_event_date(event.get("starttime"))
        if d is None:
            continue
        event_id = str(event.get("event_id", "")).strip()
        if not event_id:
            continue
        mapping, all_names = {}, set()
        for player in event.get("players", []):
            name = player.get("player")
            if not name:
                continue
            all_names.add(name)
            main_counts, side_counts = deck_to_counts(player)
            arch = match_archetype(main_counts, side_counts, archetypes)
            if arch is not None:
                mapping[name] = arch
        out.append((d, event_id, mapping, all_names))
    return out

# ---------- 累计单个赛事到给定的窗口结构 ----------
def accumulate_event(event_id, player_arch, official_names,
                     matrix, mirror, overall, seen_keys, stats):
    matches_path = os.path.join(MATCHES_DIR, f"{event_id}.json")
    if not os.path.exists(matches_path):
        stats["no_match_file"] += 1
        return
    with open(matches_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    rows = raw.get("matches", []) if isinstance(raw, dict) else raw
    if not rows:
        stats["no_match_file"] += 1
        return

    for row in rows:
        if not isinstance(row, dict) or row.get("isbye"):
            continue
        player = row.get("player")
        opponent = row.get("opponent")
        result = row.get("result")
        rnd = row.get("round")
        if not player or not opponent or result not in ("win", "loss", "draw"):
            continue

        key = (str(event_id), rnd, frozenset((player, opponent)))
        if key in seen_keys:
            stats["dedup_skipped"] += 1
            continue
        seen_keys.add(key)
        stats["physical_matches"] += 1

        a = player_arch.get(player)
        b = player_arch.get(opponent)
        if a is None or b is None:
            stats["dropped_unmapped"] += 1
            for name, arch in ((player, a), (opponent, b)):
                if arch is None:
                    if name in official_names:
                        stats["drop_reason_unknown_deck"] += 1
                    else:
                        stats["drop_reason_not_in_official"] += 1
            continue

        stats["counted"] += 1
        if a == b:
            cell = mirror.setdefault(a, _blank_cell())
            if result == "win":
                cell["wins"] += 1; cell["losses"] += 1
            elif result == "loss":
                cell["losses"] += 1; cell["wins"] += 1
            else:
                cell["draws"] += 2
            stats["mirror_matches"] += 1
        else:
            cell_ab = matrix.setdefault(a, {}).setdefault(b, _blank_cell())
            cell_ba = matrix.setdefault(b, {}).setdefault(a, _blank_cell())
            ov_a = overall.setdefault(a, _blank_cell())
            ov_b = overall.setdefault(b, _blank_cell())
            if result == "win":
                cell_ab["wins"] += 1; cell_ba["losses"] += 1
                ov_a["wins"] += 1; ov_b["losses"] += 1
            elif result == "loss":
                cell_ab["losses"] += 1; cell_ba["wins"] += 1
                ov_a["losses"] += 1; ov_b["wins"] += 1
            else:
                cell_ab["draws"] += 1; cell_ba["draws"] += 1
                ov_a["draws"] += 1; ov_b["draws"] += 1
            stats["cross_matches"] += 1

# ---------- 把三元组格子转成带胜率+区间的输出格子 ----------
def _emit_cell(cell, is_mirror):
    total = cell["wins"] + cell["losses"] + cell["draws"]
    wr = _win_rate(cell)
    ci = wilson_half_width(cell["wins"], total)
    return {
        "wins": cell["wins"], "losses": cell["losses"], "draws": cell["draws"],
        "matches": total,
        "win_rate": round(wr, 4) if wr is not None else None,
        "ci_half": round(ci, 4) if ci is not None else None,
        "low_sample": total < MIN_MATCHUP_SAMPLE,
        "mirror": is_mirror,
    }

# ---------- 组装一个窗口的输出 ----------
def build_window_output(matrix, mirror, overall):
    archetypes = set(matrix) | set(mirror) | set(overall)
    # archetype 排序：按整体样本量降序（主流在前，前端 Overall 列同序）
    order = sorted(
        archetypes,
        key=lambda a: (
            -(overall.get(a, _blank_cell())["wins"]
              + overall.get(a, _blank_cell())["losses"]
              + overall.get(a, _blank_cell())["draws"]),
            a,
        ),
    )
    matrix_out, overall_out = {}, {}
    for a in order:
        overall_out[a] = _emit_cell(overall.get(a, _blank_cell()), False)
        row = {}
        if a in mirror:
            row[a] = _emit_cell(mirror[a], True)
        for b in matrix.get(a, {}):
            row[b] = _emit_cell(matrix[a][b], False)
        matrix_out[a] = row
    return order, matrix_out, overall_out

# ---------- 主流程：分档聚合 + 输出 ----------
def build_window(events, end_monday, n_weeks):
    start_monday = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)

    matrix, mirror, overall = {}, {}, {}
    seen_keys = set()
    stats = {k: 0 for k in ("events_in_window", "no_match_file", "physical_matches",
                            "dedup_skipped", "counted", "dropped_unmapped",
                            "cross_matches", "mirror_matches",
                            "drop_reason_unknown_deck", "drop_reason_not_in_official")}

    for d, event_id, mapping, all_names in events:
        if start_monday <= d <= end_sunday:
            stats["events_in_window"] += 1
            accumulate_event(event_id, mapping, all_names,
                             matrix, mirror, overall, seen_keys, stats)

    order, matrix_out, overall_out = build_window_output(matrix, mirror, overall)
    data = versioned({
        "format": "standard",
        "source": "mtgo",
        "period": {
            "type": f"{n_weeks}w",
            "start": start_monday.isoformat(),
            "end": end_sunday.isoformat(),
            "weeks": n_weeks,
        },
        "min_sample_hint": MIN_MATCHUP_SAMPLE,
        "archetype_order": order,
        "overall": overall_out,
        "matrix": matrix_out,
    })
    return data, stats

def main():
    archetypes = load_rules()
    events = load_official_events(archetypes)
    print(f"  加载官方赛事 {len(events)} 个（含日期与分类映射）")

    end_monday = latest_complete_week([(d, None) for d, *_ in events])
    if end_monday is None:
        print("  没有可用的完整周，终止")
        return
    print(f"  区间终点（最近完整周周一）: {end_monday.isoformat()}")

    os.makedirs(OUT_DIR, exist_ok=True)
    index_entries = []
    for n in RANGES:
        data, stats = build_window(events, end_monday, n)
        fname = f"matchup_{n}w.json"
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        index_entries.append({
            "file": fname,
            "type": data["period"]["type"],
            "start": data["period"]["start"],
            "end": data["period"]["end"],
            "weeks": n,
            "archetypes": len(data["archetype_order"]),
            "counted_matches": stats["counted"],
        })
        print(f"  [{n:>2}w] {data['period']['start']}~{data['period']['end']} | "
              f"赛事{stats['events_in_window']} 有效对局{stats['counted']} "
              f"(跨{stats['cross_matches']}/镜像{stats['mirror_matches']}) "
              f"丢弃{stats['dropped_unmapped']} 套牌{len(data['archetype_order'])} -> {fname}")

    index = versioned({
        "format": "standard",
        "source": "mtgo",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "latest_complete_week": end_monday.isoformat(),
        "min_sample_hint": MIN_MATCHUP_SAMPLE,
        "ranges": index_entries,
    })
    with open(os.path.join(OUT_DIR, "matchup_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"  写出 matchup_index.json，全部输出到 {OUT_DIR}/")


if __name__ == "__main__":
    main()
