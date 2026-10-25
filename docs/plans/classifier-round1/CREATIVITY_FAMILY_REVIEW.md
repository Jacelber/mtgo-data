# 五色创新家族核对与 WURG 归属建议

状态：Owner 已明确同意“保留五色创新，不新增子类”。WURG 同父类分支已加入候选，颜色诊断保持真实 WURG；公开类别名称、统计归属和父类五色标识保留。尚未发布。

## 样本范围与独立依据

从当前适配器遍历全部 18,830 副保留 Modern 牌表，取主牌实际包含 Indomitable Creativity 的全部 55 条记录；不是只检索旧“五色创新”标签。原输入字节与冻结基线 manifest 逐一一致。旧标签只用于比较迁移，不能充当正确答案。原五色创新 47 条、44 个不同 75 张配置；原勇得创新 6 条、创新怨灵 2 条。赛事记录数不等于独立构筑数。

旧五色规则只要求 Creativity≥3、Mine≥1、Archon≥1，没有颜色或 Binding 条件，是更具体规则之外的宽入口；旧结果包含 3 份本轮纠正为勇得的构筑及 1 份已批准单列的红黑创新。因此不能因过去归五色就认定必须保留。

## 实际构筑分布

为审阅而按实际主牌组合分组：同时有 Teferi 和 Ending／Binding 的有 44 份；这一分组只帮助比较，不提出 Teferi 等永远必需，也不将流行辅助组件全部升级为硬条件。剩余 8 份勇得（含已确认 UBRG 子类）、1 份红黑、2 份创新怨灵具有不同配置。

| 44 份比较组内的主牌 | 出现数量分布 |
| --- | --- |
| Indomitable Creativity | 4 张：44 份 |
| Dwarven Mine | 3 张：39 份；4 张：5 份 |
| Archon of Cruelty | 1 张：19 份；2 张：5 份；3 张：20 份 |
| Wrenn and Six | 3 张：20 份；4 张：24 份 |
| Teferi, Time Raveler | 1 张：1 份；2 张：10 份；3 张：15 份；4 张：18 份 |
| Leyline Binding | 0 张：4 份；2 张：1 份；4 张：39 份 |
| Prismatic Ending | 0 张：8 份；1 张：2 份；2 张：20 份；3 张：9 份；4 张：5 份 |
| Pawpatch Formation | 2 张：21 份；3 张：19 份；4 张：4 份 |
| Persist | 0 张：42 份；1 张：2 份 |
| Faithless Looting | 0 张：43 份；1 张：1 份 |

44 份中 40 份带 Binding，4 份不带。按现有共享用途规则计算，26 份正常颜色 WUBRG、18 份 WURG；后者中 16 份已经通过此前确认的 Binding／Domain 惯例归为五色，仅本次 2 份无 Binding 牌表待定。颜色为 WURG 并不是本次才出现的新事实。

4 份无 Binding 的比较如下：

| 来源 | Ending / Teferi / Wrenn / Pawpatch | 黑色正常咒语 | 核对时候选 |
| --- | --- | --- | --- |
| MTGO 12853722，players/19 | 4 / 3 / 3 / 4 | 无；Archon 目标、Surgical 可付生命 | Unknown |
| Melee 405588，decklists/1358 | 4 / 3 / 3 / 4 | 无；Archon 目标、Surgical 可付生命 | Unknown |
| Melee 405590，decklists/787 | 4 / 3 / 4 / 4 | 1 Persist | 五色创新 |
| MTGO 12843449，players/25 | 4 / 1 / 3 / 3 | Thoughtseize、Fatal Push、Persist、Looting | 五色创新（旧勇得，候选迁移仍需整轮解释） |

两个待定样本分别与 405590/787 参照共享 51/60、54/60 张主牌。第二副差异精确为：4 Wooded Foothills 对 4 Bloodstained Mire，以及 2 Flow State 对 1 Persist＋1 Wrenn。此处的重合仅为可读比较证据，不建立相似度分类器或以比例决定归属。

两副共有 Creativity 4、Mine 3、Archon 3、Fable 4、Wrenn 3、Teferi 3、Ending 4、Pawpatch 4；没有 Looting／Persist 主牌掘坟配置，也没有 Goryo’s。没有充分依据把它们视为构筑错误或独立新家族。第二副 Blood Crypt 可为 Ending 提供第五种支付颜色；这不等于应在共享正常颜色中加入黑色。Fable 珍宝按 Owner 最新要求不作为颜色识别依据。

## 推荐的类别边界及实际影响

推荐保持 `five-color-creativity` 父类，不新建 WURG／普通五色子类；把该类别明确作为既有创新家族，容纳正常用色 WURG 的路线。这是对该家族边界的明确选择，而不是声称严格颜色仍为 WUBRG，也不是全局允许任意颜色落入五色。

技术写法：保留现有父类共同核心 Creativity≥3、Mine≥1、Archon≥1 和原五色路线；增加正常颜色恰为 WURG 的同父类分支，`subtype_id: null`。共同核心不能被分支绕过；不要求 Teferi／Ending／Pawpatch 永远必带，不增加主牌黑色牌排除或 Persist 数量门槛。勇得／UBRG、红黑、创新怨灵仍按已确认各自路线归属，既有局部优先关系保留。

共享分析结果继续报告 WURG，不往贡献中伪加黑色；公开分类名称、父类聚合、父类五色标识沿用现有配置。若 Owner 希望公开每副牌另显实际颜色，那是另一项展示选择，不能在这次默认偷偷改变。

内存中的候选规则只改变上述两副 Unknown → five-color-creativity/None。检查覆盖全部 55 副含创新牌表；其余保留牌表不满足父类 Creativity≥3 核心，因此不会被新增分支命中。初次试算没有修改正式 YAML 或赋予测试预期。Owner 确认后已加入正式候选规则和按该决定赋值的完整牌表样本，按现有流程补全量对照，无新增阶段审批。

## 全部 55 条审阅索引

| 原始位置 | 旧父类 | 核对时候选父类 | 正常咒语颜色 | Binding | Ending | Teferi | Wrenn | Persist | Looting |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `data/modern/Modern_Challenge_16_12854950.json#players/15` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_16_12854950.json#players/18` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 3 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_16_12856647.json#players/10` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_16_12856647.json#players/26` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 4 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12838136.json#players/20` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 3 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12838140.json#players/13` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 3 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12838150.json#players/8` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 3 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12838150.json#players/31` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 2 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12838154.json#players/29` | five-color-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 3 | 3 | 4 |
| `data/modern/Modern_Challenge_32_12840556.json#players/21` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12840562.json#players/22` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12842914.json#players/25` | jund-creativity | jund-creativity | black,blue,green,red | 0 | 0 | 0 | 4 | 4 | 4 |
| `data/modern/Modern_Challenge_32_12842925.json#players/27` | five-color-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 3 | 4 | 4 |
| `data/modern/Modern_Challenge_32_12844334.json#players/5` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 4 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12844343.json#players/11` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12844932.json#players/19` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 3 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12845664.json#players/7` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 4 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12854949.json#players/6` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856172.json#players/10` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856172.json#players/13` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856172.json#players/26` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 3 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856194.json#players/12` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856335.json#players/12` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_32_12856339.json#players/10` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 0 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12838113.json#players/17` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12838888.json#players/26` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12839672.json#players/26` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12842886.json#players/22` | jund-creativity | jund-creativity | black,blue,green,red | 0 | 0 | 0 | 4 | 4 | 4 |
| `data/modern/Modern_Challenge_64_12842958.json#players/23` | five-color-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 3 | 4 | 4 |
| `data/modern/Modern_Challenge_64_12843449.json#players/25` | jund-creativity | five-color-creativity | black,blue,green,red,white | 0 | 4 | 1 | 3 | 1 | 1 |
| `data/modern/Modern_Challenge_64_12845638.json#players/19` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 4 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12847704.json#players/9` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 3 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12848173.json#players/30` | jund-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 3 | 4 | 4 |
| `data/modern/Modern_Challenge_64_12853202.json#players/21` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 2 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12853722.json#players/19` | five-color-creativity | Unknown | blue,green,red,white | 0 | 4 | 3 | 3 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12854115.json#players/27` | jund-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 4 | 4 | 4 |
| `data/modern/Modern_Challenge_64_12855459.json#players/3` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_64_12855490.json#players/21` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 3 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_96_12854942.json#players/0` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 4 | 4 | 0 | 0 |
| `data/modern/Modern_Challenge_96_12854942.json#players/3` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 4 | 4 | 0 | 0 |
| `data/modern/melee/events/405588.json#decklists/1150` | grixis-creativity-goryos | grixis-creativity-goryos | black,blue,red | 0 | 0 | 0 | 0 | 0 | 4 |
| `data/modern/melee/events/405588.json#decklists/1266` | five-color-creativity | five-color-creativity | blue,green,red,white | 4 | 2 | 4 | 3 | 0 | 0 |
| `data/modern/melee/events/405588.json#decklists/1278` | jund-creativity | jund-creativity | black,green,red | 0 | 0 | 0 | 4 | 4 | 4 |
| `data/modern/melee/events/405588.json#decklists/1358` | five-color-creativity | Unknown | blue,green,red,white | 0 | 4 | 3 | 3 | 0 | 0 |
| `data/modern/melee/events/405590.json#decklists/787` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 0 | 4 | 3 | 4 | 1 | 0 |
| `data/modern/melee/events/405591.json#decklists/293` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 2 | 2 | 3 | 4 | 0 | 0 |
| `data/modern/melee/events/405591.json#decklists/598` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 1 | 2 | 4 | 0 | 0 |
| `data/modern/melee/events/405591.json#decklists/783` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 3 | 4 | 0 | 0 |
| `data/modern/melee/events/441441.json#decklists/93` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 3 | 3 | 3 | 0 | 0 |
| `data/modern/melee/events/441441.json#decklists/365` | grixis-creativity-goryos | grixis-creativity-goryos | black,blue,red | 0 | 0 | 0 | 0 | 0 | 4 |
| `data/modern/melee/events/470109.json#decklists/296` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 1 | 3 | 4 | 0 | 0 |
| `data/modern/melee/events/470109.json#decklists/364` | five-color-creativity | rakdos-creativity | black,red | 0 | 0 | 0 | 0 | 4 | 4 |
| `data/modern/melee/events/470109.json#decklists/586` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 0 | 3 | 4 | 0 | 0 |
| `data/modern/melee/events/482105.json#decklists/44` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 2 | 3 | 4 | 0 | 0 |
| `data/modern/melee/events/482105.json#decklists/46` | five-color-creativity | five-color-creativity | black,blue,green,red,white | 4 | 0 | 3 | 4 | 0 | 0 |

采用决定后的完整 Modern 对照：18,830 副中只有两份获批 WURG 样本从 Unknown 回到原父类，其他签名不变，无新增冲突。完整样本同时验证正常颜色仍为 WURG；无新增子类、名称或指示色修改。
