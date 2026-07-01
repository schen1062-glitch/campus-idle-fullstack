"""
BaseTask — 抽象任务基类
所有异步任务处理器应继承此类，实现 execute 方法
内置执行追踪、状态更新、异常处理与重试逻辑
"""

from __future__ import annotations

import abc
import logging
import time
import traceback
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class BaseTask(abc.ABC):
    """
    抽象任务基类

    子类必须实现:
        async def execute(self, task_id: str, task_type: str, payload: dict) -> dict | None

    子类可覆盖:
        max_retries, retry_delay_seconds 以自定义重试策略
    """

    # 子类可覆盖
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    def __init__(self) -> None:
        self._task_type: str = ""

    @property
    @abc.abstractmethod
    def task_type(self) -> str:
        """返回此处理器负责的任务类型标识"""
        ...

    # ────────────────────── 核心执行入口 ──────────────────────

    async def run(self, task_id: str, payload: dict[str, Any]) -> None:
        """
        外部调用入口：
        1. CAS 领取任务
        2. 调用子类 execute
        3. 成功 → complete_task；异常 → fail_task
        """
        session: AsyncSession | None = None
        try:
            # 创建独立会话
            async with async_session_factory() as session:
                service = TaskService(session)

                # 1. CAS 领取
                task = await service.claim_task(task_id)
                if task is None:
                    logger.warning("任务 %s 已被其他 worker 领取，跳过", task_id)
                    return

                # 2. 执行子类逻辑
                start_time = time.monotonic()
                logger.info(
                    "开始执行任务 task=%s type=%s payload=%s",
                    task_id, self.task_type, payload,
                )

                result = await self.execute(task_id, self.task_type, payload)

                elapsed = time.monotonic() - start_time
                result = result or {}
                # 注入执行元数据
                result["_meta"] = {
                    "duration_seconds": round(elapsed, 3),
                    "worker": self.__class__.__name__,
                }

                # 3. 标记完成
                await service.complete_task(task_id, result=result)
                logger.info(
                    "任务执行成功 task=%s type=%s duration=%.2fs",
                    task_id, self.task_type, elapsed,
                )

        except Exception as exc:
            elapsed = time.monotonic() - start_time if "start_time" in dir() else 0.0
            error_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            logger.error(
                "任务执行异常 task=%s type=%s duration=%.2fs error=%s",
                task_id, self.task_type, elapsed, error_msg,
            )

            # 使用新会话执行失败处理
            try:
                async with async_session_factory() as session:
                    service = TaskService(session)
                    await service.fail_task(
                        task_id=task_id,
                        error_message=error_msg[:2000],  # 截断长错误
                    )
            except Exception as fail_err:
                logger.error(
                    "fail_task 调用失败 task=%s error=%s",
                    task_id, fail_err,
                )

        finally:
            if session is not None and session.is_active:
                await session.close()

    # ────────────────────── 子类必须实现 ──────────────────────

    @abc.abstractmethod
    async def execute(
        self,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        子类实现具体的任务逻辑

        Args:
            task_id: 任务 ID（UUID）
            task_type: 任务类型标识
            payload: 任务参数

        Returns:
            执行结果 dict（可选），将存入 Task.result
        """
        ...

    # ────────────────────── 工具方法 ──────────────────────

    async def update_progress(
        self,
        session: AsyncSession,
        task_id: str,
        progress: float,
        message: str = "",
    ) -> None:
        """
        更新任务进度（在长任务中调用）
        将进度信息写入 result 字段
        """
        from sqlalchemy import update as sql_update

        from app.models.task import Task

        stmt = (
            sql_update(Task)
            .where(Task.id == task_id)
            .values(
                result={
                    "progress": progress,
                    "message": message,
                }
            )
        )
        await session.execute(stmt)
        await session.commit()
        logger.debug("任务进度 task=%s progress=%.1f%% %s", task_id, progress * 100, message)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} task_type={self.task_type}>"
</file_content>