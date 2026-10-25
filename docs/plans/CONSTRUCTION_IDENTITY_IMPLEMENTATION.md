# B：构筑统计身份迁移结果（2026-10-24）

本文保留该阶段的实现、验证与候选信息；后续验收和本地版本化进展见[源码交付准备](SOURCE_DELIVERY_PREPARATION.md)。

状态：B 的既定开发范围、本地验证与产物同步已完成。先前遗漏跨写法兼容就宣布完成，属于验收遗漏；本次已补齐实现、独立变体验证、完整分类回放及产物对照。四赛制 CURRENT 仅作为依赖一致性证明，不代替功能验收。未提交、推送、打包部署候选或发布。B 完成时 C、D、E 尚未启动；此后进展见整体计划。授权与范围见 [整体计划](DEVELOPMENT_PLAN_CURRENT.md)。

## 输入兼容遗漏及补齐

复核时确认，`Callous Sell-Sword` 与 `Callous Sell-Sword // Burn Together` 已统一，但 `Callous Sell-Sword/Burn Together`、`Callous Sell-Sword//Burn Together`、`Callous Sell-Sword / Burn Together` 仍保留不同键。Fable、Sink into Stupor 等双面牌也存在相同分隔符边界。之前的测试主要覆盖快照已登记写法，没有充分证明输入表示变化不影响实体身份。

这属于已批准 B2／B4 的遗漏，不是后续新增需求。现已依据已登记的完整、有序卡面组合支持 `/`、`//` 和分隔符两侧空白，覆盖饼干牌、转化双面牌、模式双面牌、分割牌和房间。精确登记名字优先；仅当完整组合唯一对应实体时才归并。未知、错配、逆序、有歧义或错误分隔符保留原名，SP//dr 等名字内部的斜线不会被全局替换。运行时与离线事实导出器复用同一匹配函数，不向事实快照批量添加变体，也不重写原输入、显示名字或记录 ID。

共享身份契约升级为 1.1.0，因此分类摘要和依赖它的当前产物需要更新；不能继续把初次 B 实施时的“分类摘要不变”当作最终状态。类别规则和卡牌事实快照未变，完整回放验证的是实际分类结果不变。补齐阶段单独冻结基线 `/workspace/construction-b-notation-baseline-98c4a1bacf625dd2`，证据置于 `/workspace/scratch/construction-roundb/notation/`。

## 实现

`mtgo.stats.deck_vector` 复用既有 `classifier_cards.classifier_card_name` 实体解析，再应用原有普通／雪境基本地比较等价。没有增加第二套别名表。同实体在主牌中以多个名字出现时先合并数量；出现率按合并后的每副向量计一次。分割牌、历险牌仍按一张实体计数；颜色分析的非施放用途例外不会删除构筑中的牌。

均值、Core/Flex、代表牌表、加权距离、绝对偏离度、近期变化和兼容 P99 字段均沿用原公式、门槛及窗口，通过共享向量取得修正。`normalize_legacy_card_name` 与 `merge_cards` 保留为原显示／记录标识口径，避免改写原提交名称、精确牌表和 ID。未登记实体保留其名字与数量；实际公开输入盘点未发现事实缺失。

滚动统计 index／range／decks 和 Top 8 index／week／bases 新增 `construction_digest`，绑定构筑身份版本、共享实体事实、别名和基本地等价规则。初次统计迁移未改变分类摘要；补齐共享写法兼容后，摘要按新身份版本更新。六个输出 schema 以可选字段兼容旧档案；缺少此字段表示旧构筑结果，并不被当前可重建统计检查误认成最新结果。现有闭合入口检查新摘要，已有生成进度指纹已涵盖共享事实、别名和 stats 实现，不另建执行框架。

## 基线及范围

实施前已冻结原始输入、完整代码与已有产物：

- 基线目录：`/workspace/construction-b-baseline-c20c53507b46f845`。
- 清单：`/workspace/scratch/construction-roundb/baseline-manifest.json`，包含四赛制受保护输入和 A 最终分类摘要。
- 盘点：同目录 `identity-inventory.json`。

本次构筑统计按规范作用于已接纳的 MTGO 产品，不给 Melee 额外增加构筑统计。因此语料范围与 A 的全部保留输入＋Melee 分类回放不同。

| 赛制 | 公开 MTGO 牌表 | 构筑向量键变化的牌表 | 不同名称映射 |
| --- | ---: | ---: | ---: |
| Standard | 7,052 | 1,000 | 30 |
| Modern | 11,107 | 49 | 9 |
| Pioneer | 5,540 | 1,228 | 14 |
| Pauper | 4,767 | 94 | 4 |
| 合计 | 28,466 | 2,371 | — |

2,371 包含房间等牌的名称表示统一，不等于数值纠错数量或独立准确率样本。

## 真实纠错与差异

**Pauper W38 白绿 Packbeast。** 从同一四周窗口的原牌表独立重计，21 副均有 Darval／Spider-Man，合计 41 张。旧产物将二者列为两项 Flex，出现率 0.714／0.286；修正后只有 Spider-Man, Web-Slinger 一项 Core，出现率 1.0，平均 41/21，展示四舍五入为 2.0 张。原赛事牌表继续显示其提交名字。独立来源、逐副数量与公式保存在 `packbeast-w38-independent-oracle.json`。

**Standard 四周矮人。** Giantcraft Helm／Doc Ock's Tentacles 旧均值分别 0.5／0.3、出现率 0.364／0.182；合并后为 Doc Ock's Tentacles，均值 0.8、出现率 0.545。父类与 Boros 子类平均偏离度均由 12 修正为 11；样本数仍为 11。

完整产物对照仅允许构筑指标及其技术绑定变化，并验证其他字段相等：

| 赛制 | 滚动统计平均偏离度字段变化 | 八强周次×身份基准变化 | 八强牌表偏离度变化 |
| --- | ---: | ---: | ---: |
| Standard | 2（均为 4w） | 33 | 44 |
| Modern | 0 | 0 | 0 |
| Pioneer | 0 | 20 | 0 |
| Pauper | 4（4w／12w 各 1，36w 为 2） | 7 | 8 |

这里的基准变化也包含单纯规范名称变化，不全是数值变化。当前 Standard Lifegain 的近期变化度由 18 到 19；Pauper Packbeast 最佳牌表偏离度由 12 到 9。Standard 兼容 P99 字段由 23.9693 到 24.0726，其他赛制不变；当前偏离度及近期变化仍使用各自参照基准的加权总量作分母，未改为 P99 归一化。

完整差异见 `product-impact-proof.json`、`current-metric-details.json`；本轮没有更改类别、权重、统计窗口或来源成员资格。

## 初次统计迁移的历史与消费者

按现有 STATISTICS_SPEC 16.8，八强历史的源赛事、选手、名次、精确主备牌不可变；比较基准和偏离度允许随对应计算契约重述。此次补齐独立构筑摘要以解释这种重述，不制造分类变化。

初次统计迁移时，四赛制原始数据、分类报告、Melee 产物、配置和规则均逐字节保持。整个 Landing 目录（含当前已接受页面、绑定数据、审阅记录和 Feature 历史）当时也逐字节保持，继续使用其已接受快照。这是初次迁移基线的验证结果；补齐共享身份兼容后，分类派生绑定和当前 Landing 统计另行同步，不能再将上述结果概括为最终全部产物均未改变。

## 初次统计迁移的验证

- 24 项针对性测试通过：同实体跨表示、同副牌别名合并、出现率、独立手算均值／权重／分母／medoid／P99、仅换别名的跨周零变化、源显示／指纹不变、新摘要失效及八强派生重述；包括既有基本地与 Top 8 保护检查。
- 闭合及 schema 入口另有 19 项通过。误选的既有全量 schema 测试遍历 419 份公开产物，在无关 Melee 大文件处达到默认 120 秒时限，未完成且不计为通过；本次没有放宽规则或重跑无关全量检查，改用下述实际受影响输出的完整格式证明。
- 通过现有 `classifier_closure` 完成四赛制同步：Standard 37、Modern 37、Pioneer 23、Pauper 27 个产物，共 124 个，实际选中 JSON 格式检查全部通过。原始输入及已接受历史保护检查通过。
- 原基线与最终产物逐字段核对：除构筑指标、构筑摘要、生成时间和已有影响报告字段外，范围统计、子类成员、样本数、精确牌表和分类身份均相同。分类摘要四赛制完全不变，未重跑无关分类全量测试。
- 系统 Chromium 使用真实本地页面验证 Pauper W38 八强 Core、原 Darval 牌名保留，以及 Standard 四周 Boros Dwarves 的合并 Flex 与代表牌表切换，无页面运行错误。记录 `browser-verification.json`；截图 `packbeast-w38-core.png` 已人工查看。
- 相关 Ruff 与差异空白检查通过。

初次同步结果 `closure-result.json`、日志 `closure-progress.log`、完整保护及指标证明 `product-impact-proof.json` 均在上述外部证据目录。阶段目录保留，未清理基线。这些验证当时没有覆盖分隔符兼容，不能单独证明 B 完成。

## 补齐写法兼容的验证

- 111 项针对性测试通过，涵盖六组代表牌的八种分隔符／空白写法、MTGO 与 Melee 输入适配、分类数量、构筑数量、均值、出现率、Core/Flex、加权距离和代表牌表。另覆盖未知／错配／逆序／歧义组合、精确名字优先和牌名内部斜线。离线导出器接受同样的完整组合，并产生相同事实快照。
- 快照全部 236 组有序卡面组合通过变体验证；四赛制原始输入中 4,778 种牌名解析结果均未改变。见 `notation/source-name-proof.json`。
- 完整 37,447 份牌表回放，对比冻结的 A 最终结果，分类身份、状态、匹配和诊断签名零变化；Unknown 仍为 Standard 1、Modern 20、Pioneer 0、Pauper 1。见 `notation/replay-summary.json` 和分赛制回放结果。这只证明既有语料无分类回归，新增变体的正确性另由上述独立测试证明。
- 身份代码 Ruff／mypy 与差异空白检查通过；事实快照未重写。

补齐阶段通过既有入口同步 Standard 54、Pioneer 40、Pauper 52、Modern 132 个产物，共 278 个；实际受影响公开与内部 JSON 的格式检查全部通过，四赛制均 CURRENT。分类摘要和构筑摘要更新到共享身份 1.1.0，Melee 与分类报告只更新派生绑定及生成元数据，实际分类与统计内容保持不变。

与补齐前冻结基线逐字段对照，原有滚动统计、Top 8 基准及数值没有第二次变化。Top 8 的 `classification_impact` 是相对上一次生成的即时报告，本次分类／基准变化列表均为空；首次 B 的真实差异仍保存在冻结基线和初次影响证明中，没有用空报告抹去首次纠错记录。

当前 Landing 经现有允许重述入口刷新绑定：Standard、Pioneer、Pauper 的 2026-W42 `environment_decks.json`／`feature_decks.json` 共六份数据接入首次 B 的构筑修正；Modern 无构筑内容变化。四赛制当前绑定的 range、environment、feature 数据分别与滚动 1w range、1w decks、4w decks 完全相等。当前页面的编辑内容和选择未变。

1,794 份原始数据文件及 131 份受保护审阅／历史文件逐字节保持，保护指纹全部一致；配置、规则、卡牌事实及源牌表没有变化。旧周绑定数据和旧 Feature 档案未改写。完整证明见 `notation/product-proof.json`，同步结果及日志见 `notation/closure-result.json`、`notation/closure-progress.log`。完整部署候选、实际包体测量及发布依旧未执行。
