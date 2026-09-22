# 周审材料、决定与续作

业务边界见 [WEEKLY_MAINTENANCE](../WEEKLY_MAINTENANCE.md)。下列操作由 Codex 执行，
不要求 Owner 填文件或学命令；一次对话可明确确认多个展示项。材料与决定继续使用
DELIVERY 规定的现有私有归档，禁止进入公开产品或公共附件。

## 提交材料

每个输出目录是不可覆盖的快照，含可直达各项的 `index.html` 和 `submission.json`。
对话中引用页面的 `#条目编号`；完整分类网页支持 `#deck=赛事ID-排名`。分组请求的
`members` 必须列出全部对应 reference，不能只放代表牌表。生成器检查列出的成员
全部存在、主备牌和数量完整；Codex 仍负责判定有没有漏列本应属于该组的成员。

```text
python tools/review_submission.py classification --materials <review-data.json> --requests <groups.json> --output <new-private-directory>
python tools/review_submission.py content --input <proposed-content.json> --localization <validated-card-localization.json> --output <new-private-directory>
```

`groups.json` 是数组，每项含 `id`、`members`、`reason`、`proposed`；`names` 可分别含
`zh`、`en`。内容源使用对话导入器的 format/week/bindings/review 结构。
网页中的既有名称继续显示，但已批准语言无需重复决定；其他显示项各自待审。
内容材料必须同时传入本次已验证的牌名本地化表；人工写入的 `[[card:英文|显示名]]`
若英文牌名不存在，或显示的中文名并非同一张牌，生成器会直接拒绝，不得提交审查。
生成材料后，Codex 打开实际入口，核对链接、完整牌表、数量及视觉呈现，再请求判断。

## 记录实际决定

```text
python tools/review_submission.py record --submission <submission.json> --dimension <shown-key> --dimension <another-shown-key> --evidence <actual-conversation-reference> --accepted-on <YYYY-MM-DD> --entrypoint <actual-submitted-entry> --output <new-private-acceptance.json>
```

没有默认全选。`--previous` 可追加同一范围的已有决定。证据必须来自真实对话，
不能以文件生成、测试通过或页面打开代替。需要重新准备材料时，准备命令接受
`--decisions <acceptance.json>`：同周不变维度继续有效；跨周仅复用完全相同的名称与
视觉决定，周正文和最终页面不自动继承。不同赛制不共用决定。

W38 起完整分类网页同时输出 `full-classification-submission.json`；全表实际验收后，
将其 acceptance 对象写入相应 `data_admissions` 条目的 `classification_acceptance`。
逐条类别建议的确认不能代替完整分类验收。

内容源的 `acceptance` 字段保存 `{submission, decisions}`，或将 `review_submission.py record`
的输出通过 `tools/import_landing_conversation.py --acceptance <acceptance.json>` 单独传入；
W38 起没有对应材料或内容已变会拒绝。
Excel 使用同一合同：先用 `review_submission.py workbook --input <book.xlsx>
--output <private-directory>` 提取待提交内容，再走 content/record；将各份 acceptance
按 `format/week` 保存到工作簿同名 `.submissions.json` 后，用既有 Excel 导入器。
提取工作簿不等于批准工作簿。

## 最终页面与完成

```text
python tools/review_submission.py --root <candidate-site> preview --format <format> --entrypoint <actual-preview-url> --output <new-private-directory>
python tools/review_submission.py completion --acceptance <preview-acceptance.json> --candidate <immutable-package-directory> --publication-state <confirmed-state.json> --output <new-private-completion-evidence.json>
```

预览决定的 entrypoint 必须是实际提交给 Owner 的最终页面。材料摘要辅助定位，不能
代替页面本身；Codex 同时检查实际图片解码、颜色、名称及交互。最终页面确认记录
`final_page` 维度。completion 读取已确认发布状态，并仅解包读取同一产品包的数据，
不执行归档脚本、不重新抓取或生成；`pending` 未结束或 `health` 未 passed 不算完成。
将所得对象按赛制保存为 `{format: completion_evidence}`；既有
`tools/export_weekly_classification_review.py format-completion`（或多赛制 `completion`）
增加 `--preview-acceptances <file.json>` 后生成正式记录，W38 起公开完成缺少该证据会拒绝。
记录写入对应赛制的 `preview_acceptance`。现有私有赛制完成入口不因此要求公开发布。

## 换电脑续作

```text
python tools/review_submission.py resume --format <format> --week <week> --acceptance <optional-private-acceptance.json> --output <new-private-summary.json>
```

每个赛制独立调用。摘要从当前分类、正式内容、可选私有决定与完成记录恢复状态；
无法从这些本地来源证明的发布状态保持未知，按原操作定位查询。先向 Owner 报告
已有决定和剩余判断，再继续不依赖待定条件的授权工作。记录是工作事实，不是签名、
权限令牌或新的审批制度；不会阻止有写权限的人伪造记录，行为边界仍由代理遵守。

## 技术变更后的决定复用与历史完成

新生成的完整分类和内容 submission 在自身摘要内保存 `material_digest`。完整分类绑定
同赛制、同周、同赛事的全部记录、主备牌及分类结果；内容绑定实际统计事实与观察，
人工正文、选择、名称和视觉仍由各自维度约束。仅排除分类器身份，不排除真实结果。
技术比较使用 `classification_comparison_packet`：原始 review 的逐牌组材料摘要与 Web
补全的主备牌归一为同一表示，展示用 reference 不参与比较，原始来源定位和分类字段
仍参与。两种材料同时存在时必须一致；缺失、无效或相互矛盾的依据不能自动续用。
面向人工的 `full_classification_packet` 仍要求完整主备牌和直接引用。W38 之前的
原始 review 没有逐牌组摘要，完成导出沿用既有合同，不凭空补造技术快照。

共享判断返回 `current`（完全匹配）、`equivalent`（上述材料一致而技术摘要变化）、
`changed`（实际材料或范围变化）或 `evidence_required`（缺少可独立比较的旧材料）。
Feature 准备、内容读取/导入、Landing 接纳、分类续作和完成导出复用该判断。
只有前两种结果允许继续；缺少证据不等于应重新人工验收，也不能自动刷新历史摘要。
分类决定续用时保留原决定与原 submission 引用；不会制造新的历史决定或改写原快照。
旧包没有 material_digest 时仍可完全匹配使用，版本变化时不能仅凭版本名称推定等价。

完成查询分别报告历史记录的有效性与当前对象的差异。历史确认的发布不会因当前
分类器或资源变化被撤销；下一待审周不因这种差异倒退。当前差异保留在 handoff 中
供聚焦核查。晚到且未接纳的赛事仍需处理，但以已完成周的补充事项出现，既不获得
自动公开资格，也不重开原完成通知。W38 起新完成记录保存分类 submission 以便后续比较。
`outstanding_supplement_weeks` 按周汇总未接纳的晚到赛事，以及已接纳但尚未被该周
完成记录覆盖的赛事；后者不会因为数据准入完成而提前消失。通知依据这个完整队列
关闭补充事项，不依据 historical_changes，也不只看当前选中的最早待审周。仅有历史
技术差异时仍保留差异报告；旧 handoff 缺少该队列时不推断补充事项已经完成。
最终页面资源绑定范围和既有归档/发布校验未因这项改动放宽。


## 已完成周的追加式补充完成

已完成周新增赛事，沿用既有分类接纳、数据验证和按实际影响范围的内容/页面验收。
完成时只追加新的事实，不修改原 `completed_on`、`evidence`、`accepted_event_ids`、
分类、Landing 或预览/发布绑定，也不新增同周同赛制的第二条普通 completion。

```text
python tools/review_submission.py --root <validated-repository> supplement-completion --format <format> --week <week> --candidate <confirmed-package-directory> --publication-state <confirmed-state.json> --completed-on <actual-date> --evidence <actual-closeout-evidence> --output <new-private-fact.json>
```

入口从现有 registry 查找唯一原完成，读取真实本周 review 和已有完整分类接纳。
`covered_event_ids` 由当前已接纳范围减去有效历史覆盖推导，不接收调用者手填覆盖集合。
它验证当前数据输出，再解包读取同一个已确认的不可变产品包，核对该赛制的产物集合、
文件字节、发布绑定和实际预览；不执行归档程序，不重新采集、生成或发布。

当前归档中的页面与上一有效完成预览相同时，只保存比较快照与原决定引用，
不制造新的 Landing 或页面 Owner 验收。页面变化时增加 `--preview-acceptance <file>`，
使用该实际页面的已验收快照；入口同时核对当前页面周对应的正式内容及其维度验收。
未变化维度可以沿用既有决定，不需要重新签发日期。缺少依据或发布未确认时不输出事实。

输出是一个独立补充对象。按当前交付的授权，将完整输出追加到原 registry 的
`records[week].formats[format].supplements` 列表末尾。入口自身只导出新的私有文件，
不直接写 registry；旧事实及此前 supplements 保留。对象内的 `base_completion`
绑定原周/赛制对象，`previous` 绑定上一有效补充，自己的日期、证据和增量范围单独保存。
共享校验拒绝错周/错赛制、重叠覆盖、错序、缺失验收、未确认发布及变化页面冒充沿用。

Readiness 与 resume 汇总原完成加有效补充的覆盖，当前比较使用最新有效补充的材料；
无效补充单独报告，不抹去原完成，也不为未证明完成的赛事关闭补充通知。新一轮晚到
赛事继续产生新的补充事项。旧周缺少本入口要求的原完成依据时报告需查明，不迁移、
重建或回填 W38 之前的材料。记录的摘要用于定位与一致性核对，不是新的授权制度。
