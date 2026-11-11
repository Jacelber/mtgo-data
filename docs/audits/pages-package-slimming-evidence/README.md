# PR #531：验收证据补充

审阅对象为 `be9e648ba6802ff4a2673b2c3a7107cd92f78b8c`。本目录是在原工作区取回的证据副本，
不是根据交付报告重造的日志。本次没有重新运行原 193 项测试、浏览器验收或完整构建／解包。
新增工作仅为证据整理、文件摘要与提交绑定核对、raw v3 定向测试，以及只读恢复状态查询。
本次不合并、不部署、不上传发布归档、不回滚。

## 原件、提交与候选的对应关系

原件根目录：`/workspace/scratch/pages-slimming/`，仍在本地。
[原件索引](original-evidence-index.json)逐份记录原始绝对路径、取得时的修改时间、字节数、SHA-256、
副本路径及副本 SHA-256。除 `baseline.json` 无损压缩为 gzip 外，27 份副本均保持原始字节。
这些摘要是本次取得原件时计算的，不能冒充运行当时的签名证据；文件时间也不是独立时间戳证明。
原始失败日志中的尾随空格原样保留，因此不把原件目录纳入新增源码的空白检查；没有为通过格式检查修改证据。

| 证据 | 本目录中的原件副本 | 原运行所证明的内容 |
| --- | --- | --- |
| Python 主批次 | [final-tests.log](original/final-tests.log) | 174 passed，6 subtests；原命令见下文 |
| 后补闭包及多赛事批次 | [added-tests.log](original/added-tests.log) | 43 passed，与主批次有重叠 |
| 修复过程 | [integration-tests.log](original/integration-tests.log)、[repair-tests.log](original/repair-tests.log) | 保留原失败与修复后结果，不把失败记录删掉 |
| 现有浏览器用例 | [browser-tests.log](original/browser-tests.log)、[配置](original/playwright.config.cjs)、[last-run](original/browser-results/.last-run.json) | 17 项通过，服务根目录为候选解包站点 |
| 补充浏览器验收 | [browser-acceptance.json](original/browser-acceptance.json)、[stdout](original/browser-acceptance.log)、[实际脚本](original/acceptance.cjs) | 24 个检查点、799 次请求及完整 URL 清单 |
| 浏览器截图 | [Landing](original/landing.png)、[Tabletop](original/tabletop.png) | 当时的页面画面，不代替操作断言 |
| 最后一次失败尝试 | [失败结果](original/browser-acceptance-failure.json)、[失败截图](original/browser-failure.png) | Top 8 详情误用选择器的脚本错误；不是证书错误的原始记录 |
| 业务／来源比较 | [comparison.json](original/comparison.json)、[stdout](original/compare.log)、[脚本](original/compare.py)、[原始基线 gzip](original/baseline.json.gz) | 807 个保留业务文件与基线及线上包一致；17,895 个基线记录未损坏／丢失；资源复用和目录排除 |
| 构建计量 | [build-report.json](original/build-report.json)、[build.log](original/build.log) | 构建 PASS，含资源后的字节数、文件数、输入绑定数量 |
| 完整候选 | [manifest](original/candidate/manifest.json)、[prepare](original/prepare.json)、[verify](original/verify.json)、[extract](original/extract.json) | 原完整包准备、验证与安全解包结果 |
| 原实现清单 | [implementation-files.json](original/implementation-files.json)、[工作区](original/worktree.txt)、[lint](original/lint.log) | 当时变更文件摘要及原 Ruff 结果 |

所有原运行都发生在提交前的工作树，基线是
`4fb30c822447873693841e3a9c1ea1f4ad34ecf7` 加本地瘦身实现。
候选 manifest 的 `source` **原样保留**为
`4fb30c822447873693841e3a9c1ea1f4ad34ecf7+pages-package-slimming-local`，不改成后来出现的提交号。
原测试日志没有嵌入 Git SHA，也没有主批次逐测试 JUnit；不能将它们表述为在干净的 be9e648 checkout 上重跑过。

[本次提交绑定核对](binding-check.json)使用 `git show be9e648:<path>` 对照原实现摘要：
30 条记录中 29 条吻合（含删除），唯一差异是 `docs/audits/PAGES_PACKAGE_SLIMMING.md`，
其在建立 PR 时更新了授权与停点说明。生产实现和测试文件吻合。
主批次与后补批次的时间不同；后补闭包测试覆盖了新增的三项用例。按当时命令集合去重为
193 项加 6 个 subtests，**不是 174+43 个互不重复测试**。原日志仅保留批次摘要，命令来自同一任务执行记录：

```bash
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/test_melee_independent_statistics.py tests/test_melee_source_integrity.py \
  tests/test_classifier_closure.py tests/test_pages_publication.py \
  tests/test_pages_candidate_measurement.py tests/test_melee_event_delivery.py \
  tests/test_landing_card_image_cache.py tests/test_archetype_visuals.py \
  tests/delivery/test_weekly_material.py tests/delivery/test_weekly_resources.py \
  tests/delivery/test_content_composition.py tests/delivery/test_packages.py \
  tests/test_melee_multi_event_contract.py tests/test_melee_source_identity.py \
  --basetemp=/tmp/mtgo-slim-final
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/test_classifier_closure.py tests/test_melee_multi_event_matchup.py \
  --basetemp=/tmp/mtgo-slim-added
```

完整候选原文件：`/workspace/scratch/pages-slimming/candidate/product.tar.gz`，本次实际读取并重算摘要，
与原 manifest 相符：

- SHA-256：`cda0da698ae6332f0f15f6c29f6c9680b0d451c91fef1be01e43dd83587c6523`。
- 压缩文件大小：**47,308,851 字节**。
- 原 prepare／verify／comparison 中的展开大小：**242,362,449 字节**，文件数 **1,011**。
- 包 ID：`pages-cda0da698ae6332f0f15f6c29f6c9680b0d451c91fef1be01e43dd83587c6523`。

本次重新核对的是压缩包实际大小、哈希及代码绑定；未重新展开、重建或重跑业务文件比较。
47 MB 完整包和线上包仍保留在本地，没有提交进 Git、上传 Release 或公开下载入口。
独立审阅者可以审查原比较清单与基线摘要；若要自行检查全部 tar 成员，仍需取得原完整包。

## raw v3：原覆盖与本次补证

be9e648 的 `test_raw_v4_direct_identity_and_historical_v3_identity_are_both_readable`
调用 `parse_raw_snapshot`，证明旧 v3 的 `hmac-sha256-event-v1`、`participant_ref` 与 `key_id`
可读，输入仅是一份合成 decklist 资源。该测试文件在原主批次命令中。
它没有调用新 `validate_retained_source`，不证明完整存档集合、标准化身份及来源链通过通用检查。

本次[只读格式盘点](supplement/review-findings.json)确认公开目录中的 17 场仍为 1 场 v2、16 场 v4；
此前真实赛事构建验证因此不构成 v3 针对性证据。没有真实历史 v3 赛事完整链验证记录。

补充 [test_melee_v3_integrity.py](../../../tests/test_melee_v3_integrity.py)：

- 独立虚构 900003 赛事，两名选手、一轮、一场胜负、两份 60 张 Island 牌表。
- 手写 v3 manifest 和五份 minimized v1 资源：赛事、积分榜、对局、两份牌表；
  使用两个固定的合法 `melee-v3-…` 引用及虚构 retired key ID。没有 HMAC 密钥、网络采集或历史来源重写。
- 调用真实解析、规范化和通用完整性检查；核对来源身份、实体数、完整文件集合及校验前后字节不变。
- 五个负例分别破坏身份方案、资源版本、牌表参与者上下文、文件大小及标准化参与者身份。
  每例匹配对应错误原因，不能因其它不相关 Schema 错误而假通过。

实际新增执行：6 项新测试加 1 项既有 v3／v4 解析测试，**7 passed，0.42 秒**。
[逐项日志](supplement/v3-tests.log)、[JUnit](supplement/v3-tests.xml)、
[命令／开始结束时间／基线提交／测试文件 SHA-256／退出码](supplement/v3-run.json)、[Ruff](supplement/lint.log)。
运行时为 be9e648 加新增测试文件，随后提交；没有更改生产代码、数据、规则或候选包。

```bash
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python -m pytest -v \
  tests/test_melee_v3_integrity.py \
  tests/test_melee_source_identity.py::test_raw_v4_direct_identity_and_historical_v3_identity_are_both_readable \
  --basetemp=/tmp/mtgo-v3-review-final \
  --junitxml=/workspace/scratch/pages-slimming-review/v3-tests.xml
```

新增夹具最初有 HTTP method、文件名和 request_id 与既有 Schema 不符的错误，已按规范修正；
没有放松生产校验。早期尝试日志留在本地 `v3-first-run.log` 至 `v3-fourth-run.log`。

## 浏览器证书问题与实际边界

原系统 Chromium 访问外部卡图出现 `net::ERR_CERT_AUTHORITY_INVALID`，属于当前测试环境对
出站代理 CA 的信任问题，**不是线上站点故障**。当时独立 HTTP 探针使用环境代理和 Node 的
`NODE_EXTRA_CA_CERTS`，对同一真实图片取得 `200 image/webp`，47,490 字节。
这两次探针输出只在本次聊天的工具记录中，**没有单独落盘的诊断日志**；不根据说明伪造一份原始日志。
第一次图片超时的结果文件被后续 Top 8 脚本失败覆盖，也未找回；当前保留的失败文件不能代替它。

最终 `acceptance.cjs` 用 `page.route('https://**/*')` 转送 HTTPS 请求，
由 Playwright HTTP 客户端经环境代理、保留 TLS 校验取得真实响应，再 `route.fulfill({response})` 交给浏览器。
拦截模式覆盖所有 HTTPS，而非仅文件后缀为图片的地址；本次记录实际只有 8 次外部请求，
host 均为 `images.mtgch.com`，另 791 次为解包站点的 localhost 请求。
本地 HTML、JS、CSS、JSON 与包内图片不经过该转送，也没有用假图替换真实内容。

明确验证过的图片条件是 Standard 和 Modern 的 W33 历史周报中，**各第一个 Feature 的 4 张图片**，
滚动到可见位置后断言 `complete && naturalWidth > 0`。不把请求数量当作每个外部 URL 的解码证据。
其余检查证明了指定页面和交互可用；`localFailures=[]` 仅统计本地 HTTP 状态码 ≥400，
没有完整外部 HTTP 错误／requestfailed 清单、HAR 或所有图片的逐张解码断言。
因此不声称所有外部卡图、全部历史页、全部设备或 Chromium 原生外部 TLS 路径已验证。
现有 17 项浏览器用例用的是原配置，没有上述 HTTPS 转送；通过结果不能用来替代外部卡图证书验证。

## 恢复前版及剩余事项

[只读恢复状态记录](supplement/recovery-observation.json)来自本次 GitHub 查询（2026-11-11 05:11 UTC），
保留来源路径和 Git blob SHA，只投影当前、前版和这两个包的资格字段，没有修改控制状态。

- 当前 A：`pages-30d236b2e1eb9293283d6c6c43624930d5065e5649351d797aef5d5d28735802`，
  operation `weekly-645cbee9819343fdad2ff7a5e321a115`，health passed、platform succeed、complete／eligible 为 true。
- 当前状态中 previous Z：`pages-79f336fb99a740775cb6cdb0cd31d420d65a5e0b75f7b350e05e246b84ebb610`，
  health passed、complete／eligible 为 true。pending 和 recovery 均为空。

若瘦身包 B 在 A 仍为实际健康线上版本时发布，**本次发布需要核实的直接恢复前版是 A**，
不能机械地把当前状态里的 previous Z 当成 B 的恢复目标。Z 是当前 A 的前版记录，仍按保留政策保护。
正式发布前须重新确认当时实际操作／线上标识、包资格和可取用性、无未完成写入，以及候选是否包含
等待期间已交付的其它更新；若实际线上已变，应以届时适用前版为准。

当前 A 的原完整包此前已取回并验证，仍在本地；Z 仅核实记录／归档定位，未下载解包。
本次没有再下载恢复包、核对线上实际标识或进行线上浏览器健康检查，状态查询不替代这些发布前事实核对。
完整候选尚未归档／登记发布准备；没有生产发布、恢复演练、全仓回归、真实 v3 全赛事验证、
全部历史页面或原生外部 TLS 验收。等待 Owner 决定是否合并与发布，失败也不自动授权回滚。
