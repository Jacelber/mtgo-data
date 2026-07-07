# MTG 数据分析系统 — 项目笔记

最后更新：2026-07-05（平均牌表 & 偏离度设计定稿并**全面落地**：架空平均牌表 Core/Flex + 实际典型牌表 medoid + 单副偏离度 deviation + 区间平均偏离度 + 近期变化度；后端 stats_standard.py 与前端 index.html 均已实现并验证）

## 一、项目总目标
搭建一个自动化系统，爬取 MTGO 官方赛事数据（以及未来的 melee.gg 实体赛数据），对牌表自动分类，统计各套牌类型的胜率、瑞士轮表现、八强占比等，最终以网页形式展示给其他用户查看。操作者无编程基础，全程在 AI 协助下用 Python 实现，工具尽量免费。

## 二、系统四大模块及状态
1. 数据抓取（MTGO）—— ✅ 已完成并实现云端自动化
2. 牌表分类 —— 🔨 进行中（j6e 数量规则体系，**76 条规则，整体分类率 98.2%，高分/八强段 Unknown 已压到 0.7%**，可视需要继续补规则）
3. 数据统计（高分占比/八强占比/转化率等）—— ✅ 阶段一已完成（stats_standard.py 输出 1/4/12/36 周区间 JSON + decks JSON + index.json，见第七章）；**平均牌表 & 偏离度设计已定稿并全面落地（见第六章）**
4. 网页展示 —— ✅ **阶段二（前端骨架）已完成，且平均牌表/偏离度/近期变化度前端已落地**，进入阶段三（部署上线，见第八章）；**用户体验补足清单见 8.7**

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
- player_count 字段确认为**全场报名人数**（非公布牌表数），是模块三推断赛事轮数的依据（见第七章 7.5）。
- starttime 格式为 `"YYYY-MM-DD HH:MM:SS.微秒"`（如 `"2026-06-26 18:00:00.0"`），无时区后缀。做日期处理时只需取前 10 个字符 `YYYY-MM-DD`，忽略时间与小数秒（模块三已如此实现，稳健）。
- final_rank 只有进八强的牌手才有值，其余为缺失/None（正常）。统计时用 to_int 兜底为大数（9999），八强判定用 `final_rank <= 8`。
- ⚠️ 已确认的数据类型隐患：排名/数值字段（如 final_rank、swiss_rank、swiss_score、player_count）在 JSON 里很可能是**字符串而非数字**。这会导致排序按"字典序"出错（例如 "10" 排在 "2" 前面）。目前只影响排序展示，分类不受影响；但模块三做统计（求和、比较、阈值判断）时必须先用安全转换（如 to_int 辅助函数，None/空值兜底为大数）统一转成整数，否则结果会错。event_report.py 的排序与 stats_standard.py 的统计均已用此法处理。

### 脚本清单（都在 D:\dl\crawlerpj，云端仓库 Jacelber/mtgo-data）
- fetch_mtgo.py —— 抓单个赛事（最早写的，验证用）
- batch_mtgo.py —— 主力批量抓取脚本
- recon.py / recon_list.py —— 早期侦察脚本（已完成使命）
- classify_standard.py —— 分类脚本（模块二，j6e 体系，含别名表与 min/exact/max/zone 匹配）
- cluster_unknown.py —— Unknown 牌表自动聚类脚本（辅助找出待补套牌；import 复用 classify_standard 逻辑，保证判定一致）
- dump_unknown_highperf.py —— 只导出"高分或八强的 Unknown 牌表"完整主备牌到 unknown_highperf.txt，按战绩（final_rank 升序、swiss_score 降序）排序。用于专门清理"打得好却没被识别"的高价值漏网套牌。import 复用 classify_standard + stats_standard 的门槛逻辑。
- event_report.py —— 单场赛事分类报告脚本（按 final_rank 排名输出每位牌手的套牌+主备牌，用于人工比对验证规则）
- stats_standard.py —— 统计脚本（模块三，阶段一 + 平均牌表/偏离度/近期变化度全部落地）。import 复用 classify_standard 分类逻辑；含 to_int / rounds_from_player_count / high_score_threshold / process_event / 周归类 / aggregate / pick_best_deck / merge_cards / **deck_vector / mean_vector / appearance_rates / split_core_flex / weighted_l1 / normalize_dev / deck_diff / pick_medoid / build_base_pack / recent_change_for_arch** / build_range / build_all_stats，输出 stats/standard/mtgo/ 下的区间 JSON + decks JSON + index.json（index.json 含全局 D99）。
- index.html —— 前端单页（模块四，阶段二成果 + 平均牌表/偏离度/近期变化度已落地，见第八章）。

### batch_mtgo.py 当前配置与健壮性
- 默认抓"最近两个月"（当月+上月），跨年自动处理（1月→上年12月）。**补抓历史月份**：把 USE_RECENT_MONTHS 改为 False，填 TARGET_YEAR / TARGET_MONTH，跑完记得改回 True（本次补 4 月数据即用此法）。
- 数据存到 data/<格式>/<赛事描述>_<event_id>.json
- fetched.txt 记录已抓链接，自动去重跳过（load_fetched 用 set() 读，重复行无害）。
- 支持的格式：standard, legacy, pioneer, pauper, vintage, modern（一次运行抓全部六个赛制）
- 健壮性机制（经多轮打磨）：
  * download() 函数：最多重试 5 次，timeout=90 秒，失败间隔等待。
  * 整体重试：下载+解析作为一体，最多 4 轮，每轮间隔 15 秒。
  * is_data_complete() 函数：检查解析出的数据是否含关键字段（event_id, description, player_count, decklists 且 decklists 非空），残缺数据视为失败、触发重试，而不是崩溃。
  * build_clean_data() 内部用 .get() 安全取值（format, starttime 等），即使意外缺字段也不崩溃（双保险）。这是为修复一次 `KeyError: 'player_count'` 崩溃而加固的。
  * 失败的赛事不记入 fetched.txt，下次运行自动重试（自愈）。

### 已抓数据现状
- 全六赛制赛事 JSON，覆盖 2026 年 **4/5/6 月**（已补齐 4 月，填满近 12 周）。
- 其中 standard **103 个赛事文件、3296 副牌表**（模块二分类对象；上一版为 71 场 / 2272 副）。
- 数据已 git commit + push 到云端仓库。

### 自动化（已打通并验证稳定）
- GitHub 仓库：https://github.com/Jacelber/mtgo-data （默认分支 **master**）
- GitHub 账号用户名：Jacelber（也写作 jacelber）
- GitHub Actions 配置文件：.github/workflows/scrape.yml（名为 "Daily MTGO Scraper"）
- **scrape.yml 当前流程（已确认全文）**：checkout（含已有 data/ 和 fetched.txt）→ setup-python 3.12 → `pip install requests` → `python batch_mtgo.py` → `git add data/ fetched.txt` → 若无 staged 变化则 exit 0，否则 commit → `git pull --rebase` → `git push`。
- ⚠️ **重要：目前 scrape.yml 只跑爬虫，不跑 classify/stats。** 也就是云端每天只更新 data/ 和 fetched.txt，**不会重新生成 stats/ 下的 JSON**。因此网站统计数据目前完全靠本地手动跑 classify_standard.py + stats_standard.py 再提交。阶段三的核心任务之一就是把这两步接进 workflow（见第八章 8.5）。
- 定时：每天 UTC 04:00 = 北京时间中午 12:00 运行（cron: '0 4 * * *'），另支持手动 workflow_dispatch。
- 已修复的关键问题：
  * 403 推送被拒：Actions 默认无写权限。已在仓库 Settings → Actions → General → Workflow permissions 改为 "Read and write permissions"。
  * push 撞车（rejected, fetch first）：已在推送步骤改为 commit 后先 `git pull --rebase` 再 push，无新数据时 exit 0。已验证有效。
- ✅ 定时运行已确认正常（GitHub 上观察到多次 scheduled run 绿色成功）。实际触发比设定晚约 3 小时（北京约 15:00），这是 GitHub Actions 定时任务的**已知固有特性**（整点高峰排队，官方不保证准点），对本项目无影响（数据非时效敏感 + 去重自愈机制）。如需更准可把 cron 改为非整点分钟（如 `17 4 * * *`），非必要。
- 注意：公开仓库若连续 60 天无活动，GitHub 会暂停定时 workflow（本项目每天有自动提交，不会触发）。
- "Node.js 20 is deprecated" 是黄色警告，可忽略。
- ⚠️ 将来把分类/统计接入 Actions 时，`pip install requests` 要改成 `pip install requests pyyaml`（分类脚本依赖 yaml）。

### Git / 仓库注意事项（实战补充）
- 本地 Git 已配置：user.name=jacelber, user.email=jacelber@gmail.com
- .gitignore 现状：page_source.html, list_page.html, __pycache__/, /*.json（只忽略**根目录**层的 json，data/ 与 stats/ 子目录的 json 不受影响、正常纳入）。建议再补上临时分析产物：unknown_decks.txt, unknown_clusters.txt, unknown_highperf.txt, event_classify_report.txt（这些每次跑都重生成、无需入库；此前是手动挑选未提交，尚未写进 .gitignore，下次可补）。
- ⚠️ stats/ 目录（统计产物 JSON）**要纳入 git、不能 ignore**：静态网站方案下这些 JSON 需被 GitHub Pages 发布。
- ⚠️ **data/ 和 fetched.txt 必须纳入 git**：云端 Actions 每次靠 checkout 出来的 fetched.txt 做增量去重、靠 data/ 累积历史，不提交会导致每次从零重抓。
- **日常更新流程（亲历验证，务必照此顺序）**：
  1. 先 `git add` + `git commit` 本地改动（若工作区脏，pull --rebase 会拒绝）
  2. 再 `git pull --rebase` 同步云端每日自动抓的数据
  3. **fetched.txt 几乎必冲突**（本地和云端都往里加行）→ 解决办法是"两边内容都保留、删掉 `<<<<<<<` / `=======` / `>>>>>>>` 三个标记行"（VS Code 点 "Accept Both Changes" 最快；重复 URL 无害因 set() 去重）→ `git add fetched.txt` → `git rebase --continue`
  4. rebase --continue 可能弹出 vim 提交信息界面：保存退出按 `Esc` 然后 `:wq` 回车；**误改了想放弃**按 `Esc` 然后 `:q!` 回车（不保存退出，用默认信息，不影响代码改动）
  5. 最后 `git push`
- 首次本地↔云端对撞已成功解决并推送（184 文件变更，含 4 月全赛制数据 + 76 条规则 + stats + index.html + dump 脚本）。
- 本地服务器预览命令：`python -m http.server 8000`，浏览器开 http://localhost:8000，停止按 Ctrl+C，改数据后 **Ctrl+Shift+R 强制刷新**避开缓存。

### 存储与费用
- 公开仓库 + Actions 完全免费、不限分钟数。
- 仓库建议 ≤1GB，单文件 ≤100MB。当前数据约几 MiB，每年增长几十 MB，远低于上限。
- ⚠️ 未来考虑：原始赛事数据（data/）与网页+统计产物可能需分仓库存放，避免原始数据撑大展示仓库。现阶段同仓库，到几百 MB 时再拆。

---

## 四、模块二：牌表分类（进行中 —— j6e 数量规则体系，76 条规则，整体分类率 98.2%，高分/八强 Unknown 0.7%）

### 重大决策：放弃 Badaro，全面转向 j6e 格式
- 初期用 Badaro 的 MTGOFormatData（基于"含/不含"逻辑），跑出 96% 但大量是 fallback 兜底硬塞进大类的粗糙结果，对精细统计价值有限。
- 关键局限：Badaro 原生不支持"数量"条件，而 MTG 中"满编 4 张的关键卡"往往才定义套牌，且"特殊度/基准张数"分析也依赖数量。
- 已全面转向 j6e（https://j6e.me/mtg-meta-analyzer/，仓库 https://github.com/j6e/mtg-meta-analyzer）格式，原生支持数量条件。Badaro 规则库保留本地仅作参考。
- j6e 官方 standard 规则库位于其仓库 `data/archetypes/standard.yaml`，我们最初的 standard.yaml 即基于该文件（约 40 条，date: 2026-03-08）。

### j6e 规则格式（YAML，存于 my_archetypes/standard.yaml）
- 顶层有 format、date、archetypes 列表。
- 每个 archetype 有 name 和 signatureCards 列表。
- 每张签名卡可指定：
  * minCopies: N —— 至少 N 张
  * exactCopies: N —— 恰好 N 张（常用 exactCopies: 0 表示"不能有这张卡"，用于排除）
  * maxCopies: N —— 至多 N 张（**我们的扩展**）
  * 都不写 —— 默认"有就行"（>=1）
- 一个套牌所有 signatureCards 条件都满足才算匹配（纯 AND）。
- ⚠️ j6e 原生不支持 anyOf 和别名，两处缺口各自做了扩展（见下）。
- 经典技巧：多套牌用同一核心卡，靠"地的数量"区分颜色分支；用 Mountain minCopies:12 / Swamp minCopies:10 锁定单色。
- ⚠️ YAML 写法：卡名含逗号、冒号、撇号（'）、双斜杠（//）、连字符的，统一用双引号包起来最安全。缩进极敏感，复制粘贴易错位导致 ScannerError / ParserError。

### 我们对 j6e 体系做的三项扩展

**1. zone 字段（区分主/备牌位置）**
- 给签名卡增加可选 zone：不写或 any=主备合计（默认，兼容原版）；main=只数主牌；side=只数备牌。绝大多数规则不写 zone。

**2. maxCopies 条件（至多 N 张）**
- signature_card_met 里 `if "maxCopies" in sig: return actual <= sig["maxCopies"]`。用于区分变体（如 Izzet Lessons 要求 Monument to Endurance 至多 1 张）。

**3. 卡名别名表 CARD_ALIASES（处理 MTGO 版权改名卡）**
- 背景：MTGO 上联动版权卡会被改名。窗口是"去年年末蜘蛛侠系列发售"到"2026 年 6 月漫威超级英雄系列发售"，之后线上获版权用回正名。所以同一张卡在 5 月叫改名、6 月叫正名，两种名字并存。
- 方案：classify_standard.py 顶部建 CARD_ALIASES 字典 + normalize_name() 函数，在 deck_to_counts 读卡时把主备牌卡名归一化成标准名。一处维护、全局生效。
- 已知实例（当前表内容）：
  * `Kavaero, Mind-Bitten` → `Superior Spider-Man`
  * `Leyline Weaver` → `Spider Manifestation`
- ⚠️ **Leyline Weaver 案例的完整教训**：这类改名不只影响分类计数，还影响**前端卡图**——Scryfall 只认正式名，用占位名拉图会失败。因此别名归一必须贯穿三层：① 分类计数（deck_to_counts 已用 normalize_name）；② stats 生成牌表 JSON 时（merge_cards 也要用 normalize_name，见 7.9）；③ 前端展示与卡图 URL（因后端已归一化输出正式名，前端无需再处理）。**结论：只要 classify 的 deck_to_counts 和 stats 的 merge_cards 都调用 normalize_name，正式名就会写进 decks JSON，前端卡图自然正常。** YAML 规则里也应直接用正式名（已确认 yaml 中无 Leyline Weaver）。

### classify_standard.py 当前能力
- 需要 yaml 库（pip install pyyaml）。本地装在全局环境。
- 顶部含 CARD_ALIASES 别名表 + normalize_name()。
- 读 my_archetypes/standard.yaml。
- 把每副牌处理成"卡名->主牌张数"和"卡名->备牌张数"两字典（保留数量，走别名归一化）。
- signature_card_met 支持 minCopies / exactCopies / maxCopies / zone。
- 规则按 YAML 先后顺序匹配，匹配到第一个就停（顺序影响结果）。match_archetype 匹配不到返回 None（主流程标 "Unknown"）。
- 无 fallback，未匹配老实标 Unknown。
- 输出分类报告 + 把 Unknown 牌表（带张数）导出到 unknown_decks.txt。
- main() 用 `if __name__ == "__main__":` 保护，供其他脚本 import 复用。
- 可复用关键函数：load_rules() / deck_to_counts(player) / signature_card_met(sig,main,side) / match_archetype(main,side,archetypes) / normalize_name(name)。

### 分类率提升历程
- 起点（纯 j6e 40 条）：精确分类率 46.0%（1015/2208）。
- 迭代（2272 副数据阶段）：91.3% → 91.6% → 95.3%（58 条规则，Unknown 106/2272）。
- **补 4 月后（3296 副数据）**：
  * 补 4 月数据后仅用旧 58 条规则：**95.9%**（3161/3296，Unknown 135）——说明规则对新赛季覆盖尚可。
  * 加 4 条新规则（62 条）：**96.5%**（Unknown 117），且已有套牌数字全部不变（新规则做兜底、无误抢）。
  * 针对性放宽 Golgari Midrange / Sultai Control 签名卡：**96.8%**（Unknown 104）。
  * 手动大规模补充/拆分规则（76 条）：**98.2%**（3238/3296，Unknown 58）。
  * **高分/八强段 Unknown 专项清理后降到 0.7%**（已达成"高分八强 Unknown < 1%"目标）。

### 分类工作方法（专项清理高分/八强 Unknown）
- 用户最初目标从"整体分类率"细化为"**高分/八强段的 Unknown < 1%**"——理由：乱搭实验牌归不了类无所谓（它也打不进高分），但能打进八强/高分的牌归不了类，说明是有竞争力的真实套牌，漏掉会让统计失真。
- 新增 dump_unknown_highperf.py：只导出满足"高分 or 八强"的 Unknown 牌表完整主备牌，按战绩排序，逐副人工审阅。这批数量少、质量高、补规则性价比最高。
- 配合 cluster_unknown.py（对高分/八强 Unknown 聚类，MIN_GROUP_SIZE 视数量可降到 2），找出成群漏网的强势套牌针对性补规则。
- ⚠️ cluster_unknown.py 和 dump_unknown_highperf.py 都必须 import 复用 classify_standard（含别名表）+ stats_standard（门槛函数），否则 Unknown 判定与门槛计算和主流程不一致。

### 写规则的核心经验教训
1. 选签名卡要选套牌【定义性功能组件】，不选"恰好流行但非必需"的卡，否则漏掉变体。
2. 数量很关键：满编 4 张的关键卡才定义套牌。
3. 规则顺序至关重要：越具体越前，避免被宽泛规则抢走。
4. 双面牌（含 //）卡名要照抄数据全名（如 "Unholy Annex // Ritual Chamber"），否则计数为 0。
5. 放宽规则后立刻核对相邻套牌数量有无异常波动（用数据验证）。
6. archetype 显示名（name）和文件名是两回事。
7. 用同一核心卡的多套牌，宽泛那条要补 exactCopies:0 排除，最具体的排最前。
8. **"色组兜底规则"策略**：对归不进具体套牌、但能识别颜色/大类的中速/杂类牌表，写"无明显签名卡、靠土地基底 + 一串 exactCopies:0 排除"的宽松规则，**统一放在 YAML 最末尾**。这样所有具体套牌先匹配，兜底只吃剩下的，既提升识别率又不误抢。约定：兜底规则前加注释分隔行标明"须始终置于最后"；兜底之间**颜色越多越靠前、越少越靠后**（避免多色牌被少色兜底截胡）。首个实例：Golgari Midrange（Overgrown Tomb + Blooming Marsh + Restless Cottage 各≥2，排除 Nature's Rhythm / Flow State / Unholy Annex），成功收纳绿黑中速多个变体、且不动任何已有套牌数字。

### 规则迭代记录

**（早期，46%→95.3%，58 条，详见旧版记录，此处保留要点）**
- 关键排序约束（重排 yaml 时务必保持）：
  * Izzet 系：Spellementals → Sling → Prowess → Opus → Aggro（**注：Izzet Sling 已改名 Izzet Fling**，逻辑不变）
  * Dimir Excruciator 必须在 Dimir Deceit 之前
  * Jeskai Manufacturing 在 Boros Manufacturing 之前
  * Rhythm 系：Bant → Selesnya → Simic（最具体在前）
  * Lessons 系（Monument/Jeskai/Izzet）在 Tablet 系之前；4-Color Tablet 在 Jeskai Tablet 之前；Mardu Discard 在 Rakdos Discard 之前
- 关键区分逻辑：Excruciator vs Deceit（Doomsday Excruciator exact 0）；Boros vs Jeskai Manufacturing（Hallowed Fountain exact 0 / Cryogen Relic min 2）；Izzet Opus 指纹 Colorstorm Stallion + Ashling's Command；Simic vs Selesnya Rhythm（Temple Garden exact 0 排白）。

**新增/调整（58 → 76 条）**
- 针对 4 月数据聚类出的漏网套牌新增：
  * **Golgari Reanimator**：Zombify + Broodheart Engine（复活流，专属性极强）。
  * **Golgari Midrange**（色组兜底）：见上"经验教训 8"。收纳带 Badgermole/Emeritus 与带 Mosswood/Preacher 两种绿黑中速变体。
  * **Sultai Control**：核心签名卡从 Flow State 改为 **Ancient Cornucopia + Rakshasa's Bargain**（这两张才是所有 Sultai 变体共性；最初误用 Flow State 当必需卡，导致大量不带 Flow State 的变体漏分，从 13 副掉到 1 副，修正后回升）。
  * **4-Color Control（组4变体）**：Rakshasa's Bargain + Aang, Swift Savior + Three Steps Ahead + Emeritus of Abundance，用 Flow State exact 0 与 Sultai Control 区分。
- 另手动补充多条低频但真实的套牌（每条命中 1~6 副）：Golgari Crime、Golgari Roots、Mono-Blue Spellementals、Mono-Black Aggro、Mono-Green Aggro、Selesnya Midrange、Sultai Demon、Orzhov Repartee、Orzhov Control、Boros Leyline、Mono-Red Leyline、Temur Tablet、Simic Ramp、Gruul Fling 等（具体签名卡见 yaml）。
- 改名：**Izzet Sling → Izzet Fling**（同步新增 Gruul Fling）。
- ⚠️ 低频"一次性规则"要注意别过拟合（为一副牌写一条规则，新数据来了可能永远只匹配那一副）。识别率优先则保留无妨。
- ⚠️ 排序副作用记录：某条新规则曾使 Sultai Control 从 13 掉到 1（被更靠前的规则截胡 / 签名卡选错），经把核心签名卡换成 Cornucopia+Bargain 修正。**每次大改后必须逐个核对相邻套牌数字有无异常升降。**

---

## 五、用户的"特殊度发现"构想（分类维护机制，已认可待实现）
1. 计算近期同类套牌各单卡平均张数作为基准（平均<1张的单卡忽略）。
2. 用单副牌与基准比较，评价其构筑"特殊度"。
3. 列出特殊度高的牌表，人工评定是否需修改规则。
4. 改规则后重复，直到稳定。

本质是一套半自动、持续的每周规则维护流程。j6e 数量规则体系是实现基础。可参考 j6e 官方仓库的 archetype-cleaner 思路。

（此构想的**统计学落地设计已定稿并落地**，见第六章——第六章把"平均牌表"与"偏离度/特殊度"的具体数学口径全部确定并实现。本章描述的是分类维护的应用目的：面向用户的 decks JSON 只放单副偏离度 + 平均牌表，**全量"每副牌偏离度排行"留给本章的特殊度维护脚本单独输出**，复用第六章已落地的均值向量 + 加权 L1 距离函数即可。）

---

## 六、平均牌表 & 偏离度（特殊度）统计设计定稿并落地（2026-07-03 定稿 → 2026-07-05 落地 → 2026-07-06 归一化改为绝对刻度）

本章确定并**已实现**「平均牌表」「偏离度」「近期变化度」三大统计功能。核心原则：**机器比较**与**用户参考**彻底解耦；所有距离度量**共用同一个加权 L1 函数**（一处定义、多处复用）。

⚠️ **重大迭代记录**：
- 旧版（2026-07-03）：Overall / High-score 双 medoid + deviation_percentile。**已废弃。**
- 中版（2026-07-05）：单一架空平均牌表（Core/Flex）+ 单一实际典型牌表（medoid）+ 单副 deviation + 区间平均偏离度 + 近期变化度；归一化用**全局 P99（D99）**。
- **今版（2026-07-06）：归一化从「全局 D99」改为「绝对刻度」（见 6.5）。** 起因见下。

### 6.0 为什么从 D99 改为绝对刻度（本次迭代动因，务必理解）
- D99 归一化（距离 / 全体牌表距离的 P99 × 100）测的是「这副牌在全体里有多极端（相对语义）」。
- 实测暴露问题：一副构筑已高度成型、核心完全没动、只调整了地基和几张 Flex 卡的 4-Color Tablet，D99 口径下算出 **94 分**（接近满分），与玩家体感严重不符——它本质就是标准 Tablet，不该接近「最独创的 1%」。
- 根因：D99 锚点偏小（约 19.8），而地和低权重 Flex 卡的琐碎差异就能贡献十几点距离，除以小锚点后分数虚高，分辨率被压在高区间。
- 用户目标是「绝对语义」刻度：**0 分 = 与主流构筑几乎完全一致；接近 100 分 = 几乎换掉整副（现实中极少出现，因为完全不同的牌不会被归为同一套牌类型）**。
- 解决：改用「加权 L1 距离 / base 自身加权总量 × 100」。这把尺子天然满足上述直觉，且核心卡（高权重）没动时分数自然低、真正魔改核心才拿高分——正好贴合「独创性」语义。改后同一副 Tablet 落到 **40 分（那副具体牌）/ best_deck 25 分**，符合体感。

### 6.1 固定 4 周 base（所有偏离度计算的统一基准）
- **BASE_WEEKS = 4**：所有偏离度相关计算（单副偏离度、区间平均偏离度、Core/Flex 分组、实际典型 medoid、近期变化度）**统一基于最近 4 个完整自然周的数据**，与用户查询的时间区间（1/4/12/36 周）无关。
- base 采用"最近 4 个完整自然周"滑动窗口，与区间口径一致（终点为最近一个已结束的完整周）。偏离度随时间自然更新。
- **样本门槛 MIN_SAMPLE = 8**：该套牌 4 周内牌表数 ≥8 才计算 base。不足则该套牌无偏离度基准。

### 6.2 三个核心定义（术语已与用户敲定）
- **架空平均牌表（Typical deck, abstract）**：过去一个月（4 周 base）该套牌的平均构筑。逐卡计算平均张数，**保留小数、不取整、不凑 60**。这是唯一参与偏离度打分的机器基准。
- **实际典型牌表（Typical deck, actual / medoid）**：4 周 base 内，离架空平均牌表最近的一副**真实、合法、高胜率**牌表。用作用户可读的代表牌。
- **偏离度（deviation）**：单副牌相对架空平均牌表的偏离程度（独创性度量）。

### 6.3 Core/Flex 分组
架空平均牌表按**出现率**（而非均值张数）拆成两组呈现给用户：
- **核心卡 / Core**：出现率 ≥ **CORE_RATE = 0.8** 的卡（"大多数牌表中都使用的组件"）。
- **弹性卡 / Flex**：出现率 < 0.8 的卡（"相对只有少数牌表才使用的组件"）。
- 展示时每张卡保留均值张数（保留一位小数）用于排序，另存出现率 rate。
- 边缘卡地板 **AVG_FLOOR = 0.15**：均值 < 0.15 的卡从向量中滤除（一次性错卡噪声），不进 Core/Flex 也不进偏离度计算。
- CORE_RATE=0.8 为初版验证值，若 Core 组过空或过满可再调。

### 6.4 距离函数：加权 L1（曼哈顿）——全局共用
- **度量：加权 L1** —— `Σ w_card × |牌表张数 − 均值张数|`。兼具可解释性（能拆成"少带 X、多带 Y"）与合理性（核心卡偏离权重更高）。
- **权重 w_card = 该卡的出现率**（0~1，干净的"核心程度"刻度）；不用均值张数当权重。
- **共用性**：选 medoid、单副偏离度、区间平均偏离度、近期变化度**全部共用此函数**（weighted_l1），只实现一次。选 medoid 用原始距离比大小即可。
- ⚠️ **口径：纯主牌（use_side = False），备牌完全不算**（2026-07-06 复核确认）。
  - `deck_vector` 只读 `main_deck`，整条偏离度链路（base 均值 / Core/Flex / medoid / 单副偏离度 / 区间平均 / 近期变化度）自始至终只有主牌。
  - 理由：主牌定义套牌核心策略、信号干净；备牌随环境波动大、方差高，会引入噪声、淹没主牌信号。玩家的真正创新几乎都在主牌。
  - ⚠️ **一致性铁律**：base 与被比较对象必须在同一「卡空间」——要么都含备牌、要么都不含，**绝不能一边含一边不含**，否则距离度量失真（base 里的备牌卡会被当成被比牌「少带的卡」，凭空拉高偏离度）。现状全链路纯主牌，自洽无问题。将来若要纳入备牌，必须**所有调用点同步切换**（给 `deck_vector` 加 include_side 参数并全改），或改为「主牌偏离度 / 备牌偏离度」两个独立指标，且都要重新校准数值。当前明确不纳入。

### 6.5 归一化：绝对刻度（本次核心改动，替代旧 D99）
- 所有偏离度类指标（单副偏离度、区间平均偏离度、近期变化度）**统一改用绝对刻度**归一化到 0~100，仍保持同量纲可比。
- **公式**：`deviation = min(100, round( weighted_l1(vec, base_mean, weights) / denom × 100 ))`
  - 其中 **分母 denom = base 自身的加权总量 = Σ(权重 × base均值张数)**，对 base 里所有卡求和。
  - 语义：把 base 里每张卡「完全拿掉」所对应的加权距离作为满分 100 的锚点。
  - **0 分 = 与 base 完全一致；接近 100 = 几乎换掉整副 base。**
- **分母是每套牌各自的常数**（各套牌 base 加权量不同），存入 base_pack 的 `denom` 字段，随各指标复用。
  - 区间平均偏离度：分母用该套牌 **4 周 base** 的 denom。
  - 近期变化度：两端为「本周平均 vs 前 4 周平均」，参照系是前 4 周，分母用**前 4 周（远端）平均向量的加权总量**。
- ⚠️ **语义变化（与旧 D99 的区别）**：
  - 旧 D99 是**全局单一锚点**，任意两套牌偏离度可直接横向比「谁更极端」。
  - 新绝对刻度**分母因套牌而异**，偏离度含义变为「相对各自 base 改了多少比例」。**同一套牌内部比较（哪副更独创）完全有效，也是主要用途**；跨套牌横向比时应理解为「改动比例」而非「绝对差异量」。对本项目场景（用户关心「这副 Tablet 相对标准 Tablet 改了多少」）反而更合理。
- ⚠️ **数值特征**：绝对刻度下数值普遍温和（日常构筑差异多落在 5~40，最独创也就 25~40），接近 100 基本不可能出现（那意味着换掉整副）。这正是「绝对刻度」的预期效果，代价是区分度集中在中低区间。若将来需拉开独创牌差距，可考虑温和的非线性拉伸，但初版不做（先让用户用直觉刻度，看反馈再说）。
- **旧 D99 相关代码保留但不再用于归一化**：`percentile()` 计算、`build_base_pack` 里的 `d99`、`index.json` 的 `global_d99` 字段均保留（历史遗留、无害），归一化已切到 `normalize_dev_abs(d, denom)`。旧 `normalize_dev(d, d99)` 函数保留未删。

### 6.6 三个独立指标（含义各异，均用绝对刻度）

**① 单副偏离度（deviation）** —— 套牌固有属性
- 某副牌（纯主牌）相对 4 周 base 架空平均的加权 L1 距离，绝对刻度归一化到 0~100。越高越非主流（独创性越强）。
- 用于 best_deck，并附**逐卡差异拆解 deviation_diff**（比典型"少带/多带"的卡）。
- ⚠️ **差异过滤**：前端只显示绝对张数差 ≥ 1 的卡（`DIFF_MIN = 1`）——差零点几张属均值小数波动，忽略。

**② 区间平均偏离度（avg_deviation）** —— 衡量某类套牌一段时间内的构筑漂移
- 口径（用户敲定）：该区间内该套牌**每副牌各自对 4 周 base 算偏离度，再取平均**。
  - （注：此为「先算距离、再平均」，测的是该区间牌表相对固定 base 的平均偏离水平。）
- 各区间语义：1 周=本周相对整月主流的平均偏离；4 周≈base 内在离散度；12/36 周=更长窗口的偏离水平（拖入更早老构筑，数值更大）。
- 因基准固定为 4 周，趋势为 1w ≤ 4w ≤ 12w ≈ 36w。小样本也照常显示（不设额外门槛）。
- ⚠️ **不进主表格**（见 6.7）。

**③ 近期变化度（recent_change）** —— 套牌固有属性，衡量"本周相对之前主流的变化"
- 近端 = 最近完整 1 周该套牌主牌平均向量；远端 = 前 4 周（不含本周）该套牌主牌平均向量。
- 权重 = **前 4 周出现率**；距离 = 加权 L1；归一化 = 绝对刻度（分母用前 4 周加权总量）。
- **样本门槛 RECENT_MIN = 3、PRIOR_WEEKS = 4**：本周 <3 副 → null，原因枚举 `"recent"`；前 4 周 <3 副 → null，原因 `"prior"`；无 4 周 base → `"nobase"`。
- 结果与 average_deck / best_deck 同级存进 decks 文件，**在展开区显示，不进表格**。

### 6.7 UI 决策（用户敲定，不变）
- **主表格列结构完全不动**：区间平均偏离度、近期变化度都不进表格（避免"表格里出现不随区间变的列"这种反直觉设计）。
- 展开区（deck-row）：
  * **best_deck**：显示单副偏离度 + 逐卡差异拆解。
  * **average_deck 区**，两个 tab：架空平均牌表（synthetic，默认）显示 Core/Flex 两栏 + 均值张数；实际典型牌表（real）显示 medoid 主牌 + 备牌。
  * **近期变化度**行：固定显示在 tab 切换按钮与"常备卡（Core）"之间。

### 6.8 后端实现（stats_standard.py，已落地）
- **常量**：AVG_FLOOR=0.15、MIN_SAMPLE=8、BASE_WEEKS=4、CORE_RATE=0.8、DEV_PERCENTILE=99（旧 D99 遗留、不再用于归一化）、RECENT_MIN=3、PRIOR_WEEKS=4。
- **距离/归一化函数**：`weighted_l1(vec, mean, weights)`、`dev_denominator(mean_vec, weights)`（= Σ 权重×均值，绝对刻度分母）、`normalize_dev_abs(d, denom)`（= min(100, round(d/denom×100))）。旧 `normalize_dev(d, d99)` 保留未用。
- **向量/分组函数**：`deck_vector`（仅主牌）、`mean_vector`（滤 <AVG_FLOOR）、`appearance_rates`、`split_core_flex`、`deck_diff`、`pick_medoid`、`record_to_deck_display`。
- **base 构建 `build_base_pack`**：返回 `(base_pack, d99)`；每个达标套牌含 mean / weights / **denom** / core / flex / medoid_display / sample_size / recent_change / recent_change_reason；d99 仍计算但仅用于遗留字段。
- **近期变化度 `recent_change_for_arch`**：返回 `(value, reason)`，分母用远端加权总量（`dev_denominator(prior_mean, weights)`），`normalize_dev_abs`。
- **区间构建**：`build_range` 用 `normalize_dev_abs(..., base["denom"])` 算 avg_deviation；`build_decks` 用 `normalize_dev_abs(raw, base["denom"])` 算 best_deck.deviation + deviation_diff。
- **全量统计 `build_all_stats`**：先建 base 包，逐区间生成 JSON；index.json 仍写 `global_d99`（遗留）。
- ⚠️ 中间量（均值向量、权重、denom）只在内存/base_pack 流转，denom 不必写进用户 decks JSON（偏离度已是算好的 0~100 值）。

### 6.9 验证结果（2026-07-06，绝对刻度）
- 4 周内达标套牌 **14 个（≥8 副）**（数据窗口滑到 2026-06-08~07-05）。
- 单副偏离度 / 12 周平均偏离度 / 近期变化度（best_deck，纯主牌，绝对刻度）：
  * Selesnya Offense（4 周样本 165）：14 / 15 / 13
  * Izzet Prowess（160）：9 / 15 / 6
  * Jeskai Lessons（128）：7 / 10 / 4
  * 4-Color Tablet（102）：25 / 31 / 15
  * Izzet Spellementals（87）：12 / 22 / 7
- 数值符合直觉：Jeskai Lessons 核心 5 张全 rate=1.0 满编、构筑极固定 → 偏离度 7、变化度 4（最稳定）；4-Color Tablet Flex 槽多、弹性大 → 偏离度 25、变化度 15（相对高）；均落在温和区间，不再出现旧 D99 的虚高 90+。
- **跨区间平均偏离度**趋势正确（1w ≤ 4w ≤ 12w ≈ 36w）：
  * Selesnya Offense：1w=11, 4w=13, 12w=15, 36w=15
  * Izzet Prowess：1w=11, 4w=10, 12w=15, 36w=16
  * Jeskai Lessons：1w=9, 4w=9, 12w=10, 36w=10
- 关键校验案例：曾报 94 分的 4-Color Tablet（_Batutinha_ 那副），绝对刻度下降到 **40 分**，符合"成型牌只改了地基和几张 Flex"的体感。

### 6.10 前端实现（index.html，已落地）
- 移除旧版 Overall/High-score 切换；展开区改架空平均（默认）/ 实际典型两 tab，`bindAvgToggle` 每次右栏重渲染后重新绑定按钮、从 `dataset.mode` 读模式（修复"切到高分后无法切回"bug）。
- `filterDiff` 过滤张数差 <1 的卡（DIFF_MIN=1）；`deviationHtml` 只渲染非空 fewer/more。
- `recentChangeHtml` 固定于 tab 与 Core 之间，依 `recent_change_reason`（recent/prior/nobase）选 i18n 文案（change_note_recent / change_note_prior / change_note_nobase）。
- i18n：`t()` 用 `!== undefined` 区分缺 key 与空串；已加 Core/Flex、tab 名、近期变化度、样本不足文案等键。
- ⚠️ 前端展示的偏离度已是后端算好的 0~100 绝对刻度值，前端不做归一化，切换 D99→绝对刻度对前端透明、无需改动。

---

## 七、模块三：数据统计（MTGO，阶段一已完成 —— stats_standard.py）

### 7.1 目标与范围
基于分类结果计算各套牌的流行度与强度指标，供网页展示。MTGO 只放出前 32 牌表，整体占比不准，故**不用整体占比**，改用高分/八强指标（人少的赛事高胜几乎 100% 收录、八强必然收录）。MTGO 与 melee 数据分开处理展示，互不混合。MTGO 只放出八强淘汰赛对阵结果（一赛制一周约 42 场对局，太少），故不做对阵矩阵，只做宏观指标；矩阵留给 melee（二期）。

### 7.2 核心指标
- **高分占比**：达高分门槛的牌中该套牌占比（分母=全部高分牌数）。
- **八强占比**：final_rank≤8 的牌中该套牌占比（分母=全部八强牌数）。
- **转化率（conversion）**：八强计数/高胜计数，衡量强度；高分数为 0 时输出 null（前端 N/A）。
- **原始计数**：保留高分/八强/总计数。
- 占比反映流行、转化率反映强度（实测 4-Color Tablet 数量少但转化率高、Izzet Prowess 数量多转化率低，能区分"流行"与"强"）。

### 7.3 Unknown 处理
Unknown 计入分母，标为 new/rogue decks。上线前尽量完善规则减少 Unknown。

### 7.4 高分门槛
以瑞士轮积分（每胜 3 分，无平局）衡量，melee 平局以积分等效计。统一公式：

    threshold = (floor(rounds × 1.5 / 3) + 1) × 3

判定 `swiss_score ≥ threshold`。各轮次门槛：5轮→9，6轮→12，7轮→12，8轮→15，9轮→15。仅基于积分，兼容 melee 平局。

### 7.5 轮数判定（player_count 查表法）
MTGO 不提供轮数字段，用 player_count 查官方对照表（"最高分反推"不可靠，全场无满分时会低估）。

| 报名人数 | 轮数 |
| --- | --- |
| 8 | 3 |
| 9–16 | 4 |
| 17–32 | 5 |
| 33–64 | 6 |
| 65–128 | 7 |
| 129–212 | 8 |
| 213–384 | 9 |
| 385–672 | 10 |

规律：人数每翻倍约加一轮，超表按翻倍外推。**Challenge 32/64/96 是奖励规模档位（最低报名门槛），不是固定轮数，均"按 attendance 定瑞士轮再切 Top 8"，故赛事名数字不能推轮数**（如报名 78 人的 Challenge 32 实跑 7 轮）。不抓 Preliminary（固定 4 轮无八强），故无需固定轮数特判。melee 直接提供轮数字段，无需反推。

### 7.6 时间切片
预计算滚动区间：最近 1/4/12/36 周，各输出 JSON。终点为"最近一个已结束的完整周"（判定：该周周日 < 今天）。每副牌按 starttime 归入自然周（周一到周日，周一日期为该周标识）。**补 4 月数据后，12 周档已真正填满**（此前仅约 9 周，12w/36w 曾等于全部数据）。⚠️ 前端须标出各区间实际起止日期，见 8.7 第 5 条。

### 7.7 JSON 输出结构
输出到 `stats/standard/mtgo/`：`range_1/4/12/36w.json`（统计数字）+ **`decks_1/4/12/36w.json`（每套牌的牌表详情）** + `index.json`（索引，含全局 D99）。
- range 文件字段：format、source（"mtgo"）、period(type/start/end/weeks)、total_decks、total_high_score、total_top8、unknown_count、archetypes[]（按 count 降序，每项含 name/count/high_score_count/high_score_share/top8_count/top8_share/conversion，**外加 `avg_deviation`**：该套牌该区间平均向量对 4 周 base 的归一化偏离度，0~100，可 null）。
- **decks 文件结构（2026-07-05 更新，平均牌表/偏离度/近期变化度全部落地）**：format/source/period + `decks` 对象（键为套牌名），每套牌含：
  * `best_deck`：最佳牌表（player/final_rank/swiss_score/player_count/starttime/main_deck[]/side_deck[]），样本达标时额外含 `deviation`（单副偏离度 0~100，原 deviation_percentile 改名）与 `deviation_diff`（{fewer,more}，各项 name/deck_qty/typical_qty；前端只显示张数差 ≥1 的项）。
  * `average_deck`：{ `sample_size`（4 周 base 样本数）, `medoid`（实际典型牌表，同 best_deck 牌表格式，样本不足为 null）, `core`（[{name, mean_qty}] 出现率 ≥0.8）, `flex`（[{name, mean_qty}] 出现率 <0.8）, `recent_change`（近期变化度 0~100 或 null）, `recent_change_reason`（null / "recent" / "prior" / "nobase"，用于前端选样本不足文案） }。样本不足（<8）时 medoid/core/flex 空、recent_change_reason="nobase"。
  **拆两文件理由**：range 文件小、首屏快加载；decks 文件大、用户点击套牌名时才 fetch。
- ⚠️ **旧版 average_deck 的 overall/high_score 双 medoid 结构已废弃**，替换为上述 medoid + core + flex + recent_change 结构。

### 7.8 最佳牌表选择逻辑（pick_best_deck，阶段一完成）
"示例牌表"需求：点击套牌名看到该区间内**战绩最好**的牌表。三级排序选出 best_deck：
1. final_rank 最小（瑞士轮/最终排名最高）
2. 并列时 player_count 最大（人数最多的场次）
3. 再并列时 starttime 最近
实现：process_event 的每条 record 额外保留 final_rank / player_count / starttime / main_deck / side_deck（备牌来源字段是 **sideboard**，内部键统一叫 side_deck）；pick_best_deck 用 `min(key=(final_rank, -player_count, -时间序))` 选出。已验证：4-Color Tablet 选到 rank 1 / 176 人场次，Selesnya Offense 选到 rank 1 / 36 人场次，均正确。

### 7.9 合并同名卡（merge_cards，完成）
MTGO 原始牌表同一张卡可能拆成多条（如 Jeskai Revelation 出现两次各 2 张）。merge_cards 在生成 decks JSON 前把同名卡 qty 累加、按名排序，得到干净牌表（主牌 60、备牌 15）。⚠️ **merge_cards 内必须调用 normalize_name**（应用别名表），否则占位名/正式名不会合并、且前端卡图失败（见第四章 Leyline Weaver 教训）。

### 7.10 字段结构确认（牌手对象）
牌手对象顶层字段：player, loginid, swiss_rank, swiss_score, swiss_wins, opp_match_win_pct, game_win_pct, final_rank, **main_deck**, **sideboard**。卡条目字段：**name**（卡名）、**qty**（数量）。注意主牌列表长度是"卡种数"（如 16）不是总张数，总张数须 sum(qty) 得 60。

### 7.11 关键提醒
复用现有分类逻辑；计算前统一 to_int；占比与原始计数并存；Unknown 计入分母；stats/ 产物纳入 git 供 Pages 发布；merge_cards 与 deck_to_counts 都要走 normalize_name 保持卡名口径一致。偏离度/平均牌表/近期变化度全部基于固定 4 周 base（BASE_WEEKS=4）与全局单一 D99（DEV_PERCENTILE=99），与用户查询区间解耦。

### 7.12 数据来源与日期
轮数对照表：MTGO 官方 Events & Formats（https://www.mtgo.com/en/mtgo/events）。Challenge 档位：MTGO Preliminaries and Format Challenges（https://www.mtgo.com/premier-play-prelims-and-format-challenges，96 档为 2026-06-23 新增）。

---

## 八、模块四：网页展示与上线（阶段二已完成，进入阶段三）

### 8.1 总体开发顺序
"垂直切一刀，先做出能用的东西"，三阶段：
- **阶段一：统计模块（纯 Python，产出 JSON）** —— ✅ 完成（第七章）。
- **阶段二：前端骨架（浏览器能看到数据、能交互）** —— ✅ 完成（index.html，见 8.3），且平均牌表/偏离度/近期变化度已落地。
- **阶段三：自动化 + 上线** —— 🔨 **下一步**。开 GitHub Pages 发布公开网址；把 classify+stats 接进 Actions 每日自动重算并 commit（见 8.5）。

后续：standard 跑通后复制流程到其他赛制（换数据目录和规则文件，架构不动）；最后啃 melee（Cloudflare + 登录 + 对阵矩阵，二期）。

### 8.2 上线方式：静态网站 + GitHub Pages
数据每天更新一次、只读、无登录、所有用户看同一份预计算结果，故**不需要服务器/后端/数据库**，用静态网站即可，免费近零运维。Actions 生成 JSON 并 commit → Pages 发布网页+JSON → 用户浏览器加载 JSON 本地渲染。与现有架构无缝衔接。"静态 ≠ 不能交互"：时间档切换靠预算好的多份 JSON，前端点按钮加载对应文件，体验等同动态查询。

### 8.3 前端 index.html 当前能力（阶段二成果 + 平均牌表/偏离度/近期变化度已落地，均已本地验证）
单页 HTML + CDN 引入 Chart.js（4.4.1）。放项目**根目录**，fetch 相对路径 `stats/${currentFormat}/mtgo/...`。功能：
- **顶部赛制 Tab**：目前仅 Standard 可用，Pioneer/Modern 置灰禁用（预留，FORMATS 常量控制）。
- **时间区间按钮**：1/4/12/36 周（RANGES 常量），点击切换 currentRange 重新加载。
- **横向分组柱状图**（Chart.js，indexAxis:"y"）：每套牌两根柱（高分占比蓝 #3b6ea5 / 八强占比橙 #e0973b），按高分占比降序。**只显示高分占比 ≥ 2%（CHART_MIN_SHARE=0.02）的套牌**，其余合并为一条 **"Others"** 累加显示在最下方（高分/八强各自累加）。图表高度随套牌数自适应。
- **数据表格**：6 列——套牌名、高分数量、高分占比、八强数量、八强占比、转化率（**不含总数量列**，因多为 32 人赛事总数意义不大）。默认按高分占比降序，列标题可点击切换升降序（▼/▲）。**隐藏高分数量为 0 的套牌**（renderTable 里 `.filter(a=> a.high_score_count > 0)`）。表格无 2% 过滤（长尾套牌在表格里可见）。**平均偏离度/近期变化度不进表格**（见 6.7）。
- **行内展开牌表详情**：点击套牌名，在该行下方插入跨列展开区（deck-row）。**左侧 best_deck**（player/rank/score/日期 + 主牌 + 备牌 + 单副偏离度 + 逐卡差异拆解"少带/多带"，仅显示张数差 ≥1 的卡）。**右侧 average_deck 区**：两个 tab——「架空平均牌表（默认）」显示 Core/Flex 两栏 + 均值张数；「实际典型牌表」显示 medoid 主牌+备牌；tab 与 Core 之间固定显示「近期构筑变化度」行（有值显分数，无值按 recent_change_reason 显文案）。切换按钮每次重渲染后由 bindAvgToggle 重新绑定（修复"切到高分后无法切回"bug）。最佳/平均**宽屏并排、窄屏自动上下**（flex-wrap）。关闭按钮 ✕ 在右上角。卡列表无圆点。
- **单卡交互**：卡名是链接，点击跳转 Scryfall 精确查询（`https://scryfall.com/search?q=!"卡名"`）；**鼠标悬停显示 Scryfall 卡图**（api.scryfall.com/cards/named?exact=...&format=image），跟随光标、near 边缘翻转、带缓存、移开消失。卡图/跳转都走别名后的正式名，故 Leyline Weaver→Spider Manifestation 后卡图正常。
- **中英双语 i18n 骨架**：lang 变量（zh/en）+ I18N 字典 + t(key)。`t()` 用 `!== undefined` 区分缺 key 与空串。UI 文本全部走 t()，含 Core/Flex、两 tab 名、近期变化度、三种样本不足文案（change_note_recent / change_note_prior / change_note_nobase）等键。**卡名和套牌名预留 cardName(en)/archetypeName(en) 占位函数**（当前返回原文英文），将来接翻译表即可无缝切换（见 8.4）。语言切换按钮在右上。
- **防缓存**：fetch URL 加 `?v=${Date.now()}`（range 和 decks 两处都加）。⚠️ 开发期这样每次都不走缓存最省心；**上线时建议改用 index.json 的 generated 时间戳做版本号**（数据没变时命中缓存、变了立刻更新）。

### 8.4 多语言（i18n）方案（已定，待阶段三或之后实现）
- 三层翻译：① UI 文本——前端 I18N 字典（已就位）；② 套牌名——需维护中英对照表（约 50~76 条，随规则增长；**用户已有对照表，将来上传**）；③ 卡名——参考半官方库 **HeliumOctahelide/magic-cards-zhs**（英文来自 Scryfall，中文来自官方+志愿者，数据以 GitHub Release 附件形式发布，最新 data-2026-06-11 约 75MB tar.gz；配套浏览站 sbwsz.com "大学院废墟"；卡字段英文名/中文名待下载样本确认）。
- ⚠️ **架构原则：绝不让前端加载整个卡库（几万张 75MB）**。而是在**后端构建时**只提取"本项目数据实际出现的卡"（几百张）生成精简的 `card_names_zh.json`（几十 KB），随 stats 发布，前端只加载这个小表。套牌名同理做 `archetype_names_zh.json`。
- **无缝对接方式**：前端翻译逻辑集中在 cardName()/archetypeName()，最初返回英文，将来函数内部改为查静态表即可，页面代码不用动。**不建议前端实时调用 sbwsz API**（性能、跨域 CORS、外部服务不稳定），翻译应在后端构建阶段批量做成静态表。

### 8.5 阶段三待办（下一步）
1. **开 GitHub Pages**：仓库 Settings → Pages → Source 选 "Deploy from a branch" → Branch **master** / 目录 **/(root)** → 保存。等 1-2 分钟得网址（形如 https://jacelber.github.io/mtgo-data/）。因 index.html 在根目录、stats/ 也在，路径对得上，理论直接可用。验收：访问网址能打开、数据能加载、图表/表格/牌表/卡图/平均牌表/偏离度/近期变化度都正常。
2. **（可选，推荐）云端自动更新数据**：现 scrape.yml 只跑爬虫。要让网站每天自动刷新，需在 workflow 爬虫后加：`pip install pyyaml` → 跑 `python stats_standard.py`（内部会调分类逻辑生成 JSON，含 base 包 + D99 + 平均牌表 + 偏离度 + 近期变化度）→ `git add stats/`。注意验证脚本在云端 ubuntu 环境路径/依赖正常。做完则每天中午自动重算发布，无需本地手动。

### 8.6 未来盈利（流量广告）注意事项
静态网站可放广告（嵌 JS 即可）。现实门槛（流量起来才需处理）：AdSense 等通常要独立域名（一年几十到百余元）、原创内容/流量/隐私政策；GitHub Pages 免费版不鼓励纯商业广告站，认真盈利后更稳妥是迁到 Cloudflare Pages / Netlify（迁移成本近零）。现阶段唯一顺手可做：前端预留 1-2 个广告位空区块（不做也可后补）。广告是"有流量之后"的后期事，不影响当前设计。

### 8.7 用户体验补足清单（2026-07-03 评审 → 2026-07-05 落地进度）

从**用户视角**复审设计后梳理出 8 项体验不足，多为展示层（前端+文案）补足，不动统计内核。本轮平均牌表/偏离度落地时已完成大部分，进度标注如下。按价值排序：

**高价值（把偏离度从"孤立数字"变成"能学到东西的洞察"）**
1. ✅ **偏离度配战绩并列展示**（已落地）。best_deck 展开区里偏离度与 final_rank / swiss_score 并列，并附文案"偏离度衡量与主流构筑的差异，不代表强弱"。
2. ✅ **逐卡差异拆解**（已落地，核心价值）。best_deck 展开区显示"比典型少带 X / 多带 Y"，按权重排序，仅显示张数差 ≥1 的卡（DIFF_MIN=1，滤掉小数波动）。

**低成本高收益（顺手就做）**
3. ✅ **"Average Deck"改名**（已落地）。改为"架空平均牌表 / 实际典型牌表"两 tab，避免误解为逐卡平均或困惑署玩家名。
4. ✅ **样本不足给可读说明**（已落地）。近期变化度按 recent_change_reason 显"本周样本不足 / 缺少历史构筑数据 / 4 周样本不足暂无变化度"；平均牌表样本不足显对应说明，不留白。
5. 🔨 **时间区间标出实际起止日期**（待做，D 项）。显示 period.start–period.end（JSON 已有字段），如"最近 1 周(6/23–6/29)"。

**锦上添花（可上线后看反馈再补）**
6. 🔨 **Others 可展开**（待做，D 项）。点击图表 Others 列出被合并套牌及占比。
7. 🔨 **每个指标标签加悬停/点击 tooltip 显示定义**（待做，D 项）。就地解释高分占比/八强占比/转化率/偏离度。实现要点：
   - 内容两层——先人话再精确定义；点破"哪个是流行度、哪个是强度"。
   - 覆盖表格五个数值列标题、图表两个图例、偏离度。
   - 文案集中存 i18n 字典（tip_high_score_share / tip_conversion 等），支持中英双语。
   - ⚠️ 移动端无 hover：配小 ⓘ 图标点击也能弹；须与既有点击交互（表头排序、套牌名展开）错开。
   - ⚠️ 与既有"悬停卡名显示卡图"共存：用不同 CSS 类隔开。
8. 🔨 **极简指标引导**（待做，可选，D 项）。若第 7 条 tooltip 已充分则可省。

**剩余待做（D 项，本轮之后）**：第 5（区间日期标注）、第 6（Others 展开）、第 7（指标 tooltip）、第 8（极简引导）。第 1~4 已随本轮平均牌表/偏离度落地完成。

---

## 九、下次继续的待办（DOWN TO HERE）

**2026-07-02 完成**：
- 补齐 2026 年 4 月全赛制数据（batch_mtgo.py 改 USE_RECENT_MONTHS=False 抓 4 月，跑完改回）；standard 数据从 71 场/2272 副增至 **103 场/3296 副**，近 12 周填满。
- 分类规则从 58 条扩到 **76 条，整体分类率 98.2%**；用 dump_unknown_highperf.py 专项清理，**高分/八强段 Unknown 压到 0.7%**（达成 <1% 目标）。确立"色组兜底规则置于 YAML 末尾"策略。修复 Sultai Control 签名卡选错问题。
- 阶段一补完牌表详情：pick_best_deck（三级排序选最佳牌表）+ merge_cards（合并同名卡，含别名归一）+ decks_Xw.json 输出（average_deck 留 null 占位）。
- **阶段二前端完成**：index.html 具备赛制 Tab、时间档切换、横向双指标柱状图（≥2% 显示 + Others 聚合）、可排序数据表（隐藏 0 高分）、行内展开牌表详情（最佳/平均并排）、单卡 Scryfall 跳转 + 悬停卡图、中英 i18n 骨架、防缓存。
- 修复 Leyline Weaver → Spider Manifestation 别名（贯穿分类 + merge_cards + 卡图）。
- **首次本地↔云端合并推送成功**：走通 commit→pull --rebase→解决 fetched.txt 冲突→rebase --continue→push 全流程（184 文件），index.html 首次纳入仓库。

**2026-07-03 完成**：
- **平均牌表 & 偏离度统计设计初版定稿**（纯设计推进，当时为双 medoid 方案）。
- **用户体验补足清单 8 项定稿（见 8.7）**，从用户视角复审设计。

**2026-07-04 ~ 07-05 完成（本轮，设计重构 + 全面落地）**：
- **设计重构（见第六章）**：把旧版"Overall/High-score 双 medoid + deviation_percentile"重构为最终方案——
  * 固定 4 周 base（BASE_WEEKS=4）作为一切偏离度基准，与查询区间解耦；全局单一 D99（DEV_PERCENTILE=99，实测 19.55）归一化。
  * 架空平均牌表按出现率分 **Core（≥0.8）/ Flex（<0.8）**；实际典型牌表 = 离均值最近的 medoid。
  * 偏离度 **改名 deviation**（0~100）；新增**区间平均偏离度 avg_deviation**（"先平均、再算距离"，测中心漂移，不进表格）；新增**近期变化度 recent_change**（本周 vs 前 4 周，RECENT_MIN=3，null 时用 recent_change_reason 枚举，不进表格、放展开区 tab 与 Core 之间）。
  * 距离统一加权 L1（权重=出现率）、初版仅主牌。
- **后端落地（stats_standard.py）**：新增 deck_vector / mean_vector / appearance_rates / split_core_flex / weighted_l1 / normalize_dev / deck_diff / pick_medoid / build_base_pack / recent_change_for_arch；改写 build_range（输出 avg_deviation）、build_decks（best_deck.deviation + deviation_diff，average_deck 改为 medoid+core+flex+recent_change+recent_change_reason）、build_all_stats（先建 base+D99，index.json 写 D99）。自测通过，15 副达标套牌三指标区分良性（见 6.9）。
- **前端落地（index.html）**：移除双 medoid 切换；展开区改架空平均（默认）/ 实际典型两 tab + bindAvgToggle 修复切换 bug；filterDiff 过滤张数差 <1；deviationHtml 只渲非空；recentChangeHtml 固定于 tab 与 Core 之间、按 reason 选文案；t() 用 !==undefined 修复空串键；新增 Core/Flex/tab/变化度/样本不足等 i18n 键。
- **用户体验清单 1~4 项随本轮落地完成**（偏离度配战绩、逐卡差异拆解、Average Deck 改名、样本不足给说明）。
- **本轮同步更新本项目笔记文档**（标题日期、模块状态、第五/六/七/八/九章）。

**下一步：阶段三（部署上线）**——见 8.5：
1. 开 GitHub Pages（Settings→Pages→master / root），得公开网址，验收线上可访问、数据/图表/牌表/卡图/平均牌表/偏离度/近期变化度正常。
2. （可选推荐）把 stats 生成接进 scrape.yml（加 pyyaml + 跑 stats_standard.py + git add stats/），实现每日全自动更新。

**剩余 D 项（展示层补足，见 8.7）**：
- 时间区间标出实际起止日期（8.7 第 5 条）。
- Others 可展开（8.7 第 6 条）。
- 指标标签 tooltip 定义 + 移动端 ⓘ 图标（8.7 第 7 条）。
- 极简指标引导（8.7 第 8 条，可选）。

**并行可选**：
- 多语言落地（8.4）：用户上传套牌名中英对照表后，从 magic-cards-zhs 提取"仅本项目出现的卡"生成 card_names_zh.json（几十 KB）+ archetype_names 中英表，接上前端 cardName/archetypeName 占位函数。
- 分类继续打磨（边际收益递减）：剩余 58 副整体 Unknown 多为低战绩长尾，可上线后慢慢补；避免为单副牌写过拟合规则。
- "特殊度发现"分类维护机制（第五章）：复用第六章已落地的均值向量 + 加权 L1 距离，单独输出"每副牌偏离度排行"供人工审规则。

**后续（二期）**：复制流程到其他赛制（换 DATA_DIR + 规则文件，前端 FORMATS 解禁对应 Tab）→ melee.gg（Cloudflare + 登录抓取 + 对阵矩阵）。

---

## 十、关于用 Claude Code 推进本项目（2026-07-03 评估）
- **能做好**：实现文档中已明确定义的功能（第六章数学、8.7 前端展示补足、多语言静态表生成等）；读懂脚本 import 关系、JSON 格式；跑本地 Python 脚本自查逻辑/语法错误并修复。本文档信息密度适合直接作为输入。
- **做不了 / 需人把关的三处**：
  1. **领域判断**：分类规则对不对、偏离度/近期变化度排序符不符合 MTG 直觉、CORE_RATE/阈值取值合不合理——须由玩家（你）拍板，Claude Code 只能算数字。
  2. **线上操作**：开 GitHub Pages、改 Actions 写权限、真实大量抓 MTGO 数据——在 GitHub 网页/云端环境操作，它碰不到。
  3. **视觉验证**：前端渲染效果（卡图、图表布局、tab 切换、tooltip 移动端表现）——它能起本地 server 但看不到浏览器画面，须你 Ctrl+Shift+R 亲验。
- **协作模式**：给它库+文档，让它按第九章任务清单一块块实现（写码+单测+自查），你负责领域判断、线上操作、视觉验证。给任务时**明确"当前做哪一块"**（文档覆盖全项目，不聚焦会不知从何下手）。
- ⚠️ 部分产物涉及大量数据抓取，Claude Code 默认不应自行大规模爬取 MTGO；数据仍走既有 Actions 每日抓取机制。

## 第七章 前端术语说明（tooltip）— 进行中

### 7.1 目标与交互设计
为前端各标签中出现的专有名词提供用户说明。交互方式采用混合方案：
表头等位置加圆圈 i 图标（ⓘ），桌面端 hover 显示、移动端点击显示，
两端兼顾。弹出内容用自写的轻量浮层组件（绝对定位 div，支持多行中文），
不用原生 title。文案走 i18n，每条一个 `xxx_tip` 键，zh 先写，
en 留空时 fallback 到中文（与解说同一套策略）。

### 7.2 覆盖的术语清单
场均分、转化率、高分数量、高分占比、八强数量、八强占比、
偏离度（单副）、区间平均偏离度、近期变化度、Core 卡、Flex 卡、
抽象典型、实际典型、每周精选、构筑变化、新增套牌。

### 7.3 文案草稿（待管理者定稿）
- **场均分**：选手在瑞士轮每轮的平均得分，按总积分除以理论总轮数计算，
  范围 0–3 分。分数越高代表该套牌整体战绩越好。（3 分为满分，约等于全胜。）
- **高分数量**：该套牌中打出高分成绩的牌手数量。高分门槛随赛事轮数变化
  （如 6 轮赛事需 12 分以上）。
- **高分占比**：高分牌手占该套牌总数的比例，反映这套牌"打出好成绩"的稳定程度。
- **八强数量**：该套牌进入赛事八强（前 8 名）的牌手数量。
- **八强占比**：八强牌手占该套牌总数的比例。
- **转化率**：该套牌中，打出高分的牌手里最终进入八强的比例，衡量这套牌从
  "打得好"到"真正夺冠竞争力"的转化能力。
- **偏离度**：某一副牌相比这套牌的"基准典型构筑"的改动幅度，0 分代表几乎
  完全一致，接近 100 代表改动极大。数值越高说明这副牌的构筑越有个性。
- **区间平均偏离度**：所选时间区间内，这套牌所有牌表相对基准典型构筑的平均
  改动幅度，反映整套牌在这段时间的构筑分歧程度。
- **近期变化度**：本周该套牌的主流构筑与前 4 周相比的改动幅度。数值高说明
  这套牌最近正在明显调整。
- **Core 卡（核心卡）**：这套牌里几乎每副都会出现的卡（出现率 ≥80%），
  构成套牌的固定骨架。
- **Flex 卡（弹性卡）**：出现率不到 80% 的卡，属于选手可自由调整的部分，
  往往体现构筑差异。
- **抽象典型**：由这套牌近 4 周所有牌表平均得出的"理论典型构筑"，各卡张数
  可能带小数，仅作为比较基准。
- **实际典型**：在真实高胜率牌表中，与"抽象典型"最接近的一副实际存在的牌表，
  可直接照着组。
- **每周精选**：每周从上周成绩优秀的牌表中人工挑选、附带解说的推荐牌表列表。
- **构筑变化**：现有套牌中，本周构筑相比近期平均有明显调整、且取得八强以上
  成绩的牌表。
- **新增套牌**：本周首次出现的新套牌分类中，取得八强以上成绩的牌表。

### 7.4 进度与待办
- [已定] 交互混合方案、浮层组件自写、i18n 键策略、术语清单、文案由管理者定稿。
- [进行中] 管理者对照实际界面修改文案。
- [待做] tooltip 浮层组件 CSS + JS、各表头/标签挂载点、i18n `xxx_tip` 键接入。

### 7.5 本次会话其他进度
- 前端 index.html 删除了残留的重复 `tablePanel` 占位块（"（数据表格待接入）"
  在两个 tab 底部重复出现的 bug），修复了 id 重复问题。
- 每周精选 pickup 前端链路验证通过：index.json → 往期列表 → 周详情展开正常。
- 同步问题记录：957aae0 提交昨日未成功 push，本次补推。
