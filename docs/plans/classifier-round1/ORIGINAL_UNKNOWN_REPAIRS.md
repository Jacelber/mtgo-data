# 原基线 Unknown：本轮续作

## 已完成的局部修正

- Modern Amalia Combo：Amalia 的回血触发探索与 Wildgrowth Walker 的探索触发回血构成组合技核心。保留主牌两种核心各至少 3 张，集中到父类；Guide of Souls／Ocelot Pride／Springheart Nantuko 是其中一种辅助包，不再强制三者同时存在。已有 Guide 路线仍命中，另一副 Lunarch Veteran／Prosperous Innkeeper／Chord／Company 路线恢复原有父类。
- Modern Dimir Mill：保留 Hedron Crab ≥2；磨牌组件接受原 Archive Trap ≥3，或 Fractured Sanity ≥3＋Glimpse the Unthinkable ≥3。没有统一降低门槛；仅有一类替代磨牌组件、缺少螃蟹仍不能借本分支命中。
- Standard Azorius Control：Theorist 分支保留 Countersculpt、The Theorist、No More Lies、Day of Judgment、Hallowed Fountain 与正常 WU 颜色；取消强制 Jace's Machinations。移除任一保留的正向控制条件仍不能命中本分支。

两项 Modern 修正回放仅恢复 2 条原 Unknown，其余 18,828 条状态／身份／匹配不变。Standard 的控制修正仅恢复 12856631:30；同批 Kona 变化另列如下。完整来源保存在 `tests/fixtures/classifier_round1_original_unknown_repairs.json`。

## 已批准的 Kona 全知

Owner 批准 sultai（Sultai Kona Omniscience／苏勒台全知）与 four-color（Four-Color Kona Omniscience／四色全知）。父类共同核心为主牌 Kona ≥3、Omniscience ≥3；当前既有 Uthros ≥3 驻扎路线通过同一 YAML anchor 复用，未据此声称其他启用路线必然不属于该家族。

五种颜色分支接入共享主备牌正常施放原则，移除 Ashling 或具体白地名代替颜色的判断。两条正常红牌＋红源的旧 Simic 纠正为 Temur；一条备牌白牌＋Plains 的旧 Simic 纠正为 Bant；一条普通白源在备牌的旧 Temur 归批准的四色。原有 Bant 保持归属，仅合并重复地名分支造成规则 ID 更新。两条主牌 3＋3、正常 Extrapolate 的牌表归 Sultai；它们的黑源包括 Watery Grave 3 与 Susur Secundi 3，不能漏掉后者。

## 已批准的标准红黑鬼怪

新增 rakdos-goblins（Rakdos Goblins／红黑鬼怪）。父类共同条件分为两组：主牌 Boggart Cursecrafter 或 Boggart Mischief ≥3；主牌 Howlsquad Heavy 或 Mudbutton Cursetosser ≥3。分别表达鬼怪死亡收益与部族协同，各组可替换，不强制某个终结手段；分支只要求正常 BR 用色。

真实 60＋15、所有替代组合、缺少核心、只有五色支持不计黑、普通备牌黑源可计黑、替换具体地名与名称／前端 mana 均已验证。全量仅 12856631:31 从 Unknown 进入该父类，其余 7,147 条不变。

## 验证与边界

初次检查拦截了新增规则的两处格式错误（any 的分支结构、空条件格式）；按现有 schema 修正，没有放松校验。Kona 的去除黑源测试也补齐了 Susur Secundi，保持原“没有普通黑源不计黑”断言。随后 89 项受影响检查通过；四色全知续作 13 项通过；红黑鬼怪续作 31 项通过，各组存在重叠，不相加。Ruff 检查通过。原始输入 SHA、记录集合和冻结基线不改。

增量证据位于 `/workspace/scratch/classifier-round1/`：`modern-original-unknown-repairs-incremental-proof.json`、`standard-original-unknown-repairs-incremental-proof.json`、`four-color-kona-incremental-proof.json`、`rakdos-goblins-incremental-proof.json`。四赛制最新回放摘要已核对匹配当前规则和共享机制。

当前 Standard 仅 1 条 intentional Unknown（原有效登记）；Pioneer 0；Pauper 1 条已确认 intentional Unknown；Modern 20 条 Unknown 中 6 条基本地记录、1 条纯红鼠类构筑、2 条矮人与 1 条红蓝元素构筑、3 条散牌及 3 条主题构筑已确认保留，最后 4 条也按已核实历史和 Owner 指示保留，现无未处理 Unknown。发布暂停；四个赛制均已完成本版派生产物同步与验证，详见 [交付记录](DELIVERY_PROGRESS.md)。
