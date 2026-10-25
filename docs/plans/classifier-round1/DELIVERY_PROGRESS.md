# 首轮交付续作

当前状态：共享颜色、已确认用途例外、父类共同条件及已定位的局部修正已接入本轮涉及的四个赛制。完整回放共 37,447 份牌表，Unknown 为 Modern 20、Standard 1、Pioneer 0、Pauper 1，均有适用处置，无待答分类问题。四个赛制本地产物均已同步并验证为 CURRENT；发布仍暂停，未提交或推送。最终差异见 [影响核对](IMPACT_REVIEW.md)，具体实现见 [原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md)，范围限制见 [维护清单](REMAINING_COLOR_WORK.md)。

以下为此前阶段记录，其中的“最新”与数量仅指相应阶段，以顶部链接为当前状态。

最新执行状态：本组历险用途例外、两张新增护身符用途、Standard Temur Prowess 与 Jeskai Looting 父类决定均已实施。红蓝／洁斯凯滤牌共享必要结构核心；本次 100 项受影响检查通过，标准 7,148 条回放只有已确认牌表 Unknown → Jeskai Looting 一项增量。严格颜色接入为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；标准当前 Unknown 26（较原冻结基线新增 21）。这组决定不再待答，更早待维护项继续保留。详见 [实现与剩余边界](FLING_EXCEPTION_IMPLEMENTATION.md)。下文此前数字属于阶段记录，尚未提交或发布。

最新 Owner 决定：保留原有共享颜色原则，Sell-Sword／Otter 使用局部用途例外。对应额外色源为零或一张时不因其相关卡面算混色，足量配置则计色；4 Blood Crypt 正例保留。未批准“至少两张”门槛，也不影响其他正常同色咒语。用途例外尚未接入生产；下文旧待答状态以 [历险用途方案](ADVENTURE_OPTIONS_AND_VALIDATION.md) 顶部最新确认为准。

状态：分类改进与具体类别决定已落实，当前派生产品同步和必要验证进行中；未提交、未发布。当前分支 `codex/classifier-shared-semantics`，冻结原始基线见 IMPLEMENTATION.md。

Owner 最新指示：暂缓发布，正常推进其他三个赛制的实际修正。2026-10-23 的接入前核对保留在 [OTHER_FORMATS_COLOR_AUDIT.md](OTHER_FORMATS_COLOR_AUDIT.md)；2026-10-24 已将新颜色机制接入三个赛制共 43 个父类，详见 [OTHER_FORMATS_IMPLEMENTATION.md](OTHER_FORMATS_IMPLEMENTATION.md)。当前仍有用途／类别边界；旧 Pauper 测试缺口已修复，下面的 CURRENT 结果只证明上一候选，不能用于本版。发布与环境发布步骤均暂不推进。

最新决定已落实：Standard Fling 构筑的备牌单张 Frog 为护身符用途，不因 Starting Town 加绿；限定构筑范围并保留其他正常绿牌贡献。29 条有来源记录与 1 条无来源记录均已核对。三个相关父类新增用途诊断，历险色组筛选仍待后续判断；当前统一核对 Sell-Sword 黑色与 Otter 绿色的施放判据，见历险用途方案。

Sell-Sword 补充决定：Owner 明确“4 张 Blood Crypt＋仅 Sell-Sword 用黑”应为红黑。当前三条 Pioneer 记录已正确归 Rakdos Leyline，已补完整牌表和同色换地回归保护；不再请求这类牌表的业务归属确认。剩余问题是如何识别其他边缘构筑中的正常施放用途，不将此正例扩展为未经批准的统一四源门槛。

继续开发后的最新进度见 [ADVENTURE_OPTIONS_AND_VALIDATION.md](ADVENTURE_OPTIONS_AND_VALIDATION.md)：修复 Multiversal Passage 来源识别、实现可配置历险卡面用途、完成 385 条试算；修复已有 Gruul Landfall 漏识别，严格颜色接入现为 43 个父类；旧 Pauper 验证缺口已修复，174 项通过。Owner 已纠正两张历险牌的不对称处理；原单独 Sell-Sword 提问撤回，已补同一 385 条记录的统一判据试算。单张来源门槛尚未批准，不再重问 4 Blood Crypt。历险候选口径未写入生产规则，发布仍暂停。

## 已解释的当前 W42 绑定更新

Modern 首页中英文正文、Feature 选择、名称、颜色、代表牌维度与原接受记录逐项相同。使用冻结旧代码重算事实摘要为 `600c6f9408263c44acc28daaeb58e185c33ed88b7d4e3a7d689139de248838d9`，与原接受记录精确相符；不是拿候选输出当原始正确答案。

新事实只有一条机器观察将 Esper Blink 的 parent 标识改为已批准的 esper 子类，score45、参照66份及全部牌表差异不变。完整 104 份八强目录中仅以下 5 份补上已批准的普通 esper 子类，其他字段、成员集合不变：

- `deck:40d6f1600ddfdf8c914d`
- `deck:8ce4068712eb5da1fb62`
- `deck:6f06837741c02221d950`
- `deck:ad1761a5e4ff44be6b07`
- `deck:df413c762bad20ced2ac`

因此使用现有 `reuse_decisions` 重用原逐项决定，更新当前 W42 review 的 bindings 和 submission；原 decisions、review 正文对象完全不变，没有创建新的 Owner 确认。旧 review 字节保存在 `/workspace/scratch/classifier-round1/modern-W42-review-before-rebinding.yaml`，前后摘要及严格比对在同目录 `modern-W42-rebinding-proof.json`。所有历史周次 review 不修改。

## 历史档案保护修复

既有生成器在分类重建时给所有历史 Feature 档案写入最新 classifier_digest，触发闭合工具的越界保护。这不是通过扩宽保护清单解决：已限定 `allow_classifier_restatement` 路径保留当前周以前的既有档案、校验其格式／周次／来源绑定，且不重新分类历史 Feature。当前周的 Feature 档案和 index 属于实际依赖，补入闭合产物登记。

7 项针对性检查通过，覆盖历史对象不重新分类、来源变动拒绝、当前周产物登记、保留旧首页绑定与破坏反例；相关 ruff 通过。失败暂存目录保留，只恢复失败生成造成的历史档案改写，再重建受影响 Landing／metadata，从原目录继续验证，不重做统计采集或全量分类对照。

## 外部访问限制

2026-10-23：原有 HTTPS Git 只读查询成功，远端 HEAD 为 `34235d879475c0b4f40e4d6dff43b21a230e67f7`。GitHub API 查询被云环境允许列表拒绝；`api.github.com` 不在当前已生效列表。已通过环境设置技能保存仅新增此域名、保留原有域名的草稿。工具确认 saved，requires_publish=true；需用户在环境设置保存并发布后重新检查 API。未新增秘密要求，也未尝试绕过代理。

API 恢复后核对既有 22 个 Melee Unknown 的原公开处置、当前远端状态、可信资源缓存／私有恢复包及后续交付入口。现有旧 Unknown 标签不自行转为接受依据。尚未取得完整部署包大小与发布证明，不能声明整轮交付完成。


## 本地验证补充

- Standard、Pauper、Pioneer 的闭合结果已为 CURRENT；当前周 Feature 只同步分类 provenance，历史周次逐字节保留。
- Modern 暂存目录的 11 场 Melee（含 434455）已重建；逐场、逐 scope 对照，除类别分组外的总体指标完全相同，quality counts 全部相同。四赛制原输入哈希仍与冻结 manifest 一致。
- 使用系统 Chromium 检查真实候选页面：405588 的 Four-Color Control／四色控制、405591 展开的 Esper Blink/WUBR 中英文名称正确，W/U/B/R 四个 SVG 图标已加载并解码，无运行时异常。结果在外部 browser-verification.json。未声称已验收完整部署包或线上状态。
- 前端共享指示色已由现有生成器更新，新增 14 项配置；没有修改其他渲染行为。
- Modern 大对局文件的格式检查曾超过默认 120 秒，输出仍保留；现从同一 stage 以 600 秒运行时限续验，不改变 schema 或质量标准。

最终本地同步结果：Modern CURRENT，134 个派生产物更新；112 份公开 JSON、22 份内部 Melee JSON 格式检查全部通过（同一保留 stage，443 秒）。四赛制均已完成当前派生闭合。统计生成目录与验证日志均保留，不需重做已通过结果。仍未提交、构建完整部署包或发布。

## 最新本地派生产物同步（2026-10-24 续作）

沿用 classifier_closure，以当前规则和同一保留输入重新生成并原子同步三个已稳定赛制。Standard、Pioneer、Pauper 均为 CURRENT；分别同步 55、41、53 个产物。Standard 55 个公开 JSON、Pioneer 41 个公开 JSON、Pauper 51 个公开及 2 个内部 JSON 的格式检查全部通过。原始输入与已接受历史内容保护检查通过，没有抓取新数据或发布。

新增标准地落、Kona 两个子类、红黑鬼怪，以及先驱 Esper／WUBG 变境、Pauper Orzhov／Naya 战呼与 Sultai Gardens 的实际公开名称文件和层级目录已按 Owner 确认核对；Pauper 中文使用“苏勒台控制”，不是“苏勒台花园”。

当前产物证明为 `/workspace/scratch/classifier-round1/closure-stable-formats-result.json`，过程日志为同目录 `closure-stable-formats-progress.log`。三个暂存目录保留在结果记录中，可直接续查，无须重做已通过对象。

Modern 仍等待剩余具体 Unknown 处置，不把其他三赛制的 CURRENT 当作整体交付完成。未提交、未推送、未发布。

## 最终本地同步完成（2026-10-24）

Modern 最终闭合已为 CURRENT，原子同步 132 个派生产物；110 份公开 JSON、22 份内部 Melee JSON 格式检查通过（303 秒），736 项原始输入／已接受历史内容指纹保护通过。Standard、Pioneer、Pauper 的既有本轮 CURRENT 结果仍适用，没有重做其通过的生成与检查。四赛制合计本次同步 281 个产物。

实际生成的内部分类和公开 decks 数据已核对：最后四副继续 Unknown；Amalia 与 Dimir Mill 两项局部修正恢复到既有父类；Modern 剩余 20 条 Unknown 全部保留适用处置。四副各自 11 个保存版本均为 Unknown，按 Owner 最新指示不再询问。

结果：`/workspace/scratch/classifier-round1/closure-modern-round1-final.json`；日志同名 `.log`；暂存目录 `/workspace/classifier-closure-modern-c1df093bb4589e24`；具体归属核对 `modern-final-generated-identity-proof.json`。三赛制结果沿用 `closure-stable-formats-result.json`。完整原基线对照见 [影响核对](IMPACT_REVIEW.md)。

当前完成的是本轮分类器代码、适用回归验证和本地产物同步。仍未提交、推送、打包完整部署候选或发布；外部归档／部署确认未执行，不能将 CURRENT 宣称为线上已更新。Legacy 和后续统计／前端／性能工作不属于本轮。
