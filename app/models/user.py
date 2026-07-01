"""
用户 ORM 模型 + 权限枚举
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, enum.Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    DISABLED = "disabled"
    BANNED = "banned"


class User(TimestampMixin, Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID 主键",
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名",
    )
    email: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="密码哈希",
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="昵称",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="头像 URL",
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_constraint=True),
        default=UserRole.USER,
        nullable=False,
        comment="角色：admin / user",
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", create_constraint=True),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="状态：active / disabled / banned",
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="邮箱是否已验证",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="软删除标记",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} username={self.username} "
            f"role={self.role.value} status={self.status.value}>"
        )