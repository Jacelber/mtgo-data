# verify_match_names.py — 比对官方数据与 Videre 的选手名匹配率
# 用法:
#   python verify_match_names.py <官方json路径> <event_id>
# 例:
#   python verify_match_names.py data/standard/Standard_Challenge_32_12846517.json

import sys
import json
import urllib.request
import urllib.parse

BASE = "https://api.videreproject.com"
FORMAT = "standard"


def api_get(path, params):
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "videre-verify/0.2"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_rows(path, params):
    rows, offset = [], 0
    while True:
        p = dict(params, limit=500, offset=offset)
        body = api_get(path, p)
        rows.extend(body.get("data", []))
        meta = body.get("meta", {})
        if meta.get("has_more") and meta.get("next_offset") is not None:
            offset = meta["next_offset"]
        else:
            break
    return rows


def main():
    if len(sys.argv) < 3:
        print("用法: python verify_match_names.py <官方json路径> <event_id>")
        return
    official_path, event_id = sys.argv[1], sys.argv[2]

    # 官方选手名
    with open(official_path, encoding="utf-8") as f:
        official = json.load(f)
    off_names = {p["player"] for p in official.get("players", []) if p.get("player")}

    # Videre 选手名（对局行里的 player 字段）
    matches = fetch_all_rows(f"/matches/{FORMAT}", {"event_id": event_id})
    vid_names = {m["player"] for m in matches if not m.get("isbye") and m.get("player")}

    print(f"官方选手数: {len(off_names)}")
    print(f"Videre 选手数: {len(vid_names)}")

    # 精确匹配（区分大小写）
    exact = off_names & vid_names
    print(f"\n精确匹配(区分大小写): {len(exact)} / {len(off_names)} "
          f"= {100*len(exact)/max(len(off_names),1):.1f}%")

    # 忽略大小写匹配
    off_lower = {n.lower(): n for n in off_names}
    vid_lower = {n.lower(): n for n in vid_names}
    ci = set(off_lower) & set(vid_lower)
    print(f"忽略大小写匹配: {len(ci)} / {len(off_names)} "
          f"= {100*len(ci)/max(len(off_names),1):.1f}%")

    # 大小写不一致的（忽略能匹配但精确匹配不上的）
    case_diff = [(off_lower[k], vid_lower[k]) for k in ci
                 if off_lower[k] != vid_lower[k]]
    if case_diff:
        print(f"\n大小写不一致的名字 ({len(case_diff)} 个): 官方 | Videre")
        for o, v in case_diff[:20]:
            print(f"    {o}  |  {v}")

    # 官方有、Videre 完全没有（连忽略大小写也匹配不上）
    off_only = [n for n in off_names if n.lower() not in vid_lower]
    if off_only:
        print(f"\n官方有但 Videre 缺失 ({len(off_only)} 个): {sorted(off_only)}")

    # Videre 有、官方没有
    vid_only = [n for n in vid_names if n.lower() not in off_lower]
    if vid_only:
        print(f"\nVidere 有但官方缺失 ({len(vid_only)} 个): {sorted(vid_only)}")


if __name__ == "__main__":
    main()
