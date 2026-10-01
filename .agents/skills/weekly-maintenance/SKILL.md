---
name: weekly-maintenance
description: 执行或续作本项目周维护：联合 MTGO／指定 Melee 分类、统一数据交付、Feature 与 Landing 内容及页面交付。查询或讨论只回答，不启动维护；遵守用户本次范围和终点。
---

# 周维护

恢复本次范围、当前赛制、终点与已有进度，只读取下一动作必需事实。沿实际依赖接续，条件齐备直接继续。当前实施／隔离验证不授权生产维护。

## 当前步骤

仅打开当前一份参考，结束后按实际缺口接续；不每轮读完整基准或源码找参数。

| 动作 | 参考 |
| --- | --- |
| 开始／接续范围 | [1-start.md](references/1-start.md) |
| 固定分类材料 | [2-classification.md](references/2-classification.md) |
| 分类意见落实 | [3-rules.md](references/3-rules.md) |
| 统一数据交付 | [4-data.md](references/4-data.md) |
| Feature／环境栏及缺项 | [5-content-options.md](references/5-content-options.md) |
| 用户输入、英文和实际页面 | [6-content.md](references/6-content.md) |
| 组合及确认复用 | [7-preview.md](references/7-preview.md) |
| 发布和完成 | [8-delivery.md](references/8-delivery.md) |

## 边界

- 用户决定分类含义、Feature有无／对象／类别／展示牌、逐条Feature中文、Landing中文。缺项一次提醒，随后只提醒剩余项；无委托不建议／代写。
- 已展示且沿用的环境配置默认接受；仅有配置不等于已展示。用户明确选择和中文定稿忠实转换不原样重复确认，英文及实际未决展示正常提交。
- 第6步展示实际页面，第7步默认复用确认。技术证据缺口由机器处理；复用判定不变成全面检查。
- MTGO／指定Melee同赛制联合分类，来源、统计、完成记录保持分开。统一交付覆盖自动入口；内容仍用既定MTGO来源。
- 固定快照不覆盖，保留输入及原操作续作。未知不冒充通过；失败不清零。完成后结束，不自动追加历史修复、优化或下一周。

工具：仓库根目录 `python tools/weekly_maintenance.py`，使用任务已确认的Python。子命令及参数见当前参考，正常路径直接执行。准备入口只写私有输出，不采集赛事、不发布、不自动接受决定；所选缺图按第6步补齐。pending齐备立即提交；真实故障才针对性读实现。

设计／验收才按标题定位 `docs/plans/weekly-maintenance-skill/BEHAVIOR_BASELINE.md`，运行时不通读。
