import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Fix list_tasks route: use manual dict instead of ORM objects
old_list = '''@app.get("/api/v1/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """列出所有任务（测试用）"""
    from app.services.task_service import TaskService
    service = TaskService()
    tasks = await service.list_tasks(db=db)
    return {"tasks": [{"id": t.id, "type": t.task_type, "status": t.status.value, "attempt": t.attempt_count} for t in tasks]}'''

new_list = '''@app.get("/api/v1/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """列出所有任务（测试用）"""
    from app.services.task_service import TaskService
    from app.models.task import Task as Tbl
    service = TaskService()
    tasks = await service.list_tasks(db=db)
    return {"tasks": [{"id": str(t.id), "type": t.task_type, "status": t.status.value, "attempt": t.attempt_count} for t in tasks]}'''

c = c.replace(old_list, new_list)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("list_tasks route fixed")
