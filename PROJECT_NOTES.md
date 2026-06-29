# MTG 数据分析系统 — 项目笔记

最后更新：2026-06-29

## 一、项目总目标
搭建一个自动化系统，爬取 MTGO 官方赛事数据（以及未来的 melee.gg 实体赛数据），
对牌表自动分类，统计各套牌类型的胜率、瑞士轮表现、八强占比等，最终以网页形式
展示给其他用户查看。操作者无编程基础，全程在 AI 协助下用 Python 实现，工具尽量
免费。

## 二、系统四大模块及状态
1. 数据抓取（MTGO）—— ✅ 已完成并实现云端自动化
2. 牌表分类 —— 🔨 进行中（已转向 j6e 数量规则体系，正在补规则提高覆盖率）
3. 数据统计（胜率/八强占比等）—— ⬜ 未开始
4. 网页展示 —— ⬜ 未开始
（melee.gg 抓取因有 Cloudflare + 登录，暂缓，第一阶段只做 MTGO）

---

## 三、模块一：数据抓取（已完成）

### 关键技术发现
- MTGO 赛事页面的数据藏在 HTML 里的 JS 对象 `window.MTGO.decklists.data`。
- 用括号配对法（数花括号深度，跳过字符串内的括号）精确截取该段 JSON，比
  简单找 `};` 稳健。
- 赛事列表页按月份分页，URL 格式为：
  `https://www.mtgo.com/decklists/<年>/<两位数月份>`
  例：https://www.mtgo.com/decklists/2026/05
- 注意：当月页面和历史归档月份页面，赛事链接都是静态写在 HTML 里的
  （在页面靠后位置，约 20000 字节之后），requests 能正常提取。之前怀疑
  历史页是 JS 动态加载，经核实是误判——真正原因是网络下载偶发残缺。
- MTGO 有时返回状态码 200 但页面残缺（内容不完整或缺字段），需要把
  "下载+解析+完整性检查"作为整体重试。
- 只抓竞技赛事（challenge/qualifier/showcase 等），排除含 "league" 的链接。
- 用 inplayoffs == 1 字段筛掉没有八强单淘的赛事（如 preliminary）。
- premodern 不能用模糊包含判断，否则会被误判成 modern；改为取链接首段词精确匹配。

### 数据字段结构（每个赛事 JSON）
- 赛事层：event_id, description, format, starttime, player_count, players[]
- 每位牌手（players[] 里）：
  player（牌手名）, loginid（唯一ID）, swiss_rank, swiss_score,
  swiss_wins（score//3）, opp_match_win_pct, game_win_pct, final_rank,
  main_deck[], sideboard[]
- 每张卡：{ "name": 英文卡名, "qty": 数量 }
- 三张表（standings / final_rank / decklists）都靠 loginid 串联。
- 注意：MTGO 只公布部分牌手牌表（如 92 人赛事只有 32 份牌表），属正常。

### 脚本清单（都在 D:\dl\crawlerpj）
- fetch_mtgo.py —— 抓单个赛事（最早写的，验证用）
- batch_mtgo.py —— 主力批量抓取脚本
- recon.py / recon_list.py —— 早期侦察脚本（已完成使命）
- classify_standard.py —— 分类脚本（模块二，已重写为 j6e 体系）

### batch_mtgo.py 当前配置与健壮性
- 默认抓"最近两个月"（当月+上月），跨年自动处理（1月→上年12月）。
- 数据存到 data/<格式>/<赛事描述>_<event_id>.json
- fetched.txt 记录已抓链接，自动去重跳过。
- 支持的格式：standard, legacy, pioneer, pauper, vintage, modern
- 健壮性机制（经多轮打磨）：
  * download() 函数：最多重试 5 次，timeout=90 秒，失败间隔等待。
  * 整体重试：下载+解析作为一体，最多 4 轮，每轮间隔 15 秒。
  * is_data_complete() 函数：检查解析出的数据是否含关键字段
    （event_id, description, player_count, decklists 且 decklists 非空），
    残缺数据视为失败、触发重试，而不是崩溃。
  * build_clean_data() 内部用 .get() 安全取值（format, starttime 等），
    即使意外缺字段也不崩溃（双保险）。
  * 失败的赛事不记入 fetched.txt，下次运行自动重试（自愈）。

### 已抓数据现状
- 约 345+ 个赛事 JSON，覆盖六个格式，2026 年 5 月和 6 月。
- 数据已 git commit + push 到云端仓库。

### 自动化（已打通并验证稳定）
- GitHub 仓库：https://github.com/Jacelber/mtgo-data
- GitHub 账号用户名：Jacelber（也写作 jacelber）
- GitHub Actions 配置文件：.github/workflows/scrape.yml
- 定时：每天 UTC 04:00 = 北京时间中午 12:00 运行（cron: '0 4 * * *'）
- 已修复的关键问题：
  * 403 推送被拒：Actions 默认无写权限。已在仓库 Settings → Actions →
    General → Workflow permissions 改为 "Read and write permissions"，
    确认 workflow 变绿。
  * push 撞车（rejected, fetch first）：多次运行时间接近会撞车。已在
    workflow 的推送步骤改为 commit 后先 `git pull --rebase` 再 push，
    并在无新数据时正常退出（exit 0）。已验证有效。
- 注意：GitHub 定时任务（schedule）经常延迟几分钟到几十分钟，整点
  （如 UTC 04:00）尤其容易被排队/跳过，属正常现象，不代表配置失败。
  判断是否正常应看"接近该时间的运行记录"，并连续观察一两天。
- 注意：公开仓库若连续 60 天无活动，GitHub 会暂停定时 workflow（会发邮件
  提示，需手动重新启用）。本项目每天有自动提交，暂不会触发。
- "Node.js 20 is deprecated" 是黄色警告，可忽略，不影响运行。

### Git / 仓库注意事项
- 本地 Git 已配置：user.name=jacelber, user.email=jacelber@gmail.com
- .gitignore 已忽略：page_source.html, list_page.html, __pycache__/,
  根目录的 /*.json（但 data/ 下的 json 要保留，用 /*.json 只忽略根层）,
  以及 MTGOFormatData/（Badaro 的规则库，不纳入自己仓库）
- 日常更新代码流程：先 git pull（同步云端自动抓的数据，重要！）→
  本地编辑测试 → git add . → git commit -m "说明" → git push
- 因为云端每天自动提交数据，本地开工前必须先 git pull，否则 push 会被拒。
- 主要在本地 VS Code 改代码，网页编辑只用于极小确定的改动。

### 存储与费用
- 公开仓库 + Actions 完全免费、不限分钟数。
- 仓库建议 ≤1GB，单文件 ≤100MB。当前数据约几 MiB，每年增长几十 MB，远低于上限。
- 只要账号和公开仓库存在，数据长期保存。

---

## 四、模块二：牌表分类（进行中 —— 已转向 j6e 数量规则体系）

### 重大决策：放弃 Badaro，全面转向 j6e 格式
- 初期用了 Badaro 的 MTGOFormatData 规则库（基于"含/不含"逻辑，JSON 格式），
  跑出 96% 分类率，但其中很大比例是 fallback 兜底"硬塞"进 Control/Midrange/
  Aggro 大类的粗糙结果，对精细胜率统计价值有限。
- 关键局限：Badaro 体系原生不支持"数量"条件（只能判断含不含某卡），
  而 MTG 中"满编 4 张的关键卡"往往才是定义套牌的核心，且后续"特殊度/基准
  张数"分析也依赖数量。因此 Badaro 体系不够用。
- 已决定全面转向 j6e（https://j6e.me/mtg-meta-analyzer/）的规则格式，
  它原生支持数量条件，更契合需求。Badaro 规则库（MTGOFormatData 文件夹）
  保留在本地仅作参考，分类已不再使用它。

### j6e 规则格式（YAML，存于 my_archetypes/standard.yaml）
- 顶层有 format、date、archetypes 列表。
- 每个 archetype 有 name 和 signatureCards 列表。
- 每张签名卡可指定：
  * minCopies: N —— 该卡至少 N 张
  * exactCopies: N —— 该卡恰好 N 张（常用 exactCopies: 0 表示"不能有这张卡"）
  * 都不写 —— 默认"有就行"（>=1）
- 一个套牌的所有 signatureCards 条件都满足才算匹配。
- 经典技巧：多个套牌用同一核心卡，靠"地的数量"区分颜色分支
  （如 Landfall 系列用 Stomping Ground/Temple Garden 的 minCopies/exactCopies
  区分 Gruul/Selesnya/Mono-Green）；用 Mountain minCopies:12 / Swamp
  minCopies:10 锁定单色。

### 我们对 j6e 格式做的扩展：zone 字段
- 需求：j6e 原版不区分主牌/备牌（按主备合计计数）。现阶段合计是合理的
  （主备交换不改变套牌本质），但为未来可能需要严格区分位置的情况预留能力。
- 扩展方案：给签名卡增加可选的 zone 字段：
  * 不写 zone 或 zone: any —— 主备合计（默认，完全兼容 j6e 原版规则）
  * zone: main —— 只数主牌
  * zone: side —— 只数备牌
- 设计原则：简单情况简单写（绝大多数规则不写 zone），需要时才加。

### classify_standard.py 当前能力（已重写）
- 需要 yaml 库（pip install pyyaml）。本地已装在全局环境（未用虚拟环境，
  保持简单）。注意：将来分类若要上云端 GitHub Actions，scrape.yml 里的
  `pip install requests` 要改成 `pip install requests pyyaml`。
- 读取 my_archetypes/standard.yaml 规则。
- 把每副牌处理成"卡名 -> 主牌张数"和"卡名 -> 备牌张数"两个字典（保留数量）。
- 匹配逻辑支持 minCopies / exactCopies / zone。
- 规则按 YAML 中的先后顺序匹配，匹配到第一个就停（顺序会影响结果，
  越具体/越优先的套牌应放越前面）。
- 已去掉 fallback 机制（按决定），未匹配的老实标 Unknown。
- 输出分类报告 + 把 Unknown 牌表（带张数）导出到 unknown_decks.txt。

### 最新分类结果（2208 副牌，2026年5-6月 standard，纯 j6e 规则）
- 加载了 40 条 j6e 规则。
- 精确分类率 46.0%（1015/2208），Unknown 1193 副（54.0%）。
- 主要识别出：Izzet Lessons 8.7%、Izzet Spellementals 7.2%、Izzet Prowess
  5.8%、Mono-Green Landfall 4.6%、Jeskai Control 4.6%、Momo-White 4.2%、
  Rakdos Discard 2.9% 等。
- 重要理解：46% 看似比之前 Badaro 的 96% 低，但这是"真实的精确分类率"。
  之前 96% 含大量 fallback 兜底的粗糙结果。现在 54% Unknown 不是"分错"，
  而是"还没写规则覆盖"——是真实暴露出来的待补缺口，反而更有意义。

### 写规则的核心经验教训
1. 选"标志卡/签名卡"要选这个套牌【定义性的功能组件】，不要选"恰好流行
   但非必需"的卡，否则会漏掉不带那张卡的变体。
   （教训实例：最初给 Izzet Aggro 选了 Tokka 当必需卡，但很多 Izzet Aggro
   不带 Tokka、或只放备牌，导致漏分。用户指出应选 Spirebluff Canal 定颜色
   + Scalding Viper / Razorkin Needlehead 等核心 pinger。）
2. 数量很关键：满编 4 张的关键卡才能定义套牌，零星 1 张可能只是过渡牌。
   这是放弃 Badaro、转向 j6e 数量体系的根本原因。
3. archetype 的显示名（name）和文件名是两回事；Badaro 里搜 name 字段定位文件。

## 五、下次继续的待办（DOWN TO HERE）
当前分类率 46%，Unknown 1193 副。下一步是看 unknown_decks.txt 里成堆的
套牌，逐步补 j6e 规则把分类率提上去。具体：
1. 打开 unknown_decks.txt（已带张数），找出反复出现的同类套牌。
2. 为每类未覆盖的套牌，按 j6e 格式在 my_archetypes/standard.yaml 里新增规则，
   选定义性签名卡 + 合理的 minCopies 阈值。
3. 每加一批规则就重跑 classify_standard.py，观察分类率上升、Unknown 下降，
   并注意不要误伤已有分类（迭代调试）。
4. 注意规则顺序：越具体的套牌放越前面。
5. 之前手动分析过 84 副 Unknown（旧 Badaro 体系下）聚成约 8 类，命名已定：
   Izzet Aggro、Boros Manufacturing、Sultai Control、Izzet Opus、
   Mono-Red Aggro、Rakdos/Mardu Discard、Mono-Black Aggro、Boros/Mardu Token。
   这些可作为补规则的参考起点（但需用 j6e 数量格式重新表达）。
6. 分类打磨到满意后，进入模块三：数据统计（胜率、瑞士轮分数、当周/上周/
   当月八强占比、瑞士轮胜率>50%套牌中的占比等）。

## 六、用户的"特殊度发现"构想（第二阶段维护机制，已认可待实现）
1. 计算近期同类套牌各单卡平均张数作为基准（平均<1张的单卡忽略）。
2. 用单副牌与基准比较，评价其构筑"特殊度"。
3. 列出特殊度高的牌表，人工评定是否需修改规则。
4. 改规则后重复，直到稳定。
本质是一套半自动、持续的每周规则维护流程（环境每周变，不是一次性收敛）。
j6e 的数量规则体系正是实现这个构想的技术基础。
