# 3 分类意见

输入：固定材料、用户业务决定、本批原accepted分类器。先查现有分支，调整必要条件；确实不能表达才加分支。门槛须有业务理由，不按样本四张写四张，不合并既有独立分支或加ID特判。
顺序：局部诊断→稳定候选→身份／名称／颜色自动补齐→原accepted到最终candidate完整retained MTGO/Melee累计比较→按既有依赖确定产品范围。比较入口 `python tools/compare_classifier_impact.py --repository-root ROOT --format FORMAT --accepted-rules ACCEPTED_RULES --candidate-rules FINAL_RULES --expected-changes EXPECTED_JSON --output NEW_RESULT`。两个规则作用于同一已保留输入，不重新采集。expected只能来自独立用户决定及输入，不能抄diff；无需预期变化表时省略该参数。
无规则变化且证明有效不造candidate／不跑drift；纯名称只查消费者。受保护历史产品不强迁当前摘要。
禁止：重采、每个临时写法完整检查、无关引擎开发、提前生产暴露规则、内容制作。
输出：业务足够的表达摘要、变化与其他差异解释、完整确认覆盖、产品同步范围和发布阻塞。新边界仅问差异，旧决定复用；全批齐备直接4。
