# 5 完整待定材料

输入：第4步确定数据、既定MTGO内容范围、现有周输入及实际已展示页面。
已有绑定当前数据的内容事实时复用；只有缺失时执行 `python tools/weekly_maintenance.py facts --root ROOT --format FORMAT --week WEEK --output FACTS_DIR`，得到 SOURCE 和 FACTS。它从保留输入准备本周机器事实，不更新线上 Landing。随后执行 `python tools/weekly_maintenance.py inspect --root ROOT --source SOURCE --facts FACTS --displayed-page DISPLAYED_JSON --output NEW_DIR`。
SOURCE用现有周内容JSON/YAML（format、week、all_top8、bindings、review），允许部分review缺项；机器忠实整理，不让用户写JSON。修订加 `--previous PREVIOUS_INVENTORY` 保留编号，删除不复用。实际对象和事实变化使用新引用。
用户已明确不选Feature时直接加`--no-feature`，工具保存带此决定的私有source副本。正常入口输出已包含缺项与位置，不全量打印source/facts；只在确有业务需要时展开对象。已展示摘要应覆盖已知历史展示事实，不能把“上周没有”自动解释为“从未展示”；已有具体展示决定可直接补入当前事实，无须重审历史。
工具输出只读Web、完整牌表、环境事实与待定项。首次明确是否出现未展示新类型；旧已展示配置按政策复用，不追历史收据。确定性颜色、已定名称不问；缺Feature选择与中文提醒，后续依赖只列依赖。
输出齐备立刻提交Web及必要缺项，不等英文／图片／下游草稿。禁止建议、主观筛选、代写中文或为全部候选配图。候选为空不等于无Feature。决定已全有直接6/7。
Landing中文缺失只提醒提供，不主动建议免交／空正文；用户主动改变终点或明确例外才按其指令处理。
