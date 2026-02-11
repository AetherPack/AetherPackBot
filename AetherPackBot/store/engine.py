"""
存储引擎 - 管理数据库连接和表初始化
Storage engine - manages database connection and table initialization.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类 / SQLAlchemy declarative base."""

    pass


class StorageEngine:
    """
    存储引擎 - 封装数据库操作
    Storage engine - wraps database operations.
    """

    def __init__(self, db_path: str = "data/data.db") -> None:
        self._db_path = db_path
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self) -> None:
        """
        初始化数据库表
        Initialize database tables.
        """

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("数据库已初始化: %s", self._db_path)

    def session(self) -> AsyncSession:
        """
        获取一个数据库会话
        Get a database session.
        """
        return self._session_factory()

    async def dispose(self) -> None:
        """关闭引擎 / Dispose engine."""
        await self._engine.dispose()
