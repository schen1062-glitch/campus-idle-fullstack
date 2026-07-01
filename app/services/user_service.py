"""
用户业务逻辑服务
提供注册、登录、信息查询/更新等核心功能
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserUpdate,
    UserChangePassword,
    UserRead,
    TokenResponse,
)

# ── 密码哈希上下文 ──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """用户业务逻辑"""

    # ── 密码工具 ──

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    # ── JWT 工具 ──

    @staticmethod
    def create_access_token(user_id: str) -> tuple[str, int]:
        """生成 JWT access token，返回 (token, expires_in_seconds)"""
        expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, expire_minutes * 60

    @staticmethod
    def decode_access_token(token: str) -> Optional[str]:
        """解码 JWT，返回 user_id 或 None"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload.get("sub")
        except JWTError:
            return None

    # ── 核心业务 ──

    async def register(self, db: AsyncSession, data: UserRegister) -> TokenResponse:
        """用户注册"""
        # 检查用户名/邮箱是否已存在
        stmt = select(User).where(
            or_(User.username == data.username, User.email == data.email)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            if existing.username == data.username:
                raise ValueError("用户名已被注册")
            raise ValueError("邮箱已被注册")

        # 创建用户
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=self.hash_password(data.password),
            nickname=data.nickname or data.username,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 签发 token
        token, expires_in = self.create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserRead.from_orm(user),
        )

    async def login(self, db: AsyncSession, data: UserLogin) -> TokenResponse:
        """用户登录（支持用户名或邮箱）"""
        stmt = select(User).where(
            or_(User.username == data.username, User.email == data.username),
            User.is_deleted == False,
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not self.verify_password(data.password, user.hashed_password):
            raise ValueError("用户名/邮箱或密码错误")

        if user.status != UserStatus.ACTIVE:
            raise ValueError("账号已被禁用")

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        # 签发 token
        token, expires_in = self.create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserRead.from_orm(user),
        )

    async def get_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """按 ID 查询用户"""
        stmt = select(User).where(User.id == user_id, User.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """按用户名查询用户"""
        stmt = select(User).where(User.username == username, User.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(
        self, db: AsyncSession, user_id: str, data: UserUpdate
    ) -> Optional[User]:
        """更新用户资料"""
        user = await self.get_by_id(db, user_id)
        if not user:
            return None

        if data.nickname is not None:
            user.nickname = data.nickname
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        await db.commit()
        await db.refresh(user)
        return user

    async def change_password(
        self, db: AsyncSession, user_id: str, data: UserChangePassword
    ) -> bool:
        """修改密码"""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")

        if not self.verify_password(data.old_password, user.hashed_password):
            raise ValueError("旧密码错误")

        user.hashed_password = self.hash_password(data.new_password)
        await db.commit()
        return True

    async def list_users(
        self, db: AsyncSession, skip: int = 0, limit: int = 20
    ) -> list[User]:
        """列出用户（分页）"""
        stmt = (
            select(User)
            .where(User.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_users(self, db: AsyncSession) -> int:
        """统计用户总数"""
        from sqlalchemy import func as sa_func
        stmt = select(sa_func.count()).where(
            User.is_deleted == False
        )
        result = await db.execute(stmt)
        return result.scalar_one()