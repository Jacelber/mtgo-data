# gen_meta.py —— 生成前端用的元信息（规则最后更新时间 / 数据最后更新时间）
import os
import json
import subprocess
from datetime import datetime, timezone

RULES_FILE = "my_archetypes/standard.yaml"
OUT_DIR = os.path.join("stats", "standard", "mtgo")
OUT_FILE = os.path.join(OUT_DIR, "meta.json")


def rules_last_commit_iso():
    """取 standard.yaml 的 git 最后提交时间（ISO8601，作者提交日期）。
    取不到（比如浅克隆无历史）时返回 None。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", RULES_FILE],
            capture_output=True, text=True, check=True,
        )
        val = out.stdout.strip()
        return val or None
    except Exception:
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = {
        "format": "standard",
        "source": "mtgo",
        # 套牌类型特征（分类规则）最后更新时间：取 standard.yaml 的 git 提交时间
        "rules_updated": rules_last_commit_iso(),
        # 本次自动数据更新时间（UTC）
        "data_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"写出 {OUT_FILE}: rules_updated={meta['rules_updated']}, "
          f"data_updated={meta['data_updated']}")


if __name__ == "__main__":
    main()
