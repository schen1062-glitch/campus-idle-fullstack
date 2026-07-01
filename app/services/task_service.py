from datetime import datetime, timedelta
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
            
            priority=task_data.priority or 1,
            queue_name="task_queue"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 入队（Redis 不可用时静默降级）
        try:
            await self.queue.enqueue({
                "task_id": str(task.id),
                "type": task.task_type
            })
        except Exception as e:
            print(f"[WARN] Redis enqueue failed: {e}")
        
        return TaskRead.from_orm(task)
    
    async def claim_task(self, db: AsyncSession) -> Optional[Task]:
        """Worker 领取任意 PENDING 任务"""
        stmt = select(Task).where(Task.status == TaskStatus.PENDING).limit(1)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(task)
        return task

    async def claim_task_by_id(self, db: AsyncSession, task_id: str) -> Optional[Task]:
        """按 ID 领取任务（仅 PENDING 状态可领）"""
        stmt = select(Task).where(Task.id == task_id, Task.status == TaskStatus.PENDING)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(task)
        return task
    
    async def complete_task(self, db: AsyncSession, task_id: str, result: Dict[str, Any]) -> Optional[Task]:
        """任务成功完成（返回已完成的任务对象）"""
        stmt = select(Task).where(Task.id == task_id, Task.status == TaskStatus.PROCESSING)
        result_obj = await db.execute(stmt)
        task = result_obj.scalar_one_or_none()
        
        if not task:
            return None
        
        task.status = TaskStatus.SUCCESS
        task.result = json.dumps(result)
        task.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)
        return task
    
    async def fail_task(self, db: AsyncSession, task_id: str, error: str) -> Optional[Task]:
        """任务失败处理（重试或最终失败，返回更新后的任务）"""
        stmt = select(Task).where(Task.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
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
        await db.refresh(task)
        return task
    
    async def cancel_task(self, db: AsyncSession, task_id: str) -> Optional[Task]:
        """取消任务（返回取消后的任务对象）"""
        stmt = select(Task).where(Task.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        task.status = TaskStatus.CANCELLED
        await db.commit()
        await db.refresh(task)
        return task
    
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
