# 准入与采集

先读 `docs/operations/MELEE_ADMISSION.md` 的身份、资格和注册部分。核对明确赛事 ID、官方名称／日期／主办方、已完成及非团体、受支持赛制与类别；通过赛事页和主办方日程确认每轮性质及晋级结构。两天举行不自动代表 Day 2 Swiss cut。Melee 直接请求受限时使用可用浏览器读取来源。

在隔离分支更新 `configs/melee_events.yaml`，保留证据与阶段映射；用 `schemas/melee-events.schema.json` 校验配置，再通过 `mtgmeta.melee.config.load_melee_event_registry(...).require_fetchable(EVENT_ID)` 核对采集资格。白名单与派生候选分开提交；按已授权范围完成必要 PR 集成。

正式采集前确定云端保存位置：工作流 `fetch_melee.yml`、审阅分支 `data/melee-EVENT_ID`、原始输入 checkpoint。查询该分支和已有运行；已有完整输入直接接续。确需首次采集且已获授权时：

```powershell
gh workflow run fetch_melee.yml --ref master -f event_id=EVENT_ID -f operation=collect-new
```

定位本次实际 run，查看状态及关键日志，避免按最新运行猜对象。原始输入提交后再规范化、分类；后续失败不能丢失输入。恢复已保留输入使用：

```powershell
gh workflow run fetch_melee.yml --ref master -f event_id=EVENT_ID -f operation=resume-retained -f retained_checkpoint=EXACT_CHECKPOINT_SHA
```

完整输入复用不重复 `collect-new`。空最终排名在抓对局和牌表前处理：需要用户选择 Swiss 轮次时，仅按规范进入 `review_standings_round_id` 审阅保留模式；正式最终排名补齐使用 `tools/refresh_melee_final_standings.py`。历史赛事例外不扩用于新赛事。

完成：原始输入、候选及失败点均有确切位置；记录运行、保存提交与输入校验值。进入覆盖核对，若本次只要求启动采集，则报告真实运行状态并停在该终点。
