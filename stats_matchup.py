# -*- coding: utf-8 -*-
"""
stats_matchup.py
基于官方牌表分类 + Videre 对局结果，计算 Standard 的对阵矩阵与套牌整体胜率。

数据链路：
  官方赛事 JSON (data/standard/Standard_Challenge_32_<event_id>.json)
    -> deck_to_counts + match_archetype 得到 {玩家名 -> archetype}
  Videre 对局 JSON (data/standard/mtgo/matches/<event_id>.json)
    -> 每条非轮空对局，将 player / opponent 映射到官方 archetype
    -> 任一方无法映射则丢弃
    -> 每场物理对局只计一次（视角无关的对局身份键去重）
    -> 跨 archetype 对局对称写入矩阵；镜像对局单列统计

胜率口径（MTGO / melee 通用，为平局预留）：
  match win rate = wins / (wins + losses + draws)
  平局计入分母、不计入分子（1胜1负1平 = 33.3%）。
  MTGO 无平局时该口径与忽略平局等价。
"""

import os
import glob
import json

from classify_standard import (
    load_rules,
    deck_to_counts,
    match_archetype,
)

# === 配置 ===
OFFICIAL_DIR = "data/standard"                      # 官方赛事 JSON
MATCHES_DIR = "data/standard/mtgo/matches"          # Videre 对局 JSON
OUT_DIR = "stats/standard/mtgo"
MATRIX_OUT = os.path.join(OUT_DIR, "matchup_matrix.json")
OVERALL_OUT = os.path.join(OUT_DIR, "matchup_overall.json")

MIN_MATCHUP_SAMPLE = 20   # 对阵格子低于此样本量时，前端应标注为低置信（此处仅记录，不过滤）


# ---------- 工具：三元组累加 ----------
def _blank_cell():
    return {"wins": 0, "losses": 0, "draws": 0}


def _win_rate(cell):
    total = cell["wins"] + cell["losses"] + cell["draws"]
    if total == 0:
        return None
    return cell["wins"] / total


# ---------- 1. 为单个赛事建立 {玩家名 -> archetype} ----------
def build_player_archetypes(official_path, archetypes):
    """读官方赛事 JSON，返回 (event_id, {player: archetype}, {全部官方玩家名})。
    无法分类(None)的玩家不放入 mapping，但名字仍收进 all_names，
    用于区分「官方没这人」与「官方有牌表但分不了类」。"""
    with open(official_path, "r", encoding="utf-8") as f:
        event = json.load(f)
    event_id = str(event.get("event_id", "")).strip()
    mapping = {}
    all_names = set()
    for player in event.get("players", []):
        name = player.get("player")
        if not name:
            continue
        all_names.add(name)
        main_counts, side_counts = deck_to_counts(player)
        arch = match_archetype(main_counts, side_counts, archetypes)
        if arch is not None:
            mapping[name] = arch
    return event_id, mapping, all_names


# ---------- 2. 累计单个赛事的对局 ----------
def accumulate_event(event_id, player_arch, event_official_names,
                     matrix, mirror, overall, seen_keys, stats):
    """把一个赛事的 Videre 对局并入全局统计结构。
    matrix[a][b]  : a 对 b 的三元组（跨 archetype）
    mirror[a]     : a 的镜像内战三元组
    overall[a]    : a 的整体三元组
    seen_keys     : 跨赛事的对局去重集合
    stats         : 计数器（用于运行汇总）
    """
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
        if row.get("isbye"):
            continue
        player = row.get("player")
        opponent = row.get("opponent")
        result = row.get("result")
        rnd = row.get("round")
        if not player or not opponent or result not in ("win", "loss", "draw"):
            continue

        # 视角无关的对局身份键：同一场对局的两行生成同一 key
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
            # 细分：是官方完全没这人，还是有牌表但分不了类？
            for name, arch in ((player, a), (opponent, b)):
                if arch is None:
                    if name in event_official_names:   # 官方名单里有此人
                        stats["drop_reason_unknown_deck"] += 1
                    else:                               # 官方名单里根本没此人
                        stats["drop_reason_not_in_official"] += 1
            continue

        stats["counted"] += 1

        # 从当前行（player 视角）判定该场结果
        # result 描述的是 player 相对 opponent 的结果
        if a == b:
            # 镜像对局单列
            cell = mirror.setdefault(a, _blank_cell())
            if result == "win":
                cell["wins"] += 1
                cell["losses"] += 1   # 内战：一胜必对应一负，样本对称
            elif result == "loss":
                cell["losses"] += 1
                cell["wins"] += 1
            else:  # draw
                cell["draws"] += 2
            stats["mirror_matches"] += 1
        else:
            # 跨 archetype，对称写入 a->b 与 b->a
            cell_ab = matrix.setdefault(a, {}).setdefault(b, _blank_cell())
            cell_ba = matrix.setdefault(b, {}).setdefault(a, _blank_cell())
            ov_a = overall.setdefault(a, _blank_cell())
            ov_b = overall.setdefault(b, _blank_cell())
            if result == "win":
                cell_ab["wins"] += 1
                cell_ba["losses"] += 1
                ov_a["wins"] += 1
                ov_b["losses"] += 1
            elif result == "loss":
                cell_ab["losses"] += 1
                cell_ba["wins"] += 1
                ov_a["losses"] += 1
                ov_b["wins"] += 1
            else:  # draw
                cell_ab["draws"] += 1
                cell_ba["draws"] += 1
                ov_a["draws"] += 1
                ov_b["draws"] += 1
            stats["cross_matches"] += 1


# ---------- 3. 组装输出 ----------
def build_matrix_output(matrix, mirror):
    """把三元组结构转成带胜率的输出。镜像并入矩阵对角线。"""
    archetypes = set(matrix.keys()) | set(mirror.keys())
    out = {}
    for a in sorted(archetypes):
        out[a] = {}
        # 对角线（镜像）
        if a in mirror:
            m = mirror[a]
            out[a][a] = {
                "wins": m["wins"], "losses": m["losses"], "draws": m["draws"],
                "matches": m["wins"] + m["losses"] + m["draws"],
                "win_rate": _win_rate(m),
                "mirror": True,
            }
        # 跨 archetype
        for b in sorted(matrix.get(a, {})):
            cell = matrix[a][b]
            out[a][b] = {
                "wins": cell["wins"], "losses": cell["losses"], "draws": cell["draws"],
                "matches": cell["wins"] + cell["losses"] + cell["draws"],
                "win_rate": _win_rate(cell),
                "mirror": False,
            }
    return out


def build_overall_output(overall):
    out = {}
    for a, cell in overall.items():
        out[a] = {
            "wins": cell["wins"], "losses": cell["losses"], "draws": cell["draws"],
            "matches": cell["wins"] + cell["losses"] + cell["draws"],
            "win_rate": _win_rate(cell),
        }
    return dict(sorted(out.items(), key=lambda kv: -(kv[1]["matches"])))


# ---------- 4. 主流程 ----------
def main():
    archetypes = load_rules()

    official_files = glob.glob(os.path.join(OFFICIAL_DIR, "*.json"))
    print(f"  找到 {len(official_files)} 个官方赛事文件")

    matrix, mirror, overall = {}, {}, {}
    seen_keys = set()
    stats = {
        "events_with_matches": 0,
        "no_match_file": 0,
        "physical_matches": 0,
        "dedup_skipped": 0,
        "counted": 0,
        "dropped_unmapped": 0,
        "cross_matches": 0,
        "mirror_matches": 0,
        "drop_reason_unknown_deck": 0,
        "drop_reason_not_in_official": 0,
    }

    for official_path in official_files:
        event_id, player_arch, event_official_names = build_player_archetypes(official_path, archetypes)
        if not event_id:
            continue
        matches_path = os.path.join(MATCHES_DIR, f"{event_id}.json")
        if os.path.exists(matches_path):
            stats["events_with_matches"] += 1
        accumulate_event(event_id, player_arch, event_official_names,
                         matrix, mirror, overall, seen_keys, stats)

    matrix_out = build_matrix_output(matrix, mirror)
    overall_out = build_overall_output(overall)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MATRIX_OUT, "w", encoding="utf-8") as f:
        json.dump({"min_sample_hint": MIN_MATCHUP_SAMPLE, "matrix": matrix_out},
                  f, ensure_ascii=False, indent=2)
    with open(OVERALL_OUT, "w", encoding="utf-8") as f:
        json.dump(overall_out, f, ensure_ascii=False, indent=2)

    # ---------- 汇总 ----------
    print("=" * 55)
    print(f"有对局文件的赛事: {stats['events_with_matches']}")
    print(f"缺对局文件的赛事: {stats['no_match_file']}")
    print(f"物理对局(去重后): {stats['physical_matches']}")
    print(f"  去重跳过的镜像行: {stats['dedup_skipped']}")
    print(f"  因无法映射丢弃 : {stats['dropped_unmapped']}")
    print(f"  有效计入       : {stats['counted']}")
    print(f"    跨 archetype : {stats['cross_matches']}")
    print(f"    镜像内战     : {stats['mirror_matches']}")
    print("=" * 55)
    print(f"矩阵已写入   : {MATRIX_OUT}")
    print(f"整体胜率写入 : {OVERALL_OUT}")
    print(f"  因无法映射丢弃 : {stats['dropped_unmapped']}")
    print(f"    其中 有牌表但分不了类 : {stats['drop_reason_unknown_deck']}")
    print(f"    其中 官方无此玩家     : {stats['drop_reason_not_in_official']}")


if __name__ == "__main__":
    main()
