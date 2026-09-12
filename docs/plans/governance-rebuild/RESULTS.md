# 治理重建实施结果

更新：2026-09-12。修订后的 [U6 已验收](U6_REVIEW.md)，U7 已取得下列实际切换结果。
本次收尾提交包含切换时发现的 Windows 环境修复；其最终合并事实以 Git/GitHub 为准。

## U7 实际交付结果

- Owner 明确要求在原授权内连续完成 U7，保留有效验证及最新恢复策略，不夹带产品修复。
- 已分别暂时停用原 Pages `325084643`、MTGO update `312241633`、Melee candidate `320126493`；查询 in_progress／queued／waiting／requested／pending 均为零。网站仍服务现有包。
- 切换前主分支核对为原基线，历史 ruleset 仅含 deletion／non_fast_forward，未改变。基线准备器实际确认部署 `6394719184` 后，将已归档包 `pages-fd42fbd24cc55d82f65e6905645b1e9c5bfae909c050aa57dab1ee33adbb8608` 登记为正式 `state/pages.json` 当前引用；没有重新生成产品。
- 自动审批最初拒绝将三项暂停与基线写入组合执行；命令未执行。补充已验收 §八的精确映射并逐项执行后均获允许，未重新要求 Owner 审批。
- [PR #394](https://github.com/Jacelber/mtgo-data/pull/394) 已合并，提交 `7adff02f8f92a2a3d7fb9a113e24494ec919909b`。新 selected 检查运行 `34679389367` 通过，仅核对入口和 STATUS；没有全量产品验证或旧合并证据门禁。
- 正式 [部署运行 34679526144](https://github.com/Jacelber/mtgo-data/actions/runs/34679526144) 已成功：product-archive 登记请求、github-pages 取回私有包、上传、发送及实际服务确认均完成。部署记录 `6406995564`，操作 `governance-u7-20260912-current`；复用原包全部字节，未抓取、分类、重新生成或修复 P14。
- 正式状态的 current 为上述新操作，previous 为 `baseline-6394719184`，两者指向同一已完整归档包，两个产品入口与公开目录的服务摘要匹配。pending／recovery／automatic_publication_pause 均为空。此同包切换保留可恢复引用，不虚构另一个不同内容的历史版本，也不将确认 passed 解释为 P14 缺陷已清零。
- Windows 首次调用在 GitHub 运行列表查询时用系统 GBK 解码 UTF-8，未到 POST 即失败；`GitHub.command` 已显式使用 UTF-8。同一只读查询实际解析 100 条记录通过，之后同一操作号成功提交。不用失败命令重启产品验证，也不将尚未发出的请求冒称未知写入。
- 原项目 `D:/dl/crawlerpj` 已从旧 master 快进至新规则，跟踪文件无额外修改，未跟踪预览／导出／工作区保留。实际重新读取 AGENTS／CLAUDE／Copilot，入口指向新职责规范；旧工作流文档、DECISIONS、全量验证、预检、合并证明入口不存在，统一入口的 entries 核对通过。收尾修复随最终提交继续快进同步。
- 外部项目记忆更新请求已核对存在。当前会话既有旧摘要文字不会被工具抹去，摘要后台重新生成尚无可核实结果；现行实际入口已明确取消其规则地位，本次续作未让旧阶段授权／全量要求控制执行。已打开任务的历史文字不作为另一套规则；不冒称记忆物理擦除，也不要求每项任务再声明例外。后续若发现旧提示实质重新控制任务，按当前任务范围纠正，不能将其当作新制度的要求。
- 临时验证 Pages 已删除，验证仓库 Actions 已停用，两个测试环境及归档／解密凭据、公钥变量已清理。四个 341–441 字节的合成产品 Release、合成周审草稿及 `state/verification-pages.json` 已删除；私有仓库只剩正式产品 Release `387423167`。保留验证仓库源码与历史运行记录供查阅，不保留运行站点或后台工作。
- 正式 Pages、MTGO update 和 Melee 手工入口已重新启用；保留原 09:00 UTC 定时安排，未手工发起采集。两个正式环境仍仅允许 master 且无人工 reviewer，历史防删除／非快进保护保持。平台有写权限者的历史重跑能力仍存在，受支持入口不使用旧写入运行续作；没有声称改 YAML 能消除平台外部能力。
- 本轮新增验证限于实际切换环境、归档／服务对象、Windows 受影响查询及重新加载的入口；此前机制和产品结论继续复用。Step 8 从 2026-09-12 起利用自然任务已有信息，首五项任务结束或 2026-09-26 先到者截止；不设置提醒、后台任务或新的填报。

## 本次 U6 文档纠正

Owner 暂不验收后的本轮只修改文档，保留此前实现和仍适用的验证结果：

- ROADMAP 删除固定旧赛制回归、全量收尾回归、重复恢复演练及另批发布的要求。
- STATISTICS_SPEC 将父子投影、平均牌表及来源完整性写成实际结果约束；删除固定 Standard 输出与全档案审计前置，保留缺失不能作零、计数守恒及版本兼容。
- PROJECT_SCOPE、FRONTEND_DESIGN_SYSTEM、DATA_ARCHITECTURE 清理已完成的 P2/P7/P8/P12 阶段授权和设计—实现—切换流程；保留双产品分离、有效公共路径、语言／尺寸行为、来源隐私、分类身份和旧字段含义。前端规定支持的尺寸不再等于每次重复测试。
- 只读复核 cloud master 仍为 `2e299cab25403e580c2677b4ac4c2a509104c080`。公开目录列出 Standard、Modern、Pauper MTGO；Modern Tabletop 为 `405590`、`441441`、`434455`（默认 `405590`），Pauper 为 `438329`。对应活动规范已同步；不由目录可用推断图片、颜色等缺陷已修复。
- 已把下文旧进度中被后续结果关闭的候选衔接、部署／恢复能力和缺少资产摘要分支改写为当前结论，保留历史失败和未知原因。正式生产基线初始化、实际切换、记忆重新加载仍属于 U7，未冒称完成。

事实来源：[公开产品目录](https://jacelber.github.io/mtgo-data/stats/catalog.json)、
[Modern 赛事目录](https://jacelber.github.io/mtgo-data/stats/modern/melee/index.json)、
[Pauper 赛事目录](https://jacelber.github.io/mtgo-data/stats/pauper/melee/index.json)。
本轮采用聚焦语义审阅及必要入口核对：7 份修订文档的 51 个本地链接均可达，
改动章节标题未留下旧锚点引用，文档 diff 无空白格式错误；配置、分类规则、数据和
前端产品路径无准备差异。没有修改实现、重跑产品验证或触发云端工作流。

## U1—U6 已完成的准备事实（阶段记录）

以下保留准备时的分次结果及当时未启用生产的边界；对应生产启用和环境确认已由上节实际结果关闭，不能再将阶段文字当成当前待办。

- U6 最终组合：整站来源选择实际覆盖请求提交和已交付来源；新增合成 Git 案例通过，未并入 master 的已交付来源会明确要求集成，不暗中覆盖。采集 checkpoint 改为按相关输入/执行实现判断；无关提交保留已完成操作，实际相关变化拒绝自动重绑定，聚焦案例通过。没有建立通用依赖分析平台。
- 检查入口的真实组合案例通过：选中 Standard 小样触发 Schema 和手算数值关系，合法结果通过、错误分母失败、无关 Modern 损坏不阻断；文档任务返回不需要输出检查。运行器明确区分未执行/零执行和检查失败，必要条件均不放行，对应案例通过。
- 写入终止但服务未确认的受改分支通过：成功平台的混合服务、已失败平台的未知服务、资源暂不可用和仍在执行四类状态均按事实处理；不擅自判定严重程度或回滚。聚焦案例发现部署编号补入时误触“换请求”保护，已修复同一请求的事实补全，并只重验该失败案例。一次测试命令误写类名导致未执行，改为准确选择后通过，未计为产品失败。
- 周审材料独立云端交接运行 `34675532942` 成功，prepare/retain 均完成；仅合成 JSON，加密后传入公共附件，可信作业解密、写入现有私有归档并重新下载比较。MTGO 未发布输出补丁同样加密，仅可信集成作业解密。源码/已批准输入的保留政策不变，业务审阅材料不进入 Pages 或恢复包。
- 首次基线准备器 `implementation/seed_product_baseline.py` 已只读运行，结果 `ready_read_only`：私有原包仍可取用，实际部署 `6394719184` 及必要服务资源仍匹配。正式状态未初始化，U7 切换时再次核对当时事实后才执行。
- 生产云端核对：master 仍为本节所列基线；Pages 为 workflow 发布；两个环境仅允许 master，无人工 reviewer；实际 ruleset `Protect master history` 保留 deletion/non_fast_forward 保护，无旧必需状态检查。四个人工维护工作流均已映射；GitHub 的动态 Pages 作业属于平台部署执行，不是另一条自行生成产品入口。
- 最后语法与引用核对覆盖受改工作流 Python/JavaScript/shell 和相应 job/step 依赖；未执行产品工作流。必要文档入口均可达，STATUS 为小型事实记录，完成 diff 检查。没有新增必须全量通过的收尾测试。
- 原项目 root 的已跟踪内容无本地改动，未跟踪预览/导出等保留，U7 可按快进方式同步实际入口；`.agents`/`.codex` 为空，有限专用 skill 搜索未发现其它项目入口。九份本地设计已变成迁移指针；一次性清单工具移至外部实施材料；无当前调用的旧 Standard 历史质量工具和代码片段 fixture 已退出。
- MTGO 提交准备已去掉 stale-base 自动重启整个 update 工作流和空证据提交。现传递已验证输出的实际 Git delta，在当前主分支保留不重叠变化；相关输入变化或输出冲突保留候选，交给 Codex 聚焦集成，不自动重新采集、生成或测试。四个合成 Git 历史案例通过：无关文档/另一产品更新保留、已成功提交续作复用、输入改变/输出冲突拒绝覆盖、无变化不新建提交。尚未在产品云端启用。
- Melee 准备稿关闭 checkout 的持久凭据，只在两个实际推送步骤提供令牌；将候选绑定移至结果验证前，移除相邻重复确认，保留提交前后内容一致性保护。两份修改工作流的引用与 58 段 shell 只做语法检查，没有执行其中采集或写入；新的 Git 集成行为由上述真实合成仓库案例验证。
- 本地加密入口支持指定已有 OpenSSL 路径；命令帮助及 Python 语法核对通过。DELIVERY 清理了残留“恢复须确认故障消失”的措辞，恢复完成确认所选版本实际服务，不重新引入机器判断回滚价值。
- Owner 已逐项确认“授权按上述迁移前提删除这 12 个文件”。已从准备分支删除 DECISIONS、DEVELOPMENT_WORKFLOW、OPERATIONS_RUNBOOK、MELEE_EVENT_ADMISSION_RUNBOOK、LANDING_EDITORIAL_PIPELINE，以及 CI-MASTER-ADMISSION、GOV-06/07/08、CI_EFFICIENCY_PLAN、DEVELOPMENT_PROCESS_RETROSPECTIVE_2026-07、GOVERNANCE-EFFICIENCY-20260815。有效业务去向见下表；主规则和业务入口无这些旧文件引用，Git 历史保留原文。该删除审批阻断已解除。
- 新恢复策略云端验证已完成：合成运行 `34673213234` 在当前版未标记故障时执行指令恢复；完成后保留暂停。`34673256390` 自动请求正常结束、部署 skipped；`34673374190` 明确解除仅更新状态；`34673433902` 随后正常自动部署既有合成 C，当前无 pending/recovery/pause。对应代码提交 `0b4fe437bd496d50abedcffdb1ee83b50a1bf108`，仅验证仓库，未改生产。
- 另补齐归档 API 不提供资产摘要时的下载核对分支：原字节可入库，损坏字节不登记完整，聚焦案例通过。资源复用入口固定允许旧 Pages 和替代 prepare-pages 两个生产者，继续绑定准确工作流身份/master/成功来源，拒绝任意第三来源；两个受影响案例通过。
- 已完成平台写入而服务内容未确认的聚焦分支通过：保留实际不一致观察和旧适用前版，不将未知冒称故障或完整服务、不自动回滚；明确记录写入结束后可执行 Owner 恢复指令。仍在写入时不能清除 pending。此分支为本地隔离验证，不冒称已模拟真实平台所有故障。
- 2026-09-12 Owner 已确认仅指令触发回滚，回滚附带暂停自动发布，解除依明确指令或提前授权；已同步总计划 v2.15、Step 6 v1.2、Step 7 v1.3 和 DELIVERY。已删除恢复请求的“当前版必须标记故障”前置条件。工具不判断是否值得回滚，不把每次回滚变成产品复测。
- 该策略本地 7 个聚焦案例通过：无故障判定的 Owner 恢复、恢复和单次修复发布均保留暂停、旧解除指令不能解除另一暂停、已占位自动写入被阻止、暂停不产生发布请求或假失败、明确解除不隐式部署，以及原恢复请求提交失败后的续作。仅重跑其中随后改变返回状态的案例，未执行产品测试或全套治理测试。
- 本地日常链路已改为 update → prepare-pages → 私有归档 → 标记 automatic 的交付入口；暂停时继续准备和归档，正常报告 publication_paused。Pages 在排队前及取用时也处理暂停，真正发送前再次核对冲突。工作流 YAML、嵌入 Python 和解除 CLI 已核对；该暂停／解除随后取得本节前列的独立云端结果，产品生产链路仍未切换。
- 云端基线：`2e299cab25403e580c2677b4ac4c2a509104c080`，与 Step 7 设计核查一致。
- 独立克隆：`.codex-workspaces/governance-rebuild-20260912`，分支 `codex/governance-rebuild-20260912`；默认 push URL 禁用。原检出及其修改未动。
- 成功部署 `6394719184` 的运行 `34607763179`、附件 `10266048690` 已在临时本地完整保全。部署 API 成功记录时间 `2026-09-11T14:04:02Z`。
- 真实 tar 包 552,130,560 字节，5,628 个普通文件，内容合计 547,666,947 字节。读取目录确认没有越界路径或特殊文件，两个产品入口存在。
- SHA-256：`e8797c49b6665950cd01f414c57127bbf9855d93be7aea757324644aee627caf`。这仅证明所保存包的身份和结构，不能代替产品质量或切换时线上状态确认。
- 私有归档仓库 `Jacelber/mtgo-data-releases` 已创建。真实部署 tar 未重新生成，压缩为 55,469,844 字节的传输包，完整上传并实际重新下载验证；包标识为 `pages-fd42fbd24cc55d82f65e6905645b1e9c5bfae909c050aa57dab1ee33adbb8608`，Release `387423167`。后续基线准备器已只读确认它对应当时线上部署；正式基线登记仍留待 U7 核对切换时事实，不把归档入库本身当作前版登记。
- 上传续作实际处理过 GitHub draft Release 的 tag 查询 404：通过列表定位已有草稿和完整资产，复用已上传字节后完成入库，没有重新上传整包或重做产品验证。
- Owner 已设置四个环境的 `ARCHIVE_TOKEN`，均通过名称查询确认。独立验证运行 [34667947270](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34667947270) 已在 `product-archive`、`github-pages` 两个环境分别完成合成包上传、完整取回及一致性验证；生成作业无归档凭据。正式产品环境实际执行仍待后续切换，不把同名密钥存在当作已经实测。
- 合成包 `pages-306d61f106688ed27e562f73d51f0924f511e154ee69b9a0c4d92fca03774917`，341 字节，仅含虚构文本，独立状态为 `state/verification-pages.json`。
- 本地新机制验证：初版打包／状态／检查选择 15 项通过；GitHub 传输 5 项及随后新增的 draft 查询 2 项通过；增加版本标识后只重验打包 5 项；新增平台衔接 6 项通过；拆分检查选择后只重验执行器 6 项。以上是分次受影响验证，不是累计覆盖率或全套通过声明。
- 合成 Pages 首次运行 `34668283606` 完成传递、请求受理，但远端返回 `deployment_failed`，未提供进一步原因，测试站点为 404。核对终止状态及首次空基线后清理该测试 pending，复用原包续作 `34668475218`。这两次历史失败保留；当时未完成的部署／恢复能力已由后述 `34668698295`、`34668934373` 及最新 Owner 指令策略运行取得实际结果，不再列为准备阻断。
- 续作仍在远端失败后停止相同请求。将 tar 目录结构与官方根目录布局对齐（产品文件内容不变）后，合成 A `pages-789d29b1b64164716a141cad10e1d3350ae342e6c5b8fed27a8be816bce682e7` 于运行 `34668698295` 实际部署并确认成功。平台未给出前两次的详细原因，因此仅将格式兼容性列为有依据的解释，不伪造确定根因。
- 合成 B `pages-77360b19c8226a8ca84c2b998d13400fe5c99c96a9eed6c1afd7073ff03dafbf` 于 `34668805074` 部署；实际读取页面确认新增测试链接返回 404 后，登记该缺陷，并由 `34668934373` 从归档恢复紧邻 A。恢复后实际页面 HTTP 200、显示 A 且不含失效链接，原恢复意图已解除；无重抓、重分类、产品重生成或源码回退。
- `34669039022` 提交恢复前的旧 A 操作基准，实际在 claim 阶段被拒绝，发送 Pages 请求的步骤为 skipped，恢复版未被覆盖。随后补充无写入失败记录的识别，避免一次正确拒绝形成未来永久阻断；对应两类状态的聚焦测试通过。
- MTGO 本地 staging 的隐式全仓验证、逐次规则测试和整套生成消费者 pytest 已替换为选中结果的 Schema／格式数值检查；已有范围与写入回滚案例四项取得通过，另有两项新案例证明无关损坏格式不阻断、真实计数错误和意外零输出被拒绝。原先两个命令断言误匹配临时路径中的 pytest 字样，已改为检查实际参数，未改变正确答案。
- 本次隔离运行环境只安装仓库固定运行依赖和 pytest 所需依赖；系统及失效的旧 `.venv` 未修改。环境准备失败均发生在产品验证执行之前，没有伪造产品失败结果。
- 所选 Schema 入口已改为只加载该输出的 Schema 及实际引用；相关两项案例通过，包括无关损坏 Schema 不阻断、合法数字变化被接受、错误值和未映射必要对象被拒绝。MTGO／Melee 两条工作流准备稿已移除逐次全仓／规则／消费者套件调用，改用变化输出入口。原候选编排与发布衔接缺口已由后续 prepare-pages、输出 delta 集成、加密交接及组合核对关闭；准备实现完成，正式生产启用仍在 U7。
- 续作新增三项聚焦案例通过：旧作业已结束且未发送才可由新作业承接，记录新执行作业身份；未发送状态可解除但保留恢复意图；仍运行或发送未知不能冒称未发生。错误目标不能先写入恢复意图的案例通过。任务提交入口的三项原案例亦通过（其中一处原断言错误要求重复登记意图，已依复用原则修正）。
- 归档增加发布时间、活动候选结束、到期清理入口；三项相关案例通过，验证当前／前版固定保留、并发冲突先停止清理、删除响应未知后查询续作。新增资产缺少 GitHub digest 时改为下载核对后才登记完整；后续已补齐原字节通过、损坏字节拒绝的聚焦案例，该验证缺口已关闭。
- 合成运行 [34670854494](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34670854494) 已实际验证加密候选交接：生成作业不持有归档凭据或解密钥匙，临时 Actions 附件仅含密文；可信归档作业解密原包、私有入库并取回同一字节。此前本地已验证原包一致及密文损坏拒绝。使用 OpenSSL CMS AES-256-GCM／RSA-OAEP，不引入新服务或 Python 依赖；加密不赋予质量或发布资格。
- 两个已批准仓库已准备 `ARCHIVE_HANDOFF_CERT` 公钥变量及仅 `product-archive` 环境可用的 `ARCHIVE_HANDOFF_KEY`。不同仓库独立生成；未读取或暴露既有密钥，临时私钥已清除。正式仓库尚未运行新交接入口。
- 项目记忆更新已按 Owner 明确授权提交至记忆系统更新目录：`20260912-111428-mtgo-governance-rebuild.md`。只请求替换该项目旧治理，保留业务和历史事实；实际后续注入是否更新尚未证实。

## 一次性迁移对应

本次删除混合旧文档前，按有效业务主题核对以下去处；具体分类处置仍保留在原规则、
名称和接纳配置中，不改写数值或重建历史裁定。原文统一按基线
`2e299cab25403e580c2677b4ac4c2a509104c080` 的文件及标题定位，可用
`git show 2e299cab25403e580c2677b4ac4c2a509104c080:docs/<原文件>.md` 读取。
下面补足关键章节，不建立第二张日常检查表；Git 保留来由，日常规则不再依赖 DEC 编号。

| 原决定／旧操作文档的有效主题 | 当前业务来源 |
| --- | --- |
| 两产品分离、共享分类、赛事类别／结构、赛制扩展范围、构筑／轮抽及空值区别 | PROJECT_SCOPE；STATISTICS_SPEC §§3–11；原 formats／melee_events 配置 |
| 理论轮次、ID／bye／drop／lock／DQ／no-show／Qualified、字面胜率、原始计数、层级矩阵和小样本提示 | STATISTICS_SPEC 的对应统计主题；DATA_ARCHITECTURE 的机会账本、事件质量和兼容说明 |
| 旧字段版本迁移、434455 兼容历史、动态目录及多赛事 active taxonomy | STATISTICS_SPEC；DATA_ARCHITECTURE 的版本与多赛事主题；原受保护业务 fixture 不删除 |
| 来源最小化、v2/v3/v4 原始快照、直接 source participant ID、不可用牌表、删除请求与权利范围 | DATA_ARCHITECTURE §§11–12；NOTICE、LICENSE；operations/MELEE_ADMISSION |
| 分类规则具体处置、稳定身份、名称、 intentional Unknown 与完整同输入审阅 | 原 my_archetypes／rules／名称配置；DATA_ARCHITECTURE；WEEKLY_MAINTENANCE，未修改分类内容 |
| 周产品、Top 8、Landing 筛选与文案、特征牌、工作簿输入、旧 Pickup URL 和历史 | STATISTICS_SPEC 的周与 Landing 主题；DATA_ARCHITECTURE 的 Landing／工作簿／兼容路径；WEEKLY_MAINTENANCE |
| 图片来源、社区图片既有许可、原字节保留、语言回退、有限本地资源 | DATA_ARCHITECTURE 的卡牌图与本地化主题；NOTICE。原 DEC-137 两段图像使用限制已逐字迁移 |
| 09:00 UTC 采集、输入 checkpoint、结果重用、候选／发布／恢复 | WEEKLY_MAINTENANCE 保留时间及业务交接，DELIVERY 与当前工具承担执行；旧 Gate／次数／全量／父链规范退出 |
| DEVELOPMENT_WORKFLOW §Gates／Permission classes／Pause and authorization／Accepted-task bounded repair | [GOVERNANCE](../../GOVERNANCE.md)「计划、授权与连续执行」「失败不撤销授权」「有限暂停条件」；逐阶段授权、失败次数授权和 READY 口令删除 |
| DEVELOPMENT_WORKFLOW §Validation／Change-impact discovery；STATISTICS_SPEC 原 §20 Required statistical tests；DATA_ARCHITECTURE 原 §16 Test architecture | [QUALITY](../../QUALITY.md)「阻断资格」「有限范围」「如何取得和复用证明」；[STATISTICS_SPEC](../../STATISTICS_SPEC.md) §20；[DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §16。固定套件／全量兜底删除 |
| ROADMAP Phase 16／17／19 的 Task sequence、Required work、Acceptance criteria | [ROADMAP](../../ROADMAP.md) 同名阶段保留业务结果、兼容迁移与恢复能力；固定旧赛制／全量回归及另批发布条款删除，实际触发转 QUALITY |
| STATISTICS_SPEC §§3.2、11.8、16.3、16.4、16.7；DEC-042「Calculate hierarchical matchups before the expandable front end」、DEC-043「Generate hierarchical MTGO range statistics before Phase 7」 | [STATISTICS_SPEC](../../STATISTICS_SPEC.md) 同编号章节保留父子身份／计数投影、公式和有效来源；旧阶段、Phase 6 字节冻结与全档案审计前置删除 |
| PROJECT_SCOPE §§3.2、4.2、9.5、10、11、12；DEC-051「Freeze a local format-first UI before Phase 8 backend additions」 | [PROJECT_SCOPE](../../PROJECT_SCOPE.md) 同编号章节：当前公开事实、既有页面结构、分类身份、未来产品方向及结果质量；旧 P2／P8 顺序和历史页面回归标杆退出 |
| FRONTEND_DESIGN_SYSTEM §§1、9、12；DATA_ARCHITECTURE §§12.1.1、15.9、25.1 | [FRONTEND_DESIGN_SYSTEM](../../FRONTEND_DESIGN_SYSTEM.md) §§1、9、12 保留 A3、响应式与设计选择；[DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) 对应章节保留消费者契约、两入口与当前 Landing 默认；P8／P12 开工、全视图验收和切换阶段要求删除 |
| DATA_ARCHITECTURE §§2.6、8.1–8.2、11.13、15.7、19、22、24；PROJECT_SCOPE 原 §12 Engineering-quality scope | [DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) 对应章节保留真实调用兼容、注册表资格、已实现 v4 保留契约、计数聚合含义；[PROJECT_SCOPE](../../PROJECT_SCOPE.md) §12 保留交付结果；旧 P7 顺序、全层级前置测试删除，执行职责转 GOVERNANCE／QUALITY／DELIVERY |
| MELEE_EVENT_ADMISSION_RUNBOOK §Fixed sequence 0–3、6–7、10；DEC-004「Use a manual Melee event whitelist」、DEC-006「Use three Melee event structures」 | [MELEE_ADMISSION](../../operations/MELEE_ADMISSION.md)「身份、资格和注册」「候选与审阅」「周维护补充与交付」；[PROJECT_SCOPE](../../PROJECT_SCOPE.md) §§4–8；[STATISTICS_SPEC](../../STATISTICS_SPEC.md) §§4–6。原 §Authorization matrix 和步骤 4／8／9 的技术重复审批删除 |
| DEC-011「Use theoretical rounds for average-point metrics」、DEC-012／013／014／015、DEC-047「Store mixed-event Constructed opportunities as a deterministic ledger」 | [STATISTICS_SPEC](../../STATISTICS_SPEC.md) §§3.3–3.6、6、7、11；[DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §§11.8–11.10。保留 ID／bye／drop／lock、机会账本、镜像与原始 W-L-D 含义 |
| DEC-078「Defer draw-adjusted metric retirement to Phase 19」、DEC-079「Version the 434455 compatibility closure for Selesnya Eldrazi Ramp」；DATA_ARCHITECTURE §11.12 | [STATISTICS_SPEC](../../STATISTICS_SPEC.md) §§10.0–10.0.1；[DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §11.12；[ROADMAP](../../ROADMAP.md) Phase 19。保留字段版本与原始输入／选中事件兼容边界；分类配置、434455 manifest 仍为原文件，不重跑历史样本 |
| DEC-137「Admit licensed names and Owner-authorized MTGCH community images」、DEC-147「Retain public Melee participant source IDs directly」 | [DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §25.5 的 Simple card localization boundary、§§11.13–11.15；NOTICE。保留许可、原图字节与直接源 ID 的公开 Git／Pages 差异，不恢复 HMAC 阶段授权 |
| LANDING_EDITORIAL_PIPELINE §Approved target state／Steady weekly operating contract after cutover／Workbook ownership contract；DEC-163／164 的完整周审与已审数据边界 | [DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §§25.2–25.5、26；[STATISTICS_SPEC](../../STATISTICS_SPEC.md) §§24–25；[WEEKLY_MAINTENANCE](../../WEEKLY_MAINTENANCE.md)「完整分类审阅」「数据、Landing 和完成是三个不同结果」。原 Ordered migration program 删除，业务验收结果不合并为一个状态 |
| OPERATIONS_RUNBOOK §First response／MTGO production／Pages／Correction and removal requests；DEC-031「Use one scheduled MTGO production update workflow」 | [DELIVERY](../../DELIVERY.md)「环境与候选」「发布与实际事实」「从失败处续作与取消」及恢复三节；[WEEKLY_MAINTENANCE](../../WEEKLY_MAINTENANCE.md)「输入和范围」；[DATA_ARCHITECTURE](../../DATA_ARCHITECTURE.md) §§11.14–11.16。恢复触发按下述最新 Owner 决定替换旧策略 |

| 待替换对象 | 有效内容的去处 | 状态 |
| --- | --- | --- |
| AGENTS / CLAUDE / Copilot / DEVELOPMENT_WORKFLOW | GOVERNANCE、QUALITY、DELIVERY；真实命令进入运行入口 | 已合并替换；原项目检出同步并实际重新读取新入口，旧工作流文档已删除 |
| DECISIONS 中产品、统计、分类决定 | 上表所列主题及原业务配置；按标题和原基线定位，不只按重复 DEC 编号 | 业务主题去处已核对，旧混合文档已按 Owner 明确授权删除 |
| MELEE_EVENT_ADMISSION_RUNBOOK | operations/MELEE_ADMISSION 的赛事资格和业务输入 | 新业务入口存在，旧分阶段授权文档已删除 |
| ROADMAP、STATISTICS_SPEC、PROJECT_SCOPE、FRONTEND_DESIGN_SYSTEM、DATA_ARCHITECTURE 的流程段落 | 上表定位的实际业务条款，以及 GOVERNANCE／QUALITY／DELIVERY | 初轮清理不完整；本次逐段补清固定回归、全档案审计前置和旧阶段授权，按实际输入／对象保留结果及兼容约束，不靠一句优先级声明覆盖旧正文 |
| TEST_TRIGGER_MATRIX / GOVERNANCE_REMEDIATION / 纯治理历史 | 合格风险进入 QUALITY 和相应执行实现；旧文本删除 | 对应纯治理文件已删除；当前引用/执行入口无这些旧要求，独立业务历史不作为现行操作依据 |
| ci_master_admission / validate_repository / publication_preflight 及调用 | 有限检查与交付入口 | 三个旧入口及配套 CI/modes/预检测试已删除；实际工作流已不调用 |
| ci / pages / update / fetch_melee | 同一版本的有限检查和候选交付机制 | 已随 PR #394 正式生效，有限检查和正式归档原包部署取得实际结果；prepare-pages 负责固定候选。复用隔离验证，不为切换再次生成产品 |
| 项目外默认指令及专用 skills / 记忆 | 有限定位项目来源；确需用户操作的最小更改单独说明 | 项目来源核查、新入口实际读取及记忆更新请求核对已完成；旧会话摘要与宿主重新生成的边界见 U7 结果，不冒称旧摘要已被物理删除 |

## 最新设计、准备差异与已有验证的定位

- **最新已批准恢复设计**：[Owner 恢复决定](RECOVERY_AUTOMATION_DECISION.md)「已确认的决定」；[Step 6 v1.2](GOVERNANCE_REBUILD_STEP_6.md) §§5–6；[Step 7 v1.3](GOVERNANCE_REBUILD_STEP_7.md)。日常执行入口为 [DELIVERY](../../DELIVERY.md)「Owner 决定回滚，工具执行恢复」「回滚附带暂停自动发布」「恢复执行与未确认状态」。Step 文档的早期“当前授权”是设计阶段记录，实际整体实施授权及本次 U6 等待状态见当前指令和本文件；不恢复机器判断回滚或修好即自动解除的旧提议。
- **实施差异**：[PR #394](https://github.com/Jacelber/mtgo-data/pull/394) 包含已验收的规则、实现和删除；`git diff 2e299cab25403e580c2677b4ac4c2a509104c080..7adff02f8f92a2a3d7fb9a113e24494ec919909b --` 可查看完整首次切换差异，新增文件亦已入 Git。本轮 Windows 修复与真实收尾记录在后续同范围提交中；原项目 `D:/dl/crawlerpj` 同步最终云端，外部 `*-prepared.yml` 仅是早期快照。
- **恢复实现及聚焦案例**：[state.py](../../../tools/delivery/state.py)、[platform.py](../../../tools/delivery/platform.py)、[commands.py](../../../tools/delivery/commands.py)、[pages_writer.py](../../../tools/pages_writer.py)、[pages.yml](../../../.github/workflows/pages.yml)；[test_state.py](../../../tests/delivery/test_state.py)、[test_platform.py](../../../tests/delivery/test_platform.py)、[test_commands.py](../../../tests/delivery/test_commands.py)。源文件说明案例，是否执行过以本文件已记录结果及相应运行事实为准。
- **归档／恢复已执行结果**：[归档上传取回 34667947270](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34667947270)、[加密候选交接 34670854494](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34670854494)、[Owner 指令恢复 34673213234](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34673213234)、[暂停自动写入 34673256390](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34673256390)、[明确解除 34673374190](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34673374190)、[解除后自动写入 34673433902](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34673433902)。这些是独立目标的分支验证，不冒称产品生产已切换。
- **后续组合及补充分支**：上述准备事实中的 MTGO delta、整站来源、终止写入／服务未知、checkpoint、检查运行状态对应 [tests/delivery](../../../tests/delivery)，周审交接对应 [34675532942](https://github.com/Jacelber/mtgo-data-governance-verification/actions/runs/34675532942)。策略云端案例位于验证仓库提交 `0b4fe437bd496d50abedcffdb1ee83b50a1bf108`；后续周审上传代码为 `21d467c10d7e7996080cc28acdea5242302d1f58`。不能将任一旧运行概括为当前全部准备代码的一次全量验证。
- **本地现有材料**：外部 `C:/Users/jacel/.codex/visualizations/2026/09/09/01a0863b-5be8-78c0-80d4-8380af644131/implementation/` 中，`baseline-candidate/manifest.json` 与 `baseline-retrieved/` 定位原包，`seed_product_baseline.py` 为已有只读基线核对入口（`--execute` 留待 U7），`check_final_wiring.py`／`check_changed_workflow_scripts.py` 为已用组合和语法核对。`checks.json` 只含早期有限执行结果，不能当作最新完整证明；其余后补本地案例的结果沿用本文件与本任务执行记录，不为补台账重新运行。

## 资源范围

- 主产品仓库 `Jacelber/mtgo-data`：新规则已统一合并，正式原包发布及入口确认完成。
- 私有 `Jacelber/mtgo-data-releases`：候选、完整恢复包、`state/pages.json` 及独立的必要周审业务材料；周审材料不进入 Pages／恢复包，不用于保存全部任务证据。
- `Jacelber/mtgo-data-governance-verification`：只留已批准公开源码及历史运行记录；临时 Pages、Actions 运行能力、凭据环境、合成 Release 和控制状态已清理，不含真实私有数据。
- 不使用额外服务，不配置新的周期任务，不新增付费方案。

## 后续安排

### 2026-09-12：已结束写入的续作修正

审核发现 `settle-completed` 保留 `health=unknown`、清除 `pending` 后，两个续作入口会提前返回。
本次局部修正让 `project.py resume` 与部署器共享确认路径：只有已通过对象复用
`already_confirmed`；未知对象仅续查原请求及既有服务，确认后按原状态版本保存；
已知产品失败保持失败。未知／未确认返回非成功退出码，不重发部署、不生成产品或自动回滚。
只有对应恢复确认成功才结束其恢复意图，自动发布暂停保持原决定。

本地聚焦串联验证覆盖两入口的未知→确认→复用、已知失败、平台终止失败、并发状态冲突、
其它写入冲突及恢复暂停保留；使用合成小包和替代的远端响应，不冒称真实故障演练。
相关验证身份同时纳入这条串联路径使用的命令入口；其余分类、统计、归档上传和恢复验证复用，
不重新运行。此修正不否定 U7 已取得的成功确认，也不改变当前线上产品。

U7 实际运行与外部入口情况见首节，不再等待 U6 或第二次发布审批。收尾修复在同一交付中合并、同步后结束实施。
之后获准的真实任务按 Step 8 利用现成资料完成一次初始效果总结；不为补样本制造任务，不承诺精确提速。
新产品目标（包括 P14 图片／颜色修复）需要其自身明确范围；本次实施不取得永久改造或自动回滚权。
