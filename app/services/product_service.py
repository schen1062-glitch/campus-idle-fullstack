"""
物品业务逻辑服务
发布、浏览、搜索，发布后自动触发匹配任务
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, or_, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStatus, ProductCategory
from app.schemas.product import ProductCreate, ProductUpdate, ProductSearch, ProductRead
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


class ProductService:
    """物品业务逻辑"""

    def __init__(self):
        self.task_service = TaskService()

    # ── 查询辅助 ──

    async def get_by_id(self, db: AsyncSession, product_id: str) -> Optional[Product]:
        """按 ID 查询物品"""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_public(self, db: AsyncSession, product_id: str) -> Optional[Product]:
        """按 ID 查询公开物品（用户可见，含 reserved/sold）"""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False,
            Product.status != ProductStatus.DELETED,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── 核心业务 ──

    async def create_product(
        self, db: AsyncSession, seller_id: str, data: ProductCreate
    ) -> Product:
        """发布物品，自动触发匹配任务"""
        product = Product(
            seller_id=seller_id,
            title=data.title,
            description=data.description,
            price=data.price,
            original_price=data.original_price,
            category=data.category,
            images=data.images,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

        # ── 发布后自动创建匹配任务 ──
        try:
            task_data = TaskCreate(
                task_type="matching",
                payload={
                    "product_id": str(product.id),
                    "seller_id": seller_id,
                    "category": product.category.value,
                    "title": product.title,
                    "price": product.price,
                },
                priority=1,
            )
            await self.task_service.create_task(db=db, task_data=task_data)
            print(f"[PRODUCT] 匹配任务已触发: product_id={product.id}")
        except Exception as e:
            print(f"[WARN] 匹配任务创建失败（不影响发布）: {e}")

        return product

    async def update_product(
        self, db: AsyncSession, product_id: str, seller_id: str, data: ProductUpdate
    ) -> Optional[Product]:
        """更新物品（仅卖家可更新）"""
        product = await self.get_by_id(db, product_id)
        if not product or product.seller_id != seller_id:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
        return product

    async def delete_product(
        self, db: AsyncSession, product_id: str, seller_id: str
    ) -> bool:
        """软删除物品（仅卖家可删除）"""
        product = await self.get_by_id(db, product_id)
        if not product or product.seller_id != seller_id:
            return False

        product.is_deleted = True
        product.status = ProductStatus.DELETED
        await db.commit()
        return True

    async def increment_view_count(self, db: AsyncSession, product_id: str) -> None:
        """增加浏览次数"""
        product = await self.get_by_id_public(db, product_id)
        if product:
            product.view_count += 1
            await db.commit()

    # ── 搜索与列表 ──

    async def search_products(
        self, db: AsyncSession, params: ProductSearch
    ) -> tuple[list[Product], int]:
        """搜索/筛选物品，返回 (列表, 总数)"""
        conditions = [
            Product.is_deleted == False,
            Product.status.in_([ProductStatus.ACTIVE, ProductStatus.RESERVED]),
        ]

        # 关键词搜索标题
        if params.keyword:
            conditions.append(Product.title.ilike(f"%{params.keyword}%"))

        # 分类筛选
        if params.category:
            conditions.append(Product.category == params.category)

        # 价格范围
        if params.price_min is not None:
            conditions.append(Product.price >= params.price_min)
        if params.price_max is not None:
            conditions.append(Product.price <= params.price_max)

        # 卖家筛选
        if params.seller_id:
            conditions.append(Product.seller_id == params.seller_id)

        # 状态筛选
        if params.status:
            conditions.append(Product.status == params.status)

        # 排序
        sort_field = Product.created_at
        if params.sort_by == "price":
            sort_field = Product.price
        elif params.sort_by == "view_count":
            sort_field = Product.view_count

        sort_expr = sort_field.desc() if params.sort_order == "desc" else sort_field.asc()

        # 总数
        count_stmt = select(sa_func.count()).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # 分页数据
        offset = (params.page - 1) * params.page_size
        stmt = (
            select(Product)
            .where(and_(*conditions))
            .order_by(sort_expr)
            .offset(offset)
            .limit(params.page_size)
        )
        result = await db.execute(stmt)
        products = list(result.scalars().all())

        return products, total

    async def list_by_seller(
        self, db: AsyncSession, seller_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[Product], int]:
        """查询卖家的所有物品"""
        conditions = [
            Product.seller_id == seller_id,
            Product.is_deleted == False,
        ]

        count_stmt = select(sa_func.count()).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(Product)
            .where(and_(*conditions))
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        products = list(result.scalars().all())

        return products, total

    async def count_active(self, db: AsyncSession) -> int:
        """统计在售物品总数"""
        stmt = select(sa_func.count()).where(
            Product.is_deleted == False,
            Product.status == ProductStatus.ACTIVE,
        )
        result = await db.execute(stmt)
        return result.scalar_one()