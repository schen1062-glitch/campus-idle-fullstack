"""
TaskService 状态机端到端测试（无需 Redis，仅验证数据库逻辑）
"""
import asyncio
import sys
sys.path.insert(0, "c:/Users/14040/Desktop/campus-idle-fullstack")
sys.stdout.reconfigure(encoding="utf-8")

from unittest.mock import AsyncMock, patch

from app.core.database import async_session_factory, init_db, close_db
from app.models.task import TaskStatus
from app.services.task_service import TaskService


mock_queue = AsyncMock()
mock_queue.enqueue.return_value = "ok"
mock_queue.ack.return_value = 0
mock_queue.requeue.return_value = 0
mock_queue.size.return_value = 0
redis_patcher = patch("app.services.task_service.RedisQueue", return_value=mock_queue)
redis_patcher.start()


async def main():
    print("=" * 60)
    print("  TaskService 状态机端到端测试")
    print("=" * 60)
    await init_db()
    print("[OK] 数据库表已创建")

    async with async_session_factory() as session:
        svc = TaskService(session)

        # ── create_task ──
        print("\n--- 1. create_task ---")
        task = await svc.create_task(
            task_type="matching",
            payload={"item_id": "abc"},
            priority=1, max_retries=2,
            retry_delay_seconds=0.5, queue_name="test",
        )
        assert task.status == TaskStatus.PENDING
        assert task.attempt_count == 0
        print(f"  [OK] id={task.id[:8]}... status={task.status.value}")

        # ── claim_task ──
        print("\n--- 2. claim_task ---")
        claimed = await svc.claim_task(task.id, worker_id="w1")
        assert claimed is not None
        assert claimed.status == TaskStatus.PROCESSING
        assert claimed.attempt_count == 1
        print(f"  [OK] status={claimed.status.value} attempt={claimed.attempt_count}")

        # 重复领取拒绝
        dup = await svc.claim_task(task.id, worker_id="w2")
        assert dup is None
        print("  [OK] CAS 原子性：重复领取被拒绝")
        # ── complete_task ──
        print("\n--- 3. complete_task ---")
        done = await svc.complete_task(task.id, result={"ok": True})
        assert done is not None
        assert done.status == TaskStatus.SUCCESS
        print(f"  [OK] status={done.status.value}")

    # ── fail_task + 重试 ──
    print("\n--- 4. fail_task + 指数退避重试 ---")
    async with async_session_factory() as session:
        svc = TaskService(session)
        t = await svc.create_task("notification", {"x": 1}, max_retries=2, retry_delay_seconds=0.1, queue_name="t")
        await svc.claim_task(t.id)

        # 第1次失败 → 应有重试
        f1 = await svc.fail_task(t.id, error_message="err1")
        assert f1.status == TaskStatus.PROCESSING and f1.next_retry_at
        from app.models.task import Task as Tbl
        st = sql_upd(Tbl).where(Tbl.id == t.id).values(next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        await session.execute(st); await session.commit()
        ret = await svc.schedule_retries()
        assert len(ret) == 1
        print(f"  [OK] 调度重试: {len(ret)} 个任务重置为 PENDING")

        # 第2次领 + 失败（还有1次机会）
        await svc.claim_task(t.id)
        f2 = await svc.fail_task(t.id, error_message="err2")
        assert f2.status == TaskStatus.PROCESSING
        st = sql_upd(Tbl).where(Tbl.id == t.id).values(next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        await session.execute(st); await session.commit()
        await svc.schedule_retries()

        # 第3次领 + 失败 → 重试耗尽
        await svc.claim_task(t.id)
        f3 = await svc.fail_task(t.id, error_message="final")
        assert f3.status == TaskStatus.FAILED
        print(f"  [OK] 重试耗尽: status={f3.status.value}")

    # ── cancel_task ──
    print("\n--- 5. cancel_task ---")
    async with async_session_factory() as session:
        svc = TaskService(session)
        t = await svc.create_task("cleanup", {}, queue_name="t")
        c = await svc.cancel_task(t.id)
        assert c is not None and c.status == TaskStatus.CANCELLED
        assert await svc.cancel_task(t.id) is None
        print(f"  [OK] 取消成功 status={c.status.value}，终态拒绝再次取消")

    # ── retry_task ──
    print("\n--- 6. retry_task(手动重试) ---")
    async with async_session_factory() as session:
        svc = TaskService(session)
        t = await svc.create_task("cleanup", {}, max_retries=1, queue_name="t")
        await svc.claim_task(t.id); await svc.fail_task(t.id, "xx")
        r = await svc.retry_task(t.id)
        assert r is not None and r.status == TaskStatus.PENDING and r.attempt_count == 0
        print(f"  [OK] 手动重试: status={r.status.value} attempt={r.attempt_count}")

    # ── list_tasks ──
    print("\n--- 7. list_tasks ---")
    async with async_session_factory() as session:
        svc = TaskService(session)
        all_t = await svc.list_tasks()
        pending_t = await svc.list_tasks(status=TaskStatus.PENDING)
        print(f"  [OK] 总任务={len(all_t)}  PENDING={len(pending_t)}")

    print("\n" + "=" * 60)
    print("  所有状态机测试通过！")
    print("=" * 60)
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
