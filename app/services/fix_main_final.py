import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. update retry scheduler job to match current API
old_job = (
    "    async with async_session_factory() as session:\n"
    "        service = TaskService()\n"
    "        tasks = await service.schedule_retries(session)"
)
new_job = (
    "    async with async_session_factory() as session:\n"
    "        service = TaskService()\n"
    "        tasks = await service.schedule_retries(db=session)"
)
c = c.replace(old_job, new_job)

# 2. replace claim_task route: should claim by task_id (use simple optimistic approach)
old_claim = (
    '@app.post("/api/v1/tasks/{task_id}/claim")\n'
    'async def claim_task(task_id: str, db: AsyncSession = Depends(get_db)):\n'
    '    """领取任务（测试用）- 简化版：领取任意待处理任务"""\n'
    '    from app.services.task_service import TaskService\n'
    "    service = TaskService()\n"
    "    task = await service.claim_task(db=db)\n"
    "    if task:\n"
    '        return {"id": str(task.id), "status": task.status.value}\n'
    '    return {"id": None, "status": None}'
)
new_claim = (
    '@app.post("/api/v1/tasks/{task_id}/claim")\n'
    'async def claim_task(task_id: str, db: AsyncSession = Depends(get_db)):\n'
    '    """领取任务（测试用）"""\n'
    '    from app.services.task_service import TaskService\n'
    "    service = TaskService()\n"
    "    task = await service.claim_task(task_id=task_id, db=db)\n"
    "    if task:\n"
    '        return {"id": str(task.id), "status": task.status.value}\n'
    '    return {"id": None, "status": None}'
)
c = c.replace(old_claim, new_claim)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("main.py final fixes applied")
