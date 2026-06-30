# MTG 数据分析系统 — 项目笔记

最后更新：2026-06-30

## 一、项目总目标
搭建一个自动化系统，爬取 MTGO 官方赛事数据（以及未来的 melee.gg 实体赛数据），对牌表自动分类，统计各套牌类型的胜率、瑞士轮表现、八强占比等，最终以网页形式展示给其他用户查看。操作者无编程基础，全程在 AI 协助下用 Python 实现，工具尽量免费。

## 二、系统四大模块及状态
1. 数据抓取（MTGO）—— ✅ 已完成并实现云端自动化
2. 牌表分类 —— 🔨 进行中（已转向 j6e 数量规则体系，分类率已达 91.3%，仍在补规则）
3. 数据统计（胜率/八强占比等）—— ⬜ 未开始
4. 网页展示 —— ⬜ 未开始

（melee.gg 抓取因有 Cloudflare + 登录，暂缓，第一阶段只做 MTGO）

---

## 三、模块一：数据抓取（已完成）

### 关键技术发现
- MTGO 赛事页面的数据藏在 HTML 里的 JS 对象 `window.MTGO.decklists.data`。
- 用括号配对法（数花括号深度，跳过字符串内的括号）精确截取该段 JSON，比简单找 `};` 稳健。
- 赛事列表页按月份分页，URL 格式为：`https://www.mtgo.com/decklists/<年>/<两位数月份>`，例：https://www.mtgo.com/decklists/2026/05
- 注意：当月页面和历史归档月份页面，赛事链接都是静态写在 HTML 里的（在页面靠后位置，约 20000 字节之后），requests 能正常提取。之前怀疑历史页是 JS 动态加载，经核实是误判——真正原因是网络下载偶发残缺。
- MTGO 有时返回状态码 200 但页面残缺（内容不完整或缺字段），需要把"下载+解析+完整性检查"作为整体重试。
- 只抓竞技赛事（challenge/qualifier/showcase 等），排除含 "league" 的链接。
- 用 inplayoffs == 1 字段筛掉没有八强单淘的赛事（如 preliminary）。
- premodern 不能用模糊包含判断，否则会被误判成 modern；改为取链接首段词精确匹配。

### 数据字段结构（每个赛事 JSON）
- 赛事层：event_id, description, format, starttime, player_count, players[]
- 每位牌手（players[] 里）：player（牌手名）, loginid（唯一ID）, swiss_rank, swiss_score, swiss_wins（score//3）, opp_match_win_pct, game_win_pct, final_rank, main_deck[], sideboard[]
- 每张卡：{ "name": 英文卡名, "qty": 数量 }
- 三张表（standings / final_rank / decklists）都靠 loginid 串联。
- 注意：MTGO 只公布部分牌手牌表（如 92 人赛事只有 32 份牌表），属正常。
- ⚠️ 已发现的数据类型隐患：排名/数值字段（如 final_rank、swiss_rank、swiss_score）在 JSON 里很可能是**字符串而非数字**。这会导致排序按"字典序"出错（例如 "10" 排在 "2" 前面）。目前只影响排序展示，分类不受影响；但模块三做统计（求和、比较、胜率）时必须先用安全转换（如 to_int 辅助函数，None/空值兜底为大数）统一转成整数，否则结果会错。

### 脚本清单（都在 D:\dl\crawlerpj）
- fetch_mtgo.py —— 抓单个赛事（最早写的，验证用）
- batch_mtgo.py —— 主力批量抓取脚本
- recon.py / recon_list.py —— 早期侦察脚本（已完成使命）
- classify_standard.py —— 分类脚本（模块二，已重写为 j6e 体系，含别名表与 min/exact/max/zone 匹配）
- cluster_unknown.py —— Unknown 牌表自动聚类脚本（辅助找出待补套牌；已改为 import 复用 classify_standard 的逻辑，保证判定一致）
- event_report.py —— 单场赛事分类报告脚本（按 final_rank 排名输出每位牌手的套牌+主备牌，用于人工比对验证规则，见模块二）

### batch_mtgo.py 当前配置与健壮性
- 默认抓"最近两个月"（当月+上月），跨年自动处理（1月→上年12月）。
- 数据存到 data/<格式>/<赛事描述>_<event_id>.json
- fetched.txt 记录已抓链接，自动去重跳过。
- 支持的格式：standard, legacy, pioneer, pauper, vintage, modern
- 健壮性机制（经多轮打磨）：
  * download() 函数：最多重试 5 次，timeout=90 秒，失败间隔等待。
  * 整体重试：下载+解析作为一体，最多 4 轮，每轮间隔 15 秒。
  * is_data_complete() 函数：检查解析出的数据是否含关键字段（event_id, description, player_count, decklists 且 decklists 非空），残缺数据视为失败、触发重试，而不是崩溃。
  * build_clean_data() 内部用 .get() 安全取值（format, starttime 等），即使意外缺字段也不崩溃（双保险）。这是为修复一次 `KeyError: 'player_count'` 崩溃而加固的。
  * 失败的赛事不记入 fetched.txt，下次运行自动重试（自愈）。

### 已抓数据现状
- 约 345+ 个赛事 JSON，覆盖六个格式，2026 年 5 月和 6 月。
- 其中 standard 约 70 个赛事文件、2240 副牌表（模块二的分类对象）。
- 数据已 git commit + push 到云端仓库。

### 自动化（已打通并验证稳定）
- GitHub 仓库：https://github.com/Jacelber/mtgo-data
- GitHub 账号用户名：Jacelber（也写作 jacelber）
- GitHub Actions 配置文件：.github/workflows/scrape.yml
- 定时：每天 UTC 04:00 = 北京时间中午 12:00 运行（cron: '0 4 * * *'）
- 已修复的关键问题：
  * 403 推送被拒：Actions 默认无写权限。已在仓库 Settings → Actions → General → Workflow permissions 改为 "Read and write permissions"，确认 workflow 变绿。
  * push 撞车（rejected, fetch first）：多次运行时间接近会撞车。已在 workflow 的推送步骤改为 commit 后先 `git pull --rebase` 再 push，并在无新数据时正常退出（exit 0）。已验证有效。
- ✅ 定时运行已确认正常：在 GitHub 上观察到两次 scheduled run 均正常运行并显示绿色成功。但实际触发时间晚于设定值——设定北京 12:00（UTC 04:00），实际约在北京 15:00 左右触发，延迟约 3 小时。
- 关于时间差的结论：这是 GitHub Actions 定时任务的**已知固有特性**（整点如 UTC 04:00 处于全球任务高峰，会排队延迟，官方明确不保证准点，极端情况下甚至会跳过某次运行），**不是配置或代码问题**。对本项目无任何影响，可作为正常误差忽略。原因：(1) 每日抓取的是累积、非时效敏感的赛事数据，12 点还是 15 点跑抓到的内容一样，不丢数据；(2) 脚本有去重（fetched.txt）和自愈（残缺重试、失败不记录下次重抓）机制，即使偶尔延迟或跳过，下次会补上；(3) 关键是"绿色成功运行"已确认，调度链路通畅。
- 如果将来希望更接近设定时间，可把 cron 从整点 `0 4` 改成冷门的非整点分钟（如 `17 4 * * *`）避开高峰，但对本项目纯属锦上添花，无必要。
- 注意：公开仓库若连续 60 天无活动，GitHub 会暂停定时 workflow（会发邮件提示，需手动重新启用）。本项目每天有自动提交，暂不会触发。
- "Node.js 20 is deprecated" 是黄色警告，可忽略，不影响运行。

### Git / 仓库注意事项
- 本地 Git 已配置：user.name=jacelber, user.email=jacelber@gmail.com
- .gitignore 已忽略：page_source.html, list_page.html, __pycache__/, 根目录的 /*.json（但 data/ 下的 json 要保留，用 /*.json 只忽略根层）, 以及 MTGOFormatData/（Badaro 的规则库，不纳入自己仓库）
- 日常更新代码流程：先 git pull（同步云端自动抓的数据，重要！）→ 本地编辑测试 → git add . → git commit -m "说明" → git push
- 因为云端每天自动提交数据，本地开工前必须先 git pull，否则 push 会被拒。
- 主要在本地 VS Code 改代码，网页编辑只用于极小确定的改动。

### 存储与费用
- 公开仓库 + Actions 完全免费、不限分钟数。
- 仓库建议 ≤1GB，单文件 ≤100MB。当前数据约几 MiB，每年增长几十 MB，远低于上限。
- 只要账号和公开仓库存在，数据长期保存。

---

## 四、模块二：牌表分类（进行中 —— 已转向 j6e 数量规则体系，分类率 91.3%）

### 重大决策：放弃 Badaro，全面转向 j6e 格式
- 初期用了 Badaro 的 MTGOFormatData 规则库（基于"含/不含"逻辑，JSON 格式），跑出 96% 分类率，但其中很大比例是 fallback 兜底"硬塞"进 Control/Midrange/Aggro 大类的粗糙结果，对精细胜率统计价值有限。
- 关键局限：Badaro 体系原生不支持"数量"条件（只能判断含不含某卡），而 MTG 中"满编 4 张的关键卡"往往才是定义套牌的核心，且后续"特殊度/基准张数"分析也依赖数量。因此 Badaro 体系不够用。
- 已全面转向 j6e（https://j6e.me/mtg-meta-analyzer/，仓库 https://github.com/j6e/mtg-meta-analyzer）的规则格式，它原生支持数量条件。Badaro 规则库（MTGOFormatData 文件夹）保留在本地仅作参考，分类已不再使用它。
- j6e 官方 standard 规则库位于其仓库的 `data/archetypes/standard.yaml`，我们最初的 standard.yaml 即基于该文件（约 40 条规则，date: 2026-03-08）。

### j6e 规则格式（YAML，存于 my_archetypes/standard.yaml）
- 顶层有 format、date、archetypes 列表。
- 每个 archetype 有 name 和 signatureCards 列表。
- 每张签名卡可指定：
  * minCopies: N —— 该卡至少 N 张
  * exactCopies: N —— 该卡恰好 N 张（常用 exactCopies: 0 表示"不能有这张卡"，用于排除）
  * maxCopies: N —— 该卡至多 N 张（**我们的扩展**，见下）
  * 都不写 —— 默认"有就行"（>=1）
- 一个套牌的所有 signatureCards 条件都满足才算匹配（纯 AND 关系）。
- ⚠️ j6e 原生格式不支持"多卡名/任一匹配（anyOf）"，也不支持别名。这两个缺口我们各自做了扩展（见下）。
- 经典技巧：多个套牌用同一核心卡，靠"地的数量"区分颜色分支（如 Landfall 系列用 Stomping Ground/Temple Garden/Plains 的 minCopies/exactCopies 区分 Gruul/Selesnya/Mono-Green）；用 Mountain minCopies:12 / Swamp minCopies:10 锁定单色。
- ⚠️ YAML 写法注意：卡名含逗号、冒号、撇号（'）、连字符的，统一用双引号包起来最安全（如 "Surrak, Elusive Hunter"、"Sazh's Chocobo"）。缩进对齐极敏感，从对话复制粘贴时容易错位导致 ScannerError。

### 我们对 j6e 体系做的三项扩展

**1. zone 字段（区分主/备牌位置）**
- 需求：j6e 原版不区分主牌/备牌（按主备合计计数）。现阶段合计是合理的（主备交换不改变套牌本质），但为未来可能需要严格区分位置的情况预留能力。
- 方案：给签名卡增加可选的 zone 字段：
  * 不写 zone 或 zone: any —— 主备合计（默认，完全兼容 j6e 原版规则）
  * zone: main —— 只数主牌
  * zone: side —— 只数备牌
- 设计原则：简单情况简单写（绝大多数规则不写 zone），需要时才加。

**2. maxCopies 条件（至多 N 张）**
- 需求：区分变体时需要"某卡至多 N 张"的能力（例：Izzet Lessons 要求 Monument to Endurance 至多 1 张，以与 Monument Lessons 变体区分）。
- 方案：在 signature_card_met 里增加 `if "maxCopies" in sig: return actual <= sig["maxCopies"]` 分支。

**3. 卡名别名表 CARD_ALIASES（处理 MTGO 版权改名卡）**
- 背景：MTGO 上联动版权卡会被改名。具体窗口是"去年年末蜘蛛侠系列发售"到"2026 年 6 月漫威超级英雄系列发售"这段时间；之后线上游戏获得版权，新数据用回正名。所以同一张卡在 5 月数据叫改名、6 月数据叫正名，两种名字会并存。
- 已知实例：`Kavaero, Mind-Bitten` 实际就是 `Superior Spider-Man`（MTGO 改名）。
- 方案：在 classify_standard.py 顶部建 `CARD_ALIASES` 字典 + `normalize_name()` 函数，在 deck_to_counts 读卡时把主备牌卡名统一归一化成 j6e 规则使用的标准名。一处维护、全局生效，规则文件保持干净。别名表把两个时期的数据自动归一。
- 范围：只需 cover 构筑中高频出现的改名卡即可（未来其他联动系列再现该问题的概率低）。

### classify_standard.py 当前能力（已重写）
- 需要 yaml 库（pip install pyyaml）。本地已装在全局环境（未用虚拟环境，保持简单）。注意：将来分类若要上云端 GitHub Actions，scrape.yml 里的 `pip install requests` 要改成 `pip install requests pyyaml`。
- 顶部含 CARD_ALIASES 别名表 + normalize_name()。
- 读取 my_archetypes/standard.yaml 规则。
- 把每副牌处理成"卡名 -> 主牌张数"和"卡名 -> 备牌张数"两个字典（保留数量，且走别名归一化）。
- 匹配逻辑 signature_card_met 支持 minCopies / exactCopies / maxCopies / zone。
- 规则按 YAML 中的先后顺序匹配，匹配到第一个就停（顺序会影响结果，越具体/越优先的套牌应放越前面）。
- 已去掉 fallback 机制（按决定），未匹配的老实标 Unknown。
- 输出分类报告 + 把 Unknown 牌表（带张数）导出到 unknown_decks.txt。

### 分类率提升历程（2026-06-30 当日工作）
- 起点（纯 j6e 原版 40 条规则）：精确分类率 **46.0%**（1015/2208），Unknown 1193 副。这个 46% 看似比 Badaro 的 96% 低，但它是"真实的精确分类率"——之前 96% 含大量 fallback 兜底的粗糙结果，现在的 Unknown 不是"分错"而是"还没写规则覆盖"，更有意义。
- 经过当日多轮"聚类 → 识别 → 写规则 → 重跑"的迭代，分类率提升至 **91.3%**（2045/2240），Unknown 降至 195 副。
- 当日新增/修改的规则（按主题）：
  * Izzet Sling（新）：Callous Sell-Sword 投掷流，区别于 Prowess。
  * Golgari Demon（新）：Unholy Annex 黑绿恶魔中速（注意用双面牌全名 "Unholy Annex // Ritual Chamber"）。
  * Jeskai Tablet / 4-Color Tablet（新）：满编 Tablet 的控制，靠 Inevitable Defeat 区分四色与三色。
  * Lessons 三层拆分：Monument Lessons（Monument to Endurance）/ Jeskai Lessons（含白）/ Izzet Lessons（纯 Izzet，加 Monument maxCopies:1 + Jeskai Revelation exactCopies:0）。
  * Mardu Discard（新，Hardened Academic）：当前 meta 近两月无纯 Rakdos 版本，故 Discard 牌目前都归 Mardu，属正常。
  * Izzet Aggro（Scalding Viper + Razorkin Needlehead 红蓝速攻）、Gruul Delirium（Patchwork Beastie + Wildfire Wickerfolk）、Bant Bounce（Brightglass Gearhulk + Stormchaser's Talent）。
  * 放宽：Selesnya/Mono-Green/Gruul Landfall 的 Mightform Harmonizer 统一放宽到 min 1；Selesnya Landfall 的 Temple Garden 放宽到 min 1，同时 Mono-Green 加 Plains exactCopies:0 排除含白；Izzet Prowess 改用 Stormchaser's Talent + Boomerang Basics + Spirebluff Canal，并加 Gran-Gran/Accumulate Wisdom exactCopies:0 排除 Lessons；Izzet Spellementals 放宽到 Sunderflock min 2 + Hearth Elemental min 1；Dimir Excruciator 靠别名表自动吃下 Kavaero 版本。
- 最新分类分布（前几名）：Izzet Prowess 22.0%、Selesnya Offense 8.9%、Unknown 8.7%、Izzet Spellementals 8.3%、Dimir Excruciator 7.1%、4-Color Tablet 6.6%、Jeskai Lessons 6.4%、Selesnya Landfall 5.1%、Mono-Green Landfall 4.6%、Momo-White 4.2%、Mardu Discard 2.9% 等。

### 关键工作方法：人工比对验证（强于盲聚类）
- 因操作者已手动分类过"上周之前的所有赛事"，可用 event_report.py 选一场手动分过的赛事，按 final_rank 排名逐副输出（排名/牌手/自动分类套牌名/主牌/备牌），与手动结果逐副比对，精准暴露规则的漏判与误判。
- 这套方法比单纯跑聚类质量高，因为有"标准答案"。当日靠它发现并修复了 Lessons/Tablet 纠缠、Izzet Sling 漏分、Mardu/Rakdos 等多处问题。
- event_report.py 复用 classify_standard 的逻辑（含别名表），保证比对结果与主分类一致；排序用 final_rank 优先、swiss_rank 兜底，并用安全转整数避免字符串排序错乱（"10" 排到 "2" 前的坑）。

### 辅助工具：cluster_unknown.py（Unknown 自动聚类）
- 对所有 Unknown 牌表按"主备合计卡名集合"的 Jaccard 相似度（阈值 0.60）做贪心聚类，输出大组（≥3 副）及每组代表牌表，写入 unknown_clusters.txt。
- ⚠️ 重要：该脚本必须 `from classify_standard import ...` 复用同一套规则加载、计数（含别名表）和匹配逻辑，否则它判定的 Unknown 会与主分类不一致（曾因没同步别名表，把已分类的 Dimir Excruciator 误当 Unknown 聚成最大组）。现已改为 import 复用，二者完全同步。
- 工作流：跑聚类 → 看前几大组代表牌表 → 人工识别套牌+命名+挑签名卡 → 写 j6e 规则 → 重跑分类。优先处理最大的几组（投入产出比最高）。

### 写规则的核心经验教训
1. 选"标志卡/签名卡"要选这个套牌【定义性的功能组件】，不要选"恰好流行但非必需"的卡，否则会漏掉不带那张卡的变体。（实例：最初给 Izzet Aggro 选了 Tokka 当必需卡，但很多不带 Tokka 或只放备牌，导致漏分；后改用 Spirebluff Canal 定颜色 + Scalding Viper/Razorkin Needlehead 等核心 pinger。Izzet Prowess 同理——生物组成多样无定论，应抓最稳定的 Stormchaser's Talent。）
2. 数量很关键：满编 4 张的关键卡才能定义套牌，零星 1 张可能只是过渡牌。这是放弃 Badaro、转向 j6e 数量体系的根本原因。
3. 规则顺序至关重要：越具体的套牌放越前面，让它先匹配，避免被宽泛规则抢走。当日确立的关键顺序：Spellementals → Sling → Prowess；Monument/Jeskai Lessons → Tablet 系；Mardu Discard → Rakdos Discard；4-Color Tablet → Jeskai Tablet。
4. 双面牌（含 //）的卡名坑：规则里要照抄数据里的完整写法（如 "Unholy Annex // Ritual Chamber"），否则计数为 0、规则失效。这是体系级隐患，后续遇到双面牌都要注意。
5. 放宽规则后要立刻核对相邻套牌数量有没有异常波动（如放宽 Spellementals 后看 Prowess 有没有暴跌），用数据验证而非过度提前设计。
6. archetype 的显示名（name）和文件名是两回事。

## 五、下次继续的待办（DOWN TO HERE）
当前分类率 91.3%，Unknown 195 副。可选方向：

**方向 A：继续打磨分类（推荐用比对法）**
1. 用 event_report.py 再选一两场手动分过的赛事，逐副比对，把误判/漏判摘出来，逐条修规则。这比盲聚类质量高。
2. 或重跑 cluster_unknown.py 处理剩余 195 副 Unknown 的前几大组。但边际收益已递减（每条规则只能捞回几十甚至十几副）。
3. 目标可推到 93~95%。

**方向 B：转入模块三（数据统计）**
- 91% 分类率对算胜率、八强占比已足够；剩余 Unknown 可单列一类或忽略。
- ⚠️ 开工前必须先确认的关键问题：**数据里有没有逐轮对局胜负结果（谁打赢谁）**，还是只有 swiss_score / swiss_wins / final_rank 这类汇总名次？
  * 若只有汇总名次：能算"八强占比""瑞士轮胜率>50% 的套牌占比""各套牌平均名次"。
  * 若有逐轮对局结果：才能算真正的"套牌 vs 套牌对战矩阵胜率"。
- 统计模块务必先处理"数值字段是字符串"的隐患（用 to_int 统一转换），否则求和/比较会错。
- 拟算指标：各套牌胜率、瑞士轮分数、当周/上周/当月八强占比、瑞士轮胜率>50% 套牌中的占比等。

**之后：模块四（网页展示）** 与 melee.gg 抓取（需解决 Cloudflare + 登录）。

## 六、用户的"特殊度发现"构想（第二阶段维护机制，已认可待实现）
1. 计算近期同类套牌各单卡平均张数作为基准（平均<1张的单卡忽略）。
2. 用单副牌与基准比较，评价其构筑"特殊度"。
3. 列出特殊度高的牌表，人工评定是否需修改规则。
4. 改规则后重复，直到稳定。

本质是一套半自动、持续的每周规则维护流程（环境每周变，不是一次性收敛）。j6e 的数量规则体系正是实现这个构想的技术基础。可参考 j6e 官方仓库（github.com/j6e/mtg-meta-analyzer）的 archetype-cleaner 思路。
