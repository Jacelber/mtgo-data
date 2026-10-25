# 非 Modern 颜色接入与 Poison Dart Frog 核对

2026-10-23，Owner 要求暂缓发布并核对其他赛制。此次只核对并修正影响说明，没有修改分类规则、牌表或发布产品。

历史核对说明：本文件记录接入前的状态。2026-10-24 Owner 要求继续开发后，已实际接入三个赛制共 42 个父类；当前实现和影响以 [OTHER_FORMATS_IMPLEMENTATION.md](OTHER_FORMATS_IMPLEMENTATION.md) 为准，不能继续引用本文件的“尚未接入／零变化”描述当前代码。

## 已证实的范围

当前适配器重新读取保留输入，与冻结基线逐条比较；验证全部原输入 SHA256 和记录集合后，结果如下。

| 赛制 | 记录数 | 分类／匹配签名差异 | 配置新 color_profile 的父类数 |
| --- | ---: | ---: | ---: |
| Standard | 7148 | 0 | 0 |
| Pauper | 5897 | 0 | 0 |
| Pioneer | 5572 | 0 | 0 |

签名包括父类、子类、状态、选中／匹配／覆盖分支、冲突及错误，不包括完整条件证据或全部颜色诊断。三个赛制沿用原有规则和旧语义标记；`classifier.py` 只在父类声明 `color_profile` 时运行新颜色分析。因此不能将零差异表述为所有赛制已统一采用新颜色政策。当前派生产物仍因共享代码摘要更新而发生变化。Legacy 未纳入核对。

## Frog 实际样本

以下是对真实完整主备牌单独调用新 `deck_colors` 的诊断，**不是这些赛制当前分类器实际执行的颜色条件**。

| 赛制／情况 | 记录数 | 当前实际分类 | 新函数对 Frog 的处理 |
| --- | ---: | --- | --- |
| Standard，4 张 Starting Town | 29 | Izzet Fling 21、Izzet Prowess 1、Leyline Aggro 7 | 计入绿色 |
| Standard，无绿色土地支持 | 1 | Leyline Aggro | 不计绿色 |
| Pioneer，无绿色土地支持 | 3 | Rakdos Leyline | 不计绿色 |
| Pauper，已有 Forest 等绿色土地及绿色主体 | 1 | Gruul Ramp | 计入绿色，不增加新颜色 |

上述 34 条实际分类签名全部与冻结结果相同。Standard 的 30 条中 27 条为 MacIsaac、2 条为 Searzist、1 条为 sandydogmtg；这是比赛记录数，不是去重构筑数。

可读定位示例：

- `data/standard/Standard_Challenge_32_12840549.json#players/26`：MacIsaac，Leyline Aggro，备牌 1 张 Poison Dart Frog；没有绿色土地支持，新函数理由为 `sideboard-without-land-color-support`。
- `data/standard/Standard_Challenge_16_12856183.json#players/26`：MacIsaac，Izzet Fling，主牌 4 张 Starting Town，备牌 1 张 Poison Dart Frog。Starting Town 自身可付 1 点生命产生任意颜色，目前正常土地支持逻辑将其计为五色来源。
- `data/pioneer/Pioneer_Challenge_32_12853196.json#players/27`：MacIsaac，Rakdos Leyline，无绿色土地支持，Frog 不增加绿色。
- `data/pauper/melee/events/438329.json#decklists/760`：Gruul Ramp，主牌 14 Forest、2 Mountain，Frog 本来就在套牌既有颜色内。

29 条 Starting Town 记录还含 Callous Sell-Sword 与 Elusive Otter。新函数按有地源支持的历险两部分计色，得到 UBRG；删除备牌 Frog 后仍得到 UBRG。故潜在颜色分歧不能只归因于 Frog，也不能靠全局排除 Frog 解决。

## 对下一步的约束

已确认的“没有正常绿色土地支持的备牌 Frog 不增色”在共享函数中成立；不能把这项事实扩大为“所有带 Frog 的标准牌表都会被排除绿色”。Starting Town 与正常用色／历险用途的关系尚未据此获得新的 Owner 口径，不直接把这些标准牌表改成四色，也不静默扩大 Modern 家族例外。

后续应先将这些真实标准／先驱牌表纳入共享颜色验证样本，区分无来源、任意色地支持和历险两部分用途；再确定受影响父类是否以及如何接入新颜色判断。应保留当前分类作对照，但不能以旧标签或新函数输出作为独立正确答案。无需全面重写其他赛制规则。

复现材料保留在 `/workspace/scratch/classifier-round1/`：`compare_full.py`、三个 `candidate-{format}.json`、冻结基线及输入 manifest；`other-formats-frog-audit.json` 含全部 34 条来源、完整牌表、新函数逐牌贡献和旧／新实际分类比较。
