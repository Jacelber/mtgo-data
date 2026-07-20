import time
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
import sys

SHARED_SRC = Path(__file__).resolve().parent / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.mtgo.fetch import (
    MTGOFetchError,
    MTGOParseError,
    discover_event_links,
    download_page as shared_download_page,
    extract_event_data,
    is_event_data_complete,
    load_fetched as shared_load_fetched,
    mark_fetched as shared_mark_fetched,
    parse_event_link,
    save_event,
)
from mtgmeta.mtgo.normalize import cards_to_simple as shared_cards_to_simple
from mtgmeta.mtgo.normalize import normalize_event

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

# ============ 下载（带重试） ============
def download(url):
    try:
        return shared_download_page(
            url,
            on_error=lambda attempt, attempts, error: print(
                f"    下载失败({attempt}/{attempts}): {error}"
            ),
        )
    except MTGOFetchError:
        return None


# ============ 解析赛事 JSON（括号配对法） ============
def extract_data(html):
    try:
        return extract_event_data(html)
    except MTGOParseError as exc:
        if isinstance(exc.__cause__, JSONDecodeError):
            raise exc.__cause__
        return None

def is_data_complete(data):
    """检查解析出的赛事数据是否包含我们需要的关键字段，残缺则视为失败"""
    return is_event_data_complete(data)

# ============ 牌表简化 ============
def cards_to_simple(card_list):
    return shared_cards_to_simple(card_list)


# ============ 整理成干净数据 ============
def build_clean_data(data):
    return normalize_event(data, include_inplayoffs=True)



# ============ 从链接里取赛制和日期 ============
def parse_link(link):
    return parse_event_link(link, FORMATS)



# ============ 已抓记录的读写 ============
def load_fetched():
    return shared_load_fetched(RECORD_FILE)

def mark_fetched(link):
    shared_mark_fetched(RECORD_FILE, link)


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

        candidates = discover_event_links(list_html, FORMATS)

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
            folder = Path(DATA_DIR) / fmt
            path = save_event(clean, folder)

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
