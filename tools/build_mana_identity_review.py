"""Build the Owner review table for unreviewed mana identities."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlencode

import yaml

from mtgmeta.mana_identity import load_mana_identities, required_mana_identity_ids


FORMAT_LABELS = {
    "standard": "标准",
    "modern": "摩登",
    "pauper": "Pauper",
    "pioneer": "先驱",
}
CODE_PREFIXES = {
    "standard": "S",
    "modern": "M",
    "pauper": "P",
    "pioneer": "PI",
}
COLOR_LABELS = {
    "w": "白",
    "u": "蓝",
    "b": "黑",
    "r": "红",
    "g": "绿",
    "c": "无色",
}


def names(root: Path) -> dict[tuple[str, str], dict]:
    document = yaml.safe_load(
        (root / "configs/mtgo_archetype_names.yaml").read_text(encoding="utf-8")
    )
    result = {}
    for item in document["names"]:
        identity_id = item["parent_id"]
        if item.get("subtype_id"):
            identity_id += "/" + item["subtype_id"]
        result[(item["format"], identity_id)] = item
    return result


def deck_evidence(root: Path, format_id: str, identity_id: str) -> dict | None:
    path = root / "stats" / format_id / "mtgo" / "decks_36w.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    parent_id, _, subtype_id = identity_id.partition("/")
    parent = next(
        (
            item
            for item in document.get("decks", {}).values()
            if item.get("archetype_id") == parent_id
        ),
        None,
    )
    if parent is None:
        return None
    record = parent
    if subtype_id:
        record = next(
            (item for item in parent.get("subtypes", []) if item.get("id") == subtype_id),
            None,
        )
        if record is None:
            return None
    deck = record.get("best_deck") or record.get("average_deck", {}).get("medoid")
    if not deck:
        return None
    query = urlencode(
        {
            "format": format_id,
            "product": "mtgo-statistics",
            "range": 36,
            "detail": identity_id,
            "lang": "zh",
        }
    )
    return {
        "event_id": str(deck.get("event_id", "")),
        "rank": deck.get("final_rank"),
        "player": deck.get("player"),
        "url": "/index.html?" + query,
    }


def basis_label(value: str | None) -> str:
    if not value:
        return "待核对"
    if value.startswith("taxonomy label:"):
        return "按分类名称中的颜色组合生成"
    if value == "same identity in another public format":
        return "沿用其他公开赛制的同名身份"
    if value.startswith("inherits candidate from parent"):
        return "与父类使用同一组颜色"
    return "按代表牌表与分类定义生成"


def build(root: Path, output: Path) -> None:
    catalog = names(root)
    formats = load_mana_identities(root)
    rows = []
    for format_id, entries in formats.items():
        required = required_mana_identity_ids(root, format_id)
        candidates = [
            (identity_id, entries[identity_id])
            for identity_id in sorted(required)
            if entries[identity_id].status == "candidate"
        ]
        for index, (identity_id, entry) in enumerate(candidates, 1):
            name = catalog.get((format_id, identity_id), {})
            rows.append(
                {
                    "code": f"{CODE_PREFIXES[format_id]}{index:02d}",
                    "format": format_id,
                    "format_label": FORMAT_LABELS.get(format_id, format_id),
                    "identity_id": identity_id,
                    "chinese": name.get("chinese", identity_id),
                    "english": name.get("english", identity_id),
                    "colors": list(entry.colors),
                    "basis": basis_label(entry.basis),
                    "priority_review": entry.basis == "representative deck and taxonomy",
                    "evidence": deck_evidence(root, format_id, identity_id),
                }
            )

    output.mkdir(parents=True, exist_ok=True)
    (output / "review.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sections = []
    for format_id in formats:
        selected = [row for row in rows if row["format"] == format_id]
        body = []
        for row in selected:
            icons = "".join(
                f'<img src="/assets/images/mana/{color}.svg" alt="{html.escape(COLOR_LABELS[color])}">'
                for color in row["colors"]
            )
            color_text = "、".join(COLOR_LABELS[color] for color in row["colors"])
            evidence = row["evidence"]
            if evidence:
                rank = f'第{evidence["rank"]}名' if evidence.get("rank") else "牌表"
                label = " / ".join(
                    value
                    for value in (evidence.get("event_id"), rank, evidence.get("player"))
                    if value
                )
                evidence_html = f'<a href="{html.escape(evidence["url"])}" target="_blank">{html.escape(label)}</a>'
            else:
                evidence_html = '<span class="muted">36周内无公开牌表</span>'
            search = " ".join(
                str(row[key]) for key in ("code", "identity_id", "chinese", "english")
            ).lower()
            body.append(
                f'<tr data-search="{html.escape(search)}" data-priority="{str(row["priority_review"]).lower()}">'
                f'<td class="code">{row["code"]}</td>'
                f'<td><strong>{html.escape(row["chinese"])}</strong><small>{html.escape(row["english"])}</small>'
                f'<code>{html.escape(row["identity_id"])}</code></td>'
                f'<td><span class="colors">{icons}</span><span>{html.escape(color_text)}</span></td>'
                f'<td>{html.escape(row["basis"])}</td><td>{evidence_html}</td></tr>'
            )
        sections.append(
            f'<section id="{format_id}"><h2>{html.escape(FORMAT_LABELS.get(format_id, format_id))}'
            f' <span>{len(selected)} 项</span></h2><div class="table-wrap"><table><thead><tr>'
            '<th>编号</th><th>套牌身份</th><th>候选指示色</th><th>生成依据</th><th>代表牌表</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'
        )

    page = f'''<!doctype html>
<html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>全赛制指示色候选审阅</title>
<style>
:root{{--ink:#173c39;--muted:#667b77;--line:#d7e2dc;--paper:#fff;--bg:#f1f5f1;--accent:#126b60}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:1440px;margin:auto;padding:24px}} header{{position:sticky;top:0;z-index:2;background:rgba(241,245,241,.96);padding:10px 0 16px}}
h1{{margin:0 0 8px;font-size:26px}} p{{margin:6px 0}} nav{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}
nav a{{padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:white;color:var(--accent);text-decoration:none}}
input[type=search]{{width:min(520px,100%);padding:10px 12px;border:1px solid #aabcb5;border-radius:8px;font:inherit}}
header label{{display:block;margin-top:10px;color:var(--muted)}}
section{{margin:22px 0;background:var(--paper);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
h2{{margin:0;padding:14px 16px;font-size:20px;border-bottom:1px solid var(--line)}} h2 span{{color:var(--muted);font-size:14px}}
.table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;min-width:900px}} th,td{{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #edf1ee}}
th{{position:sticky;top:0;background:#f8faf8}} td small,td code{{display:block;color:var(--muted)}} td code{{font-size:12px;margin-top:3px}}
.code{{font-weight:700;color:var(--accent)}} .colors{{display:flex;gap:3px;margin-bottom:4px}} .colors img{{width:22px;height:22px}}
.muted{{color:var(--muted)}} tr[hidden]{{display:none}} a{{color:var(--accent)}}
</style>
<main><header><h1>全赛制指示色候选审阅</h1>
<p>共 {len(rows)} 项。已有指示色保持不变；本页只列新增候选。无色必须显示 c，本批候选没有空颜色。</p>
<p>候选在确认前保持未批准状态，公共发布门会主动阻止上线。</p>
<nav>{''.join(f'<a href="#{key}">{FORMAT_LABELS.get(key,key)}</a>' for key in formats)}</nav>
<input id="search" type="search" placeholder="搜索编号、名称或身份 ID">
<label><input id="priority" type="checkbox"> 只看需要按牌表或分类定义重点核对的候选</label></header>
{''.join(sections)}</main>
<script>const input=document.querySelector('#search'),priority=document.querySelector('#priority');function apply(){{const q=input.value.trim().toLowerCase();document.querySelectorAll('tbody tr').forEach(row=>row.hidden=(q&&!row.dataset.search.includes(q))||(priority.checked&&row.dataset.priority!=="true"));}}input.addEventListener('input',apply);priority.addEventListener('change',apply);</script>
</html>'''
    (output / "index.html").write_text(page, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/mana-identity-review")
    )
    args = parser.parse_args()
    root = args.repository_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    build(root, output)
    print(f"Generated mana identity review: {output / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
