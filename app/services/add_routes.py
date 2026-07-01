import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add only routes that match the current TaskService API
routes = '''
# ── 测试路由：任务状态机 ──

from fastapi import Depends
from pydantic import BaseModel
from app.schemas.task import TaskCreate
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


@app.get("/api/v1/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """列出所有任务（测试用）"""
    from app.services.task_service import TaskService
    from app.models.task import Task as Tbl
    from sqlalchemy import select
    service = TaskService()
    stmt = select(Tbl)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return {"tasks": [{"id": str(t.id), "type": t.task_type, "status": t.status.value, "attempt": t.attempt_count} for t in tasks]}


@app.post("/api/v1/tasks")
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    """创建任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.create_task(db=db, task_data=body)
    return {"id": task.id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/claim")
async def claim_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """领取任务（测试用）- 简化版：领取任意待处理任务"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.claim_task(db=db)
    if task:
        return {"id": str(task.id), "status": task.status.value}
    return {"id": None, "status": None}


@app.post("/api/v1/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """完成任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.complete_task(db=db, task_id=task_id, result={"ok": True})
    return {"id": str(task.id), "status": task.status.value}


@app.post("/api/v1/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "test_error", db: AsyncSession = Depends(get_db)):
    """失败任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.fail_task(db=db, task_id=task_id, error=error)
    return {"id": str(task.id), "status": task.status.value, "attempt": task.attempt_count}


@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """取消任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.cancel_task(db=db, task_id=task_id)
    if task:
        return {"id": str(task.id), "status": task.status.value}
    return {"id": None, "status": None}

'''

# Insert before if __name__
insert_point = 'if __name__ == "__main__":'
c = c.replace(insert_point, routes + "\n" + insert_point)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Routes added successfully")
