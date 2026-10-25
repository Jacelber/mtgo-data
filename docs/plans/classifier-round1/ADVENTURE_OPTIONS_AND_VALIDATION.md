# 历险用途方案及验证续作

最新执行状态：本组历险用途例外、两张新增护身符用途、Standard Temur Prowess 与 Jeskai Looting 父类决定均已实施。红蓝／洁斯凯滤牌共享必要结构核心；本次 100 项受影响检查通过，标准 7,148 条回放只有已确认牌表 Unknown → Jeskai Looting 一项增量。严格颜色接入为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；标准当前 Unknown 26（较原冻结基线新增 21）。这组决定不再待答，更早待维护项继续保留。详见 [实现与剩余边界](FLING_EXCEPTION_IMPLEMENTATION.md)。下文此前数字属于阶段记录，尚未提交或发布。

2026-10-24，Owner 要求继续开发，发布保持暂停。以下区分已经实施的技术修复、试算能力与仍需确定的分类口径；没有将试算输出批量转成期望或新类别。

## 最新确认：保留共享原则，只给这两张牌设置局部例外

Owner 明确：“保留原有原则，这两个使用例外。”本节取代下文历史讨论中的待定表述，但不表示例外已经接入生产规则。

- 共享颜色规则不改：其他正常主备牌咒语仍按既有施放支持计色，不建立全局最少两张或四张色源要求。
- 在本轮讨论的 Fling／灵技相关构筑中，对 Sell-Sword 的黑色生物部分和 Otter 的绿色历险部分设置对称的局部用途例外：不配置或只配置一张相应额外色源，不因该部分认定混色。
- 足量配置相应额外色源时，应承认该部分的正常施放用色；4 Blood Crypt、只有 Sell-Sword 用黑的已确认构筑仍算红黑。Otter 使用同一原则，不固定永久排除绿色。
- 例外只影响这两张牌的相关部分，不排除其他正常同色咒语，不扩散到其他历险牌、其他家族或赛制惯例。既有 Frog 护身符例外独立保留。
- “足量”没有被批准为统一的数值门槛；不能把这次决定实现成“至少两张就算”。现存双绿源的 28 条 Otter 记录为 12 条双 Willowrush Verge、16 条 Breeding Pool 加 Willowrush Verge，仍需结合具体构筑处理。这一中间边界不影响零／单张不计及已确认 Blood Crypt 正例的记录。

实现应复用局部用途配置，在已确认的路线范围内选择计色卡面，并保留来源与原因诊断。不能简单给整个父类永久配置 `adventure_only`／`front_only`，否则会吞掉已确认的正常第二色路线。下文旧试算保留作证据，不作为已批准的阈值或分类真值。

## 已实施：来源事实与用途表达

`Multiversal Passage` 的 Oracle `produced_mana` 字段为空，但规则文字明确选择基本地类别。原支持计算因此漏掉了它的产色能力。现根据该已知规则文字识别其可选产色能力；它自身不增加套牌颜色，必须有相应正常咒语。普通 Fabled Passage 没有被当作无条件任意色地，仍依赖实际目标。该修复不是自动决定历险部分是否属于正常施放用途。

共享用途配置增加 `front_only`、`adventure_only`，限已登记的历险牌；非历险牌／未知牌的这类配置被拒绝。实体与数量保持一次计数，主备牌使用相同选面机制，其他正常同色牌不会被排除。以下是可试算的写法，**尚未写入生产分类规则**：

```yaml
card_uses:
  Callous Sell-Sword: adventure_only
  Elusive Otter: front_only
```

生产配置中已批准的 Standard Frog 护身符策略保持有效，已确认的 4 Blood Crypt／仅 Sell-Sword 用黑仍归红黑。

## 已撤回的不对称试算（保留诊断证据）

Owner 随后指出：Sell-Sword 的黑色部分与 Otter 的绿色部分应适用相同的施放用色判据。在相当的支持条件下，若前者计黑，后者也应计绿。接受这项纠正；撤回“单张固定黑源让 Sell-Sword 计黑，同时 Otter 一律只计蓝”的组合建议，以及仅单独询问 Sell-Sword 的提问。该纠正不等于批准单张来源门槛。以下旧试算仅保留样本分布，不作为有效的联合候选方案。

对象为 Standard 的 Izzet Fling／Izzet Prowess／Leyline Aggro 中含这两张牌的 378 条记录，以及 Pioneer 的 Rakdos Fling／Rakdos Leyline 中 7 条记录。旧家族标签用于划定本次审查范围，不作为颜色正确答案。

只计 Sell-Sword 黑色、没有其他独立正常黑色咒语的记录，其固定黑色地源数量分布如下。这里的“固定”不计 Starting Town 或 Multiversal Passage 等任意色／可选择类型来源；用于比较候选方案，不是已批准的通用法术力模型。

| 赛制 | 固定黑源数 | 记录数 |
| --- | ---: | ---: |
| Standard | 0 | 113 |
| Standard | 1 | 2 |
| Standard | 5 | 1 |
| Pioneer | 4 | 3 |

试算暂将该红蓝路线中的 Otter 只计蓝色；Sell-Sword 在有其他正常黑色依据时仍计黑，否则比较 1、2、3、4、6、8 个固定黑源门槛。

- 2、3、4 的结果完全一致，当前保留样本不能独立证明应选其中哪个数。
- 6、8 会破坏 Owner 已明确的 4 Blood Crypt 正例，淘汰，不作为可接受方案。
- 在这个已撤回的不对称试算中，1 与 2–4 仅在两条“19 Mountain＋1 Blazemire Verge”的记录上不同。完整文本保留在 [单黑源审阅](SELLSWORD_SINGLE_BLACK_SOURCE_REVIEW.md)。这不能代表同时处理 Otter 的实际影响。
- 不论上述门槛如何，Otter 的局部只计蓝建议没有抹掉其他绿牌：试算中 Standard 仍有 11 条带其他正常绿色依据的记录，其中 9 条原 Izzet Prowess、1 条原 Izzet Fling、1 条原 Leyline Aggro。

完整逐记录输入、固定来源列表及六种输出保存在 `/workspace/scratch/classifier-round1/adventure-use-options.json`，生成脚本为同目录 `compare_adventure_uses.py`。这些是方案对照，不是实际分类已改变的记录。

## 当前方案：两张牌统一比较

两张牌的次要用色都按同一条件判断，不能仅凭该部分是生物还是历险而分别制定门槛。4 Blood Crypt 的红黑正例继续受保护；相当的正常绿色施放支持也应让 Otter 在红蓝构筑中贡献绿色。单张来源是否足够、仅有 Starting Town／Multiversal Passage 时是否算正常用途，都必须成对处理，不能从 Owner 的一致性要求推导出已批准的数值门槛。

已对同一 385 条记录重新试算：对两张牌同时采用 1／2／3／4 张固定色源门槛，另有正常同色咒语时始终保留该色。这里只比较候选效果；来源数量不证明游戏计划或分类真值，固定来源模型也不是生产支持模型的替代。

| 赛制／唯一提供该色的历险牌 | 0 张固定色源 | 1 张 | 2 张 | 4 张 | 5 张 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard Sell-Sword（黑） | 113 | 2 | 0 | 0 | 1 |
| Standard Otter（绿） | 261 | 75 | 28 | 0 | 0 |
| Pioneer Sell-Sword（黑） | 0 | 0 | 0 | 3 | 0 |

统一试算下，1 与 2 张门槛的差异是 Standard 77 条：2 条 Sell-Sword 和 75 条 Otter。Otter 另有 28 条双绿源记录，因此先前“2／3／4 门槛结果相同”只适用于黑色单项，不适用于两张牌的联合方案。以上是来源记录数，不能当作独立牌手或独立构筑数量。

结果保存在 `/workspace/scratch/classifier-round1/adventure-use-options-unified.json`，生成脚本为同目录 `compare_adventure_uses_unified.py`。生产规则仍未启用选面例外，未更改分类身份或历史期望；不为保持旧红蓝标签单独排除 Otter，也不为了少建类别选择数量门槛。

## 已实施：已有 Gruul Landfall 的漏识别

`data/standard/Standard_Challenge_32_12849496.json#players/4` 使用正常红色 Full Bore，却因 Gruul Landfall 强制 3 Stomping Ground 而遗漏。该类别已经存在，不需要新身份决定。

已移除该判色地名门槛，使用正常红绿咒语；纯绿同路线也移除不相关彩色地的否定条件。组合核心、数量和类别优先级保持。完整来源牌表现在归已有 Gruul Landfall；仅将红色咒语换回绿色、保持原土地不变时归 Mono-Green Landfall。这同时证明不是用土地本身加色。

## Pauper 旧验证修复

冻结 `tests/fixtures/pauper/rule_contract.json` 未改。没有修改生产数量条件以迎合不完整测试，也没有批量刷新期望。

- `green-tron-b` 原合成输入仅有 Tower，缺 Mine／Power Plant。保留其原输入应为 Unknown 的负例，再补齐两个既有核心组件验证原正例身份。
- Wildfire Ephemerate 原合成输入缺少该维护路线的 Mulldrifter。保留缺失输入的负例，补完整路线验证。
- Gardens／Dimir Control 的极小合成输入只有彩色地、没有相应正常绿／黑咒语。补 Weather the Storm／Cast Down，符合已确认的颜色规则，不将土地当咒语。
- 四处 null 子类期望早已落后于冻结生产规则。用已经存在的 Golgari／Dimir／Azorius 普通子类验证，没有新增身份。
- Fangren 与 Gates 更具体分支被既有更高优先级的同家族分支覆盖：分别验证具体分支仍匹配、选择结果及公开身份，未修改优先级。
- 原库存检查漏掉后来维护的 25 条规则。24 条补入从冻结回放定位的真实来源，验证这些规则确实执行；另一条 artifact Gardens 混红分支用单张正常红色备牌变体验证。规则总集合必须精确等于原代表样本、补充来源及此变体的覆盖集合，没有删除全规则覆盖要求。
- 父类／子类库存与独立维护的名称配置核对，允许已有动态颜色子类格式，拒绝未登记输出。这些执行覆盖检查不声称证明分类准确率。

Pauper 174 项检查通过。共享语义、规则合同、求值、用途与其他赛制接入的合并检查 301 项通过；随后新增的地落修复所在模块 21 项通过。相关 Ruff、mypy 通过。测试日志保留，已解释的旧失败不再列为当前阻断项。

## 当前实际全量影响

Multiversal Passage 技术修复及用途能力增加后，四赛制相对前一候选的分类签名变化为零；这不等于颜色诊断没有改变。用途试算没有启用到生产规则。Gruul Landfall 实际接入后，Standard 一条新增 Unknown 被解决。

| 赛制 | 当前 Unknown | 相对冻结输入新增 Unknown |
| --- | ---: | ---: |
| Standard | 26 | 21 |
| Pauper | 10 | 9 |
| Pioneer | 108 | 108 |
| Modern | 22 | 0 |

当前严格按新颜色筛选的父类为 Standard 29、Pauper 5、Pioneer 9，共 43；另 3 个 Standard Fling 相关父类仅执行用途诊断，历险口径未定前不混计为完成筛选。尚未更新本版派生产物、提交或发布；相关新类别决定仍按既有维护流程处理。
