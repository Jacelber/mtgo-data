# 覆盖与分类

在已保留输入上运行只读报告，输出放私有任务目录：

```powershell
python tools/melee_event_delivery.py audit --root ISOLATED_ROOT --format FORMAT --event-id EVENT_ID --output NEW_AUDIT_JSON
```

报告核对事件／规则／分类输入绑定、原始响应校验值和唯一参与者；提供人数、排名、牌表状态、Unknown 完整牌表、缺失名单、DQ 与原质量结果。它不替代赛程及统计语义核对：结合轮次、对局和机会数检查 bye、无出席、ID、判胜、DQ 双方排除和淘汰赛范围。报名栏数字与实际排名不同，应记录来源差异，不能从恰好相等推断原因。

面向用户区分已提交且可用、未分类、冲突／无效和来源无牌表；Unknown 提供名次、选手、原链接及完整主备牌入口。非阻断 Unknown 是否暂时接受属于用户决定。审阅保留不等于已形成可发布产品。

用户给出分类意见后，先检查现有完整牌表规则，落实必要条件、父／子类及中英名称／颜色，避免选手或赛事 ID 特判。规则内容变化且缺少有效既有证明时，对同一保留输入进行一次 accepted 到最终 candidate 比较；纯名称／颜色修改只核对名称、颜色及受影响消费者：

```powershell
python tools/compare_classifier_impact.py --repository-root ISOLATED_ROOT --format FORMAT --accepted-rules ACCEPTED_RULES --candidate-rules CANDIDATE_RULES --expected-changes EXPECTED_JSON --output NEW_IMPACT_JSON
```

expected 来自用户决定与独立输入，没有预期变化清单时省略该参数。分别解释身份迁移、仅命中记录／优先级变化、Unknown 和冲突；有效既有证明直接复用。accepted 规则放在加载器支持的规则路径，保持其配套依赖可解析。

先明确派生范围：无共享规则变化只生成本场确缺步骤；共享规则改变同步同赛制当前 Melee 消费者与受影响 MTGO。来源事实、公开范围、周报编辑内容及完成记录分别保留。当前赛事成员由实际目录决定，不冻结事故中的赛事数量。完成后进入完整候选。
