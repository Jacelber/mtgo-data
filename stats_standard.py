# stats_standard.py —— MTGO standard 赛制统计模块
# 阶段一：底层工具 + 单赛事处理

import math
import os
import json
import glob
from classify_standard import load_rules, deck_to_counts, match_archetype

DATA_DIR = "data/standard"


# ---------- 工具函数 ----------

def to_int(value, default=0):
    """把可能是字符串/None/空值的字段安全转成整数，转不了返回 default。"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def rounds_from_player_count(n):
    """按 MTGO 官方人数-轮数对照表，用全场报名人数推断瑞士轮数。
    表来源：https://www.mtgo.com/en/mtgo/events
    """
    table = [(8, 3), (16, 4), (32, 5), (64, 6),
             (128, 7), (212, 8), (384, 9), (672, 10)]
    for cap, rounds in table:
        if n <= cap:
            return rounds
    r, cap = 10, 672
    while n > cap:
        cap *= 2
        r += 1
    return r


def high_score_threshold(rounds):
    """高分门槛：积分严格超过总可能积分的一半，向上取整到最近的 3 的倍数。
    swiss_score >= threshold 即算高分。
    """
    return (math.floor(rounds * 1.5 / 3) + 1) * 3


# ---------- 单赛事处理 ----------

def process_event(event, archetypes):
    player_count = to_int(event.get("player_count"))
    rounds = rounds_from_player_count(player_count)
    threshold = high_score_threshold(rounds)
    starttime = event.get("starttime", "")
    description = event.get("description", "?")
    records = []
    for player in event.get("players", []):
        main_counts, side_counts = deck_to_counts(player)
        arch = match_archetype(main_counts, side_counts, archetypes) or "Unknown"
        swiss_score = to_int(player.get("swiss_score"))
        final_rank = to_int(player.get("final_rank"), default=9999)
        records.append({
            "archetype": arch,
            "is_high_score": swiss_score >= threshold,
            "is_top8": final_rank <= 8,
            "swiss_score": swiss_score,
            "final_rank": final_rank,
            # 以下为示例牌表功能新增字段
            "player": player.get("player", player.get("name", "?")),
            "player_count": player_count,   # 事件规模，用于最佳牌表第二级排序
            "starttime": starttime,         # 事件时间，用于最佳牌表第三级排序
            "main_deck": player.get("main_deck", []),
            "side_deck": player.get("sideboard", []),
        })
    return {
        "description": description,
        "player_count": player_count,
        "rounds": rounds,
        "threshold": threshold,
        "starttime": starttime,
        "records": records,
    }


from datetime import datetime, timedelta


def parse_event_date(starttime):
    """从 starttime 取日期部分。只用前 10 个字符 YYYY-MM-DD，
    忽略时间与小数秒，稳健。返回 date 对象；解析失败返回 None。
    """
    if not starttime:
        return None
    try:
        return datetime.strptime(str(starttime)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def week_monday(d):
    """给一个 date，返回它所属自然周（周一到周日）的周一日期。
    周一 weekday()==0，减掉即可回到本周一。
    """
    return d - timedelta(days=d.weekday())

def aggregate(records):
    """把一批牌手记录聚合成各套牌的统计。
    records: process_event 返回的 records 列表可跨赛事拼接后传入。
    返回: {total_decks, total_high_score, total_top8, unknown_count, archetypes[...]}
    占比口径：高分占比=该套牌高分数/全部高分数；八强占比=该套牌八强数/全部八强数。
    转化率=八强数/高分数；高分数为0时输出 None（前端显示 N/A）。
    """
    # 按套牌累计三个计数
    stats = {}   # name -> {"count","high","top8"}
    total_decks = 0
    total_high = 0
    total_top8 = 0

    for r in records:
        name = r["archetype"]
        s = stats.setdefault(name, {"count": 0, "high": 0, "top8": 0})
        s["count"] += 1
        total_decks += 1
        if r["is_high_score"]:
            s["high"] += 1
            total_high += 1
        if r["is_top8"]:
            s["top8"] += 1
            total_top8 += 1

    unknown_count = stats.get("Unknown", {}).get("count", 0)

    archetypes = []
    for name, s in stats.items():
        high_share = s["high"] / total_high if total_high else None
        top8_share = s["top8"] / total_top8 if total_top8 else None
        conversion = s["top8"] / s["high"] if s["high"] else None
        archetypes.append({
            "name": name,
            "count": s["count"],
            "high_score_count": s["high"],
            "high_score_share": round(high_share, 4) if high_share is not None else None,
            "top8_count": s["top8"],
            "top8_share": round(top8_share, 4) if top8_share is not None else None,
            "conversion": round(conversion, 4) if conversion is not None else None,
        })

    # 按出现次数降序，方便查看
    archetypes.sort(key=lambda a: a["count"], reverse=True)

    return {
        "total_decks": total_decks,
        "total_high_score": total_high,
        "total_top8": total_top8,
        "unknown_count": unknown_count,
        "archetypes": archetypes,
    }

def load_all_events():
    """读取 DATA_DIR 下所有赛事，返回 [(event_date, event_dict), ...]，跳过无日期的。"""
    events = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            ev = json.load(f)
        d = parse_event_date(ev.get("starttime"))
        if d is not None:
            events.append((d, ev))
    return events


def latest_complete_week(events, today=None):
    """返回最近一个『已结束』完整周的周一。判定：该周周日 < 今天。"""
    if today is None:
        today = datetime.now().date()
    weeks = sorted({week_monday(d) for d, _ in events})
    complete = [w for w in weeks if (w + timedelta(days=6)) < today]
    return complete[-1] if complete else (weeks[-1] if weeks else None)


def build_decks(records):
    """按套牌分组，为每套牌选出最佳牌表（average_deck 暂留 None 占位）。
    返回 dict: { archetype_name: {best_deck, average_deck} }
    """
    from collections import defaultdict
    by_arch = defaultdict(list)
    for r in records:
        by_arch[r["archetype"]].append(r)

    result = {}
    for arch, arch_records in by_arch.items():
        result[arch] = {
            "best_deck": pick_best_deck(arch_records),
            "average_deck": None,   # 平均牌表定义待补，先占位
        }
    return result


def build_range(events, archetypes, end_monday, n_weeks):
    """聚合从 end_monday 那周往前数 n_weeks 个自然周内的所有赛事。
    区间 = [start_monday, end_sunday]，含首尾。
    返回 (stats_data, decks_data)：统计 JSON 与牌表详情 JSON 两份内容。
    """
    start_monday = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)

    records = []
    for d, ev in events:
        if start_monday <= d <= end_sunday:
            records.extend(process_event(ev, archetypes)["records"])

    agg = aggregate(records)
    period = {
        "type": f"{n_weeks}w",
        "start": start_monday.isoformat(),
        "end": end_sunday.isoformat(),
        "weeks": n_weeks,
    }
    stats_data = {
        "format": "standard",
        "source": "mtgo",
        "period": period,
        **agg,
    }
    decks_data = {
        "format": "standard",
        "source": "mtgo",
        "period": period,
        "decks": build_decks(records),
    }
    return stats_data, decks_data


def build_all_stats(today=None):
    """生成 1/4/12/36 周四档区间 JSON + index.json，写入 stats/standard/mtgo/。"""
    archetypes = load_rules()
    events = load_all_events()
    end_monday = latest_complete_week(events, today=today)
    if end_monday is None:
        print("  没有可用的完整周，终止")
        return

    out_dir = os.path.join("stats", "standard", "mtgo")
    os.makedirs(out_dir, exist_ok=True)

    ranges = [1, 4, 12, 36]
    index_entries = []
    for n in ranges:
        data, decks = build_range(events, archetypes, end_monday, n)
        fname = f"range_{n}w.json"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        decks_fname = f"decks_{n}w.json"
        with open(os.path.join(out_dir, decks_fname), "w", encoding="utf-8") as f:
            json.dump(decks, f, ensure_ascii=False, indent=2)

        index_entries.append({
            "file": fname,
            "decks_file": decks_fname,
            "type": data["period"]["type"],
            "start": data["period"]["start"],
            "end": data["period"]["end"],
            "weeks": n,
            "total_decks": data["total_decks"],
        })
        print(f"  写出 {fname} + {decks_fname}: {data['period']['start']} ~ {data['period']['end']}, "
              f"{data['total_decks']} 副牌, 高分 {data['total_high_score']}, 八强 {data['total_top8']}")

    index = {
        "format": "standard",
        "source": "mtgo",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "latest_complete_week": end_monday.isoformat(),
        "ranges": index_entries,
    }
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"  写出 index.json")
    print(f"  全部输出到 {out_dir}/")

def merge_cards(card_list):
    """合并同名卡，qty 累加。按卡名排序返回。"""
    merged = {}
    for c in card_list:
        name = c.get("name", "?")
        merged[name] = merged.get(name, 0) + to_int(c.get("qty", 0))
    return [{"name": n, "qty": q} for n, q in sorted(merged.items())]


def pick_best_deck(archetype_records):
    """按三级排序选出最佳牌表：
       1) final_rank 最小（瑞士轮排名最高）
       2) player_count 最大（场次人数最多）
       3) starttime 最新（日期更近）
       archetype_records: 属于同一套牌的 record 列表
       返回一个 dict（含选手、战绩、主牌、备牌），无记录则返回 None
    """
    if not archetype_records:
        return None
    best = min(
        archetype_records,
        key=lambda r: (
            r["final_rank"],           # 越小越好
            -r["player_count"],        # 取负号使越大越靠前
            _neg_time_key(r["starttime"]),  # 越新越靠前
        ),
    )
    return {
        "player": best["player"],
        "final_rank": best["final_rank"] if best["final_rank"] != 9999 else None,
        "swiss_score": best["swiss_score"],
        "player_count": best["player_count"],
        "starttime": best["starttime"],
        "main_deck": merge_cards(best["main_deck"]),
        "side_deck": merge_cards(best["side_deck"]),
    }


def _neg_time_key(starttime):
    """把 starttime 转成可比较的负向排序键：时间越新，返回值越小（排越前）。
       解析失败的记为最旧（排最后）。"""
    d = parse_event_date(starttime)
    if d is None:
        return 0  # 最旧
    # date.toordinal() 越大越新，取负后越新越小
    return -d.toordinal()

# ---------- 自测块（始终放在文件最末尾） ----------

if __name__ == "__main__":
    print("=== to_int 测试 ===")
    print(to_int("10"), to_int(10), to_int(None), to_int(""), to_int("abc"), to_int("  7 "))

    print("\n=== rounds_from_player_count 测试 ===")
    for n in [8, 16, 17, 32, 33, 64, 78, 128, 200, 384, 500, 700, 1400]:
        print(f"  {n} 人 -> {rounds_from_player_count(n)} 轮")

    print("\n=== high_score_threshold 测试 ===")
    for r in [5, 6, 7, 8, 9]:
        print(f"  {r} 轮 -> 门槛 >= {high_score_threshold(r)}")

    print("\n=== 单赛事处理测试 ===")
    archetypes = load_rules()
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not files:
        print("  没找到赛事文件，检查 DATA_DIR")
    else:
        sample = files[0]
        with open(sample, "r", encoding="utf-8") as f:
            event = json.load(f)
        result = process_event(event, archetypes)
        print(f"  赛事: {result['description']}")
        print(f"  报名人数: {result['player_count']}  ->  推断 {result['rounds']} 轮  ->  高分门槛 >= {result['threshold']}")
        print(f"  牌手总数: {len(result['records'])}")
        hs = sum(1 for r in result['records'] if r['is_high_score'])
        t8 = sum(1 for r in result['records'] if r['is_top8'])
        print(f"  高分牌手数: {hs}   八强牌手数: {t8}")
        print(f"  前 10 位牌手（按 final_rank 排序）:")
        for r in sorted(result['records'], key=lambda x: x['final_rank'])[:10]:
            fr = r['final_rank'] if r['final_rank'] != 9999 else "-"
            hs_mark = "★高分" if r['is_high_score'] else ""
            t8_mark = "【八强】" if r['is_top8'] else ""
            print(f"    rank={fr:<5} score={r['swiss_score']:<3} {r['archetype']:<22} {t8_mark}{hs_mark}")

    print("\n=== 自然周归类测试 ===")
    test_dates = [
        "2026-06-26 18:00:00.0",   # 周五
        "2026-06-22 10:00:00.0",   # 周一（应归到自己）
        "2026-06-28 23:59:00.0",   # 周日（应和上面同一周）
        "2026-06-29 00:01:00.0",   # 下周一（应跳到新一周）
        "2026-06-25",              # 只有日期没时间，验证兼容
        "",                        # 空值，应返回 None
    ]
    for s in test_dates:
        d = parse_event_date(s)
        if d is None:
            print(f"  {s!r:30} -> 解析失败(None)")
        else:
            print(f"  {s!r:30} -> 日期 {d} ({['周一','周二','周三','周四','周五','周六','周日'][d.weekday()]}) -> 所属周一 {week_monday(d)}")

    print("\n=== 扫描所有赛事的周分布 ===")
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    week_event_count = {}
    no_date = 0
    for path in all_files:
        with open(path, "r", encoding="utf-8") as f:
            ev = json.load(f)
        d = parse_event_date(ev.get("starttime"))
        if d is None:
            no_date += 1
            continue
        wk = week_monday(d)
        week_event_count[wk] = week_event_count.get(wk, 0) + 1
    print(f"  共 {len(all_files)} 个赛事，解析失败 {no_date} 个")
    print(f"  按自然周分布（周一日期 -> 赛事数）:")
    for wk in sorted(week_event_count):
        print(f"    {wk} 那一周: {week_event_count[wk]} 场")

    print("\n=== 单场赛事聚合测试 ===")
    with open(files[0], "r", encoding="utf-8") as f:
        ev = json.load(f)
    res = process_event(ev, archetypes)
    agg = aggregate(res["records"])
    print(f"  总牌表 {agg['total_decks']}  高分 {agg['total_high_score']}  八强 {agg['total_top8']}  Unknown {agg['unknown_count']}")
    print(f"  {'套牌':<22} {'数量':>4} {'高分':>4} {'高分占比':>8} {'八强':>4} {'八强占比':>8} {'转化率':>8}")
    for a in agg["archetypes"]:
        hs = f"{a['high_score_share']:.1%}" if a['high_score_share'] is not None else "N/A"
        t8 = f"{a['top8_share']:.1%}" if a['top8_share'] is not None else "N/A"
        cv = f"{a['conversion']:.1%}" if a['conversion'] is not None else "N/A"
        print(f"  {a['name']:<22} {a['count']:>4} {a['high_score_count']:>4} {hs:>8} {a['top8_count']:>4} {t8:>8} {cv:>8}")
    # 核对：占比应各自加起来约等于 100%
    sum_hs = sum(a['high_score_share'] for a in agg["archetypes"] if a['high_score_share'] is not None)
    sum_t8 = sum(a['top8_share'] for a in agg["archetypes"] if a['top8_share'] is not None)
    print(f"  [核对] 高分占比合计={sum_hs:.4f}  八强占比合计={sum_t8:.4f}  (应都≈1.0)")

    print("\n=== 生成区间统计 JSON ===")
    build_all_stats()
    
    print("\n=== 最佳牌表选择测试（单赛事内按套牌）===")
    # 复用前面已 process_event 的 result（第一个赛事文件）
    from collections import defaultdict
    by_arch = defaultdict(list)
    for r in result["records"]:
        by_arch[r["archetype"]].append(r)
    for arch in list(by_arch.keys())[:5]:
        best = pick_best_deck(by_arch[arch])
        main_len = sum(to_int(c.get("qty", 0)) for c in best["main_deck"]) if best["main_deck"] else 0
        side_len = sum(to_int(c.get("qty", 0)) for c in best["side_deck"]) if best["side_deck"] else 0
        print(f"  {arch:<22} 最佳: {best['player']:<14} "
              f"rank={best['final_rank']} score={best['swiss_score']} "
              f"主牌={main_len}张 备牌={side_len}张({len(best['side_deck'])}条)")

    print("\n=== 牌手对象结构探查 ===")
    first_player = event["players"][0]
    print("  牌手对象的顶层字段:", list(first_player.keys()))
    for k, v in first_player.items():
        if isinstance(v, list):
            print(f"  字段 {k!r} 是列表，长度 {len(v)}，第一个元素: {v[0] if v else '空'}")
        else:
            print(f"  字段 {k!r} = {v!r}")


