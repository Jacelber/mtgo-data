# 8 发布与完成

输入：7固定候选与确认、4交付事实、已有准备／归档／操作。
`python tools/project.py status`先定位；适用准备复用，必要时`python tools/project.py prepare --site SITE --output NEW_DIR --source SOURCE_ID`。按docs/DELIVERY既有可信归档与`python tools/project.py preflight`后，正常获准维护才`python tools/project.py deliver --operation OPERATION --package PACKAGE_ID --base BASE_OPERATION --preparation PREPARATION_ID`；原操作续作用`python tools/project.py resume --operation OPERATION`。这些标识来自实际已有操作／准备，不能猜测，线上变化按新组合处理。本次构筑／隔离重放不调用远端写入。
线上基线变化形成新组合／准备，不改旧operation。保留其他交付，不重新生成。恢复前版按既定政策，合法首次保留限制；失败不自动rollback。
实际包、操作、线上受影响入口资源及保留产品须成立。未受环境影响证明复用。`python tools/review_submission.py --root ROOT completion --acceptance ACCEPTANCE --candidate PACKAGE --publication-state STATE --output NEW_FILE`机械绑定真实发布。不足则取证，不重发、不造completion、不重复Owner验收。
输出：MTGO／Melee／Landing各自事实，本批完成为聚合结论。报告范围与入口后结束，不自动建议优化、下一周或监控。
