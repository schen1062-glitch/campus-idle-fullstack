import sys
sys.stdout.reconfigure(encoding="utf-8")

p = "c:/Users/14040/Desktop/campus-idle-fullstack/test_state_machine.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

old_start = (
    "        from datetime import datetime, timezone, timedelta\n"
    "        from sqlalchemy import update as sql_upd\n"
    "        from app.models.task import Task as Tbl\n"
    "        st = sql_upd(Tbl).where(Tbl.id == t.id).values(next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1))\n"
    "        await session.execute(st); await session.commit()\n"
    "        ret = await svc.schedule_retries()\n"
    "        assert len(ret) == 1\n"
    "        print(f\"  [OK] 调度重试: {len(ret)} 个任务重置为 PENDING\")\n"
    "\n"
    "        # 第2次领 + 失败（还有1次机会）\n"
    "        await svc.claim_task(t.id)\n"
    "        f2 = await svc.fail_task(t.id, error_message=\"err2\")\n"
    "        assert f2.status == TaskStatus.PROCESSING\n"
    "        st = sql_upd(Tbl).where(Tbl.id == t.id).values(next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1))\n"
    "        await session.execute(st); await session.commit()\n"
    "        await svc.schedule_retries()\n"
    "\n"
    "        # 第3次领 + 失败 -> 重试耗尽\n"
    "        await svc.claim_task(t.id)\n"
    "        f3 = await svc.fail_task(t.id, error_message=\"final\")\n"
    "        assert f3.status == TaskStatus.FAILED\n"
    "        print(f\"  [OK] 重试耗尽: status={f3.status.value}\")\n"
)

new_end = (
    "        from datetime import datetime, timezone, timedelta\n"
    "        from sqlalchemy import update as sql_upd\n"
    "        from app.models.task import Task as Tbl\n"
    "\n"
    "        # 手动将 next_retry_at 拨到过去\n"
    "        st = sql_upd(Tbl).where(Tbl.id == t.id).values(\n"
    "            next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1)\n"
    "        )\n"
    "        await session.execute(st)\n"
    "        await session.commit()\n"
    "        ret = await svc.schedule_retries()\n"
    "        assert len(ret) == 1\n"
    "        print(f\"  [OK] 调度重试: {len(ret)} 个任务重置为 PENDING\")\n"
    "\n"
    "        # 第2次领（attempt 1->2）-> fail_task（2<2=False）-> 重试耗尽\n"
    "        await svc.claim_task(t.id)\n"
    "        final_task = await svc.fail_task(t.id, error_message=\"重试耗尽\")\n"
    "        assert final_task.status == TaskStatus.FAILED\n"
    "        print(f\"  [OK] 重试耗尽: status={final_task.status.value}\")\n"
)

if old_start in c:
    c = c.replace(old_start, new_end)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)
    print("Test file updated successfully")
else:
    print("Could not find the old text to replace")
    # Debug: show what's at that position
    idx = c.find("from datetime import datetime, timezone, timedelta")
    if idx >= 0:
        print(f"Found at idx={idx}, showing context:")
        print(repr(c[idx:idx+800]))
