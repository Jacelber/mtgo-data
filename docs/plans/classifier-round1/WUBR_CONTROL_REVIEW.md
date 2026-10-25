# 四色控制：独立父类

状态：Owner 已确认建立 Four-Color Control／四色控制父类；候选已实现，完整 Modern 对照通过。

该牌表原归 Dimir Tempo，候选因正常用色 WUBR 成为 Unknown。它有 Wrath of the Skies3、Counterspell3、Fatal Push3、Teferi, Hero of Dominaria2、Snapcaster3；红色来自 Flame of Anor3、Galvanic Discharge2，并有 Steam Vents／Thundering Falls。不是仅有产红地或不可施放备牌造成的混色。

Owner 明确指出红色组件已超出艾斯波子类范畴，应建立独立父类。实现为 `four-color-control`，不为 Esper Control 增加子类，也不因该样本修改其原有规则。名称 Four-Color Control／四色控制，当前指示色 WUBR。

首条 `four-color-control-wrath` 分支使用共享正常 WUBR 用色，要求 Wrath≥3、Counterspell≥3、Push≥3、大泰菲力≥2，不限制迅咒数量，不绑定具体地名。这是已有证据支持的控制路线，不把大泰菲力宣布为今后一切四色控制的共同必要条件，也不建立全局控制优先。全保留语料中，此结构去除颜色限制时额外覆盖的旧 Esper 样本仍为 WUB；加 WUBR 用色后只覆盖本样本。

原有 4 副 Esper Control 正常颜色均 WUB。另一个四色牌表有 Ephemerate／Quantum Riddler／Solitude，属于不同待核对路线，本决定不包含它。原分类标签仅用于对照，不作为正确答案。

来源：`data/modern/melee/events/405588.json#decklists/395`

## 主牌（60 张）

```text
1 Arid Mesa
2 Cling to Dust
3 Consult the Star Charts
3 Counterspell
3 Fatal Push
3 Flame of Anor
4 Flooded Strand
2 Galvanic Discharge
1 Godless Shrine
3 Great Hall of the Biblioplex
1 Hallowed Fountain
2 Island
1 Kaya's Guile
1 Marsh Flats
1 Meticulous Archive
1 Mystic Gate
2 Plains
4 Polluted Delta
1 Prismatic Ending
1 Sheoldred's Edict
3 Snapcaster Mage
3 Spell Snare
1 Steam Vents
1 Supreme Verdict
2 Teferi, Hero of Dominaria
2 Teferi, Time Raveler
1 Thundering Falls
2 Tune the Narrative
1 Undercity Sewers
1 Watery Grave
3 Wrath of the Skies
```

## 备牌（15 张）

```text
4 Consign to Memory
1 Kaya's Guile
1 Murktide Regent
3 Mystical Dispute
2 Price of Freedom
1 Spell Snare
1 Supreme Verdict
1 Test of Talents
1 Wan Shi Tong, Librarian
```

验证：23 项相关样本／规则检查通过。全量 18,830 副中，本次仅该样本从 Unknown 进入新父类，其他分类签名不变，无新增冲突；22 个原有 Unknown 均保留。名称契约和 WUBR 指示色检查通过。
