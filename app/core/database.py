"""
异步数据库引擎与 Session 管理
提供 get_db 依赖注入，供 FastAPI 路由使用
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base  # noqa: F401 — 确保模型注册

# ── 异步引擎 ──
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # 连接健康检查
)

# ── Session 工厂 ──
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后依然可以访问属性
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：提供数据库会话
    用法：
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    应用启动时调用：创建所有表（开发/测试用）
    生产环境应使用 Alembic 迁移
    """
    # 导入所有模型以注册到 Base.metadata
    import app.models.task      # noqa: F401
    import app.models.user      # noqa: F401
    import app.models.product   # noqa: F401
    import app.models.order     # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """应用关闭时调用：释放引擎连接"""
    await engine.dispose()