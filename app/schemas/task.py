"""
任务相关的 Pydantic 请求/响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.task import TaskStatus


# ── 请求模型 ──


class TaskCreate(BaseModel):
    """创建任务的请求"""

    task_type: str = Field(
        min_length=1,
        max_length=64,
        description="任务类型：matching / notification / cleanup 等",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="任务参数",
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=2,
        description="优先级：0=低 1=中 2=高",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数",
    )
    queue_name: str = Field(
        default="default",
        max_length=64,
        description="队列名称",
    )


class TaskFilter(BaseModel):
    """任务查询过滤参数"""

    status: TaskStatus | None = Field(default=None, description="按状态筛选")
    task_type: str | None = Field(default=None, max_length=64, description="按类型筛选")
    date_from: datetime | None = Field(default=None, description="创建时间起始")
    date_to: datetime | None = Field(default=None, description="创建时间截止")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class TaskRetryRequest(BaseModel):
    """手动重试请求"""

    force: bool = Field(
        default=False,
        description="是否强制重试（即使状态不是 failed）",
    )


# ── 响应模型 ──


class TaskRead(BaseModel):
    """任务查询响应"""

    id: str
    task_type: str
    status: TaskStatus
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    error_message: str | None
    attempt_count: int
    max_retries: int
    retry_delay_seconds: float
    next_retry_at: datetime | None
    priority: int
    queue_name: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # 兼容 ORM 模式


class TaskCreatedResponse(BaseModel):
    """创建成功响应"""

    id: str
    status: TaskStatus = TaskStatus.PENDING
    message: str = "任务已创建"