# 周维护 Skill 实施设计

基准：同目录 BEHAVIOR_BASELINE.md（最终审核版本）。本次授权：隔离构筑、必要工具适配、代表性真实 Skill 重放；不发布、不合入生产、不改历史记录。基准内过去的“尚未授权开发”描述记录当时范围，由当前实施授权接续，不改变业务规则。

## 能力对应

| 范围 | 可直接复用 | 薄封装／具体适配 | 验证 |
| --- | --- | --- | --- |
| 1 接续 | review_submission resume、既有交接事实 | Skill 按当前阶段读必要说明，不建批次状态 | 局部续作保持范围与终点 |
| 2 材料 | weekly_review、build_weekly_review_web、classification packet | 固定私有输出和引用；Melee 明确独立来源成员，不自动混入 MTGO | 快照不覆盖、局部确认不扩域 |
| 3 分类 | compare_classifier_impact、mana identity、既有分类器 | 指定固定基准和输入；无改动走复用 | 不修改业务分类；沿用既有比较测试 |
| 4 数据 | publication stage/resume、project prepare/status/resume/deliver | stage-data按已确定范围串联Melee本地派生及MTGO隔离阶段；续作绑定原计划／根／阶段 | 顺序、失败停止、续作不生成单测；未实测整批交付 |
| 5 待定材料 | screening、top8 subject、content dimensions、只读 Web | weekly_maintenance 固定入口汇总已知输入缺项、当前环境与已展示配置；稳定 Feature 引用 | Pioneer 真实 Skill 路径 |
| 6 输入与页面 | copy_links、landing_editorial、landing、资源缓存、preview packet | 输入机械核对；原始用户输入决定与显示默认政策按真实来源记录；固定 HTTP 预览与增量页面准备 | Pauper、连续小修改真实路径 |
| 7 组合复用 | preview_validity、既有 renderer repair | 复用已验收实际对象与相关依赖，不新增全面比较 | 同页复用及变化失效 |
| 8 交付完成 | project、review_submission completion、既有归档 | Skill 固定查询／续作路径；本次不执行写入 | 现有包身份和完成绑定测试 |
| P1—P6 | 现有日志、私有输出、阶段计时 | 短主入口和八份阶段参考；入口输出实际工作及耗时；独立模型执行记录 | 工具测试与 Agent 重放分别报告 |

## 实现形状

- 仓库内 `.agents/skills/weekly-maintenance/SKILL.md` 为可审阅、可发现的 Skill；按步骤加载 references，完整基准只用于设计及验收。
- `tools/weekly_maintenance.py` 为有限的本地准备入口，复用项目 Python 逻辑。输出到显式私有目录，不采集或发布；参数和材料约定在 Skill 中直接给出。
- 仅在现有记录不能表达新业务规则时扩展记录依据；保留原记录，新增依据不冒充过去曾展示／确认。
- 可确定性核对的字段由程序核对；模型负责真实对话解释、分类规则表达和英文，禁止猜测用户未给的选择。
- 复用报告包含实际读取／生成／下载／验证对象及判定成本；不添加 batch completion 真值。

## 验证与交付

先执行风险相关单元与工具集成测试，再使用 Skill 从正常任务输入进行 Pioneer、Pauper 和同会话小修改／确认的独立 Codex 重放。输入在相应节点提供，不提前供最终答案或底层命令。操作在隔离副本，生产写入不可用。

结果分行为符合、实际工作减少、Agent 耗时、生产观察四部分。实际支持范围与缺口随实现证据更新；不把存在命令或 Skill 文档视为执行验证通过。

## 实际改动与复用边界

本轮未重写分类器、统计、筛选政策、归档、发布操作或completion机制。生产模块改动共四处：导出已有图片缓存选择函数供资源检查复用；Landing及候选筛选允许共享一次已处理的输入；Melee审阅允许在内存中从保留输入取得当前分类覆盖，不改已存提交。

新增入口仅封装确定动作：facts、inspect、classification、stage-data、prepare、check-preview、serve、record-input、adopt-displayed、page-delta、accept-page、finalize-source。它们分别输出事实／材料／私有候选／绑定记录，不维护独立批次状态。现有发布与完成工具继续负责真实交付。

具体补缺：无Feature明确输入；固定事实与旧Landing分离；环境完整构筑及频次；稳定候选编号；中文牌名精确映射；中英文实际消费者先查资源再看图片；用户输入与实际页面确认分开；单Feature变化复用其余确认；页面确认直接转为既有内容记录。stage-data仅接受已确定产品范围，不重新发现消费者。

验证强度和未覆盖项见[VALIDATION.md](VALIDATION.md)。此实现是待验收的隔离分支，未安装到生产工作流、未合入master、未执行发布。
