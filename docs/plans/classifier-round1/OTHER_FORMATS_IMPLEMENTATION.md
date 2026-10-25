# 其他赛制颜色接入：2026-10-24 开发记录

当前状态：共享颜色、已确认用途例外、父类共同条件及已定位的局部修正已接入本轮涉及的四个赛制。完整回放共 37,447 份牌表，Unknown 为 Modern 20、Standard 1、Pioneer 0、Pauper 1，均有适用处置，无待答分类问题。四个赛制本地产物均已同步并验证为 CURRENT；发布仍暂停，未提交或推送。最终差异见 [影响核对](IMPACT_REVIEW.md)，具体实现见 [原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md)，范围限制见 [维护清单](REMAINING_COLOR_WORK.md)。

以下为此前阶段记录，其中的“最新”与数量仅指相应阶段，以顶部链接为当前状态。

最新执行状态：本组历险用途例外、两张新增护身符用途、Standard Temur Prowess 与 Jeskai Looting 父类决定均已实施。红蓝／洁斯凯滤牌共享必要结构核心；本次 100 项受影响检查通过，标准 7,148 条回放只有已确认牌表 Unknown → Jeskai Looting 一项增量。严格颜色接入为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；标准当前 Unknown 26（较原冻结基线新增 21）。这组决定不再待答，更早待维护项继续保留。详见 [实现与剩余边界](FLING_EXCEPTION_IMPLEMENTATION.md)。下文此前数字属于阶段记录，尚未提交或发布。

最新 Owner 决定：保留原有共享颜色原则，Sell-Sword／Otter 使用局部用途例外。对应额外色源为零或一张时不因其相关卡面算混色，足量配置则计色；4 Blood Crypt 正例保留。未批准“至少两张”门槛，也不影响其他正常同色咒语。用途例外尚未接入生产；下文旧待答状态以 [历险用途方案](ADVENTURE_OPTIONS_AND_VALIDATION.md) 顶部最新确认为准。

Owner 要求正常推进其他三个赛制的实际修正，发布继续暂停。本轮已修改生产规则，不再将“旧结果没有漂移”当作新能力生效的证据。最新续作见 [ADVENTURE_OPTIONS_AND_VALIDATION.md](ADVENTURE_OPTIONS_AND_VALIDATION.md)：已修复 Multiversal Passage 来源识别、完成历险卡面用途能力与 385 条方案试算、补接入 Gruul Landfall、修复下文记录的旧 Pauper 验证问题。当前仍有业务边界，未同步或发布本版派生产物。

## 实际接入范围

- Standard：29 个父类，包含现有土地颜色标记分支、Dwarves、Manufacturing、Lifegain、Spider-Man、Landfall（含补充的 Gruul）和相关控制分支。
- Pauper：Dimir Control、Battle Screech、Packbeast Swarm、Golgari Gardens、Azorius Familiars，共 5 个父类。
- Pioneer：Lotus Scapeshift、Azorius Control、Izzet Prowess、Mono-Red Aggro、Izzet Phoenix、Rakdos Leyline、Boros Prowess、Temur Creativity、Gruul Creativity，共 9 个父类。

这些父类显式启用 `color_profile: default`，通过 `colors` 或 `color_subtypes` 实际筛选／选择归属；没有把所有旧语义标记悄悄改义。三个规则文件升级到 1.2 并绑定已有离线属性摘要。未全面重写 372 个父类，也未接入 Legacy。

明确的共同核心提到父类，例如 Manufacturing 的 Weapons Manufacturing 3＋United Battlefront 3，Lotus 的 Lotus Field＋Scapeshift＋Spelunking，Gardens 的 Khalni Garden 3＋Fanatical Offering 3。子类补充结构差异或颜色。保留 Lotus Field、Khalni Garden、Fabled Passage、野火桥地等有结构作用的地；删除只承担判色作用的具体地名。Dwarves、Lifegain、Spider-Man 和非 Learn Packbeast 路线共享颜色映射，Learn 仍用结构条件区分。

Standard Esper Control 复用已存在控制结构的 Deadly Cover-Up 与 Seam Rip 路线，以正常 WUB 用色识别两份旧误归蓝黑／蓝白的牌表；没有新增父类或统一放宽数量。Pauper Dimir 红色分支继续排除 Skred，并用 Terminate 排除已有 Grixis 的持续红黑去除路线；弱的 Mystic 核心不阻止其他控制家族，避免新保护逻辑误伤 Familiars／Ephemerate。

## 共享代码的实际缺口

1. 原新函数只读取印刷施放费用，漏掉返照和增幅。现按有正常土地支持的 Flashback／Kicker 费用计入颜色，保留地牌、Mite 起动费用本身不加色。Rally the Peasants、Mystical Teachings、Tear Asunder 有定向验证。
2. 支付特定颜色改变效果的识别原来只接受单个符号；现在也识别 Wistfulness 等 `if {G}{G} was spent`，沿用已经确认的 Firespout 支持来源和效果相关原则。普通混合费用仍不自动同时计入两色。
3. Leyline of Sanctity 复用现有 Leyline 非正常施放判断：没有其他已建立的正常白色用途时不凭开局地脉加白；其他正常白色牌仍计色，显式 normal_cast 可覆盖。没有按少量备牌整体豁免。
4. 增加可复用 `card_uses: {Sneaky Snacker: noncast_without_support}`，本次仅用于 Pauper Battle Screech 的弃牌／自动回场用途；没有对应土地支持时不计其蓝黑，真正支持正常施放后仍计色。默认函数与其他父类没有全局排除这张牌。
5. Pioneer Temur Creativity 的 Valgavoth 明确作为创新目标，不贡献黑色；这是本赛制实际样本的逐牌用途配置，没有复制 Modern 的目标名单或五色惯例。其他正常黑色咒语仍贡献黑色。

共享修复也回查 Modern：相对上一版本仅 1 条归属变化，`data/modern/melee/events/471573.json#decklists/13` 的 Broodscale 从候选纯绿恢复为 Golgari。备牌 Tear Asunder 增幅需黑色，主牌 Underground Mortuary 和备牌 Bojuka Bog 提供正常黑色土地；依据不是 Drum／Talisman。上一版本漏算增幅黑色。已补完整牌表回归样本，不能继续宣称 Modern 完全不受影响。

## 全量结果及不能隐去的缺口

以冻结原始输入、旧适配器和旧规则为基线，检查输入 SHA256、记录集合，并用当前适配器重新运行。

| 赛制 | 记录 | 父类变化 | 子类变化 | 新增 Unknown | 仅匹配轨迹变化 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard | 7148 | 13 | 6 | 21 | 441 |
| Pauper | 5897 | 0 | 11 | 9 | 54 |
| Pioneer | 5572 | 0 | 1 | 108 | 17 |

以上列互斥；新增 Unknown 不重复记作父类变化。保留原有 Standard 5、Pauper 1 个 Unknown 后，当前总数分别为 26、10、108。所有新增 Unknown 都是维护对象，不能据此宣布发布就绪，也不能仅因数量增加就将正常颜色删回去。

已能落到既有身份的纠错包括：Standard 10 份 Jeskai → Dark Jeskai、2 份控制 → Esper、4 份 Spider-Man → Sultai、1 份 Manufacturing → Mardu、1 份 Lifegain → Abzan；Pauper 4 份 Gardens → Jund、4 份 Packbeast → Mardu、3 份 Battle Screech → Boros；Pioneer 1 份 Lotus → Sultai。

新增缺口按完整颜色证据分组，含文本主备牌，见 [OTHER_FORMATS_PENDING_COLORS.md](OTHER_FORMATS_PENDING_COLORS.md)。其中 Pioneer 107 条来自 Lotus：5 条 URG、50 条 WUBG、42 条 WUBRG、10 条 UBRG；另 1 条原 Azorius Control 正常用色 WUB。不能把这些自动诊断直接转换成已批准的新子类。

仍待完成色组筛选的家族也明确保留：Standard Leyline／Fling 的历险用途边界；Kona 的目标用途；Pauper Ephemerate 的多种四色路线。其他未定位的旧规则不因本轮接入而宣称已全部修复。

2026-10-24 Owner 已批准 [Starting Town/Frog](STANDARD_STARTING_TOWN_REVIEW.md) 的护身符用途例外，现已实现并在 Standard Izzet Fling、Izzet Prowess、Leyline Aggro 的生产颜色诊断中执行。只影响满足已核对 Fling 核心的备牌单张 Frog；其他正常绿牌、主牌／复数 Frog 不被一并排除。这三个父类尚未完成严格色组筛选，不与上面的 43 个已筛选父类混计。标准 30 条 Frog 记录逐牌核对通过，Owner 最新要求 Sell-Sword 与 Otter 使用同一施放用色判据；原单独询问 Sell-Sword 的提问撤回，统一试算见 [历险用途方案](ADVENTURE_OPTIONS_AND_VALIDATION.md)，不将该纠正视为单张来源门槛或新类别批准。

## 验证与旧基准保护

- 新增 12 份完整来源牌表，包括 Standard／Pioneer 无绿色来源的 Frog，以及上述 Modern 增幅修正；人工预期依据正常施放口径和已有类别含义，没有把候选输出批量抄成答案。它们是本轮回归样本，不宣称独立准确率样本。
- 生产入口验证单张有支持备牌改变子类、仅增加土地不加色、同色换地不失配、父类核心移除后各子类均失配；验证非施放用途不吞掉其他同色正常咒语。
- 共享语义、规则合同、求值与接入测试通过。四赛制规则通过 JSON Schema 和生产解析验证；相关 Ruff、mypy 通过。
- 三个旧 Standard 合成测试只有土地提供目标颜色，未提供相应正常咒语。按已确认“地本身不加色”的口径补入 Sheltered by Ghosts／Duress，保留原类别预期，并加入“只有土地不能通过”的负例。
- 扩大检查曾发现 Pauper 旧测试在冻结代码／规则上已有 7 个样例失败，另有库存断言过时。现已保留冻结输入和期望文件，补完整用色／结构上下文、验证缺失核心负例，并补足全部现行规则的执行覆盖；174 项通过。具体逐项依据见最新续作记录，不再将该旧失败列作当前阻断。
- 本次另有 1 个可解释的旧 Gates 分支断言变化：去除 Boros Garrison 的判色要求后，原高优先级 Boros 分支也能匹配。测试保留冻结 fixture 中旧规则 ID，分别验证旧 Gates 分支仍匹配、现在选择通用 Boros 分支及公开身份不变；没有改优先级或刷新历史 fixture。

外部证据保留在 `/workspace/scratch/classifier-round1/`：`candidate-{format}.json`、完整基线／输入 manifest、`modern-incremental-other-formats.json`、`pauper-contract-before.json`／`pauper-contract-after.json`、测试日志及受影响规则迁移脚本。当前派生产品仍是上一候选版本，后续解决相关业务边界后再按既有流程重建，不能沿用之前的 CURRENT 状态代表本版。
