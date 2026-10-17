# 4 数据交付

输入：3的分类、确认、影响证明、产品范围与阻塞。先定位已有阶段／包／operation，保留输入在隔离候选接纳并按范围生成。
将3已确定的产品范围写入PLAN：`{"week":"2026-W39","mtgo_formats":["modern"],"melee":[{"format":"modern","event_id":"405588","steps":["classification","stats","matchup","publish"]}]}`。示例标识必须换成本批实际对象；steps只列确需生成的产品，已有适用结果不列。执行 `python tools/weekly_maintenance.py stage-data --root ISOLATED_ROOT --plan PLAN --output RESULT`；程序先从同赛制当前目录补齐所有过期赛事（含434455），按既有依赖次序运行Melee本地派生，再准备不含新Landing的MTGO隔离阶段，返回完整候选位置。这里publish是本地产品生成，没有远端写入。
stage-data 在生成前保存 RESULT 同名的 `.generation.json`，成功后生成 `.delivery.json`。中途失败保留原目录，修复后执行 `python tools/weekly_maintenance.py continue-delivery --record GENERATION_RECORD`；内部按有效进度复用，补实际缺失环节。返回 prepared 后按第8步交付返回的 record。已有完整候选直接交付，不再次 stage-data。接纳沿用既有确认，记录不创造授权。
打包／状态／原操作续作见8，首次具体交付问题才按docs/DELIVERY对应段读取。缺联合能力保留成果，不自行拆批。
保留旧Landing实际周次／分类／资源绑定，只补必要旧资源，不提前准备新Feature。接纳与规则不能提前给后台生产使用。
核对纳入／排除、绑定、统计／来源、受影响入口、旧Landing兼容、公开边界；复用证明。固定候选只打包不重生成；按既定授权统一交付。
禁止：fresh Fetch有效输入、从整站diff反猜范围、自动拆批／回滚、周完成记录。
输出：两来源实际交付事实，平台与产品确认分开。未知query、已有包resume。数据全批成立进入5。
