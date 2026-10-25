# 首轮完整分类影响核对

当前候选尚未发布。对照基线、原输入哈希和完整链来源见 IMPLEMENTATION.md；该表记录差异，不把旧标签或新自动输出作为独立正确答案。

四赛制均已实际接入本轮修正。以下是冻结原输入到最终本地候选的完整回放，不是接入前的零变化检查。保留原始基线，不用当前输出替换测试答案。证据签名不包含完整 ConditionEvidence；变化条数不能报告成独立改进样本数或准确率。

| 赛制 | 保留牌表 | 分类成功 | 原 Unknown → 当前 Unknown | 签名变化 |
| --- | ---: | ---: | ---: | ---: |
| Modern | 18,830 | 18,810 | 22 → 20 | 2,126 |
| Standard | 7,148 | 7,147 | 5 → 1 | 491 |
| Pioneer | 5,572 | 5,572 | 0 → 0 | 114 |
| Pauper | 5,897 | 5,896 | 1 → 1 | 62 |

各行变化按“状态变化 → 已分类父类变化 → 同父类子类变化 → 归属不变的轨迹变化”依次互斥统计：

| 赛制 | Unknown 恢复 | 已分类父类变化 | 同父类子类变化 | 仅匹配／诊断变化 |
| --- | ---: | ---: | ---: | ---: |
| Modern | 2 | 14 | 1,993 | 117 |
| Standard | 4 | 25 | 25 | 437 |
| Pioneer | 0 | 1 | 13 | 100 |
| Pauper | 0 | 0 | 16 | 46 |

Modern 的具体分解如下。

| 差异类型 | 数量 |
| --- | ---: |
| 父类改变 | 14 |
| 原 Unknown 恢复到既有父类 | 2 |
| 父类不变、子类改变 | 1993 |
| 归属不变、匹配／诊断轨迹改变 | 117 |

## 父类变化

| 旧归属 | 候选归属 | 数量 |
| --- | --- | ---: |
| five-color-creativity | jund-creativity/jund | 3 |
| jund-creativity | five-color-creativity | 1 |
| izzet-wizards | grixis-control | 2 |
| izzet-wizards | temur-wizards | 2 |
| dimir-tempo/grixis | four-color-control | 1 |
| steel-cutter/izzet | jeskai-ascendancy-combo/four-color | 1 |
| dimir-tempo/grixis | esper-blink/wubr | 1 |
| steel-cutter/izzet | jeskai-ascendancy-combo/jeskai | 2 |
| five-color-creativity | rakdos-creativity | 1 |

归属依据：Ascendancy 的独立组合技家族、红黑创新、铁木尔法术师、两份 Grixis Control、独立四色控制及 Esper Blink/WUBR 均有本轮 Owner 具体决定，分别见对应 REVIEW 文件。旧五色创新中 3 份 Jund 由正常 Jund 用色及既有 Wrenn 路线修正；旧 Jund 中 1 份为正常五色、含 Teferi／Ending／Pawpatch 的五色创新路线，属于共享颜色修复，不用旧父类保护覆盖已确认正常颜色。具体为 `mtgo:modern:12843449:25`：主牌 Ending 4、Reprieve 4、Teferi 1，备牌 Consign 3、Teferi 1、High Noon 2；Plains／Sacred Foundry／Elegant Parlor 支持白色，Steam Vents／Xander's Lounge 支持蓝色。黑色仍有 Thoughtseize／Fatal Push／Persist 与 Blood Crypt 等普通来源，Wrenn／Pawpatch 的绿也有 Stomping Ground 等来源。这是正常五色用色及既有五色路线的纠错，无须扩大 WURG 命名例外。

## 同父类子类变化

| 旧归属 | 候选归属 | 数量 |
| --- | --- | ---: |
| esper-goryos | esper-goryos/esper | 1116 |
| esper-blink | esper-blink/esper | 812 |
| sewer-combo/mono-blue | sewer-combo/azorius | 1 |
| oculus-ritual/simic | oculus-ritual/sultai | 4 |
| esper-goryos | esper-goryos/wubg | 2 |
| sewer-combo/simic | sewer-combo/temur | 2 |
| jund-creativity | jund-creativity/four-color | 2 |
| jeskai-ascendancy-combo | jeskai-ascendancy-combo/jeskai | 10 |
| sewer-combo/azorius | sewer-combo/jeskai | 1 |
| sewer-combo/mono-blue | sewer-combo/simic | 6 |
| sewer-combo/simic | sewer-combo/bant | 1 |
| broodscale-combo/mono-green | broodscale-combo/gruul | 1 |
| jund-creativity | jund-creativity/jund | 3 |
| prowess/izzet | prowess/temur | 2 |
| steel-cutter/izzet | steel-cutter/temur | 2 |
| broodscale-combo/golgari | broodscale-combo/mono-green | 2 |
| sewer-combo/mono-blue | sewer-combo/bant | 1 |
| oculus-ritual/sultai | oculus-ritual/four-color | 2 |
| prowess/izzet | prowess/jeskai | 16 |
| prowess/izzet | prowess/grixis | 1 |
| sewer-combo/mono-blue | sewer-combo/izzet | 1 |
| chant-control/azorius | chant-control/jeskai | 1 |
| prowess/mono-red | prowess/boros | 1 |
| rakdos-hollow-one/rakdos | rakdos-hollow-one/mardu | 1 |
| oculus-ritual/simic | oculus-ritual/temur | 1 |
| prowess/mono-red | prowess/izzet | 1 |

其中 Esper Goryo’s 1,116 条和 Esper Blink 812 条主要是明确普通子类，父类统计不变。其他变化按已确认的正常主备牌用色、Wear/Tear 完整身份、非施放目标例外及正常土地支持解释。特别是 Mite 的绿色起动费用不加色，单张有正常支持的备牌咒语仍计色；Surgical 等可付生命／非施放用途不直接等同于黑色。

## 归属不变的轨迹变化

| 父类 | 数量 |
| --- | ---: |
| broodscale-combo | 27 |
| grixis-control | 18 |
| oculus-ritual | 24 |
| prowess | 28 |
| dimir-tempo | 9 |
| five-color-creativity | 2 |
| necrodominance | 1 |
| boros-belcher | 6 |
| grixis-creativity-goryos | 2 |

这些差异源于父类共同条件、规则分支／颜色依据和重叠匹配变化，不能记作新类别修复。既有优先关系保留，不启用全局“组合技／控制优先”。全部源定位和前后签名保存在外部 candidate-modern.json，按记录逐一可回查。

## 其他赛制与限制

2026-10-23 的零变化核对仅属于接入前状态，保留在 [OTHER_FORMATS_COLOR_AUDIT.md](OTHER_FORMATS_COLOR_AUDIT.md)，不再作为当前候选结论。其他赛制的实际接入与后续修正见 [OTHER_FORMATS_IMPLEMENTATION.md](OTHER_FORMATS_IMPLEMENTATION.md)、[五色来源修正](RAINBOW_SUPPORT_IMPLEMENTATION.md)和[原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md)。属性覆盖无缺失和零漂移都不能代替颜色行为正确性的证明。

本次共享增幅费用修复使 Modern 一副 Broodscale 从中间候选的纯绿恢复为 Golgari：`data/modern/melee/events/471573.json#decklists/13` 有 Tear Asunder 及正常黑色土地支持。后续普通土地支持原则又使 3 条原候选 Izzet → Temur 灵技变化不再发生；这不等于全局忽略备牌绿色。上表按最终候选汇总，完整单卡贡献保留在 `candidate-modern.json`。原 Unknown 中 Amalia 与 Dimir Mill 的两项遗漏已恢复既有父类，具体正向核心及反例见 [局部修正](ORIGINAL_UNKNOWN_REPAIRS.md)。

Standard 的 4 条原 Unknown 分别恢复为两条已批准的 Sultai Kona、一条既有 Azorius Control、以及已批准的 Rakdos Goblins。其余变化包括正常颜色纠错和已批准的新增身份；437 条只改变匹配／诊断轨迹，不改变最终归属。Pioneer 的 1 条父类变化为 Azorius → Esper Control，13 条子类变化为 12 条 WUBG 莲花与 1 条正常黑源的 Simic → Sultai 莲花。Pauper 的 16 条子类变化包含正常主备牌混色、已批准的 Packbeast 用途及 Naya／Orzhov 战呼、Sultai Gardens。

剩余 Unknown 均有本轮适用处置：Modern 20 条保留 Unknown，其中最后 4 条各自 11 个可查历史版本始终为 Unknown，按 Owner“之前就是 unknown 则保持，不需要再问”直接保留；Pauper 1 条基本地来源已确认；Standard 1 条复用原有效 intentional Unknown 登记。具体来源及决定范围见 [维护清单](REMAINING_COLOR_WORK.md)，不推广为任意未识别构筑均可接受。

本轮未统一降低 Broodscale 到 3＋1；保留明确已准的 3＋2、拒绝 1＋1，3＋1 的完整数量边界仍待充分证据。未扩展 Legacy，也未全面迁移所有旧父类。派生产物实际同步状态以 [交付记录](DELIVERY_PROGRESS.md) 顶部为准；发布仍暂停。
