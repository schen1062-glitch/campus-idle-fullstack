import sys
sys.stdout.reconfigure(encoding="utf-8")

p = "c:/Users/14040/Desktop/campus-idle-fullstack/test_state_machine.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

old = (
    'from app.core.database import async_session_factory, init_db, close_db\n'
    'from app.models.task import TaskStatus\n'
    'from app.services.task_service import TaskService'
)

new = (
    'from unittest.mock import AsyncMock, patch\n'
    '\n'
    'from app.core.database import async_session_factory, init_db, close_db\n'
    'from app.models.task import TaskStatus\n'
    'from app.services.task_service import TaskService\n'
    '\n'
    '\n'
    'mock_queue = AsyncMock()\n'
    'mock_queue.enqueue.return_value = "ok"\n'
    'mock_queue.ack.return_value = 0\n'
    'mock_queue.requeue.return_value = 0\n'
    'mock_queue.size.return_value = 0\n'
    'redis_patcher = patch("app.services.task_service.RedisQueue", return_value=mock_queue)\n'
    'redis_patcher.start()'
)

c = c.replace(old, new)
with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("Updated test file")
