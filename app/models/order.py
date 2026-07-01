"""
交易订单 ORM 模型
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OrderStatus(str, enum.Enum):
    """订单状态枚举"""
    PENDING = "pending"             # 待付款
    PAID = "paid"                   # 已付款
    SHIPPED = "shipped"             # 已发货
    COMPLETED = "completed"         # 已完成
    CANCELLED = "cancelled"         # 已取消
    REFUNDING = "refunding"         # 退款中
    REFUNDED = "refunded"           # 已退款


class Order(TimestampMixin, Base):
    """交易订单表"""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID 主键",
    )
    order_no: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        comment="订单号（可读编号）",
    )
    buyer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="买家用户 ID",
    )
    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="卖家用户 ID",
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="物品 ID",
    )
    product_title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="下单时物品标题（快照）",
    )
    product_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="下单时物品单价（快照）",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="数量",
    )
    total_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="总价（单价 × 数量）",
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_constraint=True),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
        comment="状态：pending / paid / shipped / completed / cancelled / refunding / refunded",
    )
    shipping_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="收货地址",
    )
    buyer_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="买家备注",
    )
    seller_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="卖家备注",
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="付款时间",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间",
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="取消时间",
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="软删除标记",
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} order_no={self.order_no} "
            f"status={self.status.value} total={self.total_price}>"
        )