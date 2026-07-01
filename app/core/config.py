"""
全局配置模块
使用 pydantic-settings 从环境变量 / .env 读取，提供单例 settings
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── 应用基础 ──
    APP_NAME: str = "校园闲置流转助手"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── 数据库 ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./campus_idle.db"
    # 生产用 PostgreSQL（注释掉 sqlite 后解开下面行即可）
    # DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/campus_idle"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT / 安全 ──
    SECRET_KEY: str = "change-me-to-a-real-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 任务队列 ──
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_BASE_DELAY_SECONDS: float = 1.0
    TASK_QUEUE_DEFAULT: str = "default"
    # APScheduler 扫描重试任务间隔（秒）
    TASK_RETRY_SCHEDULER_INTERVAL_SECONDS: int = 30

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["*"]

    # ── Prometheus ──
    METRICS_PORT: int = 9090

    # ── 模型配置 ──
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# 单例
settings = Settings()

# 确保数据库 URI 中的相对路径基于项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if settings.DATABASE_URL.startswith("sqlite"):
    # 将相对路径拼接到项目根目录下
    db_path = _PROJECT_ROOT / "campus_idle.db"
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"