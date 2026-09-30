# 7 组合与复用

输入：本批实际页面、范围明确确认和技术证明。复用组成固定候选。
正常逐赛制路径直接取6最后的累积site；每个赛制的原确认对应到这个site，只读相关依赖，不重新运行prepare、facts或浏览器。不得只取一个独立赛制快照却声称包含全批。
`python tools/review_submission.py --root SITE preview --format FORMAT --entrypoint HTTP_URL --output NEW_DIR --decisions ACCEPTANCE` 使用既有实际对象绑定。第6步确认须对应页面而非仅内容数据；机械复用有效依据，不全面重验来证明复用。
技术摘要／位置改变不自动重问；实际展示／交互变化只提交差异。缺映射是技术取证，未知不通过。组合／资源／预览失败保留单赛制成果，恢复原结果不重开业务选择。
输出：完整固定候选和确认，条件满足直接8，无空验收或发布许可。禁止无关生成、改文案、发布及completion。
