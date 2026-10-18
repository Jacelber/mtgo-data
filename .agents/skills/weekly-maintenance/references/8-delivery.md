# 8 发布与完成

输入：第4步数据交付记录，或第7步内容交付记录。两者独立；数据交付不以完成第7步为前提。
正常已获准交付使用 `python tools/weekly_maintenance.py continue-delivery --record RECORD`，它按既有记录和实际状态调用资源补缺、检查、打包、归档和原操作发布接口。查询使用 inspect-delivery。数据记录保留旧 Landing，只登记数据交付；内容记录绑定已有页面确认。两者均不自行宣布整周完成。失败修复原入口后重复调用同一记录，不另写生产批处理脚本。已有旧包或旧操作但缺新交接时，按 docs/DELIVERY 查原事实，不能新造操作覆盖旧操作。
完整材料验证通过后由原交付记录保存结果；归档、发送和中断续作核对包、候选、输入、确认及检查实现仍相同才复用。失败不保存为通过，必要的远端状态和包身份核对继续执行。已知文件直接校验字节，不逐个重复扫描目录。
线上基线变化形成新组合／准备，不改旧operation。保留其他交付，不重新生成。恢复前版按既定政策，合法首次保留限制；失败不自动rollback。
实际包、操作、线上受影响入口资源及保留产品须成立。未受环境影响证明复用。`python tools/review_submission.py --root ROOT completion --acceptance ACCEPTANCE --candidate PACKAGE --publication-state STATE --output NEW_FILE`机械绑定真实发布。同批可重复传入 --acceptance，四赛制共用一个已校验解包目录；目录或原包字节变化时拒绝复用。原交付入口也自动生成各赛制content_completion。登记format-completion时继续使用已有分类材料；传 --delivery-record RECORD 从实际已确认包取用资源，核对源码其他内容仍一致，无需复制缓存回源码。图片检查先滚入视野并等待加载，分别记录尚未请求、加载中、加载失败和成功，加载后仍缺失才报告错误。
不足则取证，不重发、不造completion、不重复Owner验收。
开发与隔离验收只使用测试替身，不调用真实归档、维护或发布。
输出：MTGO／Melee／Landing各自事实，本批完成为聚合结论。报告范围与入口后结束，不自动建议优化、下一周或监控。
