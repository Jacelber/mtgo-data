# 2 固定分类材料

输入：本批固定赛事、有效保留输入、同赛制classifier。MTGO全量至最多32名，指定Melee全部可用牌表。分别列来源、范围、主备数量、直接链接、缺失与已知发布阻塞；unavailable不等于Unknown，可审不等于可发布。
动作：`python tools/weekly_maintenance.py classification --root ROOT --format FORMAT --week WEEK --melee EVENT_ID --output NEW_DIR`，每个明确纳入的Melee赛事重复一个--melee；没有则省略。复用现有分类器和保留数据生成只读完整材料，Melee覆盖全部可用牌表；材料按来源产生独立submission，统一对话可以一起确认，但不能写进同一MTGO完成记录。缺口保留在blocked及本批范围内，partial不等于完整确认。只需既有MTGO专用页面时仍可用 `python tools/build_weekly_review_web.py --scope FORMAT=WEEK --output NEW_DIR --localization CATALOG`。
禁止：默认分类建议、规则编辑、影响比较、接纳发布、内容制作及为够新重抓。
输出：不可覆盖Web快照及完整范围，修订只重算受影响部分。局部决定不冒充全表确认，未齐对象保留；查看和沉默不是确认。用户意见进入3。
