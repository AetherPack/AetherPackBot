"""
数据模型 - 定义所有数据库表结构
Data models - defines all database table structures.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from AetherPackBot.store.engine import Base


class Conversation(Base):
    """对话记录表 / Conversation record table."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True)
    platform: Mapped[str] = mapped_column(String(50), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    messages: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PlatformStat(Base):
    """平台统计表 / Platform statistics table."""

    __tablename__ = "platform_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    user_count: Mapped[int] = mapped_column(Integer, default=0)


class Persona(Base):
    """人格设定表 / Persona settings table."""

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    opening_dialogs: Mapped[str] = mapped_column(Text, default="[]")
    folder: Mapped[str] = mapped_column(String(100), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CronTask(Base):
    """定时任务表 / Cron task table."""

    __tablename__ = "cron_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    cron_expr: Mapped[str] = mapped_column(String(50))
    action_type: Mapped[str] = mapped_column(String(50))
    action_data: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PackConfig(Base):
    """扩展包配置表 / Pack configuration table."""

    __tablename__ = "pack_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pack_name: Mapped[str] = mapped_column(String(100), index=True)
    config_key: Mapped[str] = mapped_column(String(255))
    config_value: Mapped[str] = mapped_column(Text, default="")


class Preference(Base):
    """偏好设置表（KV 存储） / Preference table (KV store)."""

    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(100), index=True, default="global")
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text, default="")


class MessageHistory(Base):
    """消息历史表 / Message history table."""

    __tablename__ = "message_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    sender_id: Mapped[str] = mapped_column(String(100))
    sender_name: Mapped[str] = mapped_column(String(100), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
