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
