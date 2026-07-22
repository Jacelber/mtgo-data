# stats_standard.py —— MTGO standard 赛制统计模块
# 阶段一：底层工具 + 单赛事处理
# 阶段二：平均牌表 & 偏离度（固定 4 周 base + 全局 D99）

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from mtgmeta.classifier import classify_deck
from mtgmeta.legacy_rules import LegacyArchetypeRules
from mtgmeta.rules import RuleSet
from public_contract import versioned

from . import load_mtgo_context
from .classification import load_mtgo_events_for_format
from .normalize import load_rules_for_format


DEFAULT_RANGES = (1, 4, 12, 36)
SOURCE_ID = "mtgo"

# Preserve the narrower legacy public-output aliases. The broader shared OM1/SPM
# mapping is intentionally not used for deck construction metrics in P3-04.
_LEGACY_PUBLIC_CARD_ALIASES = {
    "Kavaero, Mind-Bitten": "Superior Spider-Man",
    "Leyline Weaver": "Spider Manifestation",
}


class MTGOStatisticsError(RuntimeError):
    """Raised when MTGO statistics cannot be produced safely."""


def normalize_legacy_card_name(name: str) -> str:
    stripped = name.strip()
    return _LEGACY_PUBLIC_CARD_ALIASES.get(stripped, stripped)

# ---------- 偏离度 / 平均牌表 常量 ----------
AVG_FLOOR = 0.15      # 均值低于此的卡不计入向量
MIN_SAMPLE = 8        # 4 周样本不足此数则不建 base
BASE_WEEKS = 4        # 偏离度基准：固定最近 4 个自然周
CORE_RATE = 0.8       # 出现率 >= 此值归为 Core（常备卡），否则 Flex（自选卡）
DEV_PERCENTILE = 99   # 全局归一化锚点分位（P99）
RECENT_MIN = 3        # 近端(本周)/远端(之前4周) 最小样本，不足则变化度为 null
PRIOR_WEEKS = 4       # 近期变化度的远端窗口：本周之前的 4 周

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
    """按 MTGO 官方人数-轮数对照表，用全场报名人数推断瑞士轮数。"""
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
    """高分门槛：积分严格超过总可能积分的一半，向上取整到最近的 3 的倍数。"""
    return (math.floor(rounds * 1.5 / 3) + 1) * 3


# ---------- 单赛事处理 ----------

def _as_rule_set(rules: RuleSet | LegacyArchetypeRules) -> RuleSet:
    if isinstance(rules, RuleSet):
        return rules
    if isinstance(rules, LegacyArchetypeRules):
        return rules.rule_set
    raise TypeError("MTGO statistics require a RuleSet or LegacyArchetypeRules")


def _classify_parent_identity(
    player: dict[str, Any],
    rules: RuleSet | LegacyArchetypeRules,
) -> tuple[str | None, str | None]:
    result = classify_deck(_as_rule_set(rules), player)
    if result.status == "classified":
        return result.archetype_id, result.archetype_name
    if result.status == "unknown":
        return None, None
    detail = result.conflict_kind or ", ".join(result.errors) or result.status
    raise MTGOStatisticsError(f"cannot aggregate {result.status} deck: {detail}")


def _classify_parent(player: dict[str, Any], rules: RuleSet | LegacyArchetypeRules) -> str | None:
    """Compatibility helper returning the selected parent display name."""

    _archetype_id, archetype_name = _classify_parent_identity(player, rules)
    return archetype_name


def process_event(
    event: dict[str, Any],
    rules: RuleSet | LegacyArchetypeRules,
    *,
    classifier: Callable[[dict[str, Any], RuleSet | LegacyArchetypeRules], str | None]
    | None = None,
):
    player_count = to_int(event.get("player_count"))
    rounds = rounds_from_player_count(player_count)
    threshold = high_score_threshold(rounds)
    starttime = event.get("starttime", "")
    description = event.get("description", "?")
    records = []
    for player in event.get("players", []):
        if classifier is None:
            archetype_id, archetype_name = _classify_parent_identity(player, rules)
        else:
            archetype_name = classifier(player, rules)
            archetype_id = archetype_name
        arch = archetype_name or "Unknown"
        arch_id = archetype_id or "unknown"
        swiss_score = to_int(player.get("swiss_score"))
        final_rank = to_int(player.get("final_rank"), default=9999)
        records.append({
            "archetype": arch,
            "archetype_id": arch_id,
            "is_high_score": swiss_score >= threshold,
            "is_top8": final_rank <= 8,
            "swiss_score": swiss_score,
            "final_rank": final_rank,
            "player": player.get("player", player.get("name", "?")),
            "player_count": player_count,
            "starttime": starttime,
            "main_deck": player.get("main_deck", []),
            "side_deck": player.get("sideboard", []),
            "rounds": rounds,
        })
    return {
        "description": description,
        "player_count": player_count,
        "rounds": rounds,
        "threshold": threshold,
        "starttime": starttime,
        "records": records,
    }

def parse_event_date(starttime):
    """从 starttime 取日期部分（前 10 字符 YYYY-MM-DD）。失败返回 None。"""
    if not starttime:
        return None
    try:
        return datetime.strptime(str(starttime)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def week_monday(d):
    """返回 date 所属自然周（周一到周日）的周一日期。"""
    return d - timedelta(days=d.weekday())


def aggregate(records, *, include_archetype_ids: bool = False):
    """把一批牌手记录聚合成各套牌的统计。
    场均分（avg_points_per_round）= Σ该套牌积分 / Σ对应赛事理论轮数（微观平均，0~3）。
    """
    stats = {}
    total_decks = 0
    total_high = 0
    total_top8 = 0

    for r in records:
        archetype_id = r["archetype_id"]
        name = r["archetype"]
        s = stats.setdefault(archetype_id, {"name": name, "count": 0, "high": 0,
                                            "top8": 0, "score_sum": 0, "rounds_sum": 0})
        if s["name"] != name:
            raise MTGOStatisticsError(
                f"archetype ID {archetype_id!r} resolved to multiple display names"
            )
        s["count"] += 1
        total_decks += 1
        s["score_sum"] += r.get("swiss_score", 0)
        s["rounds_sum"] += r.get("rounds", 0)
        if r["is_high_score"]:
            s["high"] += 1
            total_high += 1
        if r["is_top8"]:
            s["top8"] += 1
            total_top8 += 1

    unknown_count = stats.get("unknown", {}).get("count", 0)

    archetypes = []
    for archetype_id, s in stats.items():
        high_share = s["high"] / total_high if total_high else None
        top8_share = s["top8"] / total_top8 if total_top8 else None
        conversion = s["top8"] / s["high"] if s["high"] else None
        appr = s["score_sum"] / s["rounds_sum"] if s["rounds_sum"] else None
        item = {
            "name": s["name"],
            "count": s["count"],
            "high_score_count": s["high"],
            "high_score_share": round(high_share, 4) if high_share is not None else None,
            "top8_count": s["top8"],
            "top8_share": round(top8_share, 4) if top8_share is not None else None,
            "conversion": round(conversion, 4) if conversion is not None else None,
            "avg_points_per_round": round(appr, 2) if appr is not None else None,
        }
        if include_archetype_ids:
            item = {"id": archetype_id, **item}
        archetypes.append(item)

    archetypes.sort(key=lambda a: a["count"], reverse=True)

    return {
        "total_decks": total_decks,
        "total_high_score": total_high,
        "total_top8": total_top8,
        "unknown_count": unknown_count,
        "archetypes": archetypes,
    }


def load_events_from_directory(
    events_directory: str | Path,
    *,
    repository_root: str | Path | None = None,
    format_id: str | None = None,
):
    """Load dated event documents from one authorized, format-isolated directory."""

    paths = sorted(Path(events_directory).glob("*.json"))
    if format_id is not None:
        if repository_root is None:
            raise MTGOStatisticsError(
                "repository_root is required when enforcing an event format"
            )
        loaded, excluded = load_mtgo_events_for_format(
            paths,
            repository_root,
            format_id,
        )
        if excluded:
            details = ", ".join(
                f"{item.source_file} ({item.actual_format})" for item in excluded
            )
            raise MTGOStatisticsError(
                f"cross-format event input rejected for {format_id}: {details}"
            )
        documents = [event for _source_file, event in loaded]
    else:
        documents = [
            json.loads(path.read_text(encoding="utf-8")) for path in paths
        ]

    events = []
    for ev in documents:
        d = parse_event_date(ev.get("starttime"))
        if d is not None:
            events.append((d, ev))
    return events


def load_all_events(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
):
    """Load event input only after registry and capability authorization."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "event_statistics",
        registry_path=registry_path,
    )
    return load_events_from_directory(
        context.paths["events"],
        repository_root=context.repository_root,
        format_id=format_id,
    )


def latest_complete_week(events, today=None):
    """返回最近一个『已结束』完整周的周一。"""
    if today is None:
        today = datetime.now().date()
    weeks = sorted({week_monday(d) for d, _ in events})
    complete = [w for w in weeks if (w + timedelta(days=6)) < today]
    return complete[-1] if complete else (weeks[-1] if weeks else None)


# ================================================================
#            平均牌表 & 偏离度：向量 / 距离 / base 构建
# ================================================================

def deck_vector(record):
    """把 record 的 main_deck 转成 {规范卡名: 张数} 向量（仅主牌）。"""
    vec = {}
    for c in record.get("main_deck", []):
        name = normalize_legacy_card_name(c.get("name", "?"))
        vec[name] = vec.get(name, 0) + to_int(c.get("qty", 0))
    return vec


def mean_vector(vectors):
    """对一批牌表向量求均值向量，过滤均值 < AVG_FLOOR 的卡。"""
    if not vectors:
        return {}
    total = {}
    for v in vectors:
        for name, qty in v.items():
            total[name] = total.get(name, 0) + qty
    n = len(vectors)
    mean = {name: s / n for name, s in total.items()}
    return {name: m for name, m in mean.items() if m >= AVG_FLOOR}


def appearance_rates(vectors):
    """每张卡在多少比例的牌表中出现（qty>0）。返回 {卡名: 0-1}。"""
    if not vectors:
        return {}
    n = len(vectors)
    cnt = {}
    for v in vectors:
        for name, qty in v.items():
            if qty > 0:
                cnt[name] = cnt.get(name, 0) + 1
    return {name: c / n for name, c in cnt.items()}


def split_core_flex(mean_vec, rates, core_rate=CORE_RATE):
    """按出现率把均值向量里的卡分成 Core（常备）/ Flex（自选）两组。
    每项 {name, mean_qty, rate}，组内按均值张数降序。
    """
    core, flex = [], []
    for name, m in mean_vec.items():
        r = rates.get(name, 0.0)
        item = {"name": name, "mean_qty": round(m, 1), "rate": round(r, 3)}
        (core if r >= core_rate else flex).append(item)
    core.sort(key=lambda x: (-x["mean_qty"], x["name"]))
    flex.sort(key=lambda x: (-x["mean_qty"], x["name"]))
    return core, flex


def weighted_l1(vec, mean_vec, weights):
    """加权 L1 距离：Σ w_card × |vec张数 − 均值张数|。覆盖两侧全部卡名。"""
    names = sorted(set(vec) | set(mean_vec))
    return math.fsum(
        weights.get(name, 0.0) * abs(vec.get(name, 0) - mean_vec.get(name, 0.0))
        for name in names
    )


def normalize_dev(d, d99):
    """把原始加权 L1 距离归一化到 0-100（全局 P99 为 100 锚点）。"""
    if not d99 or d99 <= 0:
        return 0
    return min(100, round(d / d99 * 100))


def dev_denominator(mean_vec, weights):
    """偏离度绝对刻度的分母 = base 自身的加权总量 = Σ 权重 × 均值张数。
    含义：把 base 里每张卡完全拿掉所对应的加权距离，作为满分 100 的锚点。
    """
    return sum(weights.get(name, 0.0) * m for name, m in mean_vec.items())


def normalize_dev_abs(d, denom):
    """绝对刻度归一化：加权 L1 距离 / base 加权总量 × 100，截顶 100。
    0 = 与 base 完全一致；接近 100 = 几乎换掉整副 base。denom<=0 返回 0。
    """
    if not denom or denom <= 0:
        return 0
    return min(100, round(d / denom * 100))


def deck_diff(vec, mean_vec, top=8):
    """生成逐卡差异（相对均值）。返回 {fewer, more}，各含 {name, deck_qty, typical_qty}。
    前端再按最小差距过滤；这里输出较多项供其筛选。
    """
    names = sorted(set(vec) | set(mean_vec))
    rows = []
    for name in names:
        dq = vec.get(name, 0)
        tq = mean_vec.get(name, 0.0)
        rows.append({"name": name, "deck_qty": dq, "typical_qty": round(tq, 1),
                     "delta": dq - tq})
    fewer = sorted(
        [r for r in rows if r["delta"] < 0],
        key=lambda r: (r["delta"], r["name"]),
    )[:top]
    more = sorted(
        [r for r in rows if r["delta"] > 0],
        key=lambda r: (-r["delta"], r["name"]),
    )[:top]
    strip = lambda rs: [{"name": r["name"], "deck_qty": r["deck_qty"],
                         "typical_qty": r["typical_qty"]} for r in rs]
    return {"fewer": strip(fewer), "more": strip(more)}


def pick_medoid(records, mean_vec, weights):
    """从 records 中选离均值向量最近（加权 L1 最小）的真实牌表，返回该 record。"""
    if not records:
        return None
    best = None
    best_d = None
    for r in records:
        d = weighted_l1(deck_vector(r), mean_vec, weights)
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


def record_to_deck_display(record):
    """把 record 转成前端展示用的牌表结构（含选手/战绩/主备牌）。"""
    if not record:
        return None
    return {
        "player": record.get("player", "?"),
        "final_rank": record["final_rank"] if record.get("final_rank", 9999) != 9999 else None,
        "swiss_score": record.get("swiss_score"),
        "player_count": record.get("player_count"),
        "starttime": record.get("starttime", ""),
        "main_deck": merge_cards(record.get("main_deck", [])),
        "side_deck": merge_cards(record.get("side_deck", [])),
    }


def recent_change_for_arch(events, archetypes, end_monday, archetype_id, d99):
    """计算某套牌的近期变化度：
       近端 = 最近 1 完整周(end_monday 那周) 该套牌主牌平均向量
       远端 = 之前 PRIOR_WEEKS 周(不含本周) 该套牌主牌平均向量
       权重 = 远端出现率；距离 = 加权 L1；归一化 = 全局 D99。
       返回 (value, reason)：
         value 为 0-100 或 None
         reason 为 None（正常）/ "recent"（本周样本不足）/ "prior"（缺少历史构筑数据）
    """
    recent_start = end_monday
    recent_end_sunday = end_monday + timedelta(days=6)
    prior_start = end_monday - timedelta(weeks=PRIOR_WEEKS)
    prior_end_sunday = end_monday - timedelta(days=1)   # 本周之前一天

    recent_recs, prior_recs = [], []
    for d, ev in events:
        if recent_start <= d <= recent_end_sunday:
            for r in process_event(ev, archetypes)["records"]:
                if r["archetype_id"] == archetype_id:
                    recent_recs.append(r)
        elif prior_start <= d <= prior_end_sunday:
            for r in process_event(ev, archetypes)["records"]:
                if r["archetype_id"] == archetype_id:
                    prior_recs.append(r)

    if len(recent_recs) < RECENT_MIN:
        return None, "recent"
    if len(prior_recs) < RECENT_MIN:
        return None, "prior"

    recent_vecs = [deck_vector(r) for r in recent_recs]
    prior_vecs = [deck_vector(r) for r in prior_recs]
    recent_mean = mean_vector(recent_vecs)
    prior_mean = mean_vector(prior_vecs)
    weights = appearance_rates(prior_vecs)   # 以之前主流为参照系

    raw = weighted_l1(recent_mean, prior_mean, weights)
    denom = dev_denominator(prior_mean, weights)   # 分母=远端(前4周)加权总量
    return normalize_dev_abs(raw, denom), None


def build_base_pack(events, archetypes, end_monday, today=None):
    """构建固定 4 周 base 包 + 全局 D99 + 每套牌近期变化度。
    base_pack = { arch: {mean, weights, core, flex, medoid_display,
                         sample_size, recent_change, recent_change_reason} }
    """
    from collections import defaultdict
    start_monday = end_monday - timedelta(weeks=BASE_WEEKS - 1)
    end_sunday = end_monday + timedelta(days=6)

    by_arch = defaultdict(list)
    for d, ev in events:
        if start_monday <= d <= end_sunday:
            for r in process_event(ev, archetypes)["records"]:
                if r["archetype_id"] != "unknown":
                    by_arch[r["archetype_id"]].append(r)

    base_pack = {}
    all_distances = []
    for archetype_id, recs in by_arch.items():
        if len(recs) < MIN_SAMPLE:
            continue
        vectors = [deck_vector(r) for r in recs]
        mean = mean_vector(vectors)
        if not mean:
            continue
        rates = appearance_rates(vectors)
        weights = rates
        core, flex = split_core_flex(mean, rates)
        medoid = pick_medoid(recs, mean, weights)
        base_pack[archetype_id] = {
            "name": recs[0]["archetype"],
            "mean": mean,
            "weights": weights,
            "denom": dev_denominator(mean, weights),   # 绝对刻度分母
            "core": core,
            "flex": flex,
            "medoid_display": record_to_deck_display(medoid),
            "sample_size": len(recs),
            "recent_change": None,          # 下面补算
            "recent_change_reason": None,
        }
        for v in vectors:
            all_distances.append(weighted_l1(v, mean, weights))

    d99 = percentile(all_distances, DEV_PERCENTILE) if all_distances else 0.0

    # d99 就绪后，回头为每个达标套牌算近期变化度
    for archetype_id in base_pack:
        val, reason = recent_change_for_arch(
            events, archetypes, end_monday, archetype_id, d99
        )
        base_pack[archetype_id]["recent_change"] = val
        base_pack[archetype_id]["recent_change_reason"] = reason

    return base_pack, d99


def percentile(values, p):
    """线性插值百分位。values 非空。p 为 0-100。"""
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return xs[int(k)]
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


# ================================================================
#                      区间牌表详情构建
# ================================================================

def build_decks(records, base_pack, d99, *, include_archetype_ids: bool = False):
    """按套牌分组，为每套牌生成 best_deck（含偏离度/差异）与 average_deck（4 周 base）。
    返回 { arch: {best_deck, average_deck} }。
    偏离度均相对固定 4 周 base 计算。
    """
    from collections import defaultdict
    by_arch = defaultdict(list)
    for r in records:
        by_arch[r["archetype_id"]].append(r)

    result = {}
    for archetype_id, arch_records in by_arch.items():
        name = arch_records[0]["archetype"]
        best = pick_best_deck(arch_records)
        base = base_pack.get(archetype_id)

        if best and base:
            best_vec = {}
            for c in best["main_deck"]:
                best_vec[c["name"]] = best_vec.get(c["name"], 0) + to_int(c["qty"])
            raw = weighted_l1(best_vec, base["mean"], base["weights"])
            best["deviation"] = normalize_dev_abs(raw, base["denom"])
            best["deviation_diff"] = deck_diff(best_vec, base["mean"])

        if base:
            average_deck = {
                "sample_size": base["sample_size"],
                "medoid": base["medoid_display"],
                "core": base["core"],
                "flex": base["flex"],
                "recent_change": base["recent_change"],
                "recent_change_reason": base["recent_change_reason"],
            }
        else:
            average_deck = {
                "sample_size": 0,
                "medoid": None,
                "core": [],
                "flex": [],
                "recent_change": None,
                "recent_change_reason": "nobase",
            }

        if name in result:
            raise MTGOStatisticsError(
                f"multiple archetype IDs share statistics display name {name!r}"
            )
        entry = {"best_deck": best, "average_deck": average_deck}
        if include_archetype_ids:
            entry = {"archetype_id": archetype_id, **entry}
        result[name] = entry
    return result


def build_range(
    events,
    rules,
    end_monday,
    n_weeks,
    base_pack,
    d99,
    *,
    format_id: str,
):
    """聚合区间统计，并用固定 4 周 base 计算每套牌的区间平均偏离度。"""
    from collections import defaultdict
    start_monday = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)

    records = []
    for d, ev in events:
        if start_monday <= d <= end_sunday:
            records.extend(process_event(ev, rules)["records"])

    include_archetype_ids = format_id != "standard"
    agg = aggregate(records, include_archetype_ids=include_archetype_ids)

    # 区间平均偏离度：该区间内该套牌所有牌表逐副对 4 周 base 算偏离，取平均
    by_arch = defaultdict(list)
    for r in records:
        if r["archetype_id"] != "unknown":
            by_arch[r["archetype_id"]].append(r)

    avg_dev = {}
    for archetype_id, recs in by_arch.items():
        base = base_pack.get(archetype_id)
        if not base:
            avg_dev[archetype_id] = None
            continue
        devs = [normalize_dev_abs(weighted_l1(deck_vector(r), base["mean"], base["weights"]),
                                  base["denom"])
                for r in recs]
        avg_dev[archetype_id] = round(sum(devs) / len(devs)) if devs else None

    ids_by_name = {record["archetype"]: record["archetype_id"] for record in records}
    for a in agg["archetypes"]:
        aggregation_id = a.get("id") or ids_by_name[a["name"]]
        a["avg_deviation"] = avg_dev.get(aggregation_id)

    period = {
        "type": f"{n_weeks}w",
        "start": start_monday.isoformat(),
        "end": end_sunday.isoformat(),
        "weeks": n_weeks,
    }
    stats_data = versioned({
        "format": format_id,
        "source": SOURCE_ID,
        "period": period,
        **agg,
    })
    decks_data = versioned({
        "format": format_id,
        "source": SOURCE_ID,
        "period": period,
        "decks": build_decks(
            records,
            base_pack,
            d99,
            include_archetype_ids=include_archetype_ids,
        ),
    })
    return stats_data, decks_data


def build_all_stats(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
    registry_path: str | Path | None = None,
    ranges=DEFAULT_RANGES,
):
    """Build and write format-authorized MTGO range statistics."""

    root = Path(repository_root).resolve()
    context = load_mtgo_context(
        root,
        format_id,
        "event_statistics",
        registry_path=registry_path,
    )
    load_mtgo_context(
        root,
        format_id,
        "range_statistics",
        registry_path=registry_path,
    )
    normalized_ranges = tuple(ranges)
    if not normalized_ranges or any(
        not isinstance(weeks, int) or isinstance(weeks, bool) or weeks <= 0
        for weeks in normalized_ranges
    ):
        raise MTGOStatisticsError("rolling ranges must be positive integers")
    if len(set(normalized_ranges)) != len(normalized_ranges):
        raise MTGOStatisticsError("rolling ranges must be unique")

    rules = load_rules_for_format(root, format_id, registry_path=registry_path)
    events = load_events_from_directory(
        context.paths["events"],
        repository_root=context.repository_root,
        format_id=format_id,
    )
    end_monday = latest_complete_week(events, today=today)
    if end_monday is None:
        return {}

    base_pack, d99 = build_base_pack(events, rules, end_monday, today=today)
    out_dir = Path(output_directory) if output_directory is not None else context.paths["statistics"]

    index_entries = []
    documents = {}
    for n in normalized_ranges:
        data, decks = build_range(
            events,
            rules,
            end_monday,
            n,
            base_pack,
            d99,
            format_id=format_id,
        )
        fname = f"range_{n}w.json"
        decks_fname = f"decks_{n}w.json"
        documents[fname] = data
        documents[decks_fname] = decks

        index_entries.append({
            "file": fname,
            "decks_file": decks_fname,
            "type": data["period"]["type"],
            "start": data["period"]["start"],
            "end": data["period"]["end"],
            "weeks": n,
            "total_decks": data["total_decks"],
        })
    if generated_at is None:
        generated_value = datetime.now().isoformat(timespec="seconds")
    elif isinstance(generated_at, datetime):
        generated_value = generated_at.isoformat(timespec="seconds")
    else:
        generated_value = generated_at
    index = versioned({
        "format": format_id,
        "source": SOURCE_ID,
        "generated": generated_value,
        "latest_complete_week": end_monday.isoformat(),
        "base_weeks": BASE_WEEKS,
        "global_d99": round(d99, 4),
        "ranges": index_entries,
    })
    documents["index.json"] = index

    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for filename, document in documents.items():
        destination = out_dir / filename
        destination.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        written[filename] = destination
    return written


def merge_cards(card_list):
    """合并同名卡，qty 累加。卡名经 normalize_name 规范化。按卡名排序返回。"""
    merged = {}
    for c in card_list:
        name = normalize_legacy_card_name(c.get("name", "?"))
        merged[name] = merged.get(name, 0) + to_int(c.get("qty", 0))
    return [{"name": n, "qty": q} for n, q in sorted(merged.items())]


def pick_best_deck(archetype_records):
    """三级排序选最佳牌表：final_rank 最小 > player_count 最大 > starttime 最新。"""
    if not archetype_records:
        return None
    best = min(
        archetype_records,
        key=lambda r: (
            r["final_rank"],
            -r["player_count"],
            _neg_time_key(r["starttime"]),
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
    """时间越新返回值越小；解析失败记为最旧。"""
    d = parse_event_date(starttime)
    if d is None:
        return 0
    return -d.toordinal()


# ---------- 自测块（始终放在文件最末尾） ----------

if __name__ == "__main__":
    raise SystemExit("Run the repository-level stats_standard.py compatibility command")
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

    print("\n=== 生成区间统计 JSON（含 4 周 base 偏离度）===")
    build_all_stats()

    print("\n=== 平均牌表 & 偏离度验证（12 周区间，达标套牌）===")
    events = load_all_events()
    end_monday = latest_complete_week(events)
    base_pack, d99 = build_base_pack(events, archetypes, end_monday)
    print(f"  全局 D99 = {d99:.3f}，达标套牌 {len(base_pack)} 个")
    data12, decks12 = build_range(events, archetypes, end_monday, 12, base_pack, d99)

    # 取达标套牌里样本较大的前几个展示
    qualified = sorted(base_pack.items(), key=lambda kv: -kv[1]["sample_size"])[:5]
    for arch, base in qualified:
        entry = decks12["decks"].get(arch, {})
        best = entry.get("best_deck")
        arch_agg = next((a for a in data12["archetypes"] if a["name"] == arch), {})
        core_names = ", ".join(f"{c['name']}×{c['mean_qty']}" for c in base["core"][:5])
        flex_names = ", ".join(f"{c['name']}({c['rate']})" for c in base["flex"][:5])
        print(f"\n  【{arch}】 4周样本 {base['sample_size']}")
        print(f"    Core(常备): {core_names}")
        print(f"    Flex(自选): {flex_names}")
        if base["medoid_display"]:
            m = base["medoid_display"]
            print(f"    实际典型牌表: {m['player']} rank={m['final_rank']} score={m['swiss_score']}")
        if best and "deviation" in best:
            print(f"    最佳牌表单副偏离度: {best['deviation']}")
            fewer = best["deviation_diff"]["fewer"][:3]
            more = best["deviation_diff"]["more"][:3]
            print(f"      少带: {[(r['name'], r['deck_qty'], r['typical_qty']) for r in fewer]}")
            print(f"      多带: {[(r['name'], r['deck_qty'], r['typical_qty']) for r in more]}")
        print(f"    12周区间平均偏离度: {arch_agg.get('avg_deviation')}")
        rc = base["recent_change"]
        rc_reason = base["recent_change_reason"]
        print(f"    近期变化度(本周 vs 之前4周): {rc if rc is not None else '—(' + str(rc_reason) + ')'}")

    print("\n=== 各区间平均偏离度对比（验证跨区间不同）===")
    for arch, base in qualified[:3]:
        line = [f"{arch} (4周样本{base['sample_size']}):"]
        for n in [1, 4, 12, 36]:
            d, _ = build_range(events, archetypes, end_monday, n, base_pack, d99)
            a = next((x for x in d["archetypes"] if x["name"] == arch), {})
            line.append(f"{n}w={a.get('avg_deviation')}")
        print("  " + "  ".join(line))
