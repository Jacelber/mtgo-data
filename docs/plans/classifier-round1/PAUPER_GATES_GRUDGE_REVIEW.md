# Pauper 纳雅战呼：城门与 Ancient Grudge 的返照用色

Owner 最终更正为“还是按你的建议归纳雅”，替代此前短暂的“沿用默认，不计绿色”。按最终决定，在既有 battle-screech 父类下新增 naya 子类，名称 Naya Battle Screech／纳雅战呼；父类统计归属不变。

主牌 3 Citadel Gate＋4 Cliffgate，备牌 4 Ancient Grudge。两种城门进场时各选一个额外颜色，之后可以反复产生该色；牌表不记录实际选择。Ancient Grudge 正常施放费用为 1R，返照费用为 G。此路线明确承认绿色返照用途。

## 实现范围

- 仅 Pauper 的 battle-screech 父类启用 pauper-battle-screech profile，仍满足原 Battle Screech 主牌至少 3 张核心和现有结构分支。
- 主牌同时存在 Citadel Gate 与 Cliffgate 时，仅给 Ancient Grudge 的费用判断补充绿色支持。数量可变化，不把来源的 3＋4 城门或四张 Grudge 固定为类别核心；不推导其他套牌通用色源门槛。
- 普通土地支持集合不扩成绿色。Nature's Claim 等其他绿色咒语不能借此例外计绿；其他父类和赛制保持默认。不带 Grudge 时，城门本身不会增加绿色。
- 新子类仍按正常 WRG 用色选择；其他有普通绿源、正常绿色咒语并满足原父类结构的战呼也可归纳雅，不强制所有纳雅战呼都带 Grudge。
- 前一条短暂决定形成的测试期望按这次明确业务更正更新，fixture 保留 previous_expected 与更正依据；原始数据和冻结历史基线不改。

四赛制冻结来源中，满足这条城门＋Grudge 战呼路线的 Pauper 记录只有下列一副。

114 项受影响检查通过；随后增加的同一测试断言也通过，覆盖无 Grudge 但有普通绿源＋正常绿色咒语仍可归纳雅，以及 Grudge 移入主牌仍可使用此路线。Ruff 与 classifier_cards 的 Mypy 检查通过。四赛制全量回放仅 Pauper 这一副 Boros → Naya；Pauper 其余 5,896 条、Standard 7,148 条、Pioneer 5,572 条、Modern 18,830 条的状态、身份、匹配和错误均无增量。

四份回放摘要匹配当前实现，原始来源 SHA 与记录集合不变；没有刷新历史基线。增量证据：`/workspace/scratch/classifier-round1/naya-screech-incremental-proof.json`。名称与前端 WRG 标识已同步；其他派生产物尚未同步，发布继续暂停。

## mtgo:pauper:12840552:19

来源：`data/pauper/Pauper_Challenge_32_12840552.json#players/19`

主牌（60）

```text
3 Thraben Inspector
3 Thraben Charm
3 Novice Inspector
2 Rally the Peasants
6 Plains
3 Citadel Gate
1 Boros Guildgate
3 Faithless Looting
3 Prismatic Strands
3 Leonardo, Big Brother
3 Mountain
4 Pursue the Past
4 Battle Screech
4 Squadron Hawk
4 Lightning Bolt
4 Lunarch Veteran
3 Basilisk Gate
4 Cliffgate
```

备牌（15）

```text
4 Ancient Grudge
1 Thraben Charm
4 Electrickery
2 Journey to Nowhere
1 Prismatic Strands
3 Guardian of the Guildpact
```
