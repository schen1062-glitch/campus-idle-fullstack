import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/app/services/task_service.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Wrap Redis calls in try/except to gracefully handle Redis unavailability
old_create = '''        # 入队
        await self.queue.enqueue({
            "task_id": str(task.id),
            "type": task.task_type
        })'''

new_create = '''        # 入队（Redis 不可用时静默降级）
        try:
            await self.queue.enqueue({
                "task_id": str(task.id),
                "type": task.task_type
            })
        except Exception as e:
            print(f"[WARN] Redis enqueue failed: {e}")'''

c = c.replace(old_create, new_create)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed Redis error handling in create_task")
