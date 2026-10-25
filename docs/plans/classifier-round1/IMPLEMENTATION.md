# 分类器首轮实现与核对记录

当前状态：共享颜色、已确认用途例外、父类共同条件及已定位的局部修正已接入本轮涉及的四个赛制。完整回放共 37,447 份牌表，Unknown 为 Modern 20、Standard 1、Pioneer 0、Pauper 1，均有适用处置，无待答分类问题。四个赛制本地产物均已同步并验证为 CURRENT；发布仍暂停，未提交或推送。最终差异见 [影响核对](IMPACT_REVIEW.md)，具体实现见 [原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md)，范围限制见 [维护清单](REMAINING_COLOR_WORK.md)。

以下为此前阶段记录，其中的“最新”与数量仅指相应阶段，以顶部链接为当前状态。

最新执行状态：本组历险用途例外、两张新增护身符用途、Standard Temur Prowess 与 Jeskai Looting 父类决定均已实施。红蓝／洁斯凯滤牌共享必要结构核心；本次 100 项受影响检查通过，标准 7,148 条回放只有已确认牌表 Unknown → Jeskai Looting 一项增量。严格颜色接入为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；标准当前 Unknown 26（较原冻结基线新增 21）。这组决定不再待答，更早待维护项继续保留。详见 [实现与剩余边界](FLING_EXCEPTION_IMPLEMENTATION.md)。下文此前数字属于阶段记录，尚未提交或发布。

状态：开发和具体业务边界核对中，尚未生成完整交付候选、提交或发布。本文件记录实施事实；完整牌表及决定依据见同目录 REVIEW 文件。

2026-10-24 续作：Owner 要求正常推进其他三个赛制，现已实际迁移 43 个父类，并修复共享返照／增幅及付色效果判断。范围、验证、未解决色组及旧测试情况见 [OTHER_FORMATS_IMPLEMENTATION.md](OTHER_FORMATS_IMPLEMENTATION.md)。发布继续暂停，上一候选的派生闭合结果不代表本版已同步。

## 范围和冻结基线

沿用 Owner 已批准的 A1–A6：共享计算身份、离线卡牌事实、主备牌用色、父类共同条件、已定位 Modern 局部问题、摘要／对照验证和当前产品交付。Legacy、全局结构分类、机器学习替换、Saga／Delirium 重组、后续统计向量／前端／性能工作不在本轮范围。

分支 `codex/classifier-shared-semantics`，冻结基线 `34235d879475c0b4f40e4d6dff43b21a230e67f7`。外部诊断目录 `/workspace/scratch/classifier-round1/` 保留旧代码、旧适配器输出、输入哈希、全量候选差异；没有用新适配器重做旧侧结果。

| 赛制 | 保留牌表 | 旧分类成功 | 旧 Unknown |
| --- | ---: | ---: | ---: |
| Modern | 18,830 | 18,808 | 22 |
| Standard | 7,148 | 7,143 | 5 |
| Pauper | 5,897 | 5,896 | 1 |
| Pioneer | 5,572 | 5,572 | 0 |

旧结果只用于比较，不是独立正确答案。完整对照签名包含归属、匹配、状态和错误，不包含全部 ConditionEvidence；冻结代码和原输入可供复现。

## 已实现机制

- `classifier_cards.py` 统一分类实体身份，Wear // Tear 保留所有可施放面；分割牌数量仍是一个实体，普通名称中的斜线不拆分。原始输入不改写，统计向量别名迁移不在本轮。
- 离线事实覆盖 4,644 个实体，包含各面费用、类别、规则文字及产色。分类不联网；缺失事实明确诊断并阻止相关颜色分支默默通过，不当作无色。
- 默认从主备牌咒语费用取色，普通单张咒语也计入。土地和起动费用不直接加色；多面牌、混合、非瑞克西亚费用按相应用途处理。
- Goryo’s、Creativity 的目标用途按 Modern 父类 profile 复用；`card_uses` 可显式指定具体实体的正常施放／非施放用途。按卡调整后再合并，不抹掉其他正常同色咒语。
- 规则 1.2 增加父类共同条件、颜色 profile、动态颜色子类，以及有限 `any`／实体去重 `total_count`；旧 1.0／1.1 保持旧语义，不批量迁移其他赛制。
- 父类条件 AND 子类条件，证据标明 parent 来源；保留规则级优先关系和所有匹配，不开启全局父类优先。对有强共同核心的必需颜色子类可阻止低优先级兜底；共享其他父类核心的 Esper／创新等不机械启用此阻断。
- 摘要包含卡牌事实、用途策略和旧语义依赖；父类／分支排序规范化，但证据条件顺序保留。未知报告带颜色原因、缺失事实与相关匹配；MTGO／Melee 对应 schema 同步。
- 新共享模块纳入生成输入指纹，避免恢复执行时复用过期产物。名称合成器支持完整子类名与父类连字符差异，不重复拼接。
- 冻结完整链工具拒绝覆盖已有快照；对照工具检查原输入哈希和记录集合。`--accepted-rules` 保留兼容，但不代替适配器变更的完整链对照。必需输出缺少格式映射时不能误报通过。

## 正常法术力基础与备牌用色

Owner 明确：不能把理论上能产某色等同于分类所需的正常混色基础。通用产色神器、生物、Fable 珍宝不独立建立额外混色；单张 Mycosynth Gardens 和依赖起手运气的 Gemstone Caverns 同样不构成依据。主备牌正常地源共同检查，抓地按保留目标覆盖；受限产色和 Reflecting Pool 不凭空增加颜色。多张 Gardens 等未讨论边界不从单张结论推导普遍数量门槛。

`mana_support` 表示此分类用途的正常地源，而非全部游戏内产色。没有相应地源的备牌不贡献该色，诊断为 `sideboard-without-land-color-support`；不会再利用 Poison Dart Frog 自身的产色能力循环证明其可施放，也不会连带使 Mutagenic Growth 增加绿色。当前通用缺少支持检查作用于备牌及既有可选费用／多面用途，未建立所有主牌的完整可施放性模型。

完整 Wailing Ghoul 样本保留 `broodscale-combo/gruul`，不新增 Jund；原表仍是 2 Wailing Ghoul，没有 Talisman of Resilience。Warping Wail 只是可能误录的猜测，不作替换依据，不建立全局黑名单。完整青蛙灵技样本不增加绿色；其中一份仍有 Blood Crypt／Callous Sell-Sword 的正常黑色依据，按现有规则归 Grixis，另一份恢复 Izzet。未收录的 Tifa 赛事仅作为用户举例，不伪造历史牌表。

该支持规则变更的全量对照只改变上述 3 份 Modern 记录；其他已上线赛制签名变化为零。旧小样本把 Mox Opal 当作 Surgical 黑色支付依据，与新口径不符，改为有 Watery Grave 的真实支持情境，并保留“只有神器不建立混色”的反例；没有盲刷历史 expected。

## 已确认的具体类别决定

- 新增下水道 `temur`、`bant` 子类，父类保留。
- 新增介刀 `temur`。Firespout 有正常地源支持且付色改变效果时计入对应颜色；不扩大为所有混合费用牌都算两色。
- Jeskai Ascendancy 走已有 `jeskai-ascendancy-combo` 父类，新增 `jeskai`／`four-color`，修复 Portable Hole／Tamiyo／Saga 辅助条件硬门槛。不新增四色介刀。
- Esper Goryo’s 新增普通 `esper` 和 `wubg`；WUBG 留在 Esper 父类。原 `four-color-goryos` 保持独立 ID，显示 WUBR Goryo’s／四色怨灵（无绿）。不因用户对 Looting 的初步说明强制所有 WUBR 必须有 Looting；另有 Fable／Phelia 路线见专门核对文件。
- 新增 `rakdos-creativity`：Rakdos Creativity／红黑创新。保留 Creativity≥3、Mine≥1、Archon≥1 共同核心和黑红正常颜色，Persist 不作为整个父类必要条件。
- `jund-creativity` 下新增 `jund` 和 `four-color`（UBRG Creativity／四色创新〔无白〕），父类统计保留。两份 UBRG 样本进入四色子类，6 份普通勇得补 jund；原 W38 小样本相应更新预期，依据 Owner 决定。
- 最新 Owner 明确同意：WURG 构筑仍归 `five-color-creativity`，不新增任何子类。保留原五色分支，新增 WURG 同父类分支，继承共同核心；正常颜色诊断仍为 WURG，公开类别名称、统计归属、父类五色标识沿用现状。不是所有创新都强制归五色，也不把辅助牌 Teferi／Ending 等升级为永久必要条件。

其他局部修复按原计划限定：Company 不强制 Hierarch4；Sewer／Steel／Oculus 共享核心；用色替代已定位的具体地名或颜色代理；Wizards 保留功能性排除；Tron 仅放宽已有证据的 Mine4→3；Hammer 不改。灵技只混备牌蓝色时仍保留原结构路线，避免因无主牌 Preordain 错落 Burn。

Broodscale 当前落实 3＋2、拒绝仅 1＋1、不强制指定终结手段、不排除 Saga／Emrakul。3＋1 的统一数量标准尚未获批，当前语料无该样本不能当作其不存在的证明。

## 创新家族核对

遍历 18,830 副，提取全部 55 份主牌含创新的记录，原输入 365 个文件哈希与冻结基线一致。44 份具有 Teferi＋Ending／Binding 配置，其中 40 份带 Binding、4 份不带；此分组用于审阅，不作为新的强制结构门槛。

正常咒语颜色 WURG 的有 18 份：16 份此前通过 Binding／Domain 惯例归五色，2 份无 Binding 原为本次待定。另有无 Binding、仅 1 Persist 提供正常黑色的同路线参照。两份待定与该参照共享 51/60、54/60 张主牌；重合用于解释组件变化，不引入相似度分类器。旧五色标签曾包含勇得／红黑误归，不能拿旧标签当答案。完整索引及核对见 CREATIVITY_FAMILY_REVIEW.md。

最新获批 WURG 路线的内存试算在全部 55 份含创新牌表中只恢复两份待定的父类归属；已加入正式候选；完整 Modern 对照确认只有这两份从 Unknown 回到 five-color-creativity，其他签名不变。

## 事实快照与验证

事实来源 URI `https://data.scryfall.io/oracle-cards/oracle-cards-20261022210155.jsonl.gz`，压缩源 SHA256 `b567f5160c618730bf3a227a5496979917e4f6979687af32059097ce9e620d1f`。离线导出工具支持 `--existing-facts` 保持已有实体范围，从同一导出重建已验证逐字节一致。新实体扩充用 `--required-names`，不能凭更新摘要消除未解释差异。

此前已验证四赛制合计 37,447 副无缺失实体。共享机制／规则检查 95 项通过；随后 UBRG 完整样本和 Modern 契约 23 项、W38 契约 12 项通过；新模块 mypy、相关 ruff、输出 schema、生成输入指纹检查通过。所有结果按实际受改范围复用，不声明已经完成尚未运行的最终交付检查。

加入 WURG 之前的最新 Modern 对照为 18,801 分类成功、29 Unknown（22 原有、7 新增待核对），冻结旧链签名变化 1,313，主要来自 1,116 条 Esper 普通子类显式化；这不是错误率。另有一份四色控制落入 Azorius Control 必须处理，不能以兜底掩盖。Standard／Pauper／Pioneer 最近共享支持规则变更后的完整链对照均无签名变化。

## 尚待完成

本轮新增 Wizards／控制／Blink 具体归属已收敛，完整差异见 IMPACT_REVIEW.md；正在同步当前公开依赖产物（含已接受 Melee 434455）；沿用现有 classifier_closure、候选及交付流程核对实际完整包、保护历史和已接受内容，完成约定验收与发布。此前闭合检查四赛制均 STALE_REGENERABLE，符合当前只改代码／规则、未重建产品的事实，不能声称已完成交付。

最新 WURG 分支全量核对：Modern 18,830 副中 18,803 分类成功、27 Unknown（22 原有＋5 新增待核对），无新增冲突。两个完整获批样本及 Binding 惯例测试通过，新增样本同时断言正常颜色仍为 WURG；名称、子类配置及父类指示色未修改。剩余新增 Unknown 为 4 份 Wizards、1 份四色控制；另有 1 份四色控制错误回退到 Azorius Control，仍待处理。

Owner 已批准 Temur Wizards 新父类，中文纠正为“铁木尔法术师”；现有 Izzet Wizards 正式中文已为“红蓝法术师”，不需要修改。新父类继承相同 Snapcaster／Flame 核心及既有功能性排除，正常用色 U/R/G，不强制 Wrenn；配置和完整样本已加入候选，见 TEMUR_WIZARDS_REVIEW.md。蓝黑红两个 Unknown 的独立核对发现：放宽为 Snapcaster＋Flame＋Counterspell 的 UBR 控制路线还会涉及 9 份旧 Dimir Tempo，不能只声称修复两个样本；调查见 GRIXIS_CONTROL_SCOPE_REVIEW.md，尚未实施任何该方向迁移。

铁木尔法术师加入后的完整 Modern 对照：18,805 分类成功、25 Unknown（22 原有＋3 新增待核对），仅两个获批样本进入新父类；另 3 份 Unknown 仅增加颜色不符诊断，无额外归属迁移或冲突。完整样本、346 项名称契约、指示色及 Wrenn→Preordain 的完整牌表合法变体检查通过。正式红蓝法术师名称原本正确，本轮只纠正审阅文档中的误称，不修改真实卡牌译名。

Owner 已批准两份蓝黑红法术师归 Grixis Control。已统一父类原有核心和功能性排除，保留 Consult＋Push 路线，新增 KCommand≥2＋Thoughtseize/Inquisition 总计≥2 的回收／弃牌路线；新分支不排除 Frog。正常 UBR 取色替换原具体地名代理，未重写其他控制家族。两个获批样本、18 份既有控制、9 份相近 Dimir Tempo 及单张 Command 变化／父类核心缺失检查通过，完整 Modern 对照进行中。

Grixis 回收／弃牌分支全量完成：Modern 18,807 分类成功、23 Unknown（22 原有＋1 新增待核对）；只有两份批准样本归属变化，另一份四色 Unknown 仅改变颜色不符诊断，其他签名不变。完整样本和 Modern 契约 23 项通过。仍须解决最后一份四色控制 Unknown，以及另一份错误回退 Azorius Control 的四色牌表。

Owner 明确要求 WUBR 控制单列 Four-Color Control／四色控制父类。已实现 `four-color-control` 的 Wrath 路线及共享 WUBR 用色，不限制迅咒数量；不新增 Esper 子类、不修改既有 Esper 规则。完整样本已加入独立预期夹具，待全量对照。另一份 Ephemerate／Riddler 四色牌表不在该决定范围，继续单独核对。

四色控制全量完成：Modern 18,808 分类成功、22 Unknown（全部原有）；仅获批样本由 Unknown 进入新父类，其他签名无变化，无新增冲突。23 项相关检查、347 项名称契约与 WUBR 指示色检查通过。仍有一份四色云移路线错误回退 Azorius Control，不能将 Unknown 恢复原数量等同于所有问题已解决。

四色控制的完整 60 张变体检查通过：Consult3→2／Snapcaster3→4 仍归新父类；分别以 Consider 替换每项路线核心后均不再命中。下一项独立业务问题为 WUBR 云移归属，具体建议和两副完整文本参照见 WUBR_BLINK_REVIEW.md；尚未修改该家族规则。

Owner 选择将 WUBR 云移归入 Esper Blink 子类，不复用 Four-Color Blink。已新增 esper／wubr 名称与指示色，Ephemerate 路线单一定义并按共享颜色映射；其他旧路线补显式 esper 子类、保留原条件和 Goryo 混合路线归属。未向整个 Blink 家族复制 Atraxa 例外。完整样本及既有混合路线已加入独立预期，待全量对照。

Esper Blink 全量完成：只发生 812 份原有记录补 esper 子类和 1 份获批样本进入 wubr；其他签名不变。Modern 共 18,808 分类成功、22 原有 Unknown，累计对冻结旧链 2,125 条签名变化；数量不是错误率。共享机制／规则契约 95 项通过。进入既有下游闭合与保护核对流程。

下游收尾发现并修复既有历史 Feature 摘要重写问题，当前周实际依赖补齐登记。Modern W42 的原内容确认经独立冻结事实比对后复用，非盲刷摘要；细节及云环境 API 阻碍见 DELIVERY_PROGRESS.md。

四赛制派生闭合已完成 CURRENT：Modern 同步 11 场 Melee（含 434455），公开与内部格式检查通过；Standard／Pauper／Pioneer 同步分类 provenance，历史 Feature 档案保留。实际 Chromium 中英新类别及子类颜色渲染验证通过。完整部署资源、旧 Unknown 公开处置与远端交付仍受 GitHub API 网络限制，已保存环境配置草稿。
