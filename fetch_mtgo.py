from pathlib import Path
from json import JSONDecodeError
import sys

SHARED_SRC = Path(__file__).resolve().parent / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.mtgo.fetch import (
    MTGOFetchError,
    MTGOParseError,
    download_page as shared_download_page,
    extract_event_data,
    save_event,
)
from mtgmeta.mtgo.normalize import cards_to_simple as shared_cards_to_simple
from mtgmeta.mtgo.normalize import normalize_event


def download_page(url):
    """下载赛事页面，带重试和长超时（应对 MTGO 服务器慢）"""
    try:
        return shared_download_page(
            url,
            on_attempt=lambda attempt, attempts: print(f"  下载尝试 {attempt}/{attempts} ..."),
            on_error=lambda _attempt, _attempts, error: print(f"    失败: {error}"),
        )
    except MTGOFetchError as exc:
        raise RuntimeError("下载失败：五次尝试都没成功") from exc


def extract_data(html):
    """从页面源码里把那段 JSON 抠出来并解析（用括号配对精确定位结尾）"""
    try:
        return extract_event_data(html)
    except MTGOParseError as exc:
        if isinstance(exc.__cause__, JSONDecodeError):
            raise exc.__cause__
        if "marker" in str(exc):
            raise RuntimeError("页面里没找到数据标记，可能网站结构变了") from exc
        raise RuntimeError("没找到 JSON 的结尾，数据可能不完整") from exc



def cards_to_simple(card_list):
    """把一份牌（主牌或备牌）简化成 [{name, qty}, ...] 的清爽格式"""
    return shared_cards_to_simple(card_list)


def build_clean_data(data):
    """把原始数据整理成：赛事信息 + 每位牌手(名字/排名/分数/胜率/牌表)"""
    return normalize_event(data, include_inplayoffs=False)


def main():
    url = "https://www.mtgo.com/decklist/modern-challenge-64-2026-06-2712845671"

    print("开始下载页面...")
    html = download_page(url)

    print("解析数据...")
    raw = extract_data(html)
    clean = build_clean_data(raw)

    # 存成文件，文件名用赛事名
    filename = save_event(clean, Path.cwd()).name

    print(f"\n完成！已保存到 {filename}")
    print(f"赛事: {clean['description']}  共 {clean['player_count']} 人")
    print(f"整理出 {len(clean['players'])} 位牌手的数据")

    # 顺便打印第一位牌手的概况，方便你眼睛核对
    p = clean["players"][0]
    print(f"\n示例牌手: {p['player']}")
    print(f"  瑞士轮名次 {p['swiss_rank']}, 积分 {p['swiss_score']} (约 {p['swiss_wins']} 胜)")
    print(f"  最终排名: {p['final_rank']}")
    print(f"  主牌 {len(p['main_deck'])} 种, 备牌 {len(p['sideboard'])} 种")
    print(f"\n  === {p['player']} 的完整主牌 ===")
    main_total = 0
    for card in p["main_deck"]:
        print(f"    {card['qty']:>2} {card['name']}")
        main_total += card["qty"]
    print(f"  主牌合计: {main_total} 张")

    print(f"\n  === {p['player']} 的完整备牌 ===")
    side_total = 0
    for card in p["sideboard"]:
        print(f"    {card['qty']:>2} {card['name']}")
        side_total += card["qty"]
    print(f"  备牌合计: {side_total} 张")



if __name__ == "__main__":
    main()
