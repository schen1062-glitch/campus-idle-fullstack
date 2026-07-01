"""
物品相关的 Pydantic 请求 / 响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.product import ProductStatus, ProductCategory


# ── 请求模型 ──


class ProductCreate(BaseModel):
    """发布物品请求"""
    title: str = Field(min_length=1, max_length=128, description="物品标题")
    description: Optional[str] = Field(default=None, description="物品描述")
    price: float = Field(ge=0, description="价格（元）")
    original_price: Optional[float] = Field(default=None, ge=0, description="原价（元）")
    category: ProductCategory = Field(default=ProductCategory.OTHER, description="分类")
    images: Optional[list[str]] = Field(default=None, description="图片 URL 列表")


class ProductUpdate(BaseModel):
    """更新物品请求"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=128, description="物品标题")
    description: Optional[str] = Field(default=None, description="物品描述")
    price: Optional[float] = Field(default=None, ge=0, description="价格（元）")
    original_price: Optional[float] = Field(default=None, ge=0, description="原价（元）")
    category: Optional[ProductCategory] = Field(default=None, description="分类")
    images: Optional[list[str]] = Field(default=None, description="图片 URL 列表")
    status: Optional[ProductStatus] = Field(default=None, description="状态")


class ProductSearch(BaseModel):
    """物品搜索/筛选参数"""
    keyword: Optional[str] = Field(default=None, max_length=64, description="关键词搜索标题")
    category: Optional[ProductCategory] = Field(default=None, description="按分类筛选")
    price_min: Optional[float] = Field(default=None, ge=0, description="最低价")
    price_max: Optional[float] = Field(default=None, ge=0, description="最高价")
    seller_id: Optional[str] = Field(default=None, description="按卖家筛选")
    status: Optional[ProductStatus] = Field(default=None, description="按状态筛选")
    sort_by: str = Field(default="created_at", description="排序字段：created_at / price / view_count")
    sort_order: str = Field(default="desc", description="排序方向：asc / desc")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


# ── 响应模型 ──


class ProductRead(BaseModel):
    """物品信息响应"""
    id: str
    seller_id: str
    title: str
    description: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    category: ProductCategory
    images: Optional[list] = None
    status: ProductStatus
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    """物品列表项（缩略信息）"""
    id: str
    seller_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    category: ProductCategory
    status: ProductStatus
    created_at: datetime

    model_config = {"from_attributes": True}