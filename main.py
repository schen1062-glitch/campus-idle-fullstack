"""
校园闲置流转助手 — FastAPI 入口
Phase 2 集成：Redis 连接池 + TaskService + APScheduler 重试调度
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import init_db, close_db, async_session_factory
from app.core.redis import close_redis, get_redis
from app.services.task_service import TaskService
# ── AP Scheduler（重试调度器） ──
scheduler = AsyncIOScheduler()
async def retry_scheduler_job() -> None:
    """定时扫描到期重试任务"""
    async with async_session_factory() as session:
        service = TaskService()
        tasks = await service.schedule_retries(db=session)
        if tasks:
            print(f"[SCHED] 重试调度：{len(tasks)} 个任务已重新入队")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ── 启动 ──
    await init_db()
    print("[OK] 数据库初始化完成，任务表已就绪")
    # 测试 Redis 连接（非强制，不影响应用启动）
    try:
        redis = await get_redis()
        await redis.ping()
        print("[OK] Redis 连接成功")
    except Exception as e:
        print(f"[WARN] Redis 不可用（队列功能降级）: {e}")
    # 启动重试调度器
    scheduler.add_job(
        retry_scheduler_job,
        "interval",
        seconds=settings.TASK_RETRY_SCHEDULER_INTERVAL_SECONDS,
        id="retry_scheduler",
        name="扫描到期重试任务",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[SCHED] 重试调度器已启动（间隔 {settings.TASK_RETRY_SCHEDULER_INTERVAL_SECONDS}s）")
    yield
    # ── 关闭 ──
    scheduler.shutdown(wait=False)
    await close_redis()
    await close_db()
    print("[OK] 应用资源已释放")

# ── 引入模块路由 ──
from app.api.v1.users import router as users_router
from app.api.v1.products import router as products_router
from app.api.v1.orders import router as orders_router

app = FastAPI(
    title="校园闲置流转助手",
    description="自研生产级校园二手交易 + 智能匹配平台",
    version="0.1.0",
    lifespan=lifespan,
)
# 注册模块路由
app.include_router(users_router)
app.include_router(products_router)
app.include_router(orders_router)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {
        "message": "校园闲置流转助手 API 已启动！（Phase 2）",
        "status": "healthy",
        "database": "sqlite",
        "redis": "connected (if available)",
        "queue": settings.TASK_QUEUE_DEFAULT,
    }
@app.get("/health")
async def health():
    return {"status": "ok"}
# ── 任务状态机 API ──
from fastapi import Depends
from pydantic import BaseModel
from app.schemas.task import TaskCreate
from app.core.database import get_db
@app.get("/api/v1/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """列出所有任务（测试用）"""
    from app.models.task import Task as Tbl
    from sqlalchemy import select
    stmt = select(Tbl)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return {
        "tasks": [
            {
                "id": str(t.id),
                "type": t.task_type,
                "status": t.status.value,
                "attempt": t.attempt_count,
            }
            for t in tasks
        ]
    }
@app.post("/api/v1/tasks")
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    """创建任务（测试用）"""
    service = TaskService()
    task = await service.create_task(db=db, task_data=body)
    return {"id": task.id, "status": task.status}

@app.post("/api/v1/tasks/{task_id}/claim")
async def claim_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """按 ID 领取任务（仅 PENDING 状态可领）"""
    service = TaskService()
    task = await service.claim_task_by_id(db=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或状态非 PENDING")
    return {"id": str(task.id), "status": task.status.value}

@app.post("/api/v1/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """完成任务（仅 PROCESSING 状态可完成）"""
    service = TaskService()
    task = await service.complete_task(db=db, task_id=task_id, result={"ok": True})
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或状态非 PROCESSING")
    return {"id": str(task.id), "status": task.status.value}

@app.post("/api/v1/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "test_error", db: AsyncSession = Depends(get_db)):
    """失败任务（触发重试或最终失败）"""
    service = TaskService()
    task = await service.fail_task(db=db, task_id=task_id, error=error)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"id": str(task.id), "status": task.status.value, "attempt": task.attempt_count}

@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """取消任务"""
    service = TaskService()
    task = await service.cancel_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"id": str(task.id), "status": task.status.value}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)