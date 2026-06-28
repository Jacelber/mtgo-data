# MTG 数据分析系统 — 项目笔记

最后更新：2026-06-28

## 一、项目总目标
搭建一个自动化系统，爬取 MTGO 官方赛事数据（以及未来的 melee.gg 实体赛数据），
对牌表自动分类，统计各套牌类型的胜率、瑞士轮表现、八强占比等，最终以网页形式
展示给其他用户查看。操作者无编程基础，全程在 AI 协助下用 Python 实现，工具尽量
免费。

## 二、系统四大模块及状态
1. 数据抓取（MTGO）—— ✅ 已完成并实现云端自动化
2. 牌表分类 —— 🔨 进行中（基础分类已跑通，正在打磨）
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
- MTGO 有时返回状态码 200 但页面残缺，需"下载+解析"作为整体重试
  （最多 4 轮，每轮间隔 15 秒）。
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
- classify_standard.py —— 分类脚本（模块二，进行中）

### batch_mtgo.py 当前配置
- 默认抓"最近两个月"（当月+上月），跨年自动处理（1月→上年12月）。
- 数据存到 data/<格式>/<赛事描述>_<event_id>.json
- fetched.txt 记录已抓链接，自动去重跳过。
- 支持的格式：standard, legacy, pioneer, pauper, vintage, modern

### 已抓数据现状
- 约 340 个赛事 JSON，覆盖六个格式，2026 年 5 月和 6 月。
- 数据已 git commit + push 到云端仓库。

### 自动化（已打通）
- GitHub 仓库：https://github.com/Jacelber/mtgo-data
- GitHub 账号用户名：Jacelber（也写作 jacelber）
- GitHub Actions 配置文件：.github/workflows/scrape.yml
- 定时：每天 UTC 04:00 = 北京时间中午 12:00 运行（cron: '0 4 * * *'）
- 关键修复：之前云端推送报 403，是因为 Actions 默认无写权限。
  解决：仓库 Settings → Actions → General → Workflow permissions
  改为 "Read and write permissions"。现已确认 workflow 运行变绿成功。
- "Node.js 20 is deprecated" 是黄色警告，可忽略，不影响运行。

### Git / 仓库注意事项
- 本地 Git 已配置：user.name=jacelber, user.email=jacelber@gmail.com
- .gitignore 已忽略：page_source.html, list_page.html, __pycache__/,
  根目录的 /*.json（但 data/ 下的 json 要保留，所以用的是 /*.json 只忽略根层）,
  以及 MTGOFormatData/（别人的规则库，不纳入自己仓库）
- 日常更新代码流程：先 git pull（同步云端自动抓的数据，重要！）→
  本地编辑测试 → git add . → git commit -m "说明" → git push
- 主要在本地 VS Code 改代码，网页编辑只用于极小确定的改动。

### 存储与费用
- 公开仓库 + Actions 完全免费、不限分钟数。
- 仓库建议 ≤1GB，单文件 ≤100MB。当前数据约几 MiB，每年增长几十 MB，远低于上限。
- 只要账号和公开仓库存在，数据长期保存。

---

## 四、模块二：牌表分类（进行中）

### 采用方案
基于 Badaro 的规则库 MTGOFormatData（已 git clone 到本地
D:\dl\crawlerpj\MTGOFormatData，已加入 .gitignore 不纳入自己仓库）。

### Badaro 规则结构（Standard 在 MTGOFormatData/Formats/Standard/）
- Archetypes/ 文件夹：每个套牌一个 json，含 Conditions（所有条件都满足才匹配）
  和可选的 Variants（变体，匹配大类后再细分）。
- Fallbacks/ 文件夹：兜底规则，含 CommonCards 列表；未精确匹配的牌表
  按共享卡片比例归入最相似大类（阈值 ≥10%）。
- metas.json：按时间段划分赛季。
- color_overrides.json：手动指定某些地的颜色。

### 条件类型（注意 Badaro 拼写不统一，代码已统一转小写兼容）
InMainboard, InSideboard, OneOrMore(In)Mainboard/Sideboard,
TwoOrMore..., DoesNotContain, DoesNotContainMainboard/Sideboard

### 已修复的两个 bug
1. 条件类型大小写不一致：Badaro 写成 "OneorMore"（小写or），代码原来判断
   "OneOrMore"，导致大批规则失效。已改为 ctype.lower() 统一比较。
2. ArchivedProwess.json 有 trailing comma（变体 Conditions 数组后多余逗号），
   导致 JSON 解析失败被跳过。已手动删除多余逗号修复。

### classify_standard.py 当前能力
- 加载所有 archetype + fallback 规则（坏文件自动跳过并报告）。
- 把每副牌整理成主牌/备牌卡名集合。
- 先精确匹配 → 检查变体 → fallback → 否则标 Unknown。
- 输出分类报告（各类数量/占比、总分类率）+ 把 Unknown 牌表导出到
  unknown_decks.txt 供人工审查。

### 最新分类结果（2144 副牌，2026年5-6月 standard）
- 总分类成功率 96.1%（含 fallback）
- 完全归不了类 Unknown：84 副（3.9%）
- 主要分类：Prowess 22.8%、Cub 10.4%、Landfall 9.6%、Lessons 8.8%、
  Jeskai Control 8.3%、Spellementals 7.9%、Excruciator 6.9%、
  Midrange(fallback) 4.8%、Momo 4.4% 等。
- 结论：Badaro Standard 规则虽然停在 2025年7月较旧，但骨架仍可用，
  96.1% 分类率说明不需要重写，只需少量补充。

### 重要发现
- Badaro 规则库 Standard 最新只更新到 2025年7月，比当前数据旧约一年。
- 变体（Variants）代码已加入且逻辑正确，但当前数据恰好没有套牌触发
  那些变体条件，所以输出没变化——这是正常的，不是 bug。

## 五、下次继续的待办（DOWN TO HERE）
1. 搞清楚两个内部代号对应什么套牌，确认分类正确并改成易懂的名字：
   - 打开 MTGOFormatData/Formats/Standard/Archetypes/Cub.json（10.4%，222副）
   - 打开 .../Archetypes/Momo.json（4.4%，94副）
   - 看条件卡判断对应现实哪套牌。
2. 扫一遍 unknown_decks.txt 里的 84 副 Unknown：
   - 看有没有反复出现的同类牌表（=新套牌，值得写新规则）
   - 还是五花八门各不相同（=可接受，标 Unknown 即可）
3. 完成分类打磨后，进入模块三：数据统计
   （胜率、瑞士轮分数、当周/上周/当月八强占比、瑞士轮胜率>50%套牌中的占比等）。

## 六、用户的"特殊度发现"构想（第二阶段维护机制）
用户提出的规则维护思路（已认可，待分类基础完成后实现）：
1. 计算近期同类套牌各单卡平均张数作为基准（平均<1张的单卡忽略）。
2. 用单副牌与基准比较，评价其构筑"特殊度"。
3. 列出特殊度高的牌表，人工评定是否需修改规则。
4. 改规则后重复，直到稳定。
本质是一套半自动、持续的每周规则维护流程（环境每周变，不是一次性收敛）。
参考工具：j6e archetype-cleaner（https://j6e.me/mtg-meta-analyzer/）。
