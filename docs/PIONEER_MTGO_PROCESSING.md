# Pioneer 私有 MTGO 处理

Pioneer 使用共享 MTGO 生成器，已接入区间统计、代表构筑、周 Top 8、
对局统计及来源完整性报告。分类规则与已确认基线保持一致，
`public: false` 保持不变。此次未启用 Landing、公开元数据或公开目录。

## 执行入口

从项目根目录使用现有 Python 模块入口，将输出放在仓库外的私有目录：

```powershell
python -m mtgmeta.mtgo --format pioneer build-statistics --output-directory C:/private/pioneer/statistics
python -m mtgmeta.mtgo --format pioneer build-matchups --output-directory C:/private/pioneer/statistics
python -m mtgmeta.mtgo --format pioneer build-top8 --output-directory C:/private/pioneer/top8
python -m mtgmeta.mtgo --format pioneer build-completeness --output-directory C:/private/pioneer/completeness
```

目录可按本机环境替换。`--output-directory` 直接传给现有共享生成器，
未指定时保持原输出路径。私有赛制仍执行公开输出边界检查，
不能借目录参数写入其他赛制的公开产品树。命令不抓取数据、不接纳赛事、
不发布页面。正式公开需另满足 ROADMAP 的完整产品与 Landing 条件。

## 2026-09-13 结果

此次处理读取仓库内 154 场、4,928 份 Pioneer 牌表。最后完整周为
2026-W36（8 月 31 日至 9 月 6 日）；W37 的两场不进入闭合区间统计。
用于人工分类参考的 3 月 30 日补充赛事仍在私有材料中，未纳入本次
仓库输入，所以统计范围与分类基线的 155 场、4,960 份不同。

| 窗口 | 实际赛事 | 已公布牌表 | 高分牌表 | Top 8 |
| --- | ---: | ---: | ---: | ---: |
| 1 周 | 4 | 128 | 75 | 32 |
| 4 周 | 19 | 608 | 329 | 152 |
| 12 周 | 75 | 2,400 | 1,173 | 600 |
| 36 周 | 152 | 4,864 | 2,276 | 1,216 |

36 周是筛选窗口，不表示已有完整 36 周历史。当前存档从 4 月 2 日开始。
牌表数量是官方公布样本，不是全场参赛人数；区间均无 Unknown。

当前没有保存的对局记录。完整性报告的对局覆盖率为 0；该值表示缺少
来源，不能解释成任何套牌的胜率。W36 高分牌表模型完整性约 60.43%，
是 75 份观察值与约 124.11 份二项模型估计值的比值，不是已知真实全量
高分人数的覆盖率，也不是分类准确率。

## 结果核对与后续

直接从原始赛事独立复算四个窗口的日期、牌表、高分、Top 8 和完整性
模型分母；核对父类和子类计数守恒及转化率。W36 高分类别计数与已确认
人工参考一致，复用既有分类身份，没有重跑分类漂移检查。
22 个生成 JSON 通过对应 Schema，四个实际命令均已生成产物；
公开格式不指定输出参数时仍使用原默认值，私有输出进入公开树会被拒绝。
统计公式与分类执行器没有修改，未运行全套机制测试。

下一步依 ROADMAP 确认 Pioneer Tabletop 赛事接入对象，并准备后续 Landing
审阅。对局来源补齐和公开上线仍需明确各自范围，本轮未进行这两项操作。
