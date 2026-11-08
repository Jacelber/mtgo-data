# Legacy 分类器上线前整合

本地准备分支将 Owner 已确认的规则、父类、子类与计色接入正常分类入口。
这是分类整合，不是赛制公开上线：`configs/formats.yaml` 的 Legacy 仍为
`planned`、`public: false`、MTGO 产品执行关闭。没有新增采集、Melee 准入或发布。

## 运行结构

- `my_archetypes/legacy.yaml` 保存构筑识别条件，并显式启用
  `identity_policy: legacy-reviewed-v1`。未设置此字段的赛制不使用 Legacy 策略。
- `configs/legacy_semantic_features.yaml` 是原已确认的语义资料，使用固定摘要加载。
- `src/mtgmeta/legacy_policy/` 保存构筑分支消歧、实际用途计色、父类归并及
  最终身份目录。运行只接收主备牌计数，不读取牌手、赛事、名次或人工原表。
- `RuleSet.recognition_archetypes` 保存识别分支；`RuleSet.archetypes` 对策略规则集
  提供最终父类／子类目录。统计和周维护消费最终目录，旧混色分支名称不泄漏到输出。
  未启用策略的规则集仍只有原有 `archetypes`。规则诊断和排序验证同时覆盖识别分支。
- 普通 `classify_counts`、`classify_deck` 使用同一路径。冲突先保留；只在完整死影
  签名命中时抑制已确认过宽的复活快捷规则，其他冲突不由父类策略强行选择。
- 分类摘要包含识别规则、输出身份、用途事实与策略实现。其他赛制的摘要保持不变。
- `configs/mtgo_archetype_names.yaml` 登记已确认中英文名称；完整子类名在统计、
  八强和 Landing 名称拼接中直接使用，避免重复附加父类名。

## 保留的决定与本轮修复

延续原确认的结构与颜色规则，包括普通蓝黑节奏和蓝黑霍佳葛子类、混绿霍佳葛、
独立纯黑克撒传风暴、红蓝神器、无色画家，以及主牌黑掘坟不因备牌转换计划拆父类。
Chaos Defiler 的不计色仅用于画家焊接用途；已确认塔脉炉的双用途仍计黑红。
Haywire Mite 的不计色适用于旧计色入口和最终用途判定，不能被中间分支重新加绿。

Owner 在本轮明确确认两处重复身份统一：39 条空子类蓝白控补为已有纯蓝白子类；
3 条空子类蓝塔补为已有纯蓝子类，统一显示“蓝塔／Blue Tron”。父类均不改变。
这 42 条中 41 条为历史记录、1 条为 W44。没有新建构筑子类。
纯色补全要求实际支付证据明确；没有证据的新构筑不能借此默认归纯色。

共享牌名标准化与原用途词表的名称差异也已接通，包括房间双面名称和同牌异名。
缺失用途证据或未登记的最终身份保留为 Unknown，并返回原因，不猜测新名称。
公开运行资料剔除了私有研究路径；人工原表标签和名次修正仍留在私有审阅档案。

## 验证与停止点

以未改写的最终私有快照为预期，加上本轮 Owner 明确确认的两处修正：

- 同输入核对 4,186 条历史及 W44 的 155 条记录，包含 2,966 个不同主备牌输入。
- 保留 1,783 条原固定案例的已批准迁移和负向保护；同时核对正常牌表入口与规则重排。
- W44 常规周维护入口、统计、八强及对阵身份层级均使用相同分类；核对完整主备牌、
  名次、子类汇总及中英文名称。
- `tests/test_legacy_policy_integration.py` 使用去除身份和人工标签的牌张样本，
  覆盖 P1–P4、Mite、混绿霍佳葛、空子类修正、牌名别名、冲突与未知用途。
- 既有共享引擎和本次周维护读入口执行有针对性的检查。没有改变其他赛制规则或名称。

测试命令：

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_legacy_policy_integration.py tests/test_classifier_evaluation.py tests/test_classifier_shared_semantics.py tests/test_classifier_rule_contracts.py tests/test_reviewed_subtype_display_names.py -q
```

私有整合报告与 W44 HTML 保持在研究工作区，不提交完整人工对照资料。
HTML 的数据和交互脚本已检查；不将这些检查称为浏览器视觉验收。
后续上线准备仍须检查 Legacy Landing、共用代表牌、完整发布窗口产品及页面实际显示。
本轮不重新打开已确认分类讨论，不启用公开目录，也不执行推送、合并或发布。
