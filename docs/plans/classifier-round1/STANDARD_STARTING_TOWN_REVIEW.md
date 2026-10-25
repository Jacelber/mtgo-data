# 标准 Starting Town 与 Frog 用色边界

来源：`data/standard/Standard_Challenge_16_12856183.json#players/26`；牌手 MacIsaac；旧类别 Izzet Fling。

此牌表有 4 张 Starting Town，能够正常产生绿色；不能用“无绿色地源”解释 Frog。未加用途例外的共享默认会计入 Frog 的绿色。另有 Callous Sell-Sword 黑色生物部分、Elusive Otter 绿色历险部分，即使去掉 Frog，默认分析仍为 UBRG。

Owner 决定（2026-10-24）：“明确该用法为例外，Frog 不计绿色”。已实现，未发布。

`standard-fling` 用途策略复用现有 Fling 核心范围：主牌 Callous Sell-Sword ≥3、Slickshot Show-Off ≥4、Wild Ride ≥3，备牌单张 Frog 且主牌不含 Frog。它仅在 Standard 的 Izzet Fling、Izzet Prowess、Leyline Aggro 分支中启用，以覆盖旧规则对同一构筑路线的不同归属；不是按牌手、赛事或牌表 ID 特判。正常绿色咒语仍贡献绿色。主牌 Frog、复数 Frog、其他构筑及其他赛制不因本决定套用豁免；显式 normal_cast 可覆盖用途配置。

实际 30 条 Standard Frog 记录中，29 条有 Starting Town 的同路线牌表现在报告 `standard-fling:sideboard-charm`，另 1 条缺少绿色来源仍由默认规则排除。真实牌表、改牌手不改变结果、其他正常绿牌仍计色、范围外 Frog 正常计色及禁止跨赛制配置均有验证。

这三个父类已执行用途诊断；历险部分尚待判断，不能将其计作已经完成严格色组筛选的新增父类。7,148 条 Standard 当前分类签名相对本决定前没有变化，例外是否生效以逐牌贡献核对，不能仅看总色组或分类标签。下一项仅讨论 [Callous Sell-Sword 的黑色生物部分](STANDARD_FLING_ADVENTURE_REVIEW.md)，不将 Frog 的决定扩展到历险。

## 主牌

```text
3 Opt
2 Spirebluff Canal
2 Spirebluff Canal
3 Riverpyre Verge
4 Starting Town
3 Steam Vents
2 Drake Hatcher
4 Callous Sell-Sword
3 Multiversal Passage
4 Slickshot Show-Off
2 Turn Inside Out
4 Wild Ride
4 Elusive Otter
4 Sleight of Hand
1 Mountain
1 Balmor, Battlemage Captain
2 Secret Identity
4 Ancestral Anger
2 Full Bore
1 Shore Up
1 Steam Vents
4 Pompous Battlemage
```

## 备牌

```text
1 Pyroclasm
2 Soul-Guide Lantern
1 Secret Identity
2 Spell Pierce
2 Into the Flood Maw
1 Poison Dart Frog
3 Octopus Form
1 Dreadmaw's Ire
1 Spell Pierce
1 Full Bore
```
