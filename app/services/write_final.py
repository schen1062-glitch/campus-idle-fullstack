import sys
sys.stdout.reconfigure(encoding="utf-8")

path = "c:/Users/14040/Desktop/campus-idle-fullstack/app/services/task_service.py"

content = '''from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisQueue
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskRead


class TaskService:
    """任务状态机核心服务"""
    
    def __init__(self):
        self.queue = RedisQueue("task_queue")
    
    async def create_task(self, db: AsyncSession, task_data: TaskCreate) -> TaskRead:
        """创建新任务"""
        task = Task(
            task_type=task_data.task_type,
            payload=task_data.payload,
            status=TaskStatus.PENDING,
            max_retries=task_data.max_retries or 3,
            retry_delay_seconds=task_data.retry_delay_seconds or 60,
            priority=task_data.priority or 1,
            queue_name="task_queue"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 入队
        await self.queue.enqueue({
            "task_id": str(task.id),
            "type": task.task_type
        })
        
        return TaskRead.from_orm(task)
    
    async def claim_task(self, db: AsyncSession) -> Optional[Task]:
        """Worker 领取任务（CAS）"""
        # 简单实现：查找 PENDING 任务
        stmt = select(Task).where(Task.status == TaskStatus.PENDING).limit(1)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(task)
        return task
    
    async def complete_task(self, db: AsyncSession, task_id: str, result: Dict[str, Any]):
        """任务成功完成"""
        stmt = update(Task).where(Task.id == task_id).values(
            status=TaskStatus.SUCCESS,
            result=json.dumps(result),
            completed_at=datetime.utcnow()
        )
        await db.execute(stmt)
        await db.commit()
    
    async def fail_task(self, db: AsyncSession, task_id: str, error: str):
        """任务失败处理（重试或最终失败）"""
        stmt = select(Task).where(Task.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return
        
        task.attempt_count += 1
        task.error_message = error
        
        if task.attempt_count < task.max_retries:
            # 重试
            task.status = TaskStatus.PENDING
            delay = task.retry_delay_seconds * (2 ** (task.attempt_count - 1))
            task.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            await self.queue.requeue({"task_id": str(task.id), "type": task.task_type})
        else:
            task.status = TaskStatus.FAILED
        
        await db.commit()
    
    async def cancel_task(self, db: AsyncSession, task_id: str):
        """取消任务"""
        stmt = update(Task).where(Task.id == task_id).values(status=TaskStatus.CANCELLED)
        await db.execute(stmt)
        await db.commit()
    
    async def schedule_retries(self, db: AsyncSession):
        """扫描并重新调度到期重试任务"""
        now = datetime.utcnow()
        stmt = select(Task).where(
            Task.status == TaskStatus.PENDING,
            Task.next_retry_at <= now
        )
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        
        for task in tasks:
            await self.queue.enqueue({"task_id": str(task.id), "type": task.task_type})
        
        return tasks
'''

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written {len(content)} chars")
