# 铁木尔法术师：已确认类别

状态：Owner 已同意新增 Temur Wizards，并明确中文必须为“铁木尔法术师”。父类、规则、名称和蓝红绿指示色已加入候选，尚未发布。

两副旧 Izzet Wizards 的主牌完全相同，均有 4 Snapcaster Mage、4 Flame of Anor、4 Counterspell、4 Wrenn and Six；备牌还有 Veil of Summer，部分有 Nature’s Claim，正常绿色来源包括 Breeding Pool、Hedge Maze。不是地源或非施放用途误添绿色，也不需要猜测牌表错误。

现有 `izzet-wizards` 明确为红蓝，项目没有独立 Temur Wizards／Temur Control 类别。建议新增 `temur-wizards`（Temur Wizards／铁木尔法术师）父类：沿用 Snapcaster＋Flame 共同核心和原法术师功能性排除，要求正常蓝红绿用色。不把当前 4 Wrenn 的配置设为整个父类必要条件，不建立通用“控制优先”判断。新父类归属及正确中文名称现已由 Owner 确认。

此处只处理两副铁木尔版本；蓝黑红版本与既有 Grixis Control／Dimir Tempo 的交集另行核对，不同时替 Owner 决定。

## data/modern/Modern_Challenge_96_12845722.json#players/15

主牌（60 张）

```text
3 Lightning Bolt
1 Polluted Delta
4 Counterspell
4 Galvanic Discharge
2 Invert Polarity
3 Island
1 Sink into Stupor
1 Fiery Islet
4 Scalding Tarn
4 Misty Rainforest
1 Thundering Falls
2 Traumatic Critique
4 Tamiyo, Inquisitive Student
4 Flame of Anor
3 Spell Snare
4 Snapcaster Mage
3 Steam Vents
4 Wrenn and Six
2 Breeding Pool
1 Hedge Maze
1 Otawara, Soaring City
1 Lonely Sandbar
3 Force of Negation
```

备牌（15 张）

```text
4 Consign to Memory
1 Fire Magic
1 Forest
2 Veil of Summer
3 Meltdown
2 Blood Moon
2 Nature's Claim
```

## data/modern/Modern_Challenge_96_12845943.json#players/14

主牌（60 张）

```text
3 Spell Snare
1 Polluted Delta
3 Force of Negation
4 Galvanic Discharge
2 Invert Polarity
3 Island
1 Sink into Stupor
1 Fiery Islet
3 Lightning Bolt
4 Counterspell
1 Thundering Falls
2 Traumatic Critique
4 Tamiyo, Inquisitive Student
4 Flame of Anor
4 Misty Rainforest
4 Snapcaster Mage
4 Scalding Tarn
4 Wrenn and Six
2 Breeding Pool
1 Hedge Maze
1 Otawara, Soaring City
1 Lonely Sandbar
3 Steam Vents
```

备牌（15 张）

```text
4 Consign to Memory
2 Fire Magic
2 Vexing Bauble
2 Blood Moon
2 Veil of Summer
3 Meltdown
```

名称核对：正式目录中的 Izzet Wizards 已是“红蓝法术师”，无需改动；之前提问及本轮审阅文档中的“法师”用词已纠正。其他真实卡牌名称如“迅咒法师”“风雨法师拉尔”不属于类别命名纠错范围。

完整 Modern 18,830 副对照：仅两份获批样本的分类归属变为新父类；另 3 份既有 Unknown 仅增加新父类颜色不符诊断，状态／归属未变。名称契约 346 项通过，指示色为 U/R/G；完整 60＋15 替换 Wrenn→Preordain 后，正常绿色备牌仍能让合法变体归入 Temur Wizards。
