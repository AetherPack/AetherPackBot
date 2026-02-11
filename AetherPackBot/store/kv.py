"""
KV 存储 - 简易键值对存储
Key-Value store - simple key-value pair storage.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select

from AetherPackBot.store.engine import StorageEngine
from AetherPackBot.store.models import Preference

logger = logging.getLogger(__name__)


class KeyValueStore:
    """
    KV 存储 - 基于数据库的键值对存储
    KV store - database-backed key-value store.

    支持作用域（scope）来区分不同的命名空间。
    Supports scope to distinguish different namespaces.
    """

    def __init__(self, engine: StorageEngine) -> None:
        self._engine = engine

    async def get(self, key: str, scope: str = "global", default: Any = None) -> Any:
        """获取值 / Get value."""
        async with self._engine.session() as session:
            stmt = select(Preference).where(
                Preference.scope == scope, Preference.key == key
            )
            result = await session.execute(stmt)
            pref = result.scalar_one_or_none()

            if pref is None:
                return default

            try:
                return json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                return pref.value

    async def set(self, key: str, value: Any, scope: str = "global") -> None:
        """设置值 / Set value."""
        value_str = json.dumps(value) if not isinstance(value, str) else value

        async with self._engine.session() as session:
            stmt = select(Preference).where(
                Preference.scope == scope, Preference.key == key
            )
            result = await session.execute(stmt)
            pref = result.scalar_one_or_none()

            if pref is None:
                pref = Preference(scope=scope, key=key, value=value_str)
                session.add(pref)
            else:
                pref.value = value_str

            await session.commit()

    async def delete(self, key: str, scope: str = "global") -> bool:
        """删除键 / Delete key."""
        async with self._engine.session() as session:
            stmt = select(Preference).where(
                Preference.scope == scope, Preference.key == key
            )
            result = await session.execute(stmt)
            pref = result.scalar_one_or_none()

            if pref is not None:
                await session.delete(pref)
                await session.commit()
                return True
            return False

    async def all_keys(self, scope: str = "global") -> list[str]:
        """获取所有键 / Get all keys."""
        async with self._engine.session() as session:
            stmt = select(Preference.key).where(Preference.scope == scope)
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]
