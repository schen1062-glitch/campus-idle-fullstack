"""
异步任务模型
实现核心状态机：pending → processing → success/failed + 重试
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Index,
    JSON as SA_JSON,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""

    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"        # 成功
    FAILED = "failed"          # 最终失败（重试耗尽）
    CANCELLED = "cancelled"    # 已取消


class Task(TimestampMixin, Base):
    """异步任务表"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID 主键",
    )
    task_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="任务类型：matching / notification / cleanup 等",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_constraint=True),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
        comment="当前状态",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        # SQLite 不支持 JSONB，用 Text 存 JSON；PostgreSQL 自动用 JSONB
        SA_JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        comment="任务参数（JSON）",
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        SA_JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="执行结果（JSON）",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="当前已尝试次数",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="最大重试次数",
    )
    retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="重试基础间隔（秒），支持指数退避",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="下次重试时间",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="优先级：0=低 1=中 2=高",
    )
    queue_name: Mapped[str] = mapped_column(
        String(64),
        default="default",
        nullable=False,
        comment="所属队列名称",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始处理时间",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间",
    )

    # ── 联合索引：用于重试调度查询 ──
    __table_args__ = (
        Index("idx_task_retry_schedule", "status", "next_retry_at"),
        Index("idx_task_type_status", "task_type", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} type={self.task_type} "
            f"status={self.status.value} attempt={self.attempt_count}>"
        )