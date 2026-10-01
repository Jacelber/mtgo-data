# PR #459 环境栏裁切图补齐

针对`e110483088f0ecfd93ab3e743a3fae40136044ac`复审的唯一剩余项。跨周读取和Feature修复保持不变。

## 修改

环境栏缺图分支改用已有`_bulk_lookup()`的名称、单面、完整双面名和首个有效牌面选择规则。给共享解析器增加一个可选的候选构造函数；默认仍是原Feature实现。环境栏适配器只读取并验证`art_crop`地址，不要求与其无关的Feature缓存元信息，不重新实现牌面选择。

原JPEG校验、裁切图形状检查、缓存复用和候选续作保持不变。缺少裁切图时明确报`No art_crop image for selected environment card ...`，不退回normal全卡图，不要求用户改名或改牌。

## 直接验证

修复前，新测试实际调用`ensure()`：正面名通过，完整`Front // Back`复现`KeyError: 'image_uris'`。

新增6个有限响应情境（`environment.rows`非空，Feature为空）：

- 正面名／完整双面名分别补齐正确的正面裁切图；两面的裁切地址不同，normal地址也不同于裁切地址。
- 两面均缺少art_crop但仍有normal时，明确失败；补回响应后继续原页面。
- 错误牌张响应被拒绝，修正后续作。
- 每次成功只补1张目标图；未受影响缓存与原选择不变，重复调用下载0张。

执行命令：

```text
python -m pytest -q tests/test_weekly_cross_week_and_faces.py tests/test_weekly_revision.py tests/test_landing_card_image_cache.py tests/test_archetype_visuals.py -k "not new_week_delivery" --tb=short
```

结果：**40 passed，1 deselected**。明确跳过已关闭的跨周集成情境，未重跑90／211项或全仓；共享解析器的Feature回归、既有环境资源情境和裁切图测试保留。所有图片来自有限本地响应，没有访问真实图片服务。

本轮没有新模型耗时或生产表现结论；不重新进行整套性能重放。行为基准、历史验收及完成记录未改，未合并、未发布。

下一步：复核此环境栏分支及新增测试，按用户意见结束本轮代码验收；生产观察仍在下一次正常获准维护进行。
