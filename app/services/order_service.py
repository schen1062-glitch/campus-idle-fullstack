"""
交易订单业务逻辑服务
创建订单、状态流转、查询，下单后自动触发通知任务
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_, or_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.product import Product, ProductStatus
from app.schemas.order import OrderCreate, OrderUpdate, OrderSearch, OrderRead
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


class OrderService:
    """交易订单业务逻辑"""

    def __init__(self):
        self.task_service = TaskService()

    # ── 工具方法 ──

    @staticmethod
    def _generate_order_no() -> str:
        """生成可读订单号：O + 时间戳(12位) + 随机后缀(4位)"""
        ts = datetime.utcnow().strftime("%y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:4].upper()
        return f"O{ts}{suffix}"

    # ── 查询辅助 ──

    async def get_by_id(self, db: AsyncSession, order_id: str) -> Optional[Order]:
        """按 ID 查询订单"""
        stmt = select(Order).where(
            Order.id == order_id,
            Order.is_deleted == False,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_no(self, db: AsyncSession, order_no: str) -> Optional[Order]:
        """按订单号查询"""
        stmt = select(Order).where(
            Order.order_no == order_no,
            Order.is_deleted == False,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── 核心业务 ──

    async def create_order(
        self, db: AsyncSession, buyer_id: str, data: OrderCreate
    ) -> Optional[Order]:
        """
        创建订单
        1. 校验物品存在且状态为 ACTIVE
        2. 创建订单记录（快照物品标题和价格）
        3. 将物品状态改为 RESERVED
        4. 触发通知任务
        """
        # 1. 校验物品
        stmt = select(Product).where(
            Product.id == data.product_id,
            Product.is_deleted == False,
            Product.status == ProductStatus.ACTIVE,
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return None

        # 2. 创建订单
        total_price = round(product.price * data.quantity, 2)
        order = Order(
            order_no=self._generate_order_no(),
            buyer_id=buyer_id,
            seller_id=product.seller_id,
            product_id=product.id,
            product_title=product.title,
            product_price=product.price,
            quantity=data.quantity,
            total_price=total_price,
            status=OrderStatus.PENDING,
            shipping_address=data.shipping_address,
            buyer_note=data.buyer_note,
        )
        db.add(order)

        # 3. 物品状态改为 RESERVED
        product.status = ProductStatus.RESERVED

        await db.commit()
        await db.refresh(order)

        # 4. 触发通知任务
        try:
            task_data = TaskCreate(
                task_type="notification",
                payload={
                    "order_id": str(order.id),
                    "order_no": order.order_no,
                    "buyer_id": buyer_id,
                    "seller_id": product.seller_id,
                    "product_id": str(product.id),
                    "product_title": product.title,
                    "total_price": total_price,
                    "action": "order_created",
                },
                priority=1,
            )
            await self.task_service.create_task(db=db, task_data=task_data)
            print(f"[ORDER] 通知任务已触发: order_id={order.id}")
        except Exception as e:
            print(f"[WARN] 通知任务创建失败（不影响下单）: {e}")

        return order

    async def update_order_status(
        self, db: AsyncSession, order_id: str, user_id: str, data: OrderUpdate
    ) -> Optional[Order]:
        """
        更新订单状态（状态机流转）
        - 买家可取消 PENDING 订单
        - 卖家可标记 PAID → SHIPPED
        - 买家可确认 COMPLETED
        - 卖家/买家可发起 REFUNDING
        """
        order = await self.get_by_id(db, order_id)
        if not order:
            return None

        new_status = data.status
        if not new_status:
            # 仅更新备注
            if data.seller_note is not None:
                order.seller_note = data.seller_note
            await db.commit()
            await db.refresh(order)
            return order

        # 状态机校验
        valid_transition = self._validate_transition(order.status, new_status, user_id, order)
        if not valid_transition:
            return None

        # 执行状态变更
        order.status = new_status
        now = datetime.utcnow()

        if new_status == OrderStatus.PAID:
            order.paid_at = now
        elif new_status == OrderStatus.COMPLETED:
            order.completed_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
            # 取消订单时恢复物品状态为 ACTIVE
            await self._restore_product_status(db, order.product_id)
        elif new_status == OrderStatus.REFUNDED:
            # 退款完成时恢复物品状态为 ACTIVE
            await self._restore_product_status(db, order.product_id)

        if data.seller_note is not None:
            order.seller_note = data.seller_note

        await db.commit()
        await db.refresh(order)

        # 状态变更后触发通知任务
        try:
            task_data = TaskCreate(
                task_type="notification",
                payload={
                    "order_id": str(order.id),
                    "order_no": order.order_no,
                    "new_status": new_status.value,
                    "action": "order_status_changed",
                },
                priority=1,
            )
            await self.task_service.create_task(db=db, task_data=task_data)
        except Exception as e:
            print(f"[WARN] 状态变更通知任务创建失败: {e}")

        return order

    @staticmethod
    def _validate_transition(
        current: OrderStatus, target: OrderStatus, user_id: str, order: Order
    ) -> bool:
        """校验订单状态流转是否合法"""
        transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.REFUNDING],
            OrderStatus.SHIPPED: [OrderStatus.COMPLETED, OrderStatus.REFUNDING],
            OrderStatus.REFUNDING: [OrderStatus.REFUNDED, OrderStatus.SHIPPED],
        }
        allowed = transitions.get(current, [])
        return target in allowed

    @staticmethod
    async def _restore_product_status(db: AsyncSession, product_id: str) -> None:
        """恢复物品状态为 ACTIVE"""
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product and product.status == ProductStatus.RESERVED:
            product.status = ProductStatus.ACTIVE
            await db.commit()

    async def cancel_order(
        self, db: AsyncSession, order_id: str, user_id: str
    ) -> Optional[Order]:
        """取消订单（快捷方法）"""
        return await self.update_order_status(
            db=db,
            order_id=order_id,
            user_id=user_id,
            data=OrderUpdate(status=OrderStatus.CANCELLED),
        )

    # ── 搜索与列表 ──

    async def search_orders(
        self, db: AsyncSession, params: OrderSearch
    ) -> tuple[list[Order], int]:
        """搜索/筛选订单，返回 (列表, 总数)"""
        conditions = [Order.is_deleted == False]

        if params.buyer_id:
            conditions.append(Order.buyer_id == params.buyer_id)
        if params.seller_id:
            conditions.append(Order.seller_id == params.seller_id)
        if params.product_id:
            conditions.append(Order.product_id == params.product_id)
        if params.status:
            conditions.append(Order.status == params.status)
        if params.date_from:
            conditions.append(Order.created_at >= params.date_from)
        if params.date_to:
            conditions.append(Order.created_at <= params.date_to)

        # 排序
        sort_field = Order.created_at
        if params.sort_by == "total_price":
            sort_field = Order.total_price

        sort_expr = sort_field.desc() if params.sort_order == "desc" else sort_field.asc()

        # 总数
        count_stmt = select(sa_func.count()).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # 分页数据
        offset = (params.page - 1) * params.page_size
        stmt = (
            select(Order)
            .where(and_(*conditions))
            .order_by(sort_expr)
            .offset(offset)
            .limit(params.page_size)
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())

        return orders, total

    async def list_by_buyer(
        self, db: AsyncSession, buyer_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        """查询买家的所有订单"""
        conditions = [
            Order.buyer_id == buyer_id,
            Order.is_deleted == False,
        ]

        count_stmt = select(sa_func.count()).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())

        return orders, total

    async def list_by_seller(
        self, db: AsyncSession, seller_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        """查询卖家的所有订单"""
        conditions = [
            Order.seller_id == seller_id,
            Order.is_deleted == False,
        ]

        count_stmt = select(sa_func.count()).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())

        return orders, total

    async def count_by_status(self, db: AsyncSession, status: OrderStatus) -> int:
        """按状态统计订单数"""
        stmt = select(sa_func.count()).where(
            Order.is_deleted == False,
            Order.status == status,
        )
        result = await db.execute(stmt)
        return result.scalar_one()