# 五色来源：共享口径修正

后续原 Unknown 维护的最新结果见 [原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md) 与 [待维护清单](REMAINING_COLOR_WORK.md)。下文按阶段保留共享机制验证，不把阶段数量作为最新未解决数量。

Owner 已澄清：除明确用途／家族例外外，仅有五色地或通用五色产费能力，不构成某个特定颜色的分类依据。这是四个已接入赛制共享的默认原则，不是莲花田专用命名惯例。此前共享实现将 Starting Town、Lotus Field 等当作各色施放支持，与这一理解不符。

本版继续开发，发布暂停。工作区较早生成的 stats／reports 等派生产物尚未按本版重建，不代表本版已闭合。

## 实现

- `classifier_cards._mana_support` 区分特定颜色支持与五色能力。Starting Town、Lotus Field、Crumbling Vestige、Mana Confluence 等不建立额外颜色；通用神器／生物产费仍不建立混色。Multiversal Passage 的可选基本地类别不自动建立五色支持。
- 同一张地有固定颜色能力时保留固定部分：Citadel Gate 固定白、Cliffgate 固定红、Vivid Creek 固定蓝。Arena of Glory 的普通红色能力不因另一个受限能力被整张排除。不从“能选择另一色”推定所有颜色均成立。
- 主备牌采用相同支持要求。非正常施放目标、历险用途、护身符等已确认例外保留；正常同色咒语不会被另一个卡牌用途例外一并抹色。已审核的单卡 `normal_cast` 显式覆盖仍可使用。
- 一张普通 Swamp＋正常黑色咒语仍计黑；只有 Swamp 不会自动加黑。不引入通用的两源、四源或“深色费用可靠度”阈值。Sell-Sword／Otter 的零、一、二源例外仍只适用于这两张牌。
- 缺失卡牌事实仍显式报告并阻断必要颜色判断，不把未知属性当作无色。本轮没有修改卡牌事实源或原始牌表。
- 先驱莲花田沿用 `default`；没有加入 Kenrith 白色黑名单，没有加入“有黑地便是苏勒台”的家族规则。
- 修正同时发现的诊断顺序问题：同一规则集合重排时，Unknown 原因按优先级和文本稳定排序，不影响优先级语义。

引擎版本 `1.2.2`；来源和用途政策进入 `color_policy_subject()`，四赛制摘要包含这次共享变化。

## 已确认的 Packbeast 例外

Owner 已批准两副主牌 4 Lightning Bolt＋4 Galvanic Blast、由 Holdout Settlement 支持的红白路线。Pauper 的 `packbeast-swarm` 使用 `pauper-packbeast` profile，仍先满足原父类核心。

实现要求主牌同时有 Lightning Bolt、Galvanic Blast、Holdout Settlement，只为该路线补充红色支持；允许卡牌数量变化，不冻结完整 75 张牌。Holdout 的诊断明确标注此例外。移到备牌、缺少其一、缺少父类核心均不能走该例外，不开放黑／绿或所有五色来源。

Owner 随后已批准第二副的 Mardu 用色和第三副的 Selesnya 用色，均已实施：

- 既有 Packbeast 父类内，主牌 4 Mardu Devotee＋4 Springleaf Drum 的已确认组件补充黑、红支持；仍需要正常同色咒语，不能仅凭产色组件自动归 Mardu。不强制 Refurbished Familiar 或 Encampment，其他正常黑红牌可复用。当前同配置 5 条；其中 4 条归 Mardu，1 条 Learn 构筑按后续用途决定排除 Lesson 额外颜色，再因非 Lesson 的 Flaring Pain 归 Boros。四张各自是当前审核配置，未推定全局色源门槛或更稀疏组件的可靠度。
- 主牌 Winding Way＋4 Springleaf Drum 只补绿色支持；不为其他牌组或蓝黑红备牌开放五色能力。完整来源 12854488:29 保留 Selesnya。

完整文本与已确认归属见 [Packbeast 来源复核](PAUPER_RAINBOW_SUPPORT_REVIEW.md)。

## 同输入回放

四赛制仍使用原冻结输入、原适配器基线；逐项核对原始输入 SHA 和记录集合，无新增或删去牌表。下面数字是候选诊断，不以 Unknown 减少证明业务正确。

| 赛制 | 保留记录 | 本次修正前 Unknown | 当前 Unknown |
| --- | ---: | ---: | ---: |
| Standard | 7,148 | 26 | 5 |
| Pioneer | 5,572 | 108 | 0 |
| Modern | 18,830 | 22 | 22 |
| Pauper | 5,897 | 10 | 1 |

- Pioneer：95 条莲花田恢复可识别，其中 5 条蓝绿、90 条苏勒台。12 条为白蓝黑绿，已归后续批准的 wubg 子类：8 条有 Urban Retreat、4 条有 Lush Portico，白色支持真实存在，不因这次修正一并排除。原另一副控制已归后续批准的 Esper Control。
- Standard：3 条 Pest Control 只有五色白源的 Spider-Man、1 条 Terror 只有受限五色红源的 Spider-Man 恢复苏勒台；1 条白色仅靠五色来源的 Golgari 构筑恢复原父类。Lifegain 代表 `12851116:0` 的 Jennifer Walters 正面费用为 1W，另一面 She-Hulk 为 3GWW；没有固定绿源，不再归 Abzan，而是 Orzhov。
- Modern：3 条 Prowess 牌表的 Monstrous Growth／Violent Outburst 没有正常绿源，候选 Temur 改为 Izzet。不猜测登错牌，不修改牌名。
- Pauper：两条已批准烧牌路线保持 Boros；后续批准的黑红组件与绿色滤牌路线已落实；其他仅备牌混色仍需独立复核。一个曾因 Gate 可选颜色而出现的 Naya Battle Screech 边界已由后续决定解决：Owner 最终明确该城门＋Ancient Grudge 返照路线计绿，已归纳雅战呼；默认五色来源规则不变。

Pauper 这组决定的最终增量：黑红组件对应 4 条 Mono-White → Mardu，Learn 用途与分支修正对应 1 条 Mono-White Learn → Boros，绿色路线对应 1 条 Mono-White → Selesnya。相对这组决定之前的候选，其余 5,891 条状态／身份／匹配记录不变。

全量候选与本次修正前备份位于 `/workspace/scratch/classifier-round1/candidate-*.json`、`candidate-*-before-rainbow-support.json`。共享修正回放日志为 `rainbow-support-replay-approved.log`；随后 Pauper 局部续作日志为 `mardu-packbeast-replay.log`、`green-packbeast-replay.log`。这些是诊断证据，不替代业务确认。

## Learn 用途与已确认归属

Owner 指出：Learn 体系仅在备牌的 Lesson，如果没有相应普通色地，不应仅因能够被温习拿进手牌就算混色。共享实现识别主牌实际 Learn 文字和备牌 Lesson 类型；仅在备牌的 Lesson 使用普通土地支持，不借家族产色例外额外加色。主牌也有该 Lesson、没有 Learn、或确有普通对应色地时，不适用这项用途限制；显式 normal_cast 仍可覆盖。

实际牌表 `12843392:18` 的 Dai Li Indoctrination、Firebending Lesson、How to Start a Riot、It'll Quench Ya! 不增加黑红蓝；Yip Yip! 有普通白源仍计白。2 张 Flaring Pain 是普通 Instant，不是 Lesson，依已批准 Devotee＋Drum 支持仍计红。Owner 已确认归既有 Boros 子类，不新建 Learn 混色身份。

为此增加 `boros-learn-packbeast-swarm` 路线，与既有纯白 Learn 分支通过 YAML anchor 共用完全相同的结构条件；仍继承 Packbeast 父类核心，仅颜色要求不同。去掉 Flaring Pain 后同一牌表仍归 mono-white-learn。没有降低数量、删掉核心或刷新旧样例期望。

## 验证与未完成项

加入共享 Learn 用途后，338 项相关检查通过；四赛制全量回放表明 Standard、Modern、Pioneer 的状态／身份／匹配记录没有增量变化，只有这一条 Pauper 的颜色诊断变化。随后已批准的 Boros Learn 分支通过 212 项受影响检查（与此前检查重叠，不相加计数）；Pauper 5,897 条回放仅该记录 Unknown → Boros。原真实 Mardu 期望未改动并通过。

四份最新回放摘要与当前实现一致；原始输入 SHA、记录集合、卡牌事实均保持不变。共享 Learn 证明为 `learn-use-incremental-proof.json`，分支续作日志为 `boros-learn-tests.log`、`boros-learn-replay.log`。受影响 Python 文件 Ruff 检查通过；先前 classifier／rules 的 Mypy 检查仍适用。卡牌事实摘要保持 `b342090c746ad7a3b8e7bf9a258585abb564866d654bea4f8035ab95141c0612`。

Owner 已批准 [黑白战呼子类](PAUPER_ORZHOV_SCREECH_REVIEW.md)。已在 battle-screech 下增加 orzhov 白黑映射及 Orzhov Battle Screech／黑白战呼名称；父类核心和分支结构不变，不指定某张黑牌或地。原有白黑 mana 配置／前端标识已齐全，直接复用。213 项受影响检查通过；Pauper 5,897 条回放仅 5 条 Unknown → Orzhov Battle Screech，其余 5,892 条完全不变。验证另覆盖替换普通黑地、改用单张 Duress、只有黑地不加黑、缺少 Battle Screech 不能绕过核心。原历史结果不刷新。

Owner 已批准 [sultai 子类](PAUPER_SULTAI_GARDENS_REVIEW.md)，最终名称明确为 **Sultai Gardens／苏勒台控制**。已复用现有 Crypt Rats／神器两条结构分支，普通、混红、混蓝路线通过 YAML anchor 共享条件；父类核心不变，不强制 Kenku 或特定桥地。名称配置与前端蓝黑绿标识均已同步。216 项受影响检查通过，5,897 条回放仅该记录 Unknown → sultai；其他 5,896 条不变。

Pauper 本轮新增 Unknown 已全部解决，当前仅保留原基线的一条：`data/pauper/melee/events/438329.json#decklists/289` 主牌为 62 Swamp，不能凭空归入一个已知类别。未修改源数据或使用宽泛类别兜底。

[先驱 Esper Control 父类](PIONEER_ESPER_CONTROL_REVIEW.md) 已批准并实施：五条既有控制结构分支与 Azorius 共用条件，Esper 的 WUB 要求通过同一 YAML anchor 复用；不强制具体黑牌，也不把 Teferi 强制为所有控制路线必要条件。名称与前端白蓝黑标识已同步。5,572 条回放仅一条 Unknown → Esper Control。首轮相关检查 101 项通过、1 项名称配置失败；修正插入位置后 8 项直接受影响检查全部通过，并补证约力昂原名称未改。未修改测试期望来接受错误名称。

[莲花变境的 WUBG 子类](PIONEER_WUBG_LOTUS_REVIEW.md) 已批准并实施。12 条均有普通白源及正常白色工具牌，不依赖 Kenrith 是否计色；子类继承父类核心，仅添加 WUBG 要求。62 项受影响检查通过，全量仅这 12 条 Unknown → wubg，其余 5,560 条不变；先驱本轮 Unknown 全部解决。

[Standard Absolute Virtue 复制目标用途](STANDARD_ABSOLUTE_VIRTUE_REVIEW.md) 已批准并实施：限定 standard-spider-man profile、主牌存在 Superior Spider-Man，只排除 Absolute Virtue；其他正常白牌、其他潜在复制目标和显式 normal_cast 不受此例外排除。144 项相关检查通过。四赛制重新回放仅标准这 4 条 Unknown → Dimir，其他赛制状态／身份／匹配均无增量；四份摘要均匹配当前实现。

[标准格利极蜘蛛侠子类](STANDARD_GRIXIS_SPIDER_REVIEW.md) 已批准并实施：7 条正常红色路线归 grixis，父类结构不变；101 项相关检查通过，7,148 条回放仅这 7 条变化。

[标准四色武器（无绿）子类](STANDARD_WUBR_MANUFACTURING_REVIEW.md) 已批准并实施：3 条正常 WUBR 路线归 boros-manufacturing/wubr，仍继承 Weapons Manufacturing＋United Battlefront 核心；95 项相关检查通过，全量回放仅这 3 条变化，其余 7,145 条不变。两组均同步中英文名称及前端颜色标识，逐组增量证明保存在 scratch。

[标准黑绿地落](STANDARD_GOLGARI_LANDFALL_REVIEW.md) 已批准并实施；纯绿／红绿／黑绿路线通过 YAML anchor 共享同一结构条件。77 项受影响检查通过。7,148 条全量回放只有该副 Unknown → Golgari Landfall；纳雅候选仍 Unknown，只多一条新父类的颜色不匹配诊断，其余 7,146 条完全不变。

[标准纳雅地落](STANDARD_NAYA_LANDFALL_REVIEW.md) 已批准并实施；与白绿共用两种既有结构条件，原白绿分支保留。83 项受影响检查通过，全量仅该记录 Unknown → Naya Landfall，其余 7,147 条完全不变。四个已接入赛制本轮新增 Unknown 已全部解决；原 Unknown 和其他待复核差异不因此视为已接受。

[Pauper 城门返照用途](PAUPER_GATES_GRUDGE_REVIEW.md) 已按 Owner 最终更正完成：在 battle-screech 内新增 naya 子类；主牌同时有 Citadel Gate 与 Cliffgate 时，仅对 Ancient Grudge 的返照补绿色支持，不向其他咒语或家族扩展。114 项检查通过；随后补充的合法构筑断言单独通过，Ruff／Mypy 通过。四赛制完整回放仅该副 Boros → Naya，Pauper 其余 5,896 条及其他三赛制全部状态／身份／匹配不变。原始数据、冻结基线不改。

旧结构单元样例没有土地时，显式补入普通对应色地，保留原身份断言；冻结 Pauper `rule_contract.json` 字节不变。真实 Standard Lifegain 期望依据上面的费用和地源事实修正，同时保留 `previous_expected` 与原因；不批量刷新期望。

当前剩余 Unknown 和其他业务边界见 [当前待维护清单](REMAINING_COLOR_WORK.md)。后续按已授权范围继续修正、核对和重建本版派生产品；发布继续暂停，Legacy 不在本轮。
