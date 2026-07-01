"""
物品 API 路由
发布、浏览、搜索、管理
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductSearch,
    ProductRead,
    ProductListItem,
)

router = APIRouter(prefix="/products", tags=["物品管理"])


@router.post("", response_model=ProductRead, summary="发布物品")
async def create_product(
    seller_id: str = Query(..., description="卖家用户 ID"),
    body: ProductCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """发布新物品，发布后自动触发匹配任务"""
    service = ProductService()
    product = await service.create_product(db=db, seller_id=seller_id, data=body)
    return ProductRead.from_orm(product)


@router.get("/search", summary="搜索/筛选物品")
async def search_products(
    keyword: str = Query(default=None, max_length=64, description="关键词"),
    category: str = Query(default=None, description="分类"),
    price_min: float = Query(default=None, ge=0, description="最低价"),
    price_max: float = Query(default=None, ge=0, description="最高价"),
    seller_id: str = Query(default=None, description="卖家 ID"),
    status: str = Query(default=None, description="状态"),
    sort_by: str = Query(default="created_at", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """搜索物品，支持关键词、分类、价格区间、排序、分页"""
    from app.models.product import ProductCategory, ProductStatus

    # 转换枚举参数
    cat_enum = None
    if category:
        try:
            cat_enum = ProductCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效分类: {category}")

    status_enum = None
    if status:
        try:
            status_enum = ProductStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效状态: {status}")

    params = ProductSearch(
        keyword=keyword,
        category=cat_enum,
        price_min=price_min,
        price_max=price_max,
        seller_id=seller_id,
        status=status_enum,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    service = ProductService()
    products, total = await service.search_products(db=db, params=params)

    return {
        "items": [ProductListItem.from_orm(p) for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/{product_id}", response_model=ProductRead, summary="查看物品详情")
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    """查看物品详情（自动增加浏览次数）"""
    service = ProductService()
    product = await service.get_by_id_public(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="物品不存在")

    # 异步增加浏览次数（不阻塞响应）
    await service.increment_view_count(db=db, product_id=product_id)

    return ProductRead.from_orm(product)


@router.patch("/{product_id}", response_model=ProductRead, summary="更新物品")
async def update_product(
    product_id: str,
    seller_id: str = Query(..., description="卖家用户 ID"),
    body: ProductUpdate = None,
    db: AsyncSession = Depends(get_db),
):
    """更新物品信息（仅卖家可操作）"""
    service = ProductService()
    product = await service.update_product(
        db=db, product_id=product_id, seller_id=seller_id, data=body
    )
    if not product:
        raise HTTPException(status_code=404, detail="物品不存在或无权限")
    return ProductRead.from_orm(product)


@router.delete("/{product_id}", summary="删除物品")
async def delete_product(
    product_id: str,
    seller_id: str = Query(..., description="卖家用户 ID"),
    db: AsyncSession = Depends(get_db),
):
    """软删除物品（仅卖家可操作）"""
    service = ProductService()
    success = await service.delete_product(
        db=db, product_id=product_id, seller_id=seller_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="物品不存在或无权限")
    return {"message": "物品已删除"}


@router.get("/seller/{seller_id}", summary="卖家物品列表")
async def list_seller_products(
    seller_id: str,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """查看指定卖家的所有物品"""
    service = ProductService()
    products, total = await service.list_by_seller(
        db=db, seller_id=seller_id, page=page, page_size=page_size
    )
    return {
        "items": [ProductListItem.from_orm(p) for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
    }