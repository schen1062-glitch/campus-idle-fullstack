"""
物品 ORM 模型
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProductStatus(str, enum.Enum):
    """物品状态枚举"""
    ACTIVE = "active"       # 在售
    RESERVED = "reserved"   # 已预定
    SOLD = "sold"           # 已售出
    DELETED = "deleted"     # 已删除（软删除）


class ProductCategory(str, enum.Enum):
    """物品分类枚举"""
    TEXTBOOK = "textbook"           # 教材
    ELECTRONICS = "electronics"     # 电子产品
    DAILY_USE = "daily_use"         # 日用品
    SPORTS = "sports"               # 体育用品
    CLOTHING = "clothing"           # 衣物
    OTHER = "other"                 # 其他


class Product(TimestampMixin, Base):
    """物品表"""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID 主键",
    )
    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="发布者用户 ID",
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="物品标题",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="物品描述",
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="价格（元）",
    )
    original_price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="原价（元）",
    )
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category", create_constraint=True),
        default=ProductCategory.OTHER,
        nullable=False,
        index=True,
        comment="分类",
    )
    images: Mapped[Optional[list]] = mapped_column(
        SA_JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=list,
        comment="图片 URL 列表",
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", create_constraint=True),
        default=ProductStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="状态：active / reserved / sold / deleted",
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="浏览次数",
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="软删除标记",
    )

    def __repr__(self) -> str:
        return (
            f"<Product id={self.id} title={self.title} "
            f"price={self.price} status={self.status.value}>"
        )