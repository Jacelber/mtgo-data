# MTG 数据分析系统 — 项目笔记

最后更新：2026-07-02

## 一、项目总目标
搭建一个自动化系统，爬取 MTGO 官方赛事数据（以及未来的 melee.gg 实体赛数据），对牌表自动分类，统计各套牌类型的胜率、瑞士轮表现、八强占比等，最终以网页形式展示给其他用户查看。操作者无编程基础，全程在 AI 协助下用 Python 实现，工具尽量免费。

## 二、系统四大模块及状态
1. 数据抓取（MTGO）—— ✅ 已完成并实现云端自动化
2. 牌表分类 —— 🔨 进行中（已转向 j6e 数量规则体系，58 条规则，分类率已达 95.3%，仍可继续补规则）
3. 数据统计（高分占比/八强占比/转化率等）—— ✅ 阶段一已完成（stats_standard.py 能输出 1/4/12/36 周区间 JSON + index.json，见第六章）
4. 网页展示 —— 🔨 进行中（上线方式与开发顺序已定稿，进入阶段二最简前端，见第七章）

（melee.gg 抓取因有 Cloudflare + 登录，暂缓；第一阶段只做 standard 赛制的 MTGO 部分，跑通后复制到其他赛制，最后才啃 melee）

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
- player_count 字段确认为**全场报名人数**（非公布牌表数），是模块三推断赛事轮数的依据（见第六章 6.5）。
- starttime 格式为 `"YYYY-MM-DD HH:MM:SS.微秒"`（如 `"2026-06-26 18:00:00.0"`），无时区后缀。做日期处理时只需取前 10 个字符 `YYYY-MM-DD`，忽略时间与小数秒（模块三已如此实现，稳健）。
- final_rank 只有进八强的牌手才有值，其余为缺失/None（正常）。统计时用 to_int 兜底为大数（9999），八强判定用 `final_rank <= 8`。
- ⚠️ 已确认的数据类型隐患：排名/数值字段（如 final_rank、swiss_rank、swiss_score、player_count）在 JSON 里很可能是**字符串而非数字**。这会导致排序按"字典序"出错（例如 "10" 排在 "2" 前面）。目前只影响排序展示，分类不受影响；但模块三做统计（求和、比较、阈值判断）时必须先用安全转换（如 to_int 辅助函数，None/空值兜底为大数）统一转成整数，否则结果会错。event_report.py 的排序与 stats_standard.py 的统计均已用此法处理。

### 脚本清单（都在 D:\dl\crawlerpj）
- fetch_mtgo.py —— 抓单个赛事（最早写的，验证用）
- batch_mtgo.py —— 主力批量抓取脚本
- recon.py / recon_list.py —— 早期侦察脚本（已完成使命）
- classify_standard.py —— 分类脚本（模块二，已重写为 j6e 体系，含别名表与 min/exact/max/zone 匹配）
- cluster_unknown.py —— Unknown 牌表自动聚类脚本（辅助找出待补套牌；已改为 import 复用 classify_standard 的逻辑，保证判定一致）
- event_report.py —— 单场赛事分类报告脚本（按 final_rank 排名输出每位牌手的套牌+主备牌，用于人工比对验证规则，见模块二）
- stats_standard.py —— 统计脚本（模块三，阶段一）。import 复用 classify_standard 的分类逻辑；含 to_int / rounds_from_player_count / high_score_threshold / process_event / 周归类 / aggregate / build_all_stats，输出 stats/standard/mtgo/ 下的区间 JSON。

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
- 其中 standard 约 71 个赛事文件、约 2272 副牌表（模块二的分类对象）。
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
- ⚠️ 将来把分类/统计也接入 GitHub Actions 时，scrape.yml 里的 `pip install requests` 要改成 `pip install requests pyyaml`（分类脚本依赖 yaml）。

### Git / 仓库注意事项
- 本地 Git 已配置：user.name=jacelber, user.email=jacelber@gmail.com
- .gitignore 已忽略：page_source.html, list_page.html, __pycache__/, 根目录的 /*.json（但 data/ 下的 json 要保留，用 /*.json 只忽略根层）, 以及 MTGOFormatData/（Badaro 的规则库，不纳入自己仓库）
- ⚠️ stats/ 目录（统计产物 JSON）**要纳入 git、不能 ignore**：静态网站方案下这些 JSON 需被 GitHub Pages 发布出去，由 Actions 每天重算后 commit 更新。
- 日常更新代码流程：先 git pull（同步云端自动抓的数据，重要！）→ 本地编辑测试 → git add . → git commit -m "说明" → git push
- 因为云端每天自动提交数据，本地开工前必须先 git pull，否则 push 会被拒。
- 主要在本地 VS Code 改代码，网页编辑只用于极小确定的改动。

### 存储与费用
- 公开仓库 + Actions 完全免费、不限分钟数。
- 仓库建议 ≤1GB，单文件 ≤100MB。当前数据约几 MiB，每年增长几十 MB，远低于上限。
- 只要账号和公开仓库存在，数据长期保存。
- ⚠️ 未来考虑：原始赛事数据（data/）与网页+统计产物（stats/、网页文件）可能需要分仓库存放，避免原始数据越积越多撑大展示仓库。现阶段可先放同一仓库，到几百 MB 时再拆。

---

## 四、模块二：牌表分类（进行中 —— 已转向 j6e 数量规则体系，58 条规则，分类率 95.3%）

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
- 经典技巧：多个套牌用同一核心卡，靠"地的数量"区分颜色分支（如 Landfall 系列用 Stomping Ground/Temple Garden/Plains 的 minCopies/exactCopies 区分 Gruul/Selesnya/Mono-Green；Rhythm 系列用 Temple Garden/Breeding Pool/Plains 的 exactCopies 区分 Simic/Selesnya/Bant）；用 Mountain minCopies:12 / Swamp minCopies:10 锁定单色。
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
- 需要 yaml 库（pip install pyyaml）。本地已装在全局环境（未用虚拟环境，保持简单）。
- 顶部含 CARD_ALIASES 别名表 + normalize_name()。
- 读取 my_archetypes/standard.yaml 规则。
- 把每副牌处理成"卡名 -> 主牌张数"和"卡名 -> 备牌张数"两个字典（保留数量，且走别名归一化）。
- 匹配逻辑 signature_card_met 支持 minCopies / exactCopies / maxCopies / zone。
- 规则按 YAML 中的先后顺序匹配，匹配到第一个就停（顺序会影响结果，越具体/越优先的套牌应放越前面）。match_archetype 匹配不到返回 None（主流程再标为 "Unknown"）。
- 已去掉 fallback 机制（按决定），未匹配的老实标 Unknown。
- 输出分类报告 + 把 Unknown 牌表（带张数）导出到 unknown_decks.txt。
- main() 用 `if __name__ == "__main__":` 保护，以便 cluster_unknown.py / event_report.py / stats_standard.py import 复用而不触发全量分类。
- 可复用的关键函数：load_rules()（无参，读 RULES_FILE 常量）、deck_to_counts(player)、signature_card_met(sig, main, side)、match_archetype(main_counts, side_counts, archetypes)。

### 分类率提升历程
- 起点（纯 j6e 原版 40 条规则）：精确分类率 **46.0%**（1015/2208），Unknown 1193 副。这个 46% 看似比 Badaro 的 96% 低，但它是"真实的精确分类率"——之前 96% 含大量 fallback 兜底的粗糙结果，现在的 Unknown 不是"分错"而是"还没写规则覆盖"，更有意义。
- 经过多轮"聚类/比对 → 识别 → 写规则 → 重跑"的迭代：
  * 第一阶段（2026-06-30 当日）：提升至 **91.3%**（2045/2240），Unknown 195。
  * 第二阶段（后续）：提升至 **91.6%**（拆分 Rhythm/Momo 系后）。
  * 第三阶段：提升至 **95.3%**（58 条规则，Unknown 106 / 2272）。
- 详细的规则增删与关键约束见本章末尾"规则迭代记录"。

### 关键工作方法：人工比对验证（强于盲聚类）
- 因操作者已手动分类过"上周之前的所有赛事"，可用 event_report.py 选一场手动分过的赛事，按 final_rank 排名逐副输出（排名/牌手/自动分类套牌名/主牌/备牌），与手动结果逐副比对，精准暴露规则的漏判与误判。
- 这套方法比单纯跑聚类质量高，因为有"标准答案"。靠它发现并修复了 Lessons/Tablet 纠缠、Izzet Sling 漏分、Mardu/Rakdos、Momo 拆分等多处问题。
- event_report.py 复用 classify_standard 的逻辑（含别名表），保证比对结果与主分类一致；排序用 final_rank 优先、swiss_rank 兜底，并用安全转整数避免字符串排序错乱（"10" 排到 "2" 前的坑）。

### 辅助工具：cluster_unknown.py（Unknown 自动聚类）
- 对所有 Unknown 牌表按"主备合计卡名集合"的 Jaccard 相似度（阈值 0.60）做贪心聚类，输出大组（≥3 副）及每组代表牌表，写入 unknown_clusters.txt。
- ⚠️ 重要：该脚本必须 `from classify_standard import ...` 复用同一套规则加载、计数（含别名表）和匹配逻辑，否则它判定的 Unknown 会与主分类不一致（曾因没同步别名表，把已分类的 Dimir Excruciator 误当 Unknown 聚成最大组）。现已改为 import 复用，二者完全同步。
- 工作流：跑聚类 → 看前几大组代表牌表 → 人工识别套牌+命名+挑签名卡 → 写 j6e 规则 → 重跑分类。优先处理最大的几组（投入产出比最高）。

### 写规则的核心经验教训
1. 选"标志卡/签名卡"要选这个套牌【定义性的功能组件】，不要选"恰好流行但非必需"的卡，否则会漏掉不带那张卡的变体。（实例：最初给 Izzet Aggro 选了 Tokka 当必需卡，但很多不带 Tokka 或只放备牌，导致漏分；后改用 Spirebluff Canal 定颜色 + Scalding Viper/Hired Claw 等核心 pinger。Izzet Prowess 同理——生物组成多样无定论，应抓最稳定的 Stormchaser's Talent。）
2. 数量很关键：满编 4 张的关键卡才能定义套牌，零星 1 张可能只是过渡牌。这是放弃 Badaro、转向 j6e 数量体系的根本原因。
3. 规则顺序至关重要：越具体的套牌放越前面，让它先匹配，避免被宽泛规则抢走。见末尾"规则迭代记录"的关键排序约束。
4. 双面牌（含 //）的卡名坑：规则里要照抄数据里的完整写法（如 "Unholy Annex // Ritual Chamber"），否则计数为 0、规则失效。这是体系级隐患，后续遇到双面牌都要注意。
5. 放宽规则后要立刻核对相邻套牌数量有没有异常波动（如放宽 Spellementals 后看 Prowess 有没有暴跌），用数据验证而非过度提前设计。
6. archetype 的显示名（name）和文件名是两回事。
7. 用同一核心卡的多套牌（如 Rhythm 系、Manufacturing 系），必须给宽泛的那条补 exactCopies:0 排除条件，并把最具体的排在最前，否则会互相误吞。

### 规则迭代记录

**第一阶段新增/修改（2026-06-30 当日）**
- Izzet Sling（新）：Callous Sell-Sword 投掷流，区别于 Prowess。
- Golgari Demon（新）：Unholy Annex 黑绿恶魔中速（注意用双面牌全名 "Unholy Annex // Ritual Chamber"）。
- Jeskai Tablet / 4-Color Tablet（新）：满编 Tablet 的控制，靠 Inevitable Defeat 区分四色与三色。
- Lessons 三层拆分：Monument Lessons（Monument to Endurance）/ Jeskai Lessons（含白）/ Izzet Lessons（纯 Izzet，加 Monument maxCopies:1 + Jeskai Revelation exactCopies:0）。
- Mardu Discard（新，Hardened Academic）：当前 meta 近两月无纯 Rakdos 版本，故 Discard 牌目前都归 Mardu，属正常。
- Izzet Aggro、Gruul Delirium（Patchwork Beastie + Wildfire Wickerfolk）、Bant Bounce（Brightglass Gearhulk + Stormchaser's Talent）。
- 放宽：Selesnya/Mono-Green/Gruul Landfall 的 Mightform Harmonizer 统一放宽到 min 1；Selesnya Landfall 的 Temple Garden 放宽到 min 1，同时 Mono-Green 加 Plains exactCopies:0 排除含白；Izzet Prowess 改用 Stormchaser's Talent + Boomerang Basics + Spirebluff Canal，并加 Gran-Gran/Accumulate Wisdom exactCopies:0 排除 Lessons；Izzet Spellementals 放宽到 Sunderflock min 2 + Hearth Elemental min 1；Dimir Excruciator 靠别名表自动吃下 Kavaero 版本，Doomsday Excruciator 放宽到 min 1。

**第二/三阶段新增/调整（后续，91.6% → 95.3%）**
- Selesnya Rhythm（拆自误命名的第二条 Simic Rhythm，加 Temple Garden min 1）。
- Momo 系拆分：Azorius Momo（Hallowed Fountain min 1）/ Mono-White Momo（Hallowed Fountain exact 0）。
- Selesnya Offense 加 Temple Garden min 1 + Nature's Rhythm max 1。
- Dimir Deceit（新）：Excruciator 姊妹，Deceit + Requiting Hex + Superior Spider-Man，用 Doomsday Excruciator exact 0 区分。
- Boros Manufacturing（新）：Weapons Manufacturing + Legion Extruder + Sacred Foundry，用 Hallowed Fountain exact 0 排蓝。
- Jeskai Manufacturing（新）：同底子加蓝，用 Cryogen Relic min 2 锚定蓝色部分。
- Izzet Opus（新）：指纹为 Colorstorm Stallion + Ashling's Command 组合（该套牌专属，别的套牌不会同时用这两张）。
- Izzet Aggro（合并放宽）：合并两种红蓝速攻变体，用 Scalding Viper min 3 + Hired Claw min 3 + Spirebluff Canal min 1。

**关键排序约束（重排 yaml 时务必保持）**
- Izzet 系：Spellementals → Sling → Prowess → Opus → Aggro
- Dimir Excruciator 必须在 Dimir Deceit 之前（Excruciator 带 Doomsday，先捕获）
- Jeskai Manufacturing 在 Boros Manufacturing 之前
- Rhythm 系：Bant → Selesnya → Simic（最具体在前）
- Lessons 系（Monument/Jeskai/Izzet）在 Tablet 系之前；4-Color Tablet 在 Jeskai Tablet 之前；Mardu Discard 在 Rakdos Discard 之前

**关键区分逻辑**
- Excruciator vs Deceit：Deceit 用 Doomsday Excruciator exact 0
- Boros vs Jeskai Manufacturing：Boros 用 Hallowed Fountain exact 0，Jeskai 用 Cryogen Relic min 2
- Izzet Opus 指纹：Colorstorm Stallion + Ashling's Command 组合为该套牌专属
- Simic vs Selesnya Rhythm：Simic 补 Temple Garden exact 0 排白

---

## 五、用户的"特殊度发现"构想（分类维护机制，已认可待实现）
1. 计算近期同类套牌各单卡平均张数作为基准（平均<1张的单卡忽略）。
2. 用单副牌与基准比较，评价其构筑"特殊度"。
3. 列出特殊度高的牌表，人工评定是否需修改规则。
4. 改规则后重复，直到稳定。

本质是一套半自动、持续的每周规则维护流程（环境每周变，不是一次性收敛）。j6e 的数量规则体系正是实现这个构想的技术基础。可参考 j6e 官方仓库（github.com/j6e/mtg-meta-analyzer）的 archetype-cleaner 思路。

---

## 六、模块三：数据统计（MTGO，阶段一已完成 —— stats_standard.py）

### 6.1 目标与范围
统计模块基于已完成的分类结果，计算并输出各套牌的流行度与强度指标，供网页 dashboard 展示。

由于 MTGO 只放出前 32 的牌表，整体占比（出现次数 / 全场总数）不准确，因此**不使用整体占比**。改用两个更可靠的指标：对于人数较少的赛事，高胜套牌几乎能被 100% 收录，八强套牌则必然收录。

MTGO 与 melee 的数据**分开处理、分开展示**：MTGO dashboard 只展示 MTGO 的宏观指标；melee 的详细分析（含对阵矩阵等微观数据）单独展示，两者数据不混合。melee 抓取需先解决 Cloudflare + 登录，暂时靠后，本模块先做 MTGO。

（补充背景：MTGO 只放出八强淘汰赛的对阵结果，一个赛制一周约 6 场只有约 42 场对局记录，太少，故 MTGO 不做对阵矩阵，只做宏观指标；完整对阵结果与矩阵分析将来基于 melee 数据。）

### 6.2 核心指标
- **高分占比（high-score share）**：所有达到高分门槛的牌中，特定套牌所占的比例。分母 = 全部高分牌数。高分门槛定义见 6.4。
- **八强占比（top-8 share）**：所有 top8 牌中（final_rank ≤ 8），特定套牌所占的比例。分母 = 全部八强牌数。
- **高胜八强转化率（conversion）**：八强计数 / 高胜计数。反映套牌进入八强的转化能力，可一定程度衡量强度。若某套牌高分数为 0，转化率输出 null（前端显示 N/A）。
- **原始计数**：同时保留高分计数、八强计数、总出现次数等原始数字，便于核查与二次计算。

占比本身反映流行程度；高分占比与八强占比的对比（即转化率）反映套牌强度。（实测示例：某周 4-Color Tablet 数量不多但转化率 71.4% 最高、Izzet Prowess 数量多但转化率仅 41.2%，指标能有效区分"流行"与"强"。）

### 6.3 Unknown 处理
Unknown 牌照常计入分母，在结果中表示为 **new/rogue decks**。目标是在上线前尽量完善分类规则，让历史数据中不出现 Unknown。

### 6.4 高分门槛
以瑞士轮积分（每胜 3 分，MTGO 无平局）衡量，melee 有平局时以积分等效计（如 8 轮 5 胜 3 负与 4 胜 3 平 1 负同为 15 分，均视为等效高分，因为瑞士轮的目的就是获取积分）。

统一公式：

    threshold = (floor(rounds × 1.5 / 3) + 1) × 3

判定条件为 `swiss_score ≥ threshold`。含义是积分严格超过总可能积分的一半，并向上取整到最近的 3 的倍数（整数胜场）。

各轮次门槛验证：

| 轮数 | 门槛（≥） |
| --- | --- |
| 5 | 9 |
| 6 | 12 |
| 7 | 12 |
| 8 | 15 |
| 9 | 15 |

该公式仅基于积分，天然兼容 melee 的平局情况。

### 6.5 轮数判定（player_count 查表法）
高分门槛依赖赛事瑞士轮数，而 MTGO 数据不直接提供轮数字段。此前考虑过"最高分反推"（ceil(最高 swiss_score / 3)），但不可靠：全场无人打满分时会低估轮数（如 7 轮赛事最高只有 18 分而非 21 分）。

经查 MTGO 官方 Events & Formats 页面，确认 Scheduled Event 的瑞士轮数由**初始报名人数**决定，对应数据中的 `player_count`（全场报名人数）字段。因此改用 **player_count 查官方对照表** 作为轮数判定的唯一依据。

官方人数-轮数对照表：

| 报名人数 (players) | 瑞士轮数 (rounds) |
| --- | --- |
| 8 | 3 |
| 9–16 | 4 |
| 17–32 | 5 |
| 33–64 | 6 |
| 65–128 | 7 |
| 129–212 | 8 |
| 213–384 | 9 |
| 385–672 | 10 |

规律：人数每翻倍约加一轮。

**关于 Challenge 32 / 64 / 96 的澄清**：这三者不是固定轮数赛事，而是三种奖励规模档位（最低报名门槛分别为 32 / 64 / 96 人），全部采用"Swiss rounds based on attendance, then cut to Top 8"。因此**赛事名称里的数字不能用于推断轮数**。例如报名 78 人的 "Challenge 32" 实际跑 7 轮。所有 Challenge、Qualifier、Super Qualifier 均按实际 player_count 查表。

**排除项**：本项目不抓取 Preliminary 赛事（固定 4 轮、无八强），因此无需对固定轮数赛事做特判。轮数逻辑只需处理"按人数查表"这一种情况，`player_count` 字段确认为全场报名人数，不设回退逻辑。

**melee 差异**：melee 数据直接提供轮数字段，无需反推；仅 MTGO 用查表法。

参考实现（已在 stats_standard.py 落地并验证）：

    def rounds_from_player_count(n):
        table = [(8,3),(16,4),(32,5),(64,6),(128,7),(212,8),(384,9),(672,10)]
        for cap, rounds in table:
            if n <= cap:
                return rounds
        # 超出对照表范围时按翻倍规律外推
        r, cap = 10, 672
        while n > cap:
            cap *= 2
            r += 1
        return r

### 6.6 时间切片
时间切片可由使用者自由调整。为支持前端交互，统计模块预计算多个**滚动区间**：最近 1 周、4 周、12 周、36 周，各输出一个 JSON。所有区间都以"最近一个已结束的完整周"为终点往前推。判定"完整周"用"该周周日 < 今天"（简单可靠，不依赖场次数波动）。每副牌按其所属赛事的 starttime 归入对应自然周（周一到周日，周一日期为该周标识）。
（当前数据仅覆盖约 9 个完整周，故 12w / 36w 档暂等于"全部数据"，日后数据积累自然填满。）

### 6.7 JSON 输出结构（已落地）
结果输出到 `stats/standard/mtgo/` 目录，文件名 `range_1w.json` / `range_4w.json` / `range_12w.json` / `range_36w.json`，外加同目录 `index.json` 索引（列出各区间的 file/type/start/end/weeks/total_decks + generated 时间 + latest_complete_week，供前端填菜单）。单文件字段包括 format、source（固定 "mtgo"）、period（type/start/end/weeks）、total_decks、total_high_score、total_top8、unknown_count 与 archetypes 数组。archetypes 按 count 降序。实际输出示例（range_1w，2026-06-22~06-28，288 副牌）：

    {
      "format": "standard",
      "source": "mtgo",
      "period": {"type": "1w", "start": "2026-06-22", "end": "2026-06-28", "weeks": 1},
      "total_decks": 288,
      "total_high_score": 137,
      "total_top8": 72,
      "unknown_count": 8,
      "archetypes": [
        {
          "name": "Selesnya Offense",
          "count": 54,
          "high_score_count": 28,
          "high_score_share": 0.2044,
          "top8_count": 18,
          "top8_share": 0.25,
          "conversion": 0.6429
        }
      ]
    }

### 6.8 实现步骤（MTGO，均已完成并验证）
1. ✅ 安全整型转换辅助函数 to_int（swiss_score / final_rank / player_count 字符串安全转整）。
2. ✅ 轮数判定 rounds_from_player_count（按 player_count 查 6.5 对照表）+ 高分门槛 high_score_threshold（6.4 公式）。
3. ✅ 单赛事处理 process_event：算轮数→门槛，复用 classify_standard.match_archetype 打标签，判定 is_high_score / is_top8。
4. ✅ 自然周归类 parse_event_date（取前 10 字符）+ week_monday；latest_complete_week 找最近完整周。
5. ✅ 聚合 aggregate：按套牌累计 count/high/top8，算三占比与转化率，占比合计核对为 1.0000。
6. ✅ build_range + build_all_stats：输出 1/4/12/36 周区间 JSON + index.json。
7. ✅ 已在最近完整周（06-22）验证：288 副牌、72 八强（9×8）、占比合计精确 1.0，数字合理。

### 6.9 关键提醒
复用现有分类逻辑；计算前统一做字符串转数字（to_int）；占比与原始计数一并保留；Unknown 计入分母并标为 new/rogue decks。stats/ 产物要纳入 git 供 Pages 发布。

### 6.10 数据来源与日期
轮数对照表来源：MTGO 官方 Events & Formats 页面（https://www.mtgo.com/en/mtgo/events）。Challenge 档位说明来源：MTGO Preliminaries and Format Challenges 页面（https://www.mtgo.com/premier-play-prelims-and-format-challenges，其中 96 档为 2026-06-23 新增）。本节记录日期：2026-07-02。

---

## 七、模块四：网页展示与上线方式（阶段一已完成，进入阶段二）

### 7.1 总体开发顺序（standard MTGO 可用版本）
采用"垂直切一刀，先做出能用的东西"策略。三阶段推进，每阶段有明确产出：

**阶段一：统计模块（纯 Python，产出 JSON）** —— ✅ 已完成（见第六章 stats_standard.py，输出 stats/standard/mtgo/ 下 4 个区间 JSON + index.json）。

**阶段二：最简前端（能在浏览器打开看到数据）** —— 🔨 进行中。一个 HTML + 通过 CDN 引入的图表库（如 Chart.js），读取阶段一的 JSON 渲染。第一版做到：时间区间切换控件（1/4/12/36 周）、一张套牌占比图或三指标表格，布局预留广告位空区块。验收：本地浏览器打开能看到数据、能切换时间档。

**阶段三：自动化 + 上线** —— 把生成 JSON 接进现有 GitHub Actions，每天自动重算并 commit；开 GitHub Pages 开关发布公开网址。验收：访问网址能看到工具，次日数据自动更新。

**后续（非本次目标）**：standard 跑通后复制同一套流程到其他赛制（换数据目录和规则文件，架构不动）；最后才啃 melee（Cloudflare + 登录抓取 + 对阵矩阵，作为二期）。

### 7.2 上线方式：静态网站 + GitHub Pages
- 本项目数据特点：每天批量更新一次、只读、无用户写入、无需登录、所有用户看同一份预计算结果。因此**不需要传统服务器/后端/数据库**，用"静态网站"方式上线即可，免费且几乎零运维。
- 运作方式：GitHub Actions 每天抓取+分类+统计生成 JSON 并 commit；GitHub Pages 自动把仓库里的网页+JSON 发布成网址（形如 jacelber.github.io/xxx）；用户浏览器加载 JSON 本地渲染。这与现有"仓库 + Actions 每日自动跑"的架构无缝衔接，上线只是多加"生成网页"环节 + 打开 Pages 开关。

### 7.3 关键澄清：静态 ≠ 不能交互
- "静态"指服务器只发文件、不做实时计算，**不等于页面不能交互**。用户选时间段、切图表、筛选套牌等交互，静态网站完全能做。
- 用户可选"1/4/12/36 周"的实现：统计模块**预先把每个档位都算好各存一个 JSON**，前端点按钮就加载对应文件，体验与动态查询完全一样，但无需服务器。
- 只有当用户选择组合多到无法预先枚举（如任意拖拽起止日期 + 多维筛选组合爆炸）、或有登录/个人数据时，才需要动态后端。当前固定四档位是有限可枚举的，静态方案完全胜任。将来若要"任意区间"，也可让前端把若干周的小 JSON 在浏览器里相加，仍不需后端。

### 7.4 未来盈利（流量广告）的注意事项
- 静态网站可放广告（嵌广告商的 JS 代码即可），与静态方案不冲突。
- 现实门槛（流量起来后才需处理，现在无需改任何设计）：
  * 主流广告平台（如 Google AdSense）通常要求**独立域名**（免费二级域名通过率低）、一定原创内容与流量、隐私政策等合规页面。域名一年仅几十到一百多元。
  * GitHub Pages 免费版条款上不鼓励纯商业广告站；一旦认真盈利、流量变大，更稳妥是把静态文件迁到对商业更友好、同样免费的静态托管（如 Cloudflare Pages 或 Netlify），迁移成本几乎为零（还是那堆静态文件换个地方托管）。
  * 免费托管有带宽/请求额度，静态 JSON 单次访问很轻，普通流量足够；真超额说明已有可观流量，届时上便宜 CDN 或用广告收入覆盖即可。
- 现阶段唯一顺手可做的事：前端从一开始预留一两个广告位空区块，方便将来插代码不用重排版（不做也可后补）。
- 结论：广告是"有流量之后"的后期附加，不影响当前数据/统计/前端设计，无需提前为它设计任何东西。

---

## 八、下次继续的待办（DOWN TO HERE）
统计模块（模块三）阶段一已完成：stats_standard.py 能输出 stats/standard/mtgo/ 下 range_1/4/12/36w.json + index.json，四块核心逻辑（轮数查表、高分门槛、分类、聚合）全部单元验证通过，最近完整周（06-22）数据核对无误（288 副牌、72 八强、占比合计 1.0）。分类率维持 95.3%，58 条规则。

**已提交建议**：`git add stats_standard.py stats/` + commit + push（stats/ 要纳入 git，供 Pages 发布）。

**下一步：进入阶段二（最简前端）**，按第七章 7.1：
1. 一个 HTML 文件 + CDN 引入图表库（Chart.js）。
2. 读取 stats/standard/mtgo/index.json 填时间档菜单，再按选择加载对应 range_Nw.json。
3. 第一版做到：1/4/12/36 周切换控件 + 一张套牌占比图或三指标表格（含 count / 高分占比 / 八强占比 / 转化率，转化率 null 显示 N/A）。
4. 布局预留 1-2 个广告位空区块。
5. 验收：本地浏览器打开能看到数据、能切换时间档。

**之后**：阶段三（把统计接入 Actions 每日自动重算 + 开 GitHub Pages 上线）→ 复制到其他赛制 → melee.gg（Cloudflare + 登录 + 对阵矩阵，二期）。

**并行可选（分类打磨，边际收益递减）**：用 event_report.py 比对法或 cluster_unknown.py 继续把剩余 106 副 Unknown 的前几大组补上规则，目标 96~97%。但 95.3% 已足够统计使用，可放在上线后慢慢补。
