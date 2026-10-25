# Standard 黑绿地落

额外黑色来自备牌 Dark Knight’s Greatsword 1，备牌另有 Swamp 1。按共享规则普通色源＋正常咒语应计黑；Owner 已批准沿用现有按色组分父类的维护方式，新增 golgari-landfall（Golgari Landfall／黑绿地落）。复用纯绿／红绿路线结构：Mightform Harmonizer ≥1、Sazh's Chocobo ≥4、Fabled Passage ≥4、Earthbender Ascension ≥3；只另要求正常 BG 用色，不强制 Greatsword 或 Swamp。已加入规则，三类通过同一 YAML anchor 共用结构条件；中英文名称与前端 BG 标识已同步。77 项受影响检查通过，Ruff 检查通过。标准 7,148 条同输入全量回放只有该副发生身份变化：Unknown → Golgari Landfall。待确认的纳雅地落仍为 Unknown，仅多出新父类的颜色不匹配诊断；其余 7,146 条状态、身份、匹配和错误均不变。

增量证据：`/workspace/scratch/classifier-round1/golgari-landfall-incremental-proof.json`。原始输入 SHA、记录集合、历史基线未改。尚未发布。

## mtgo:standard:12856158:5

来源：`data/standard/Standard_Challenge_32_Special_12856158.json#players/5`

主牌（60）

```text
2 Glimpse the Core
4 Fabled Passage
4 Llanowar Elves
4 Mightform Harmonizer
4 Sazh's Chocobo
4 Earthbender Ascension
1 Surrak, Elusive Hunter
2 Snakeskin Veil
3 Ba Sing Se
15 Forest
4 Escape Tunnel
4 Esper Origins
4 Icetill Explorer
1 Sapling Nursery
4 Mossborn Hydra
```

备牌（15）

```text
1 Leatherhead, Swamp Stalker
4 Meltstrider's Resolve
1 Surrak, Elusive Hunter
3 Sapling Nursery
1 Swamp
2 Torpor Orb
1 Dark Knight's Greatsword
2 Warg Tactics
```
