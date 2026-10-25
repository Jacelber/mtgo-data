# 两副蓝黑红法术师的控制归属：已确认

状态：Owner 已同意两副均归已有 Grixis Control。规则与完整样本已加入候选，Dimir Tempo 规则未因此修改；尚未发布。

两副旧归 Izzet Wizards，但正常颜色为蓝黑红：均有 Snapcaster4、Flame3、Counterspell4、Kolaghan’s Command3、Thoughtseize2＋Inquisition2、Bowmasters4、Subtlety4。它们以反击、去除、弃牌及 Snapcaster／KCommand 回收资源运作。第一副无 Psychic Frog；第二副有 2 Frog，但不凭这两张直接排除控制家族。

推荐归入已有 `grixis-control`（Grixis Control／格利极控制），不新建 Grixis Wizards，也不把有黑色的法术师继续命名为 Izzet。既有 18 份 Grixis Control 样本同样有 Snapcaster4、Flame3–4、Counterspell4，现有分支依赖 Consult／Push 并排除任何 Frog，遗漏了这两副 KCommand＋弃牌构筑。

具体实现需保留共同核心，区分已有 Consult 路线与这里的资源回收／弃牌路线；不能用“所有 UBR Snapcaster＋Flame 都是控制”直接替代。范围核对已经发现那样会涉及 9 份旧 Dimir Tempo，其中 2 份 Frog4、7 份 Frog0，细节见 GRIXIS_CONTROL_SCOPE_REVIEW.md。这些重叠还需核对，尚未宣布既有标签全部正确或全部错误。

## data/modern/Modern_Challenge_64_12848217.json#players/14

主牌（60 张）

```text
1 Blood Crypt
4 Counterspell
3 Flame of Anor
3 Force of Negation
2 Inquisition of Kozilek
1 Invert Polarity
3 Kolaghan's Command
4 Lightning Bolt
1 Mistrise Village
4 Orcish Bowmasters
1 Otawara, Soaring City
4 Polluted Delta
4 Scalding Tarn
4 Snapcaster Mage
2 Snow-Covered Island
1 Snow-Covered Mountain
2 Snow-Covered Swamp
2 Steam Vents
4 Subtlety
4 Tamiyo, Inquisitive Student
2 Thoughtseize
1 Thundering Falls
1 Undercity Sewers
2 Watery Grave
```

备牌（15 张）

```text
4 Consign to Memory
2 Fatal Push
2 Force of Despair
1 Invert Polarity
2 Sheoldred, the Apocalypse
2 Sudden Edict
2 Surgical Extraction
```

## data/modern/melee/events/405588.json#decklists/686

主牌（60 张）

```text
1 Blood Crypt
4 Counterspell
3 Flame of Anor
3 Force of Negation
2 Inquisition of Kozilek
2 Island
3 Kolaghan's Command
4 Lightning Bolt
1 Mountain
4 Orcish Bowmasters
1 Otawara, Soaring City
4 Polluted Delta
2 Psychic Frog
4 Scalding Tarn
1 Sink into Stupor
4 Snapcaster Mage
2 Steam Vents
4 Subtlety
2 Swamp
3 Tamiyo, Inquisitive Student
2 Thoughtseize
1 Thundering Falls
1 Undercity Sewers
2 Watery Grave
```

备牌（15 张）

```text
4 Consign to Memory
2 Fatal Push
2 Force of Despair
1 Mystical Dispute
2 Sheoldred, the Apocalypse
2 Sudden Edict
2 Surgical Extraction
```

实现：父类统一声明 Snapcaster≥1、Flame≥1、Counterspell≥2，保留既有 DRC／Ragavan／Persist／Goryo’s 功能性排除。原 Consult＋Push 分支保留其数量及 Frog0 条件；新分支要求 KCommand≥2、Thoughtseize＋Inquisition 主牌合计≥2，表示多张资源回收和弃牌参与的路线，允许 Frog。没有把这两张组件变成整个父类必要条件，也没有统一下调其他数量门槛。两条分支均使用共享 UBR 正常颜色，替换旧具体地名／颜色来源代理；旧分支优先级保留，新分支稍低，兼容未来同时匹配。

父类最低核心沿用已有标准，不因当前样本都带 4 张而升为 4；新分支的多张要求避免单个边缘组件直接建立该路线。两个批准样本、18 个既有控制、9 个相近 Dimir Tempo 的直接检查通过；Command3→2 并补一张 Lightning Bolt 的完整变体仍归控制，删除任一共同核心均不能通过。全量对照另见实施记录。

全量验证：Modern 18,830 副中仅两份获批样本的归属变化为 Grixis Control；另一份既有四色 Unknown 仅改变颜色不符诊断，未改变归属。其余签名不变，无新增冲突。
