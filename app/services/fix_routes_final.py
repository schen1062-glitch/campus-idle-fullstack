import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Remove the broken test routes block entirely
start_marker = "\n\n\n# ── 测试路由：任务状态机 ──"
end_marker = 'if __name__ == "__main__":'

start_idx = c.find(start_marker)
end_idx = c.find(end_marker)

if start_idx != -1 and end_idx != -1:
    c = c[:start_idx] + "\n\n" + c[end_idx:]
    print("Removed broken test routes")
else:
    print("Markers not found, checking...")
    print(f"start_idx={start_idx}, end_idx={end_idx}")

# Also fix the retry_scheduler_job to use the correct API
c = c.replace(
    "service = TaskService()\n        tasks = await service.schedule_retries(db=session)",
    "service = TaskService()\n        tasks = await service.schedule_retries(session)"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("main.py fixed")
