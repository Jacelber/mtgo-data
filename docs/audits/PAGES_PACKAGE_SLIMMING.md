# Pages 发布包瘦身：本地交付报告

2026-11-11。按 Owner 的任务合同完成本地实现与验证；随后 Owner 授权提交远端并建立 PR 供审阅。
分支 `codex/pages-package-slimming`，基线提交
`4fb30c822447873693841e3a9c1ea1f4ad34ecf7`。以下测量和验证针对提交前的本地候选。
`push.default=nothing`。原有未跟踪的 `build/`、`src/mtgo_data.egg-info/` 保留。
本次续作停点为 PR 待审阅，不包含合并、上传归档、发布或线上回滚；没有接入新赛事。

## 实现与保护替代

- Pages 配置升级到 `1.4.0`，只选入口、assets、melee 和原有公开准入规则下的 stats；
  排除 data、data_raw、reports、fetched.txt。历史周报、Top 8、Pickup、历史赛事及私有排除规则不变。
- 最终包上限统一为 **1,000,000,000 字节**；站点测量预留最终版本标识的 87 字节。
  配置不能提高工具上限，较低的自定义上限仍有效。
- 新 `melee/integrity.py` 复用版本化快照、Schema、parser、assembler 和统计输入校验。
  按每个已纳入赛事的 provenance 检查来源文件集合、大小、哈希、赛事与选手／轮次／比赛身份；
  来源与 Pages 文件集合分离。现有来源格式不迁移、不重新采集。
- 分类闭包验证当前分类主体、分类／机会账本输入、比赛关联、公开文件身份、目录路由及描述符。
  来源损坏为 `INVALID`；过期、缺失或损坏的可重建派生物为 `STALE_REGENERABLE`。
  正常分类更新不冻结派生输出，不引入所有赛事的永久历史答案。
- 候选材料、资源准备与内容组合继续绑定来源、分类、机会账本和诊断报告。
  MTGO metadata 中的报告哈希是构建绑定，不是浏览器下载地址；报告退出网站后仍保留这些输入。
- 新虚构赛事 900001／900002 只有四名选手，从手写源响应调用真实解析、规范化、分类、账本和统计代码。
  预期来自人工计数；覆盖 Draft 排除、不同构筑轮数、Limited／同构筑淘汰赛、三个统计范围、
  W/L/D、约和、bye、退赛、提前锁定、DQ、缺牌表／Unknown／无有效比赛、父子分类守恒。
  复用原有合成多赛事测试，核对先合并 W/L/D 再计算胜率，明确拒绝直接平均赛事胜率。
- 通过故障注入证明 Draft 误纳入、锁定误作 bye、DQ 漏排除会被发现。
  来源破坏、身份错配、分类与派生链错误被拒绝；合法新增目录赛事、分类更新和来源不随 Pages 发布均通过。
- 移除 434455 专属 manifest、reference ZIP 及其兼容测试的现行作用，删除当前测试树中的旧文件；Git 历史保留。
  434455 本身的来源、配置、业务状态、公开页面和统计文件未改。
  候选测量工具的内部证据改为通用 publication 验证（证据版本 `1.1.0`）；正式完整包仍用原 `schema: 1`。
- 更新 DATA_ARCHITECTURE、PROJECT_SCOPE、STATISTICS_SPEC、ROADMAP、WEEKLY_MAINTENANCE 中过时的冻结与发布范围说明。
  没有修改统计公式、正式分类规则、前端代码或默认维护测试义务。

主要改动文件：`build_pages_artifact.py`、`configs/pages_publication.json`、
`src/mtgmeta/melee/integrity.py`、`src/mtgmeta/classifier_closure.py`、
`tools/build_pages_candidate_measurement.py`、`tools/compact_public_products.py`、
`tools/delivery/{packages,verification,resources,content}.py`，以及相应定向测试和上述规范。
完整工作区清单见任务证据目录的 `worktree.txt`。

## 重新测量的大小与产品对照

所有大小均为十进制字节，展开大小按普通文件内容累加。

| 对象 | 文件数 | 展开字节数 |
| --- | ---: | ---: |
| 当前线上完整包，实际下载并验证 | 18,080 | 991,744,528 |
| 当前仓库按旧选择规则，未叠加资源 | 17,892 | 979,651,055 |
| 当前仓库按旧规则，加同一已验证资源及版本标识的逐文件计量 | 18,096 | 994,054,361 |
| 新完整候选包，实际准备、验证、解包 | **1,011** | **242,362,449** |

同输入对照减少 **751,691,912 字节，75.62%**；相对当前线上包减少
**749,382,079 字节，75.56%**。最终有效上限余量 **757,637,551 字节**。
压缩归档 `product.tar.gz` 为 **47,308,851 字节**。

| 新包主要部分 | 文件数 | 字节数 | 占比 |
| --- | ---: | ---: | ---: |
| stats | 527 | 207,388,589 | 85.5696% |
| assets，含两个既有生成资源包 | 480 | 34,961,527 | 14.4253% |
| index.html | 1 | 6,718 | 0.0028% |
| melee/index.html | 1 | 5,528 | 0.0023% |
| .product-version.json | 1 | 87 | 0.000036% |
| .nojekyll | 1 | 0 | 0% |

新包中无 data、data_raw、reports、fetched.txt。
807 个保留业务文件共 227,959,143 字节，逐文件 SHA-256 与开发前基线及当前线上包一致。
202 个生成资源文件共 14,403,219 字节，复用当前线上包，并通过现有资源主体和闭包验证。
所有 17,895 个基线记录（包含来源与必要中间资料）均仍存在且哈希未变。
唯一新增内容标识为按新文件集合生成的 `.product-version.json`，不涉及产品数据重算。

242.36 MB 与历史约 243.8 MB 估算相差约 1.44 MB（约 0.59%）。这里使用当次实际文件清单，
没有把历史估算当验收值。当前旧规则计量较线上包多 2,309,833 字节：data 多 16 个文件、
2,309,085 字节，fetched 台账多 748 字节；这些差异原已存在，全部属于本次移出的目录，
没有任何保留业务文件差异。

## 验证及可重现命令

工作目录 `/workspace/mtgo-data`；任务证据目录 `/workspace/scratch/pages-slimming`。
所有生成和测试命令移除归档上传凭据；仅为取得当前完整包与恢复记录进行了只读远端访问。

主批次 174 个定向测试、6 个 subtests 通过；随后补充闭包合法变化／派生损坏测试和既有
多赛事计数测试，43 个通过。去除重叠后共 **193 个测试、6 个 subtests**。
不是全仓回归。首次集成失败涉及旧测试夹具和故障注入断言位置，修正后相关批次通过，
未通过修改产品统计或放松来源校验消除失败。

```bash
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/test_melee_independent_statistics.py tests/test_melee_source_integrity.py \
  tests/test_classifier_closure.py tests/test_pages_publication.py \
  tests/test_pages_candidate_measurement.py tests/test_melee_event_delivery.py \
  tests/test_landing_card_image_cache.py tests/test_archetype_visuals.py \
  tests/delivery/test_weekly_material.py tests/delivery/test_weekly_resources.py \
  tests/delivery/test_content_composition.py tests/delivery/test_packages.py \
  tests/test_melee_multi_event_contract.py tests/test_melee_source_identity.py
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/test_classifier_closure.py tests/test_melee_multi_event_matchup.py
```

新构建对现有 17 场公开 Melee 赛事执行通用来源及派生链检查（1 场 v2、16 场 v4），并验证
MTGO 产品绑定、公共目录引用、卡名和图片资源主体。变更 Python 文件的 Ruff 检查和
`git diff --check` 通过。

```bash
env -u MTGO_ARCHIVE_UPLOAD_TOKEN PYTHONPATH=src:. .venv/bin/python build_pages_artifact.py \
  --output /workspace/scratch/pages-slimming/candidate-site \
  --report /workspace/scratch/pages-slimming/build-report.json \
  --overlay landing_card_images=/workspace/scratch/pages-slimming/online/site/assets/card-cache/v1 \
  --overlay card_localization=/workspace/scratch/pages-slimming/online/site/assets/card-localization
```

沿原入口 `tools/project.py prepare --site .../candidate-site --output .../candidate
--source 4fb30c822447873693841e3a9c1ea1f4ad34ecf7+pages-package-slimming-local`，
再执行 `verify --candidate .../candidate` 和
`extract --candidate .../candidate --output .../extracted`，全部通过。
`source` 明确标识为该基线上的本地修改，并不声称候选来自已提交／已上线版本。
`compare.py` 对基线、仓库、解包站点和线上包进行逐文件检查，结果为 `comparison.json`。

浏览器从 **解包目录** 提供文件，不能访问仓库中退出发布的来源文件。
已有资源加载、分享链接和键盘用例 17 项通过；具体命令：

```bash
env -u MTGO_ARCHIVE_UPLOAD_TOKEN npx playwright test \
  --config /workspace/scratch/pages-slimming/playwright.config.cjs
env -u MTGO_ARCHIVE_UPLOAD_TOKEN node /workspace/scratch/pages-slimming/acceptance.cjs
```

补充浏览器共 24 个检查点、799 次请求，通过。测试使用 `/mtgo-data/` 部署前缀，覆盖：
五赛制统计及首次套牌展开、对阵；Standard／Modern 历史 W33 周报展开，各四张真实卡图解码；
Modern 历史 W30 Top 8 及详情；旧 `weekly-pickup` 链接转换；Standard／Pauper／Modern／Legacy
赛事页、434455 Day 2 和赛事切换、对阵及语言切换。移出路径请求为 0，本地 HTTP 错误为 0，
页面脚本异常为 0。详细路径、检查点及请求清单见 `browser-acceptance.json`。

环境限制与处理：系统 Chromium 不信任环境代理 CA，首次历史外部卡图检查超时；同一真实 URL
通过使用环境 CA、保留 TLS 校验的 Playwright HTTP 客户端返回 200 和真实 WebP 字节。
补充验收仅对 HTTPS 外部资源使用该客户端转送响应，再由浏览器解码；本地候选文件直接加载，
没有伪造响应、改写产品 URL 或修改站点代码。原生 Chromium 直连外部卡图的证书信任没有修复，
不报告为已验证。另一次验收脚本误用统计页详情选择器检查 Top 8，改用其真实关闭按钮后通过。
这些是测试环境／脚本调整，保留了失败记录，没有重建产品包。

## 候选、恢复和停点

本地完整候选：`/workspace/scratch/pages-slimming/candidate/`。
标识：`pages-cda0da698ae6332f0f15f6c29f6c9680b0d451c91fef1be01e43dd83587c6523`。
归档 SHA-256 即上述标识的哈希部分。原完整包 manifest、归档、版本标识与安全解包协议不变。

只读核实的当前线上版本：
`pages-30d236b2e1eb9293283d6c6c43624930d5065e5649351d797aef5d5d28735802`；
适用前版记录：
`pages-79f336fb99a740775cb6cdb0cd31d420d65a5e0b75f7b350e05e246b84ebb610`。
当前包已下载并验证；前版只核实归档及记录，没有下载解包或线上恢复演练。
没有变更现有归档、恢复记录、协调状态、发布工作流或线上版本。

未做全仓回归、每一历史页穷举、生产部署或生产恢复；这些不应报告为通过。
本次已获提交远端及建立 PR 的授权；后续合并／发布仍须另行授权，并核实最新远端与线上实际版本，
保留等待期间其它任务的产品更新；再按 DELIVERY 保存完整候选、登记准备、验证适用恢复前版并发布。
授权范围改变或输入发生变化时，只补受影响验证；发布失败也不自动授权回滚。
