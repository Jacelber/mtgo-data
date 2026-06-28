import json

with open("page_source.html", "r", encoding="utf-8") as f:
    html = f.read()

start = html.find("window.MTGO.decklists.data =") + len("window.MTGO.decklists.data =")
end = html.find("};", start) + 1
json_text = html[start:end].strip()
data = json.loads(json_text)

print("=== standings 是什么样（看前 2 条）===")
print(json.dumps(data["standings"][:2], indent=2, ensure_ascii=False))

print("\n=== final_rank 是什么样（看前 2 条）===")
print(json.dumps(data["final_rank"][:2], indent=2, ensure_ascii=False))
