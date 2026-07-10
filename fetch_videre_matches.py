# fetch_videre_matches.py — 抓取 Videre 逐轮对局，落地存盘（只抓不算）
# 用法:
#   python fetch_videre_matches.py                 # 抓 fetched.txt 里所有 Standard 赛事
#   python fetch_videre_matches.py --force         # 忽略已存在文件，全部重抓
#   python fetch_videre_matches.py 12846517        # 只抓指定 event_id

import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = "https://api.videreproject.com"
FORMAT = "standard"
FETCHED_FILE = "fetched.txt"
OUT_DIR = os.path.join("data", "standard", "mtgo", "matches")

LINE_RE = re.compile(r"standard-.*?\d{4}-\d{2}-\d{2}(\d+)\s*$")


class NoResults(Exception):
    """Videre 对该 event_id 无收录（API 返回 400 No results found）。"""


def api_get(path, params):
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "videre-fetch/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Videre 在“查无结果”时返回 400 + message: "No results found."
        if e.code == 400:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = {}
            if str(body.get("message", "")).lower().startswith("no results"):
                raise NoResults()
        raise  # 其他 HTTP 错误照常抛出


def fetch_all_matches(event_id):
    """分页拉全一场赛事的所有对局行。无收录时抛 NoResults。"""
    rows, offset = [], 0
    while True:
        body = api_get(f"/matches/{FORMAT}",
                       {"event_id": event_id, "limit": 500, "offset": offset})
        rows.extend(body.get("data", []))
        meta = body.get("meta", {})
        if meta.get("has_more") and meta.get("next_offset") is not None:
            offset = meta["next_offset"]
        else:
            break
    return rows


def event_ids_from_fetched():
    if not os.path.exists(FETCHED_FILE):
        print(f"找不到 {FETCHED_FILE}")
        return []
    ids, seen = [], set()
    with open(FETCHED_FILE, encoding="utf-8") as f:
        for line in f:
            m = LINE_RE.search(line.strip())
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                ids.append(m.group(1))
    return ids


def main():
    args = sys.argv[1:]
    force = "--force" in args
    explicit = [a for a in args if a.isdigit()]

    os.makedirs(OUT_DIR, exist_ok=True)
    event_ids = explicit if explicit else event_ids_from_fetched()
    print(f"待处理 Standard 赛事: {len(event_ids)} 场")

    fetched = skipped = notfound = failed = 0
    missing = []
    for eid in event_ids:
        out_path = os.path.join(OUT_DIR, f"{eid}.json")
        if os.path.exists(out_path) and not force:
            skipped += 1
            continue
        try:
            rows = fetch_all_matches(eid)
            if not rows:
                print(f"  [无] {eid}: 返回空")
                notfound += 1
                missing.append(eid)
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"event_id": int(eid), "matches": rows}, f,
                          ensure_ascii=False, indent=2)
            non_bye = sum(1 for r in rows if not r.get("isbye"))
            print(f"  [存] {eid}: {len(rows)} 行 (非轮空 {non_bye})")
            fetched += 1
            time.sleep(0.3)
        except NoResults:
            print(f"  [无] {eid}: Videre 未收录该赛事")
            notfound += 1
            missing.append(eid)
        except Exception as e:
            print(f"  [错] {eid}: {e}")
            failed += 1

    print(f"\n=== 汇总 ===")
    print(f"新抓取: {fetched} | 跳过(已存在): {skipped} | "
          f"未收录: {notfound} | 失败: {failed}")
    if missing:
        print(f"Videre 未收录的赛事 ({len(missing)}): {missing}")


if __name__ == "__main__":
    main()
