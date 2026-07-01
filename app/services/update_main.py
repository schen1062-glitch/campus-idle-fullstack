import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Fix TaskService instantiation to match new API (no db in __init__)
old = "service = TaskService(session)"
new = "service = TaskService()"
c = c.replace(old, new)

# Fix method calls: remove passing session, pass to methods instead
c = c.replace("tasks = await service.schedule_retries()", "tasks = await service.schedule_retries(db=session)")

# Add test routes before the 'if __name__' block
insert_before = 'if __name__ == "__main__":'
routes = '''
# ── 测试路由：任务状态机 ──

from fastapi import Depends
from pydantic import BaseModel
from app.schemas.task import TaskCreate
from app.core.database import get_db


class TestRetryRequest(BaseModel):
    task_id: str
    force: bool = False


@app.get("/api/v1/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """列出所有任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    tasks = await service.list_tasks(db=db)
    return {"tasks": [{"id": t.id, "type": t.task_type, "status": t.status.value, "attempt": t.attempt_count} for t in tasks]}


@app.post("/api/v1/tasks")
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    """创建任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.create_task(db=db, task_data=body)
    return {"id": task.id, "status": task.status}


@app.post("/api/v1/tasks/{task_id}/claim")
async def claim_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """领取任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    # Use claim_task with db session
    task = await service.claim_task(db=db)
    return {"id": task.id if task else None, "status": task.status.value if task else None}


@app.post("/api/v1/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """完成任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.complete_task(db=db, task_id=task_id, result={"ok": True})
    return {"id": task.id, "status": task.status.value}


@app.post("/api/v1/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "test_error", db: AsyncSession = Depends(get_db)):
    """失败任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.fail_task(db=db, task_id=task_id, error=error)
    return {"id": task.id, "status": task.status.value, "attempt": task.attempt_count}


@app.post("/api/v1/tasks/{task_id}/retry")
async def retry_task(task_id: str, body: TestRetryRequest, db: AsyncSession = Depends(get_db)):
    """手动重试（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    task = await service.retry_task(db=db, task_id=body.task_id, force=body.force)
    return {"id": task.id if task else None, "status": task.status.value if task else None}

'''

c = c.replace(insert_before, routes + insert_before)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("main.py updated")
