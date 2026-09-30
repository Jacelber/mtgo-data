# 6 输入与实际页面

输入：5的对象与缺项；用户Feature有无、对象、类别、四张不同主备牌、逐条Feature中文、Landing中文；环境代表牌仅实际未决时提供。自然语言在对话累计，机器整理SOURCE，不要求重填表。
用 `inspect`核对机械缺项。缺用户输入只提醒，无委托不推荐／代写。中文定稿与明确选择直接是决定，保留原消息引用；机器英文仍须确认。牌名通过共享目录规范化，真实歧义才问。无关英文不重译。
SOURCE保留all_top8和bindings不动。仅填写review.top_copy.items：`[{order:1,text:{zh:原文,en:英文草稿}}]`；review.features为`{explicit_empty:false,items:[...]}`，每项包含destination_id（已有token）、parent_id/subtype_id（从all_top8取）、category（new_deck/new_technology）、source_order（用户选择顺序）、featured_cards（4个标准牌名）、positioning（zh/en）、supporting_facts（candidate_evidence中对应reasons，无则[]）。明确不选用explicit_empty:true及items:[]。保留中文中的`[deck:...]`链接标记并在英文对应位置使用。用户不需要填写此结构。
`python tools/weekly_maintenance.py prepare --root ROOT --source SOURCE --base-site BASE_SITE --output NEW_DIR` 准备私有实际页面。有独立本周事实时加 `--facts FACTS`，不要求先更新旧Landing。BASE_SITE是现有确定站点及完整有效资源。工具复用生产渲染数据转换，缺图报告具体缺口，不假装通过、不自动采集。
`python tools/weekly_maintenance.py check-preview --site NEW_DIR/site --format FORMAT --output CHECK_DIR --node NODE` 先按实际中英文消费者检查选中资源，然后在HTTP浏览器滚动检查实际图片。Playwright通过环境变量WEEKLY_PLAYWRIGHT指定现有安装，不重复安装。单项Feature变更且其余页面证明适用时加 `--only-feature TOKEN`，只检查受影响区域，未变化证明继续复用。
`python tools/weekly_maintenance.py serve --directory NEW_DIR/site --port PORT` 用HTTP预览。先核对本次中英文实际选中资源、图片、顺序和相关交互；已有证明复用。实际页面与待确认英文／展示齐备立即提交。
小修改仅改SOURCE对应项，以原site为base写新快照；其余文字和决定复用。原快照不得覆盖。用户确认范围可合并，不能把只确认英文当全页。
默认逐赛制处理时，下一赛制的BASE_SITE沿用上一个已确认候选的site，使后续快照保留此前页面；最后一个site自然包含本批已完成页面。无需到7再重新生成四页。已有独立候选时仅组合已确认的实际文件及依赖，无法证明无冲突的部分保留技术缺口，不重新取得业务决定。
准备后执行 `page-delta --before-site OLD_SITE --after-site NEW_SITE --format FORMAT --output DELTA_JSON`，结果feature_cards_only才可复用其余页面并只检查改变Feature。用户实际确认后执行 `accept-page --packet PREVIEW_JSON --check CHECK_DIR/result.json --evidence MESSAGE_REF --accepted-on DATE --entrypoint HTTP_URL --output NEW_ACCEPTANCE`。区域确认加 `--previous OLD_ACCEPTANCE --delta DELTA_JSON`；程序核对原页面确认、差异和本次检查绑定，不再打开浏览器重复检查。更广差异按实际范围提交，不冒充只改卡牌。
原始中文和选择通过 `record-input --packet PACKET --values VALUES --evidence MESSAGE_REF --accepted-on DATE --output NEW_RECORD` 记录；VALUES只含对应的features、copy.zh、feature.TOKEN.zh维度实际值。已有决定加 `--previous ENVELOPE`，英文和页面使用现有review_submission决定入口，不把原始输入冒充页面确认。
输出：原始输入出处、实际内容及页面对象、适用确认，供7复用。无业务变化的技术错误机器修，缺映射不重问。禁止重新筛选、采集、无关翻译、生产发布。
实际整页确认成立后，`finalize-source --root ROOT --source SOURCE --site SITE --acceptance PAGE_ACCEPTANCE --output ACCEPTED_SOURCE_JSON`把已确认页面机械对应到既有1.3内容记录；只写新的私有结果，不重跑分类或页面。它不是新的用户确认。正式交付时按既有私有review位置接入这一确定源文件，不覆盖历史submitted快照。
