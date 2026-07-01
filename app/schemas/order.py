"""
交易订单相关的 Pydantic 请求 / 响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


# ── 请求模型 ──


class OrderCreate(BaseModel):
    """创建订单请求"""
    product_id: str = Field(..., description="物品 ID")
    quantity: int = Field(default=1, ge=1, le=100, description="数量")
    shipping_address: Optional[str] = Field(default=None, description="收货地址")
    buyer_note: Optional[str] = Field(default=None, max_length=500, description="买家备注")


class OrderUpdate(BaseModel):
    """更新订单请求（卖家/系统使用）"""
    status: Optional[OrderStatus] = Field(default=None, description="更新订单状态")
    seller_note: Optional[str] = Field(default=None, max_length=500, description="卖家备注")


class OrderSearch(BaseModel):
    """订单搜索/筛选参数"""
    buyer_id: Optional[str] = Field(default=None, description="按买家筛选")
    seller_id: Optional[str] = Field(default=None, description="按卖家筛选")
    product_id: Optional[str] = Field(default=None, description="按物品筛选")
    status: Optional[OrderStatus] = Field(default=None, description="按状态筛选")
    date_from: Optional[datetime] = Field(default=None, description="创建时间起始")
    date_to: Optional[datetime] = Field(default=None, description="创建时间截止")
    sort_by: str = Field(default="created_at", description="排序字段：created_at / total_price")
    sort_order: str = Field(default="desc", description="排序方向：asc / desc")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


# ── 响应模型 ──


class OrderRead(BaseModel):
    """订单信息响应"""
    id: str
    order_no: str
    buyer_id: str
    seller_id: str
    product_id: str
    product_title: str
    product_price: float
    quantity: int
    total_price: float
    status: OrderStatus
    shipping_address: Optional[str] = None
    buyer_note: Optional[str] = None
    seller_note: Optional[str] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    """订单列表项（缩略信息）"""
    id: str
    order_no: str
    product_title: str
    total_price: float
    status: OrderStatus
    created_at: datetime

    model_config = {"from_attributes": True}