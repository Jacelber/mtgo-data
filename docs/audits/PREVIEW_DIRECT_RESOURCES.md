# MTGO 入口直接资源绑定：开发验收说明

基线：master 8d3846b970c49cdb37bf1eba2182e64008c389d7（#438 已合并）。
本次为 Owner 授权的独立 P2 优化；创建 PR 后待验收，不合并、不发布。

## 问题与结果

原 preview_packet 扫描全部 phase8 JS（除 archetype-visuals.js）及 phase8 CSS，
把 MTGO 根页不加载的 app-tabletop.js 和 tabletop-controller.js 也绑定到最终预览。
新选择器只读取 index.html 的直接 script src 与 stylesheet href。当前实际集合为
15 个整文件绑定 JS、2 个 CSS 和 index.html；另一个实际加载的 archetype-visuals.js
继续使用已有视觉语义及选中图片绑定。

新材料标记 entry-direct-v1。旧证据仅在同周同赛制、入口摘要未变、当前直接资源
在旧证据中全部存在且摘要一致时允许排除旧多收项。资源映射在 dimensions 和 bindings
中必须一致，未知方法/缺证据不自动兼容。其余材料与绑定继续按原入口合同校验。

preview_validity 同时服务普通决定/续作、归档完成、completion 当前页面核对、
supplement 的生成、已存沿用事实校验及当前预览验证。原决定、日期、提交快照与
原包确认不改写。没有修改 HTML、JS、CSS、图片、W38 内容或历史记录。

## 有限自动验证

97 个测试通过（7.13 秒），git diff --check 通过。

- tests/test_preview_resources.py：实际入口资源选择；外部/缺失/越界/歧义路径拒绝；
  两个 Tabletop 文件变化不影响 MTGO；实际 JS/CSS/HTML 变化仍发现；严格旧集合兼容；
  当前颜色、图片、内容、其他绑定变化不被兼容吞掉；未知/不一致方法证据拒绝；
  续用决定仍引用原快照，跨周不自动复用。测试不冻结允许的脚本总数。
- tests/test_landing_bundle.py：实际 preview 生成器保持其他赛制视觉不影响当前赛制，
  当前选中颜色与图片字节变化仍被发现；原包完成校验及既有组合情境继续通过。
- tests/test_weekly_classification_review.py::test_legacy_preview_continues_through_resume_archive_and_supplement：
  使用真实 review、preview、归档包和完成入口；旧超集快照经 resume、普通 completion、
  supplement retained 分支、历史覆盖与 readiness 成功继续，旧决定/日期不变；
  真正加载脚本改变时仍拒绝沿用。
- 复核 tests/test_review_submission.py、tests/test_weekly_validity.py，以及既有补充完成
  CLI 连续追加、发布/接纳拒绝、无效事实、变化页面验收与追加顺序情境。

相关临时页面 fixture 改为明确声明自身 renderer，符合真实入口形态；未修改生产入口。
没有运行全仓测试、生产分类全量或增加长期浏览器 Gate。

## 一次性实际页面加载证据

2026-09-23 02:22（本机时间），用 Codex 浏览器访问本地工作树根页，临时服务仅绑定
127.0.0.1:8783。页面实际进入 Modern W38 Landing，正文及环境表可读取。
浏览器 DOM 声明 16 个 script 和 2 个 stylesheet；HTTP 请求日志确认以下文件均 200：

- JS：runtime、i18n、card-localization、archetype-names、matchup-model、mtgo-controller、
  archetype-visuals、app-core、app-freshness、app-mtgo、app-mobile-render、
  app-mobile-interactions、app-loading、app-card-preview、app-metadata、app。
- CSS：phase8-base、phase8-candidate。

两个 Tabletop 专用脚本均不在 DOM，也没有请求；新选择器收录所有整文件保护项，
archetype-visuals 按上述语义例外处理。浏览器临时标签和本机服务已结束。

限制：直接运行源码工作树缺少发布时生成的 assets/card-localization/cards.json 和
assets/card-cache/v1/manifest.json，观察到这两项 404。因此这份证据只证明实际入口
renderer 加载与选择范围，没有把它表述为完整线上页面/发布验收，也没有为此生成缓存。

## Owner 验收对象与范围

确认已证实的 Tabletop-only 误判消除；真实资源/视觉变化仍受保护；旧证据仅在充分
条件下继续，并覆盖普通与 supplement 收尾。保留共享脚本整文件绑定带来的保守判断。
不拆 JS 内部分支，不建立依赖图，不扩展 favicon/水印或图片体系，不改历史 packet。
下一步由 Owner/云端 chatbot 核对本 PR，验收后再按指令完成技术收尾。
