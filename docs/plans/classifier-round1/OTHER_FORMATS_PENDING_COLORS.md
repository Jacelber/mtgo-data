# 其他赛制接入后的待处理色组

当前状态：共享颜色、已确认用途例外、父类共同条件及已定位的局部修正已接入本轮涉及的四个赛制。完整回放共 37,447 份牌表，Unknown 为 Modern 20、Standard 1、Pioneer 0、Pauper 1，均有适用处置，无待答分类问题。四个赛制本地产物均已同步并验证为 CURRENT；发布仍暂停，未提交或推送。最终差异见 [影响核对](IMPACT_REVIEW.md)，具体实现见 [原 Unknown 续作](ORIGINAL_UNKNOWN_REPAIRS.md)，范围限制见 [维护清单](REMAINING_COLOR_WORK.md)。

以下为此前阶段记录，其中的“最新”与数量仅指相应阶段，以顶部链接为当前状态。

最新执行状态：本组历险用途例外、两张新增护身符用途、Standard Temur Prowess 与 Jeskai Looting 父类决定均已实施。红蓝／洁斯凯滤牌共享必要结构核心；本次 100 项受影响检查通过，标准 7,148 条回放只有已确认牌表 Unknown → Jeskai Looting 一项增量。严格颜色接入为 Standard 35、Pauper 5、Pioneer 10，共 50 个父类；标准当前 Unknown 26（较原冻结基线新增 21）。这组决定不再待答，更早待维护项继续保留。详见 [实现与剩余边界](FLING_EXCEPTION_IMPLEMENTATION.md)。下文此前数字属于阶段记录，尚未提交或发布。

最新 Owner 决定：保留原有共享颜色原则，Sell-Sword／Otter 使用局部用途例外。对应额外色源为零或一张时不因其相关卡面算混色，足量配置则计色；4 Blood Crypt 正例保留。未批准“至少两张”门槛，也不影响其他正常同色咒语。用途例外尚未接入生产；下文旧待答状态以 [历险用途方案](ADVENTURE_OPTIONS_AND_VALIDATION.md) 顶部最新确认为准。

这是当前开发候选的诊断清单，不是新增类别批准，也不是发布结果。每组保留一副完整文本牌表，其余来源可回查；原牌表不修改。仍需区分用途例外、旧规则遗漏与确实缺少的类别。Starting Town/Frog 用途例外已获批准并实现；当前按 Owner 最新要求统一核对 Sell-Sword 与 Otter 的施放用色判据（4 Blood Crypt 正例已确认，单张来源门槛未定），其他新业务问题按后续具体证据逐项讨论。

## standard

### selesnya-landfall：green, red, white（1 条）

来源：
- `data/standard/Standard_Challenge_16_12853666.json#players/29`

代表牌表：`data/standard/Standard_Challenge_16_12853666.json#players/29`。正常土地支持诊断：green, red, white。

**主牌**

```text
4 Esper Origins
2 Surrak, Elusive Hunter
4 Earthbender Ascension
4 Ba Sing Se
1 Plains
12 Forest
4 Fabled Passage
4 Escape Tunnel
1 Demolition Field
4 Mightform Harmonizer
4 Sazh's Chocobo
4 Sapling Nursery
4 Icetill Explorer
4 Llanowar Elves
1 Lumbering Worldwagon
2 Shared Roots
1 Mossborn Hydra
```

**备牌**

```text
3 Torpor Orb
2 Rest in Peace
3 Fire Magic
3 Mossborn Hydra
3 Erode
1 Mountain
```

### dimir-spider-man：black, blue, white（4 条）

来源：
- `data/standard/Standard_Challenge_16_12854938.json#players/1`
- `data/standard/Standard_Challenge_32_12849461.json#players/19`
- `data/standard/Standard_Challenge_32_12854114.json#players/24`
- `data/standard/Standard_Challenge_32_12854920.json#players/15`

代表牌表：`data/standard/Standard_Challenge_16_12854938.json#players/1`。正常土地支持诊断：black, blue, white。

**主牌**

```text
2 Bender's Waterskin
2 Bitter Triumph
7 Swamp
2 Deadly Cover-Up
2 Spell Snare
2 Quantum Riddler
4 Emeritus of Ideation
4 Gloomlake Verge
2 Duress
4 Requiting Hex
4 Restless Reef
4 Deceit
3 Strategic Betrayal
4 Superior Spider-Man
4 Cavern of Souls
2 Bleachbone Verge
4 Winternight Stories
4 Watery Grave
```

**备牌**

```text
3 Absolute Virtue
1 Bitter Triumph
3 Cruelclaw's Heist
2 Day of Black Sun
2 Flashfreeze
2 Duress
2 Disdainful Stroke
```

### dimir-spider-man：black, blue, red（7 条）

来源：
- `data/standard/Standard_Challenge_32_12840532.json#players/17`
- `data/standard/Standard_Challenge_32_12840554.json#players/15`
- `data/standard/Standard_Challenge_32_12840584.json#players/27`
- `data/standard/Standard_Challenge_32_12841322.json#players/20`
- `data/standard/Standard_Challenge_32_12841335.json#players/2`
- `data/standard/Standard_Challenge_32_12841345.json#players/0`
- `data/standard/Standard_Challenge_32_12856627.json#players/14`

代表牌表：`data/standard/Standard_Challenge_32_12840532.json#players/17`。正常土地支持诊断：black, blue, red。

**主牌**

```text
2 Undercity Sewers
4 Ashling, Rekindled
3 Stock Up
4 Emeritus of Ideation
4 Superior Spider-Man
4 Deceit
2 Traumatic Critique
4 Requiting Hex
3 Duress
2 Shoot the Sheriff
1 Bitter Triumph
2 Day of Black Sun
2 Cavern of Souls
4 Blood Crypt
4 Watery Grave
3 Swamp
3 Steam Vents
4 Blazemire Verge
1 Deadly Cover-Up
4 Gloomlake Verge
```

**备牌**

```text
1 The End
2 Qarsi Revenant
2 Pyroclasm
2 Ghost Vacuum
1 Negate
1 Duress
2 Intimidation Tactics
1 Annul
1 Heartless Act
2 Oildeep Gearhulk
```

### dimir-spider-man：black, blue, green, white（3 条）

来源：
- `data/standard/Standard_Challenge_32_12842511.json#players/19`
- `data/standard/Standard_Challenge_32_12842905.json#players/11`
- `data/standard/Standard_Challenge_64_12842128.json#players/9`

代表牌表：`data/standard/Standard_Challenge_32_12842511.json#players/19`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
1 Wistfulness
4 Deceit
4 Wastewood Verge
1 Underground Mortuary
1 Analyze the Pollen
2 Undercity Sewers
1 Dreamroot Cascade
4 Watery Grave
2 Shoot the Sheriff
4 Ancient Cornucopia
1 Gloomlake Verge
4 Overgrown Tomb
3 Awaken the Honored Dead
4 Rakshasa's Bargain
4 Starting Town
1 Black Cat, Cunning Thief
4 Superior Spider-Man
1 Multiversal Passage
2 Requiting Hex
1 Swamp
1 Island
3 Emeritus of Ideation
3 Withering Curse
2 Quandrix Charm
2 Witherbloom Charm
```

**备牌**

```text
2 Keen-Eyed Curator
2 Pest Control
1 Disdainful Stroke
2 Duress
1 Bitter Triumph
1 Cavern of Souls
2 Negate
2 Strategic Betrayal
1 Black Cat, Cunning Thief
1 Emeritus of Ideation
```

### dimir-spider-man：black, blue, green, red（1 条）

来源：
- `data/standard/Standard_Challenge_32_12844858.json#players/23`

代表牌表：`data/standard/Standard_Challenge_32_12844858.json#players/23`。正常土地支持诊断：black, blue, green。

**主牌**

```text
2 Terror of the Peaks
3 Wistfulness
4 Bringer of the Last Gift
4 Formidable Speaker
4 Requiting Hex
4 Superior Spider-Man
2 Town Greeter
2 Willowrush Verge
1 Wastewood Verge
4 Overlord of the Balemurk
1 Dreamroot Cascade
2 Into the Flood Maw
1 Underground Mortuary
1 Deathcap Glade
4 Watery Grave
4 Cavern of Souls
2 Breeding Pool
3 Overgrown Tomb
1 Island
2 Gloomlake Verge
2 Bitter Triumph
4 Deceit
1 Undercity Sewers
2 Swamp
```

**备牌**

```text
2 Into the Flood Maw
1 Nowhere to Run
2 Ghost Vacuum
2 Ancient Vendetta
2 Strategic Betrayal
2 Awaken the Honored Dead
2 Spider-Sense
1 Wistfulness
1 Emeritus of Ideation
```

### boros-manufacturing：black, blue, red, white（3 条）

来源：
- `data/standard/Standard_Challenge_32_12846451.json#players/16`
- `data/standard/Standard_Challenge_32_12846482.json#players/17`
- `data/standard/Standard_Challenge_32_12847680.json#players/11`

代表牌表：`data/standard/Standard_Challenge_32_12846451.json#players/16`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
4 Aang's Iceberg
4 Weapons Manufacturing
3 Dusk Rose Reliquary
4 Legion Extruder
4 Cryogen Relic
4 Pinnacle Starcage
4 Castle Doom
4 United Battlefront
4 Sacred Foundry
4 Starting Town
1 Multiversal Passage
4 Shattered Sanctum
1 Mountain
4 Spring-Loaded Sawblades
2 Plains
4 Stormcarved Coast
1 Island
2 Instant Ramen
1 Tithing Blade
1 Tarrian's Journal
```

**备牌**

```text
2 Tithing Blade
2 Authority of the Consuls
2 Sewer-veillance Cam
1 Feldon's Cane
4 Tezzeret, Cruel Captain
1 Scene of the Crime
2 Torpor Orb
1 Ghost Vacuum
```

### golgari-midrange：black, green, white（1 条）

来源：
- `data/standard/Standard_Challenge_32_12848245.json#players/14`

代表牌表：`data/standard/Standard_Challenge_32_12848245.json#players/14`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
2 Swamp
4 Badgermole Cub
1 Ral Zarek, Guest Lecturer
4 Requiting Hex
1 Ba Sing Se
3 Wastewood Verge
4 Multiversal Passage
2 Ouroboroid
1 Strategic Betrayal
4 Llanowar Elves
1 Forest
2 Duress
1 Maelstrom Pulse
4 Overgrown Tomb
4 Mosswood Dreadknight
1 Shoot the Sheriff
4 Blooming Marsh
3 Keen-Eyed Curator
1 Restless Cottage
3 Practiced Offense
2 Leatherhead, Swamp Stalker
2 Surrak, Elusive Hunter
4 Starting Town
2 Professor Dellian Fel
```

**备牌**

```text
1 Decorum Dissertation
1 Surrak, Elusive Hunter
2 Heritage Reclamation
1 Strategic Betrayal
2 Duress
1 Scrapshooter
1 Keen-Eyed Curator
2 Deadly Cover-Up
1 Ghost Vacuum
1 Ygra, Eater of All
2 Qarsi Revenant
```

### 已解决：mono-green-landfall → gruul-landfall（1 条）

2026-10-24 已移除 Gruul Landfall 的 3 Stomping Ground 判色门槛，以下牌表按正常红绿咒语归已有 Gruul Landfall；不再是待定类别。

来源：
- `data/standard/Standard_Challenge_32_12849496.json#players/4`

代表牌表：`data/standard/Standard_Challenge_32_12849496.json#players/4`。正常土地支持诊断：green, red。

**主牌**

```text
4 Ba Sing Se
4 Escape Tunnel
2 Full Bore
4 Earthbender Ascension
1 Mountain
4 Mossborn Hydra
13 Forest
4 Icetill Explorer
4 Fabled Passage
4 Mightform Harmonizer
2 Snakeskin Veil
4 Sazh's Chocobo
2 Meltstrider's Resolve
4 Badgermole Cub
4 Llanowar Elves
```

**备牌**

```text
2 Glorious Decay
2 Meltstrider's Resolve
3 Soul-Guide Lantern
2 Emeritus of Abundance
3 Sapling Nursery
2 Vivien Reid
1 Origin of Metalbending
```

### mono-green-landfall：black, green（1 条）

来源：
- `data/standard/Standard_Challenge_32_Special_12856158.json#players/5`

代表牌表：`data/standard/Standard_Challenge_32_Special_12856158.json#players/5`。正常土地支持诊断：black, green。

**主牌**

```text
2 Glimpse the Core
4 Fabled Passage
4 Llanowar Elves
4 Mightform Harmonizer
4 Sazh's Chocobo
4 Earthbender Ascension
1 Surrak, Elusive Hunter
2 Snakeskin Veil
3 Ba Sing Se
15 Forest
4 Escape Tunnel
4 Esper Origins
4 Icetill Explorer
1 Sapling Nursery
4 Mossborn Hydra
```

**备牌**

```text
1 Leatherhead, Swamp Stalker
4 Meltstrider's Resolve
1 Surrak, Elusive Hunter
3 Sapling Nursery
1 Swamp
2 Torpor Orb
1 Dark Knight's Greatsword
2 Warg Tactics
```

## pauper

### battle-screech：black, white（5 条）

来源：
- `data/pauper/Pauper_Challenge_32_12838111.json#players/3`
- `data/pauper/Pauper_Challenge_32_12841331.json#players/19`
- `data/pauper/Pauper_Challenge_32_12853676.json#players/4`
- `data/pauper/Pauper_Challenge_32_12853684.json#players/3`
- `data/pauper/melee/events/438329.json#decklists/696`

代表牌表：`data/pauper/Pauper_Challenge_32_12838111.json#players/3`。正常土地支持诊断：black, white。

**主牌**

```text
16 Plains
1 Idyllic Grange
4 Kor Skyfisher
1 Steadfast Unicorn
4 Novice Inspector
4 Battle Screech
4 Raffine's Informant
2 Militia Bugler
4 Thraben Charm
3 Thraben Inspector
4 Prismatic Strands
4 Mardu Devotee
4 Leonardo, Big Brother
2 Rally the Peasants
2 Orzhov Basilica
1 Ramosian Rally
```

**备牌**

```text
4 Dust to Dust
2 Journey to Nowhere
2 Arms of Hadar
3 Hallow
1 Thorn of the Black Rose
3 Martyr of Sands
```

### battle-screech：green, red, white（1 条）

来源：
- `data/pauper/Pauper_Challenge_32_12840552.json#players/19`

代表牌表：`data/pauper/Pauper_Challenge_32_12840552.json#players/19`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
3 Thraben Inspector
3 Thraben Charm
3 Novice Inspector
2 Rally the Peasants
6 Plains
3 Citadel Gate
1 Boros Guildgate
3 Faithless Looting
3 Prismatic Strands
3 Leonardo, Big Brother
3 Mountain
4 Pursue the Past
4 Battle Screech
4 Squadron Hawk
4 Lightning Bolt
4 Lunarch Veteran
3 Basilisk Gate
4 Cliffgate
```

**备牌**

```text
4 Ancient Grudge
1 Thraben Charm
4 Electrickery
2 Journey to Nowhere
1 Prismatic Strands
3 Guardian of the Guildpact
```

### packbeast-swarm：black, blue, red, white（1 条）

来源：
- `data/pauper/Pauper_Challenge_32_12843381.json#players/1`

代表牌表：`data/pauper/Pauper_Challenge_32_12843381.json#players/1`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
3 Refurbished Familiar
4 Moon-Circuit Hacker
2 Phyrexian Walker
4 Springleaf Drum
2 Ornithopter
4 Thraben Inspector
4 Novice Inspector
4 Holdout Settlement
1 Leonardo, Big Brother
1 Spider-Man, Web-Slinger
3 Salt Road Packbeast
4 Idyllic Beachfront
4 Thraben Charm
4 Lórien Revealed
4 Kor Skyfisher
2 Lunarch Veteran
2 Rally the Peasants
2 Palace Sentinels
1 Razortide Bridge
4 Ancient Den
1 Forsaken Sanctuary
```

**备牌**

```text
4 Relic of Progenitus
4 Hydroblast
1 Rally the Peasants
2 Blue Elemental Blast
4 Dust to Dust
```

### packbeast-swarm：black, white（1 条）

来源：
- `data/pauper/Pauper_Showcase_Challenge_12844285.json#players/21`

代表牌表：`data/pauper/Pauper_Showcase_Challenge_12844285.json#players/21`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
4 Ardent Recruit
4 Spider-Man, Web-Slinger
4 Leonardo, Big Brother
4 Elite Interceptor
4 Novice Inspector
4 Mardu Devotee
9 Plains
4 Salt Road Packbeast
4 Search Party Captain
4 Thraben Inspector
4 Ancient Den
4 Ornithopter
4 Ramosian Rally
3 Holdout Settlement
```

**备牌**

```text
1 Arms of Hadar
4 Thraben Charm
3 Sunlance
3 Conclave Phalanx
4 Dust to Dust
```

### golgari-gardens：black, blue, green（1 条）

来源：
- `data/pauper/melee/events/438329.json#decklists/1000`

代表牌表：`data/pauper/melee/events/438329.json#decklists/1000`。正常土地支持诊断：black, blue, green。

**主牌**

```text
3 Badgermole
1 Bojuka Bog
4 Brave the Wilds
4 Cast Down
3 Cram Session
3 Cryogen Relic
3 Darkmoss Bridge
3 Eviscerator's Insight
2 Extract a Confession
3 Fanatical Offering
2 Forest
3 Ichor Wellspring
2 Island
4 Kenku Artificer
4 Khalni Garden
2 Lembas
3 Mistvault Bridge
2 Rancor
3 Swamp
3 Tanglepool Bridge
3 Tithing Blade
```

**备牌**

```text
3 Bounce Off
2 Dai Li Indoctrination
2 Disturbed Slumber
2 Drown in Sorrow
2 Earthbending Lesson
2 Relic's Roar
2 Tamiyo's Safekeeping
```

## pioneer

### lotus-scapeshift：blue, green, red（5 条）

来源：
- `data/pioneer/Pioneer_Challenge_32_12838142.json#players/1`
- `data/pioneer/Pioneer_Challenge_32_12838901.json#players/0`
- `data/pioneer/Pioneer_Challenge_32_12842931.json#players/2`
- `data/pioneer/Pioneer_Challenge_32_12843391.json#players/3`
- `data/pioneer/Pioneer_Challenge_32_12847702.json#players/2`

代表牌表：`data/pioneer/Pioneer_Challenge_32_12838142.json#players/1`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
3 Aftermath Analyst
4 Arboreal Grazer
1 Arid Archway
2 Boseiju, Who Endures
4 Crumbling Vestige
2 Echoing Deeps
3 Forest
4 Hedge Maze
4 Lotus Field
4 Lumra, Bellow of the Woods
1 Lush Oasis
1 Mirrorpool
1 Otawara, Soaring City
4 Port of Karfell
4 Scapeshift
4 Spelunking
3 The Wandering Minstrel
1 Sunken Citadel
1 Thassa's Oracle
1 Starting Town
4 Formidable Speaker
1 Glasspool Mimic
1 Emrakul, the Promised End
2 Pit of Offerings
```

**备牌**

```text
2 Ephara's Dispersal
1 Negate
1 Mystical Dispute
2 Fog
1 Pick Your Poison
1 Vibrance
4 Leyline of Sanctity
1 Mistrise Village
2 Heritage Reclamation
```

### lotus-scapeshift：black, blue, green, white（50 条）

来源：
- `data/pioneer/Pioneer_Challenge_32_12838142.json#players/16`
- `data/pioneer/Pioneer_Challenge_32_12839692.json#players/13`
- `data/pioneer/Pioneer_Challenge_32_12840559.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12841363.json#players/11`
- `data/pioneer/Pioneer_Challenge_32_12842063.json#players/19`
- `data/pioneer/Pioneer_Challenge_32_12842093.json#players/11`
- `data/pioneer/Pioneer_Challenge_32_12842496.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12842900.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12842931.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12844304.json#players/4`
- `data/pioneer/Pioneer_Challenge_32_12844304.json#players/11`
- `data/pioneer/Pioneer_Challenge_32_12844327.json#players/15`
- `data/pioneer/Pioneer_Challenge_32_12844336.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12845652.json#players/4`
- `data/pioneer/Pioneer_Challenge_32_12845684.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12845702.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12846469.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12846492.json#players/25`
- `data/pioneer/Pioneer_Challenge_32_12846501.json#players/6`
- `data/pioneer/Pioneer_Challenge_32_12846506.json#players/21`
- `data/pioneer/Pioneer_Challenge_32_12847120.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12847134.json#players/15`
- `data/pioneer/Pioneer_Challenge_32_12847143.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12847160.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12847681.json#players/5`
- `data/pioneer/Pioneer_Challenge_32_12847710.json#players/3`
- `data/pioneer/Pioneer_Challenge_32_12847715.json#players/6`
- `data/pioneer/Pioneer_Challenge_32_12848187.json#players/5`
- `data/pioneer/Pioneer_Challenge_32_12848210.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12848219.json#players/9`
- `data/pioneer/Pioneer_Challenge_32_12849485.json#players/24`
- `data/pioneer/Pioneer_Challenge_32_12849498.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12850810.json#players/5`
- `data/pioneer/Pioneer_Challenge_32_12851101.json#players/19`
- `data/pioneer/Pioneer_Challenge_32_12851646.json#players/5`
- `data/pioneer/Pioneer_Challenge_32_12851646.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12851669.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12851678.json#players/6`
- `data/pioneer/Pioneer_Challenge_32_12851678.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12851678.json#players/28`
- `data/pioneer/Pioneer_Challenge_32_12852756.json#players/28`
- `data/pioneer/Pioneer_Challenge_32_12853217.json#players/3`
- `data/pioneer/Pioneer_Challenge_32_12853672.json#players/18`
- `data/pioneer/Pioneer_Challenge_32_12855505.json#players/6`
- `data/pioneer/Pioneer_Challenge_32_12856619.json#players/7`
- `data/pioneer/Pioneer_RC_Qualifier_12839644.json#players/9`
- `data/pioneer/Pioneer_RC_Qualifier_12854053.json#players/15`
- `data/pioneer/Pioneer_RC_Super_Qualifier_12853659.json#players/17`
- `data/pioneer/Pioneer_RC_Super_Qualifier_12853659.json#players/29`
- `data/pioneer/Pioneer_Showcase_Challenge_12853164.json#players/11`

代表牌表：`data/pioneer/Pioneer_Challenge_32_12838142.json#players/16`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
4 The Wandering Minstrel
4 Lumra, Bellow of the Woods
4 Spelunking
1 Boseiju, Who Endures
1 Otawara, Soaring City
4 Underground Mortuary
4 Lotus Field
4 Scapeshift
4 Crumbling Vestige
4 Port of Karfell
1 Arid Archway
2 Forest
4 Starting Town
4 Formidable Speaker
4 Arboreal Grazer
1 Memorial to Unity
1 Blooming Marsh
2 Hedge Maze
1 Castle Garenbrig
2 Aftermath Analyst
4 Badgermole Cub
1 Vein Ripper
```

**备牌**

```text
4 Abrupt Decay
4 Culling Ritual
1 Elesh Norn, Mother of Machines
1 Pit of Offerings
1 Kaervek, the Spiteful
2 Elvish Reclaimer
1 Emrakul, the Promised End
1 Blast Zone
```

### lotus-scapeshift：black, blue, green, red, white（42 条）

来源：
- `data/pioneer/Pioneer_Challenge_32_12838147.json#players/6`
- `data/pioneer/Pioneer_Challenge_32_12838869.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12840568.json#players/13`
- `data/pioneer/Pioneer_Challenge_32_12842102.json#players/17`
- `data/pioneer/Pioneer_Challenge_32_12842473.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12842496.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12842496.json#players/18`
- `data/pioneer/Pioneer_Challenge_32_12842900.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12842908.json#players/23`
- `data/pioneer/Pioneer_Challenge_32_12842935.json#players/26`
- `data/pioneer/Pioneer_Challenge_32_12842948.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12842948.json#players/31`
- `data/pioneer/Pioneer_Challenge_32_12843782.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12843805.json#players/31`
- `data/pioneer/Pioneer_Challenge_32_12843814.json#players/24`
- `data/pioneer/Pioneer_Challenge_32_12843819.json#players/29`
- `data/pioneer/Pioneer_Challenge_32_12844297.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12844304.json#players/13`
- `data/pioneer/Pioneer_Challenge_32_12844336.json#players/26`
- `data/pioneer/Pioneer_Challenge_32_12844340.json#players/8`
- `data/pioneer/Pioneer_Challenge_32_12844340.json#players/25`
- `data/pioneer/Pioneer_Challenge_32_12844353.json#players/9`
- `data/pioneer/Pioneer_Challenge_32_12844840.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12844872.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12844872.json#players/17`
- `data/pioneer/Pioneer_Challenge_32_12845645.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12845652.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12845684.json#players/11`
- `data/pioneer/Pioneer_Challenge_32_12845684.json#players/15`
- `data/pioneer/Pioneer_Challenge_32_12846462.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12846469.json#players/13`
- `data/pioneer/Pioneer_Challenge_32_12846477.json#players/20`
- `data/pioneer/Pioneer_Challenge_32_12846492.json#players/19`
- `data/pioneer/Pioneer_Challenge_32_12847112.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12847112.json#players/17`
- `data/pioneer/Pioneer_Challenge_32_12847681.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12847702.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12847710.json#players/11`
- `data/pioneer/Pioneer_Challenge_32_12848187.json#players/12`
- `data/pioneer/Pioneer_Challenge_32_12848187.json#players/14`
- `data/pioneer/Pioneer_Challenge_32_12849448.json#players/15`
- `data/pioneer/Pioneer_RC_Qualifier_12839644.json#players/13`

代表牌表：`data/pioneer/Pioneer_Challenge_32_12838147.json#players/6`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
4 Spelunking
4 The Wandering Minstrel
1 Arid Archway
2 Forest
1 Otawara, Soaring City
1 Hedge Maze
4 Port of Karfell
1 Vibrance
2 Boseiju, Who Endures
4 Arboreal Grazer
4 Starting Town
1 Conduit Pylons
4 Lotus Field
1 Aftermath Analyst
1 Ishkanah, Grafwidow
2 Blooming Marsh
4 Scapeshift
1 Glasspool Mimic
4 Formidable Speaker
4 Lumra, Bellow of the Woods
4 Crumbling Vestige
4 Underground Mortuary
1 Wistfulness
1 Littjara Mirrorlake
```

**备牌**

```text
3 Culling Ritual
1 Emrakul, the Promised End
1 Tishana's Tidebinder
1 Wistfulness
1 Quantum Riddler
1 Ghost Vacuum
1 Summon: Leviathan
1 Vibrance
2 Tear Asunder
1 Elesh Norn, Mother of Machines
2 Abrupt Decay
```

### lotus-scapeshift：black, blue, green, red（10 条）

来源：
- `data/pioneer/Pioneer_Challenge_32_12838147.json#players/18`
- `data/pioneer/Pioneer_Challenge_32_12839669.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12840537.json#players/7`
- `data/pioneer/Pioneer_Challenge_32_12840537.json#players/9`
- `data/pioneer/Pioneer_Challenge_32_12840568.json#players/9`
- `data/pioneer/Pioneer_Challenge_32_12841340.json#players/5`
- `data/pioneer/Pioneer_Challenge_32_12841340.json#players/13`
- `data/pioneer/Pioneer_Challenge_32_12841372.json#players/10`
- `data/pioneer/Pioneer_Challenge_32_12842102.json#players/9`
- `data/pioneer/Pioneer_Challenge_32_12842466.json#players/7`

代表牌表：`data/pioneer/Pioneer_Challenge_32_12838147.json#players/18`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
4 Lumra, Bellow of the Woods
4 Spelunking
4 The Wandering Minstrel
1 Arid Archway
2 Forest
1 Otawara, Soaring City
1 Hedge Maze
4 Port of Karfell
1 Vibrance
2 Boseiju, Who Endures
4 Arboreal Grazer
4 Starting Town
1 Conduit Pylons
4 Lotus Field
1 Aftermath Analyst
1 Ishkanah, Grafwidow
2 Blooming Marsh
4 Underground Mortuary
1 Glasspool Mimic
4 Formidable Speaker
4 Crumbling Vestige
4 Scapeshift
1 Wistfulness
1 Littjara Mirrorlake
```

**备牌**

```text
3 Culling Ritual
1 Tishana's Tidebinder
1 Wistfulness
1 Quantum Riddler
1 Ghost Vacuum
2 Abrupt Decay
1 Vibrance
2 Tear Asunder
3 Leyline of Sanctity
```

### azorius-control：black, blue, white（1 条）

来源：
- `data/pioneer/Pioneer_Challenge_32_12842473.json#players/26`

代表牌表：`data/pioneer/Pioneer_Challenge_32_12842473.json#players/26`。正常土地支持诊断：black, blue, green, red, white。

**主牌**

```text
2 Meticulous Archive
1 Mirrex
3 March of Otherworldly Light
3 Anoint with Affliction
1 Go for the Throat
3 No More Lies
2 Watery Grave
2 Godless Shrine
1 Teferi, Hero of Dominaria
1 Elspeth, Storm Slayer
2 Temporary Lockdown
1 Narset, Parter of Veils
2 The Wandering Emperor
1 Supreme Verdict
3 Thoughtseize
1 Plains
1 Swamp
3 Hallowed Fountain
1 Duress
1 Eiganjo, Seat of the Empire
1 Otawara, Soaring City
3 Vanishing Verse
1 Shadowy Backstreet
3 Fatal Push
2 Gloomlake Verge
4 Bleachbone Verge
4 Floodfarm Verge
2 Beza, the Bounding Spring
1 Memory Deluge
4 Consult the Star Charts
```

**备牌**

```text
2 Dovin's Veto
3 Duress
2 Pest Control
2 Thought Distortion
1 Supreme Verdict
1 Kaheera, the Orphanguard
1 Narset, Parter of Veils
1 Elspeth, Storm Slayer
2 High Noon
```
