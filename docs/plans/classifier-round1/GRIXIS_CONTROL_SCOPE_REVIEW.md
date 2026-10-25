# 蓝黑红法术师／控制的范围核对（尚未提出最终迁移）

状态：初始范围调查留档。Owner 随后批准两份新增 Unknown 归 Grixis Control；限定回收＋弃牌路线已加入候选，直接核对没有迁移这里列出的 9 份 Dimir Tempo。未将这 9 份的旧标签直接认定为独立正确答案，也未实施宽泛控制优先。

现有 Grixis Control 的 18 副均为 Snapcaster4、Counterspell4、Flame3–4、Consult1–4、Fatal Push3–4、Frog0；它们可作为已有路线参照，不能充当其他构筑的自动排除依据。

两个新 Unknown 原归 Izzet Wizards，均为 Snapcaster4、Flame3、Counterspell4、Kolaghan’s Command3、Thoughtseize2＋Inquisition2、Bowmasters4、Subtlety4；其中一副 Frog0，另一副 Frog2。旧 Grixis Control 强制主牌 Consult 和 Fatal Push、排除任何 Frog，无法容纳这两副。是否仍属同一控制家族需要根据构筑解释，而不是只降低所有数量门槛。

对全部保留牌表筛选 Snapcaster≥2、Flame≥3、Counterspell≥2、正常 UBR，保留 DRC／Ragavan／Persist／Goryo’s 主牌排除，共得到 29 副：18 份旧 Grixis Control、2 份上述 Unknown、9 份旧 Dimir Tempo。这是分析条件，不是已批准的新规则。若直接按该宽条件加入高优先级控制路线，会涉及那 9 份既有归属，不能声称仅修复两个 Unknown。

9 份中 2 份有 Frog4，其余 7 份 Frog0；也有两份主牌 KCommand2／3。因而简单添加 KCommand 分支也可能产生额外迁移。需要结合完整牌表及既有局部归属确定边界，不能以“保护历史输出”为由冻结明显错误，也不能自行创建全局控制优先。

## 范围索引

| 来源 | 旧父类 | Snapcaster | Flame | Counterspell | Consult | Push | KCommand | Frog | Bowmasters | Thoughtseize＋Inquisition |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `data/modern/Modern_Challenge_16_12855508.json#players/7` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_16_12855508.json#players/28` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_16_12856622.json#players/3` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 2 |
| `data/modern/Modern_Challenge_32_12856339.json#players/31` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12847683.json#players/0` | dimir-tempo | 3 | 3 | 4 | 0 | 3 | 0 | 4 | 4 | 0 |
| `data/modern/Modern_Challenge_64_12848217.json#players/14` | izzet-wizards | 4 | 3 | 4 | 0 | 0 | 3 | 0 | 4 | 4 |
| `data/modern/Modern_Challenge_64_12855490.json#players/19` | grixis-control | 4 | 4 | 4 | 3 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12855498.json#players/31` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12855513.json#players/9` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12856886.json#players/4` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 3 |
| `data/modern/Modern_Challenge_96_12855500.json#players/9` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 0 |
| `data/modern/Modern_Challenge_96_12855518.json#players/7` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 0 |
| `data/modern/melee/events/405588.json#decklists/104` | dimir-tempo | 2 | 4 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/405588.json#decklists/686` | izzet-wizards | 4 | 3 | 4 | 0 | 0 | 3 | 2 | 4 | 4 |
| `data/modern/melee/events/405588.json#decklists/1274` | grixis-control | 4 | 3 | 4 | 1 | 3 | 0 | 0 | 3 | 0 |
| `data/modern/melee/events/405590.json#decklists/250` | dimir-tempo | 4 | 3 | 4 | 0 | 3 | 0 | 0 | 3 | 0 |
| `data/modern/melee/events/405590.json#decklists/300` | dimir-tempo | 4 | 3 | 3 | 0 | 4 | 2 | 0 | 3 | 0 |
| `data/modern/melee/events/405591.json#decklists/401` | dimir-tempo | 4 | 3 | 4 | 0 | 3 | 0 | 0 | 3 | 0 |
| `data/modern/melee/events/405591.json#decklists/616` | grixis-control | 4 | 4 | 4 | 3 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/341` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/573` | dimir-tempo | 4 | 4 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/592` | dimir-tempo | 4 | 3 | 4 | 0 | 4 | 3 | 0 | 2 | 0 |
| `data/modern/melee/events/470109.json#decklists/659` | grixis-control | 4 | 4 | 4 | 4 | 4 | 1 | 0 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/1003` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/1168` | grixis-control | 4 | 4 | 4 | 3 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/471573.json#decklists/116` | grixis-control | 4 | 3 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/471573.json#decklists/129` | grixis-control | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| `data/modern/melee/events/471573.json#decklists/171` | dimir-tempo | 3 | 4 | 3 | 3 | 4 | 0 | 4 | 0 | 0 |
| `data/modern/melee/events/482105.json#decklists/9` | dimir-tempo | 4 | 4 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
