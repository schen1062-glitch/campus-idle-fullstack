"""
用户相关的 Pydantic 请求 / 响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole, UserStatus


# ── 请求模型 ──


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=6, max_length=128, description="密码")
    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(min_length=1, description="用户名或邮箱")
    password: str = Field(min_length=1, description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")
    avatar_url: Optional[str] = Field(default=None, max_length=512, description="头像 URL")


class UserChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str = Field(min_length=1, description="旧密码")
    new_password: str = Field(min_length=6, max_length=128, description="新密码")


# ── 响应模型 ──


class UserRead(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    status: UserStatus
    last_login_at: Optional[datetime] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录/注册成功后的 token 响应"""
    access_token: str = Field(description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间（秒）")
    user: UserRead = Field(description="用户信息")