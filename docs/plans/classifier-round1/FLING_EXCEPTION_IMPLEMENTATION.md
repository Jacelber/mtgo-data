# Sell-Sword／Otter 局部例外已接入

2026-10-24。依据 Owner 连续确认：共享原则保留；仅这两张牌的相关用途采用局部例外；没有或只有一张额外对应色源不算混色，后续明确批准两种双绿源 Otter 构筑也不计额外颜色，Sell-Sword 对称处理；足量配置承认第二色，4 Blood Crypt 正例保持。未批准“三张就算”的阈值。未提交或发布，旧派生产物仍不代表本版代码。

## 实现与范围

增加显式卡牌用途 `fling_secondary`，只接受 Sell-Sword／Otter，规则配置仅允许 Standard／Pioneer。默认 `deck_colors` 不启用此例外；Modern／Pauper 的现有配置不变。

```yaml
card_uses:
  Callous Sell-Sword: fling_secondary
  Elusive Otter: fling_secondary
```

它按对应额外固定地源决定是否使用已有 `adventure_only`／`front_only` 能力。零、一或已确认的双张专色来源情形，Sell-Sword 仅红、Otter 仅蓝；之外保留默认卡面贡献。三张专色源明确记录 `unreviewed-source-count`；若该用途是该色唯一贡献，分类引擎阻止颜色分支选择并报告用途未定，避免把默认诊断当作批准。如果另有正常同色咒语，则它已独立确立颜色，不受该用途待定影响。执行契约更新为 1.2.1，规则格式仍为 1.2.0。4 Blood Crypt 及同色地替换仍计黑；对称的正常绿色支持不会被永久排除。

局部来源统计复用正常土地支持的排除项：神器／生物产色、受限地、偶发 Caverns 等不充当额外专色地；Starting Town／Multiversal Passage 等任意色或可选类型来源不让这个用途例外失效。主备牌地源一起检查；找地目标作为实际地计数，不按每张找地地重复增加目标数量。这是本次用途约定的证据，不是全局施放概率模型。未知卡牌属性阻止该例外自动认定“没有额外色源”，沿用属性缺失诊断。

其他正常同色咒语独立计色，包含只带一张的备牌。同一家族内主备牌执行同一用途例外。初版实现曾限制必须在主牌出现，造成 21 条仅备牌带 Otter 的记录漏用例外；这是实现限制而非 Owner 要求，已经修正并补同色正常备牌保护检查。Owner 后续分别确认 Frog Butler、Quintorius Kand 也属于同一标准 Fling 构筑中的护身符用途；与 Poison Dart Frog 一起复用限定范围，总计一张备牌且主牌没有这些牌时生效，正常同色其他牌仍计色；显式 `normal_cast` 可以覆盖可选用途。

已接入 Standard 的 Izzet Fling／Izzet Prowess／Leyline Aggro，以及 Pioneer 的 Rakdos Fling／Rakdos Leyline。这是当前核对过的路线范围，没有把例外全局复制到所有包含这两张牌的类别。

## 同时完成的规则接入

- Standard Izzet Fling 使用正常蓝红颜色筛选，移除仅用于判蓝的 Spirebluff Canal 条件；既有 Sell-Sword／Slickshot／Wild Ride 结构要求不变。
- Standard Leyline 的 Leyline 4＋Slickshot 4 共同核心上移父类，五条子类分支只表达正常颜色，不再依赖土地色源标记。保留五个子类和规则 ID；其他正常咒语确实能改变子类，缺少共同核心时没有子类可以绕过。
- Pioneer Rakdos Fling 加入正常黑红筛选，移除 Blood Crypt 具体牌名条件；相同用色的合法换地不失配。Rakdos Leyline 原有黑红筛选复用本次局部用途。
- Standard Izzet Prowess 已正式使用正常蓝红筛选，移除仅用于判色的 Steam Vents／Spirebluff Canal 要求；现有其他结构条件不变。28 条已确认双绿源牌表保持红蓝，另有九条 Quandrix Charm 构筑独立贡献绿色。
- 接入时发现一副正常白蓝红牌表会从 Izzet Prowess 落入尚未判色的 Izzet Looting。为避免错误兜底，后者同时接入正常蓝红筛选；三个既有结构组件不变，没有为通过样本降低门槛。

Owner 已批准新增 Standard Temur Prowess／铁木尔灵技。它与 Izzet Prowess 通过 YAML 锚点共享五条结构分支和卡牌用途配置，只按正常蓝红绿／蓝红区分；不强制 Quandrix Charm。新增父类局部优先级保留已有 Enduring Vitality 水獭引擎的 Temur Otters 归属，没有更改既有父类优先级或设置全局组合技优先。中英文名称、法术力标识和生成的前端标识已更新。

Owner 随后批准并已实施 Standard Jeskai Looting／洁斯凯滤牌，与红蓝滤牌共享父类结构核心，只按正常白蓝红／蓝红区分。此次标准全量对照只解决该来源的一条 Unknown，没有改动其他归属。

严格颜色接入当前为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；原三个 Standard 诊断家族均已接入正式筛选。

## 验证与实际差异

155 项针对性检查通过，覆盖局部例外的对称性、默认原则不变、正常主备牌同色贡献、属性缺失、主备牌一致用途、未定三源用途的阻断及独立正常颜色、已确认 Blood Crypt 来源及同色换地、生产规则入口、父类核心和已有子类选择。Frog 源牌表原四种颜色的断言，仅依据此次另行批准的历险例外改为蓝红；默认未启用例外的分析仍保留原卡面颜色，没有复制候选输出批量刷新期望。

Ruff、mypy、四赛制规则 JSON schema 检查通过。四赛制同输入全量回放共 37,447 条，逐一校验原始源哈希与记录集合。相对本轮接入前候选：

| 赛制 | 分类签名变化 | 实际含义 |
| --- | ---: | --- |
| Standard | 13 | 两条单黑源 Leyline 改为 Mono-Red；九条正常混绿灵技归已批准 Temur Prowess；一条正常白蓝红滤牌归已批准 Jeskai Looting；一条 Temur Otters 仅增加同家族交集诊断，公开归属保持 |
| Pioneer | 0 | 已确认的正常黑色施放构筑仍为 Rakdos，生产规则确实启用例外 |
| Modern | 0 | 本次例外未配置到该赛制，全量行为核对不变 |
| Pauper | 0 | 本次例外未配置到该赛制，全量行为核对不变 |

在核对过的 399 条 Standard 与 7 条 Pioneer 历险源记录中，Standard 385 条的用途颜色诊断发生变化。该范围包括仅在备牌出现这些牌的记录，比旧的仅主牌审查多 21 条。这说明不能以公开分类签名变化数量代替颜色能力是否执行的证明。Pioneer 七条均有正常黑色支持，包含三条仅 Sell-Sword 用黑且有 4 Blood Crypt 的已确认正例。

当前全部开发候选 Unknown 为 Standard 26（较原冻结基线新增 21）、Pauper 10（新增 9）、Pioneer 108（新增 108）、Modern 22（新增 0）。不以更新旧期望或宽泛类别兜底消除这些待维护项。

## 当前剩余事项

Frog Butler 与 Quintorius Kand 两副 Fling 的用途均已由 Owner 分别确认为护身符，并已恢复正确的 Izzet Fling 归属。它们是明确用途例外，没有通过改原始牌表或合并 Oracle 身份解决。完整来源及 28 条双绿源代表见 [牌表记录](FLING_REMAINING_DECKS.md)，这些用途均不再待答。

九条正常使用 Quandrix Charm 的灵技已归新 Temur Prowess；用 Nature’s Claim 替换 Charm 的验证仍归 Temur，证明未把流行辅助牌固化为父类核心。四条三绿源构筑的绿色由正常 Charm 独立确立，不依赖尚未决定的“仅历险用途、三张色源”边界。

这组历险用途、护身符与相关新类别决定均已实施，包括 [Jeskai Looting](STANDARD_JESKAI_LOOTING_REVIEW.md)。Jeskai Looting 本次另完成 100 项受影响检查和 Standard 7,148 条回放，其他赛制复用未失效结果。更早列出的 Standard／Pauper／Pioneer 待维护项仍未全部处理，不宣称整轮完成。

验证产物在 `/workspace/scratch/classifier-round1/`：`fling-completed-tests.log`、`fling-completed-replay.log`、`fling-exception-audit.json`、四份最新 `candidate-*.json`（Standard 已由 `standard-jeskai-looting-replay.log` 的后续回放更新）。`candidate-*-before-fling-exceptions.json` 保留增量对照。早期一次性迁移脚本从更旧备份生成规则，不应再次直接覆盖当前 YAML；本次编辑脚本另存 `implement_adventure_exceptions.py`。
