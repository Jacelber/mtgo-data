# 标准：Jeskai Looting／洁斯凯滤牌归属审阅

这副原 Izzet Prowess 牌表没有 Slickshot Show-Off 或 Elusive Otter。旧灵技分支仅凭 Stormchaser’s Talent＋Boomerang Basics 命中；它另有 Tiger-Seal 2、Duelist of the Mind 4、Fear of Missing Out 4，完整符合现有 Izzet Looting 的滤牌组件路线。

正常白色来自主牌 Practiced Offense 4，备牌 Sage of the Skies 3／Sheltered by Ghosts 1；Hallowed Fountain 4、Floodfarm Verge 2 提供白色支持。这不是已批准的护身符或历险用途例外。

Owner 已批准并已实施 Standard 父类 `jeskai-looting`，英文 Jeskai Looting，中文洁斯凯滤牌。与 Izzet Looting 通过 YAML 锚点共用父类的三个必要组件，子分支只筛选对应颜色；既有数量要求不变，不强制 Practiced Offense。原有 Izzet Looting／红蓝滤牌身份保持。

来源：`data/standard/Standard_Challenge_32_12843800.json#players/25`

主牌（60 张）

```text
2 Tiger-Seal
4 Stormchaser's Talent
4 Boomerang Basics
3 Frostcliff Siege
4 Duelist of the Mind
4 Fear of Missing Out
3 Riverpyre Verge
4 Spirebluff Canal
4 Quantum Riddler
4 Practiced Offense
2 Winternight Stories
4 Torch the Tower
2 Island
4 Hallowed Fountain
1 Ghost Vacuum
1 Bounce Off
4 Starting Town
2 Floodfarm Verge
4 Steam Vents
```

备牌（15 张）

```text
1 Disdainful Stroke
1 Ghost Vacuum
2 Sunspine Lynx
2 Spell Pierce
2 Flashfreeze
1 Sheltered by Ghosts
1 Broadside Barrage
1 Into the Flood Maw
1 Sear
3 Sage of the Skies
```

## 实施验证

中英文名称与已批准白蓝红标识已登记，前端标识由现有生成器更新。新增完整来源回归、其他正常白色咒语替换、单张正常白色备牌计色、仅增加白色地不计色、同色换地及逐一移除父类核心的检查。没有用新分类输出刷新旧期望。

100 项受影响检查通过；Standard 7,148 条同输入全量回放只有一项增量：本牌表 Unknown → Jeskai Looting。原始源哈希和记录集合保持；其他赛制的规则、引擎与分类摘要未变，复用已有有效回放。Ruff、规则 schema、生成的前端 W/U/R 标识检查通过。日志为 `/workspace/scratch/classifier-round1/standard-jeskai-looting-tests.log` 与 `standard-jeskai-looting-replay.log`。未提交或发布，旧派生产物尚未作为本版最终结果同步。
