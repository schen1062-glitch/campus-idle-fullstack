"""
通用 Pydantic 模型：分页、错误响应等
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页查询参数（可注入到路由）"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应包装"""

    items: list[T] = Field(description="当前页数据")
    total: int = Field(ge=0, description="总记录数")
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, description="每页条数")
    total_pages: int = Field(ge=0, description="总页数")


class ErrorResponse(BaseModel):
    """统一错误响应"""

    code: str = Field(description="错误码")
    message: str = Field(description="人类可读的错误描述")
    detail: dict | None = Field(default=None, description="详细错误信息")


class SuccessResponse(BaseModel):
    """统一成功响应"""

    message: str = Field(default="ok", description="成功消息")