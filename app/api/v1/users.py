"""
用户 API 路由
注册、登录、个人信息管理
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.user_service import UserService
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserUpdate,
    UserChangePassword,
    UserRead,
    TokenResponse,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """注册新用户，注册成功自动签发 JWT token"""
    service = UserService()
    try:
        return await service.register(db=db, data=body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户名/邮箱 + 密码登录，返回 JWT token"""
    service = UserService()
    try:
        return await service.login(db=db, data=body)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/{user_id}", response_model=UserRead, summary="查询用户信息")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """按 ID 查询用户公开信息"""
    service = UserService()
    user = await service.get_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserRead.from_orm(user)


@router.patch("/{user_id}", response_model=UserRead, summary="更新用户资料")
async def update_user(
    user_id: str, body: UserUpdate, db: AsyncSession = Depends(get_db)
):
    """更新昵称、头像等资料"""
    service = UserService()
    user = await service.update_profile(db=db, user_id=user_id, data=body)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserRead.from_orm(user)


@router.post("/{user_id}/change-password", summary="修改密码")
async def change_password(
    user_id: str, body: UserChangePassword, db: AsyncSession = Depends(get_db)
):
    """修改用户密码（需要旧密码验证）"""
    service = UserService()
    try:
        await service.change_password(db=db, user_id=user_id, data=body)
        return {"message": "密码修改成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", summary="用户列表")
async def list_users(
    skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """分页列出用户"""
    service = UserService()
    users = await service.list_users(db=db, skip=skip, limit=limit)
    total = await service.count_users(db=db)
    return {
        "items": [UserRead.from_orm(u) for u in users],
        "total": total,
        "skip": skip,
        "limit": limit,
    }