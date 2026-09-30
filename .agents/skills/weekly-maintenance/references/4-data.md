# 4 数据交付

输入：3的分类、确认、影响证明、产品范围与阻塞。先定位已有阶段／包／operation，保留输入在隔离候选接纳并按范围生成。
将3已确定的产品范围写入PLAN：`{"week":"2026-W39","mtgo_formats":["modern"],"melee":[{"format":"modern","event_id":"405588","steps":["classification","stats","matchup","publish"]}]}`。示例标识必须换成本批实际对象；steps只列确需生成的产品，已有适用结果不列。执行 `python tools/weekly_maintenance.py stage-data --root ISOLATED_ROOT --plan PLAN --output RESULT`；程序按既有依赖次序运行Melee本地派生，再准备不含新Landing的MTGO隔离阶段，返回完整候选位置。这里publish是本地产品生成，没有远端写入。
已有成功阶段要重新核对时，用同一入口加 `--resume-stage STAGE --previous-result OLD_RESULT`，只续作既有阶段验证，不重新运行Melee。生成中断时保留错误指出的阶段及已完成项；按具体故障修复，使用既有 `python -m mtgmeta.mtgo --root ISOLATED_ROOT --format FORMAT publication stage --co-stage-format OTHER_FORMAT --resume-stage STAGE` 续作，不重新提交初始生成计划。未生成完整的阶段先补受影响产物，不能把resume当成缺失产物生成器。不为续作重抓。接纳仍使用既有已确认范围和记录，不由此工具创造授权。
打包／状态／原操作续作见8，首次具体交付问题才按docs/DELIVERY对应段读取。缺联合能力保留成果，不自行拆批。
保留旧Landing实际周次／分类／资源绑定，只补必要旧资源，不提前准备新Feature。接纳与规则不能提前给后台生产使用。
核对纳入／排除、绑定、统计／来源、受影响入口、旧Landing兼容、公开边界；复用证明。固定候选只打包不重生成；按既定授权统一交付。
禁止：fresh Fetch有效输入、从整站diff反猜范围、自动拆批／回滚、周完成记录。
输出：两来源实际交付事实，平台与产品确认分开。未知query、已有包resume。数据全批成立进入5。
