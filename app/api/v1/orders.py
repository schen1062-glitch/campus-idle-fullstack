"""
交易订单 API 路由
创建订单、状态流转、查询、管理
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.order_service import OrderService
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderSearch,
    OrderRead,
    OrderListItem,
)

router = APIRouter(prefix="/orders", tags=["交易订单管理"])


@router.post("", response_model=OrderRead, summary="创建订单")
async def create_order(
    buyer_id: str = Query(..., description="买家用户 ID"),
    body: OrderCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """
    创建订单
    - 校验物品在售
    - 自动生成订单号
    - 快照物品标题和价格
    - 物品状态改为 RESERVED
    - 触发通知任务
    """
    service = OrderService()
    order = await service.create_order(db=db, buyer_id=buyer_id, data=body)
    if not order:
        raise HTTPException(status_code=400, detail="物品不存在或已下架")
    return OrderRead.from_orm(order)


@router.get("/search", summary="搜索/筛选订单")
async def search_orders(
    buyer_id: str = Query(default=None, description="买家 ID"),
    seller_id: str = Query(default=None, description="卖家 ID"),
    product_id: str = Query(default=None, description="物品 ID"),
    status: str = Query(default=None, description="订单状态"),
    date_from: str = Query(default=None, description="创建时间起始（ISO格式）"),
    date_to: str = Query(default=None, description="创建时间截止（ISO格式）"),
    sort_by: str = Query(default="created_at", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """搜索订单，支持按买家、卖家、物品、状态、时间范围筛选"""
    from app.models.order import OrderStatus
    from datetime import datetime

    status_enum = None
    if status:
        try:
            status_enum = OrderStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效订单状态: {status}")

    date_from_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {date_from}")

    date_to_dt = None
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {date_to}")

    params = OrderSearch(
        buyer_id=buyer_id,
        seller_id=seller_id,
        product_id=product_id,
        status=status_enum,
        date_from=date_from_dt,
        date_to=date_to_dt,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    service = OrderService()
    orders, total = await service.search_orders(db=db, params=params)

    return {
        "items": [OrderListItem.from_orm(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/{order_id}", response_model=OrderRead, summary="查看订单详情")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """查看订单详情"""
    service = OrderService()
    order = await service.get_by_id(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return OrderRead.from_orm(order)


@router.patch("/{order_id}", response_model=OrderRead, summary="更新订单状态")
async def update_order(
    order_id: str,
    user_id: str = Query(..., description="操作用户 ID"),
    body: OrderUpdate = None,
    db: AsyncSession = Depends(get_db),
):
    """
    更新订单状态（状态机流转）
    - PENDING → PAID / CANCELLED
    - PAID → SHIPPED / REFUNDING
    - SHIPPED → COMPLETED / REFUNDING
    - REFUNDING → REFUNDED / SHIPPED
    """
    service = OrderService()
    order = await service.update_order_status(
        db=db, order_id=order_id, user_id=user_id, data=body
    )
    if not order:
        raise HTTPException(status_code=400, detail="订单不存在或状态流转不合法")
    return OrderRead.from_orm(order)


@router.post("/{order_id}/cancel", response_model=OrderRead, summary="取消订单")
async def cancel_order(
    order_id: str,
    user_id: str = Query(..., description="操作用户 ID"),
    db: AsyncSession = Depends(get_db),
):
    """取消订单（仅 PENDING 状态可取消），自动恢复物品状态为 ACTIVE"""
    service = OrderService()
    order = await service.cancel_order(db=db, order_id=order_id, user_id=user_id)
    if not order:
        raise HTTPException(status_code=400, detail="订单不存在或无法取消")
    return OrderRead.from_orm(order)


@router.get("/buyer/{buyer_id}", summary="买家订单列表")
async def list_buyer_orders(
    buyer_id: str,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """查看指定买家的所有订单"""
    service = OrderService()
    orders, total = await service.list_by_buyer(
        db=db, buyer_id=buyer_id, page=page, page_size=page_size
    )
    return {
        "items": [OrderListItem.from_orm(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/seller/{seller_id}", summary="卖家订单列表")
async def list_seller_orders(
    seller_id: str,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """查看指定卖家的所有订单"""
    service = OrderService()
    orders, total = await service.list_by_seller(
        db=db, seller_id=seller_id, page=page, page_size=page_size
    )
    return {
        "items": [OrderListItem.from_orm(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats/count/{status}", summary="按状态统计订单数")
async def count_orders_by_status(
    status: str,
    db: AsyncSession = Depends(get_db),
):
    """统计指定状态的订单数量"""
    from app.models.order import OrderStatus

    try:
        status_enum = OrderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效订单状态: {status}")

    service = OrderService()
    count = await service.count_by_status(db=db, status=status_enum)
    return {"status": status, "count": count}