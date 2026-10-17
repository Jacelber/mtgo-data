# 1 开始／接续

输入：用户指令、已有交接和材料位置。新批范围用明确指定或既定默认；都无才问。续作继承整批范围和终点，单赛制焦点不改变批次。
动作：仅补下一动作所需缺口。已有摘要不足时使用 `python tools/review_submission.py --root ROOT resume --format FORMAT --week WEEK`。
已有任务目录时先用 `python tools/weekly_maintenance.py find-delivery --directory TASK_DIRECTORY` 定位生成／交付记录；按本次范围选择，多个不同候选不按最新时间猜选。`inspect-delivery --record RECORD` 只读查询；只有继续工作的指令才使用 `continue-delivery --record RECORD`。生成记录返回 prepared 后沿其 record 进入交付记录。查询不自动执行续作。
禁止：全历史／全环境检查、生成发布、扩展授权、未知当失效或通过。
输出：简短范围、接续位置、当前必要问题。齐备直接实际步骤，完成则结束，缺口只阻塞依赖动作。
