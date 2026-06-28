import re

with open("list_page.html", "r", encoding="utf-8") as f:
    html = f.read()

links = sorted(set(re.findall(r'/decklist/[a-zA-Z0-9\-]+', html)))

# 你要的赛制
FORMATS = ("standard", "legacy", "pioneer", "pauper", "vintage", "modern")

def keep_link(link):
    name = link.lower()
    if "league" in name:           # 排除所有 league
        return False
    # 必须属于指定赛制之一
    if not any(fmt in name for fmt in FORMATS):
        return False
    return True

filtered = [l for l in links if keep_link(l)]

print(f"链接初筛后保留 {len(filtered)} 个赛事（待下载后再按是否有单淘精筛）：\n")
for link in filtered:
    print(link)
