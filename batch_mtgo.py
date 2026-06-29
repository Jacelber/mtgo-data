import requests
import time
import json
import re
import os
from datetime import datetime, timedelta

# ============ 配置区 ============
# === 月份设置 ===
# 默认 USE_RECENT_MONTHS = True，自动抓"最近两个月"（当月 + 上月，跨月兜底补漏）。
# 想补抓某个特定历史月份时，把它改成 False，并填好 TARGET_YEAR / TARGET_MONTH。
USE_RECENT_MONTHS = True
TARGET_YEAR = 2026
TARGET_MONTH = 5


def get_target_months():
    """返回要抓的 (年, 月) 列表"""
    if not USE_RECENT_MONTHS:
        return [(TARGET_YEAR, TARGET_MONTH)]
    now = datetime.now()
    # 当月
    months = [(now.year, now.month)]
    # 上月（正确处理 1 月跨年的情况）
    if now.month == 1:
        months.append((now.year - 1, 12))
    else:
        months.append((now.year, now.month - 1))
    return months

DATA_DIR = "data"                      # 数据存这个文件夹
RECORD_FILE = "fetched.txt"            # 记录已抓过的赛事
FORMATS = ("standard", "legacy", "pioneer", "pauper", "vintage", "modern")
DELAY_SECONDS = 4                      # 每个赛事之间停顿几秒（礼貌 & 防封）

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# ============ 下载（带重试） ============
def download(url):
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=90)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"    下载失败({attempt+1}/5): {e}")
            time.sleep(5)
    return None


# ============ 解析赛事 JSON（括号配对法） ============
def extract_data(html):
    marker = "window.MTGO.decklists.data ="
    start = html.find(marker)
    if start == -1:
        return None
    brace_start = html.find("{", start)
    depth = 0
    in_string = False
    escape = False
    for i in range(brace_start, len(html)):
        ch = html[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(html[brace_start:i + 1])
    return None

def is_data_complete(data):
    """检查解析出的赛事数据是否包含我们需要的关键字段，残缺则视为失败"""
    if data is None:
        return False
    required = ["event_id", "description", "player_count", "decklists"]
    for field in required:
        if field not in data:
            return False
    if not data["decklists"]:   # decklists 不能是空的
        return False
    return True

# ============ 牌表简化 ============
def cards_to_simple(card_list):
    return [{"name": c["card_attributes"]["card_name"].strip(),
             "qty": int(c["qty"])} for c in card_list]


# ============ 整理成干净数据 ============
def build_clean_data(data):
    standings_by_id = {s["loginid"]: s for s in data.get("standings", [])}
    finalrank_by_id = {f["loginid"]: f for f in data.get("final_rank", [])}

    players = []
    for deck in data["decklists"]:
        lid = deck["loginid"]
        standing = standings_by_id.get(lid, {})
        final = finalrank_by_id.get(lid, {})
        score = standing.get("score")
        swiss_wins = int(score) // 3 if score is not None else None
        players.append({
            "player": deck["player"],
            "loginid": lid,
            "swiss_rank": standing.get("rank"),
            "swiss_score": score,
            "swiss_wins": swiss_wins,
            "opp_match_win_pct": standing.get("opponentmatchwinpercentage"),
            "game_win_pct": standing.get("gamewinpercentage"),
            "final_rank": final.get("rank"),
            "main_deck": cards_to_simple(deck["main_deck"]),
            "sideboard": cards_to_simple(deck["sideboard_deck"]),
        })

    pc = data["player_count"]
    player_count = pc.get("players") if isinstance(pc, dict) else pc

    return {
        "event_id": data["event_id"],
        "description": data["description"],
        "format": data.get("format"),
        "starttime": data.get("starttime"),
        "player_count": player_count,
        "inplayoffs": data.get("inplayoffs"),
        "players": players,
    }



# ============ 从链接里取赛制和日期 ============
def parse_link(link):
    name = link.replace("/decklist/", "")
    m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    date_str = m.group(1) if m else None
    # 精确取链接开头的赛制词（到第一个连字符之前），避免 premodern 被当成 modern
    first_word = name.split("-")[0]
    fmt = first_word if first_word in FORMATS else "other"
    return fmt, date_str



# ============ 已抓记录的读写 ============
def load_fetched():
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_fetched(link):
    with open(RECORD_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


# ============ 主流程 ============
def main():
    target_months = get_target_months()
    print(f"本次将抓取这些月份: {target_months}\n")

    fetched = load_fetched()
    total_new = 0
    total_skip_already = 0
    total_skip_noplayoff = 0

    for (year, month) in target_months:
        list_url = f"https://www.mtgo.com/decklists/{year}/{month:02d}"
        print(f"\n========== 处理 {year}-{month:02d} ==========")
        print("下载赛事列表页...")
        list_html = download(list_url)
        if list_html is None:
            print(f"{year}-{month:02d} 列表页下载失败，跳过这个月。")
            continue

        all_links = sorted(set(re.findall(r'/decklist/[a-zA-Z0-9\-]+', list_html)))
        candidates = []
        for link in all_links:
            name = link.lower()
            if "league" in name:
                continue
            fmt, date_str = parse_link(link)
            if fmt == "other" or date_str is None:
                continue
            candidates.append(link)

        print(f"{year}-{month:02d} 初筛后有 {len(candidates)} 个候选赛事\n")

        for link in candidates:
            if link in fetched:
                total_skip_already += 1
                continue

            full_url = "https://www.mtgo.com" + link
            print(f"抓取: {link}")

            raw = None
            for try_round in range(4):
                html = download(full_url)
                if html is None:
                    print(f"    下载彻底失败，第 {try_round+1} 轮，等待后重试...")
                else:
                    candidate = extract_data(html)
                    if is_data_complete(candidate):
                        raw = candidate
                        break
                    else:
                        print(f"    解析到的数据残缺/为空，第 {try_round+1} 轮，等待后重试...")
                if try_round < 3:
                    time.sleep(15)

            if raw is None:
                print("  多轮重试后仍失败，跳过（不记录，下次运行再试）")
                continue

            clean = build_clean_data(raw)

            if str(clean.get("inplayoffs")) != "1":
                print(f"  无单淘(inplayoffs={clean.get('inplayoffs')})，排除")
                mark_fetched(link)
                fetched.add(link)
                total_skip_noplayoff += 1
                time.sleep(DELAY_SECONDS)
                continue

            fmt, date_str = parse_link(link)
            folder = os.path.join(DATA_DIR, fmt)
            os.makedirs(folder, exist_ok=True)
            fname = f"{clean['description'].replace(' ', '_')}_{clean['event_id']}.json"
            path = os.path.join(folder, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(clean, f, ensure_ascii=False, indent=2)

            print(f"  已保存 {path}（{len(clean['players'])} 位牌手）")
            mark_fetched(link)
            fetched.add(link)
            total_new += 1
            time.sleep(DELAY_SECONDS)

    print(f"\n=== 全部完成 ===")
    print(f"新抓取: {total_new} 个")
    print(f"跳过(已抓过): {total_skip_already} 个")
    print(f"排除(无单淘): {total_skip_noplayoff} 个")



if __name__ == "__main__":
    main()
