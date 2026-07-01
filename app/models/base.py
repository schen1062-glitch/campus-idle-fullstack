"""
ORM 基类模块
提供 declarative Base 和通用的 TimestampMixin
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""

    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名：驼峰转蛇形"""
        import re
        name = cls.__name__
        # 将驼峰转为蛇形：CamelCase -> camel_case
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        # 处理尾部的 _model 等命名
        snake = re.sub(r'_model$', '', snake)
        return snake + "s"  # 复数化


class TimestampMixin:
    """创建时间 / 更新时间混入"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )