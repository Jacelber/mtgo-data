# 完整候选

从实施 checkout 调用入口，`--root` 指向另一个隔离候选，避免把工具自身 checkout 当数据准备区。先保留已上线固定包作为内容比较基准，明确需要保留的周报正文、选稿、展示牌和完成记录。

写本次 PLAN，例如（实际标识和步骤需替换）：

```json
{"week":"ACTUAL_WEEK","mtgo_formats":[],"melee":[{"format":"FORMAT","event_id":"EVENT_ID","steps":["classification","opportunities","stats","matchup","publish"]}]}
```

`steps` 仅列确实缺失的本地派生；其中 publish 不写远端。无共享规则变化，`mtgo_formats` 留空；需要共享分类同步时填受影响赛制，week 使用其已准入周次。同步范围由当前目录补齐，不自行扩展公开范围。

```powershell
python tools/weekly_maintenance.py stage-data --root ISOLATED_ROOT --plan PLAN --output RESULT_JSON
```

入口保留 `.generation.json`，按有效检查点复用，完成后生成 `.delivery.json`。数据阶段保留旧周报；同周仅分类变化时自动调用受保护重绑定，业务内容改变会阻断。矩阵使用紧凑编码；`size_preflight.complete=false` 是不含资源覆盖层的体积下界，不能当作完整包预算通过。

中断后使用原记录：

```powershell
python tools/weekly_maintenance.py continue-delivery --record GENERATION_RECORD
```

生成记录接续只准备候选；到 prepared 后按当前授权终点行动，不因接续命令相同而推断可以发布。

完整预览复用同一固定数据记录及正式站点组装入口：

```powershell
python tools/melee_event_delivery.py preview --record DELIVERY_RECORD --resource-site RETAINED_SITE --offline
```

有完整保留资源时使用离线模式，缺资源直接报告；需要正常补齐卡名／图片且在授权范围内时省略 `--offline`，优先复用已验证缓存。该命令不采集赛事、不归档、不部署；资源与站点写入交付记录对应的 `.work`，后续正式交付直接复用。完整构建在复制前检查含覆盖层的体积，并继续核对来源、允许范围和实际字节。

使用现有本地服务器：

```powershell
python tools/weekly_maintenance.py serve --directory PREVIEW_SITE --port AVAILABLE_PORT
```

在实际浏览器冷启动检查概览、分类名称／颜色、主备牌展开和单赛事矩阵；共享分类变化时增加新旧赛事组合。完整预览带上四周 MTGO 参考牌表等消费者依赖。先修机械问题，再把稳定入口与审阅维度交给用户。已有未变决定继续复用；等待验收期间保持审阅材料稳定。
