# 周维护有效性与历史完成：开发验收说明

本次只实现 Owner 已确认的第 1、2 项，更新现有 Draft PR #438 后待验收。不合并、不发布，
不更改 W38 内容、规则、统计、旧验收或完成记录；不实施第 3 项预览资源范围优化。
开发基线：1349e63aa20af6581c15c34796e958c92842a529（已包含 PR #437）。

## 结果

1. 完整分类、Feature、内容导入/读取与 Landing 使用共享的材料比较。
   只有同一输入范围内保存的实际材料相同，才允许技术身份变化后继续。
   真实父类/子类、牌表、赛事、事实、正文、颜色、筛选策略变化仍被拒绝。
2. 新材料保存可比较依据，决定继续引用原验收快照；旧材料不回填、不重新签发。
   无旧材料依据时返回 evidence_required，由代理核查，不能把新摘要当成旧事实。
3. 历史完成是否有效与当前对象是否匹配分别报告。历史完成保留，当前差异列入
   historical_changes；下一周不因纯技术差异倒退。晚到赛事显示为 supplement，
   通知使用独立标识，原完成通知保持完成。现有数据接纳约束不变。
   补充队列按周检查未接纳赛事及接纳后尚未被完成记录覆盖的赛事；多个待处理周
   同时保留。历史差异不阻止已经办完的补充通知关闭。
4. W38 起新完成对象保存当次分类 submission；最终预览仍需与确认发布的确切包对应。
   当前源不可读取时报告当前差异，不因此抹掉已验证的历史发布事实。

## 接口修正

技术比较不再调用人工提交构造器。真实 `build_mtgo_weekly_review()` 产生逐牌组
`deck_material_digest`，Web 随后补全主备牌和 reference；共享比较将两者归一到
同一材料表示。主备牌与已有摘要矛盾、只提供一半牌表、缺少或无效摘要均拒绝续用。
人工提交仍要求完整主备牌和可直接定位的 reference。旧周没有摘要的原始 review
继续按既有完成合同处理，不为本次修复写入任何历史材料。

## 有限证明

测试涵盖跨入口复用、父类/子类/牌表变化拒绝、未展示英文与颜色保护、缺失旧证据、
连续两次技术变更、对话导入保留原摘要、历史完成后进入下一周、晚到赛事补充、
未确认发布不能视为历史完成，以及真实通知脚本的离线调用。
原完整分类/Feature/内容入口情境与旧 Landing 重述、归档完成检查复用其必要测试。
没有运行真实分类全量、页面浏览或全仓测试，没有调用外部通知或生产发布。

最终针对性验证：86 个测试通过（5.14 秒）；git diff --check 通过。

本次新增/加强的关键证明：

| 情境 | 结果与测试位置 |
| --- | --- |
| 真实生成器的原始 review 与 Web 补全形式 | 技术快照完全相同；人工构造器仍拒绝原始形态。`tests/test_weekly_classification_review.py::test_real_weekly_producer_continues_across_feature_readiness_and_completion` |
| 未变化、仅引擎版本变化、真实备牌变化 | 分别 current / equivalent / changed；实际 Feature 接纳判断、完成状态查询及 format-completion CLI 的成功/拒绝一致。上项测试参数化覆盖。 |
| 缺少/无效摘要、摘要矛盾、半份牌表 | evidence_required，不生成可续用快照。`tests/test_weekly_validity.py::test_classification_comparison_requires_consistent_material_evidence` |
| W38 前真实原始 review | 既有完成导出仍可用，不新增虚构材料。`tests/test_weekly_classification_review.py::test_legacy_raw_review_completion_keeps_its_existing_evidence_contract` |
| 晚到赛事从未接纳到已接纳再到完成覆盖 | 前两阶段保留 supplement，完成覆盖后移出队列，历史差异仍报告。`tests/test_weekly_validity.py::test_completed_history_survives_current_drift_and_late_event_is_a_supplement` |
| 多个待处理周 | 选择最早周，同时保留后续周的补充事项。`tests/test_weekly_validity.py::test_readiness_retains_all_queued_supplement_weeks` |
| 真实 workflow 通知脚本离线执行 | 原完成通知不重开；仅历史差异时关闭补充通知；另有更早待审周时不关闭仍待处理的补充；旧 handoff 无队列依据时不推断关闭。`tests/test_weekly_validity.py::test_readiness_workflow_preserves_old_notice_and_names_supplement` |

回归范围为 `tests/test_weekly_validity.py`、`tests/test_review_submission.py`、
`tests/test_weekly_maintenance_readiness.py`、`tests/test_weekly_review_web.py`，以及以下定点：

- `tests/test_mtgo_landing.py::test_classifier_restatement_requires_identical_accepted_material`
- `tests/test_landing_bundle.py::test_completion_requires_the_accepted_preview_in_the_confirmed_archive`
- `tests/test_weekly_classification_review.py` 中上表两个新增测试，以及既有
  `test_v2_completion_record_binds_full_review_subjects`、
  `test_completion_acceptance_event_membership_is_order_independent`、
  `test_v2_completion_rejects_name_bootstrap_even_with_formal_digest`、
  `test_completion_cli_rejects_name_bootstrap`

真实生成器测试只使用临时目录的一场合成赛事和一份牌表，没有读取或重新分类生产语料。
通知脚本使用离线 GitHub 替身，没有实际创建、修改或关闭 Issue。

## Owner 验收对象

- 接受“技术身份变化但实际材料一致”时复用决定，真实变化仍需受影响范围的确认。
- 接受历史完成不撤销、当前兼容性差异单独报告、晚到赛事独立补充的行为。
- 接受本次只对后续新材料增加比较依据，不以修复代码为理由重写 W38。

最终预览资源过宽的优化另行处理。旧材料仍可能需要代理核查，这是证据缺失的明确
限制，不代表重新要求 Owner 审阅已完成整周。PR 仅包含机制、测试与操作说明。
