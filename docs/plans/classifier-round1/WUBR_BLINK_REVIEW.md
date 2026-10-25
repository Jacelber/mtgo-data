# WUBR 云移：艾斯波云移子类

状态：Owner 已选择归入艾斯波云移的 WUBR 子类；候选已实现，完整 Modern 对照通过。

该样本主牌是 Ephemerate3、Quantum Riddler4、Solitude4、Psychic Frog4，主牌正常用色 WUB；备牌 Wear // Tear2，Steam Vents 提供正常红色地源，因此完整正常用色 WUBR。不能只考虑 Tear 面而忽略 Wear，也不适用不可施放备牌例外。

Owner 决定复用 `esper-blink` 父类，新增 `wubr`（WUBR Blink／四色云移〔无绿〕），普通版本为 `esper`（Esper Blink／艾斯波云移）。原 `four-color-blink` 保持原有 WUBG 路线，不新增子类。

实现复用规则 1.2 已有的“仅 subtype_id=null 分支按共享颜色映射”能力：Ephemerate 路线只定义一次，保持 Ephemerate≥2、Riddler≥3、Solitude≥3、Frog≥3、Wrath≤2、Goryo/Persist=0；以正常 WUB／WUBR 映射替代旧红绿地源排除。无需复制结构条件到两个颜色分支。其余既有路线明确设为普通 esper 子类，保留原结构及局部归属。本次不把全部 Blink 路线强行统一成 Ephemerate 核心，不全局忽略 Atraxa，也不把默认诊断中的 Atraxa 绿色自动用于未迁移的 Goryo 混合分支。

完整原有 812 份 Esper Blink 只应增加普通子类，待确认样本进入 WUBR；其他家族竞争沿用原优先关系。下面的范围诊断包含真实交集，不能以自动命中作为独立正确答案。

## 全语料范围

18,830 副全部筛查：现有 Esper Blink 812 副、Four-Color Blink 1 副。去除颜色限制但保留上述 Esper Ephemerate 结构路线，共匹配 186 副：52 份 Esper Blink、121 份 Esper Ketramose、11 份 Esper Energy、1 份五色 Elementals、当前 1 份 WUBR。前 184 份正常用色 WUB，Elementals 为 WUBRG；精确 WUBR 仅当前样本。真实交集保留原优先关系，不据此迁移全部匹配者。

812 份原 Esper Blink 中，811 份默认正常色为 WUB；另 1 份为 Goryo’s／Emperor／Atraxa 混合路线，默认 profile 将 Atraxa 计绿，不能据此直接宣布该牌应改四色归属。本次不修改这一分支，也不把 Goryo 目标例外自动复制到整个 Blink 家族。

## 待确认 WUBR 样本

来源：`data/modern/melee/events/405591.json#decklists/1045`

### 主牌（60 张）

```text
1 Cling to Dust
2 Consign to Memory
2 Consult the Star Charts
3 Counterspell
3 Ephemerate
3 Fatal Push
4 Flooded Strand
1 Force of Negation
2 Hallowed Fountain
1 Island
2 Marsh Flats
1 Meticulous Archive
1 Plains
4 Polluted Delta
2 Prismatic Ending
4 Psychic Frog
4 Quantum Riddler
1 Shadowy Backstreet
1 Sheoldred's Edict
1 Snapcaster Mage
4 Solitude
3 Spell Snare
1 Steam Vents
1 Swamp
2 Tamiyo, Inquisitive Student
1 Undercity Sewers
2 Watery Grave
1 Witch Enchanter
2 Wrath of the Skies
```

### 备牌（15 张）

```text
2 Consign to Memory
3 Mystical Dispute
2 Nihil Spellbomb
1 Surgical Extraction
1 Test of Talents
2 Wear/Tear
3 White Orchid Phantom
1 Wrath of the Skies
```

## 既有 WUBG 四色云移参照

来源：`data/modern/Modern_Challenge_64_12854081.json#players/0`

### 主牌（60 张）

```text
4 Prismatic Ending
1 Orim's Chant
4 Teferi, Time Raveler
4 Solitude
1 Forest
1 Wrath of the Skies
1 Island
1 Plains
1 Lush Portico
4 Flagstones of Trokair
3 Phelia, Exuberant Shepherd
1 Temple Garden
1 Godless Shrine
1 Hallowed Fountain
1 Consign to Memory
4 Flooded Strand
4 Windswept Heath
1 Breeding Pool
4 Ephemerate
1 Nissa, Resurgent Animist
1 Wall of Omens
1 Meticulous Archive
1 Elesh Norn, Mother of Machines
2 Eternal Witness
2 Sevinne's Reclamation
1 Shadowy Backstreet
1 Wooded Bastion
4 White Orchid Phantom
4 Quantum Riddler
```

### 备牌（15 张）

```text
3 Mystical Dispute
3 Consign to Memory
4 Kaya's Guile
1 Veil of Summer
1 Nature's Claim
1 Grafdigger's Cage
2 Wrath of the Skies
```

验证：共享机制及规则契约 95 项通过；18,830 副全量对照仅 812 份既有 Esper Blink 补普通子类、1 份批准样本从错误 Azorius Control 进入 esper-blink/wubr。22 个原有 Unknown 不变，无新增冲突；其他签名不变。
