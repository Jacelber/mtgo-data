# 7 组合与复用

输入：本批实际页面、范围明确确认和技术证明。复用组成固定候选。
正常逐赛制路径直接取6最后的累积site；每个赛制的原确认对应到这个site，只读相关依赖，不重新运行prepare、facts或浏览器。不得只取一个独立赛制快照却声称包含全批。
`python tools/review_submission.py --root SITE preview --format FORMAT --entrypoint HTTP_URL --output NEW_DIR --decisions ACCEPTANCE` 使用既有实际对象绑定。第6步确认须对应页面而非仅内容数据；机械复用有效依据，不全面重验来证明复用。
技术摘要／位置改变不自动重问；实际展示／交互变化只提交差异。缺映射是技术取证，未知不通过。组合／资源／预览失败保留单赛制成果，恢复原结果不重开业务选择。
通过既有 `finalize-source --root ROOT --source SOURCE --site SITE --acceptance ACCEPTANCE --facts FACTS --output RESULT` 固定本批已确认内容；它同时产生 `.delivery.json`。参数均来自第6步已有材料，不重造确认。多赛制交付须覆盖同一最终组合的所有确认，不能用单赛制记录冒充全批。
多赛制已有各自记录时，使用 `combine-content --root ROOT --site FINAL_SITE --record RECORD_A --record RECORD_B --compose --output BATCH.delivery.json` 绑定最终累积页面，可重复 --record。它在新的私有目录保留ROOT的当前数据，叠加已确认Landing字节、沿用本地卡名和图片，仅更新必要的产物绑定；四赛制共用一次组合，也可传单赛制记录。分步保存结果，失败后原命令续作；资源不足明确报告缺项，不自行联网。组合后再次核对既有页面确认，实际展示变化仍按原范围处理。仅接纳尚未开始交付的记录，已开始的原操作先按第8步查清；保留旧操作，不另写临时组合脚本。
输出：完整固定候选和交付记录，条件满足直接8，无空验收或发布许可。禁止无关生成、改文案、发布及completion。
