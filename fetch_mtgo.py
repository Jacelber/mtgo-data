import requests
import time
import json
from datetime import datetime


def download_page(url):
    """下载赛事页面，带重试和长超时（应对 MTGO 服务器慢）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for attempt in range(5):
        try:
            print(f"  下载尝试 {attempt+1}/5 ...")
            resp = requests.get(url, headers=headers, timeout=90)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"    失败: {e}")
            time.sleep(5)
    raise RuntimeError("下载失败：五次尝试都没成功")


def extract_data(html):
    """从页面源码里把那段 JSON 抠出来并解析（用括号配对精确定位结尾）"""
    marker = "window.MTGO.decklists.data ="
    start = html.find(marker)
    if start == -1:
        raise RuntimeError("页面里没找到数据标记，可能网站结构变了")
    # 从标记后面第一个 { 开始
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
                    json_text = html[brace_start:i + 1]
                    return json.loads(json_text)
    raise RuntimeError("没找到 JSON 的结尾，数据可能不完整")



def cards_to_simple(card_list):
    """把一份牌（主牌或备牌）简化成 [{name, qty}, ...] 的清爽格式"""
    result = []
    for card in card_list:
        name = card["card_attributes"]["card_name"].strip()
        qty = int(card["qty"])
        result.append({"name": name, "qty": qty})
    return result


def build_clean_data(data):
    """把原始数据整理成：赛事信息 + 每位牌手(名字/排名/分数/胜率/牌表)"""

    # 先把 standings 和 final_rank 按 loginid 建成查找表，方便对应
    standings_by_id = {s["loginid"]: s for s in data.get("standings", [])}
    finalrank_by_id = {f["loginid"]: f for f in data.get("final_rank", [])}

    players = []
    for deck in data["decklists"]:
        lid = deck["loginid"]
        standing = standings_by_id.get(lid, {})
        final = finalrank_by_id.get(lid, {})

        # 瑞士轮积分换算成胜场数（每胜 3 分）
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
            "final_rank": final.get("rank"),     # 有值表示进了淘汰赛
            "main_deck": cards_to_simple(deck["main_deck"]),
            "sideboard": cards_to_simple(deck["sideboard_deck"]),
        })

    clean = {
        "event_id": data["event_id"],
        "description": data["description"],
        "format": data["format"],
        "starttime": data["starttime"],
         "player_count": data["player_count"].get("players") if isinstance(data["player_count"], dict) else data["player_count"],
        "players": players,
    }
    return clean


def main():
    url = "https://www.mtgo.com/decklist/modern-challenge-64-2026-06-2712845671"

    print("开始下载页面...")
    html = download_page(url)

    print("解析数据...")
    raw = extract_data(html)
    clean = build_clean_data(raw)

    # 存成文件，文件名用赛事名
    filename = f"{clean['description'].replace(' ', '_')}_{clean['event_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

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
