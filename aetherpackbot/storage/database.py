"""
Database Manager - SQLAlchemy-based database management.

Provides async database access using SQLAlchemy with SQLModel integration.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar, Generic, Type

from sqlalchemy import Column, DateTime, String, Text, Integer, Boolean, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel, Field

from aetherpackbot.kernel.logging import get_logger

logger = get_logger("database")
T = TypeVar("T", bound=SQLModel)


class BaseModel(SQLModel):
    """Base model with common fields."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationModel(BaseModel, table=True):
    """Model for storing conversations."""
    
    __tablename__ = "conversations"
    
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    user_id: str = Field(index=True)
    platform_id: str
    title: str = ""
    context: str = ""  # JSON serialized messages
    token_count: int = 0
    is_active: bool = True


class MessageHistoryModel(BaseModel, table=True):
    """Model for storing message history."""
    
    __tablename__ = "message_history"
    
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(index=True)
    role: str
    content: str
    tool_calls: str | None = None  # JSON
    tool_call_id: str | None = None
    tokens: int = 0


class UserModel(BaseModel, table=True):
    """Model for storing user data."""
    
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(unique=True, index=True)
    platform_id: str
    username: str = ""
    display_name: str = ""
    role: str = "user"  # user, admin, owner
    settings: str = "{}"  # JSON


class PluginDataModel(BaseModel, table=True):
    """Model for plugin key-value storage."""
    
    __tablename__ = "plugin_data"
    
    id: int | None = Field(default=None, primary_key=True)
    plugin_name: str = Field(index=True)
    key: str
    value: str
    
    class Config:
        # Unique constraint on plugin_name + key
        pass


class SharedPreferencesModel(BaseModel, table=True):
    """Model for shared preferences (simple key-value store)."""
    
    __tablename__ = "shared_preferences"
    
    id: int | None = Field(default=None, primary_key=True)
    namespace: str = Field(default="global", index=True)
    key: str = Field(index=True)
    value: str


class DatabaseManager:
    """
    Manages database connections and provides data access methods.
    
    Uses SQLAlchemy async engine with connection pooling.
    """
    
    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url or "sqlite+aiosqlite:///data/storage/aetherpackbot.db"
        self._engine = None
        self._session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        if self._initialized:
            return
        
        # Ensure directory exists
        if "sqlite" in self._db_url:
            db_path = self._db_url.split("///")[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine
        self._engine = create_async_engine(
            self._db_url,
            echo=False,
            pool_pre_ping=True,
        )
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        self._initialized = True
        logger.info("Database initialized")
    
    async def start(self) -> None:
        """Start the database manager (called by lifecycle)."""
        await self.initialize()
    
    async def stop(self) -> None:
        """Stop the database manager."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")
    
    def session(self) -> AsyncSession:
        """Get a new database session."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized")
        return self._session_factory()
    
    # Conversation methods
    
    async def get_conversation(
        self,
        session_id: str,
        user_id: str,
    ) -> ConversationModel | None:
        """Get an active conversation for a session."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(ConversationModel).where(
                ConversationModel.session_id == session_id,
                ConversationModel.user_id == user_id,
                ConversationModel.is_active == True,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def create_conversation(
        self,
        session_id: str,
        user_id: str,
        platform_id: str,
        title: str = "",
    ) -> ConversationModel:
        """Create a new conversation."""
        async with self.session() as session:
            conversation = ConversationModel(
                session_id=session_id,
                user_id=user_id,
                platform_id=platform_id,
                title=title,
                context="[]",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation
    
    async def update_conversation(
        self,
        conversation_id: int,
        **updates,
    ) -> None:
        """Update a conversation."""
        async with self.session() as session:
            from sqlalchemy import update
            
            updates["updated_at"] = datetime.utcnow()
            stmt = update(ConversationModel).where(
                ConversationModel.id == conversation_id
            ).values(**updates)
            await session.execute(stmt)
            await session.commit()
    
    async def clear_conversation(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        """Mark conversation as inactive (clear context)."""
        async with self.session() as session:
            from sqlalchemy import update
            
            stmt = update(ConversationModel).where(
                ConversationModel.session_id == session_id,
                ConversationModel.user_id == user_id,
                ConversationModel.is_active == True,
            ).values(is_active=False, updated_at=datetime.utcnow())
            await session.execute(stmt)
            await session.commit()
    
    # User methods
    
    async def get_user(self, user_id: str) -> UserModel | None:
        """Get a user by ID."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def upsert_user(
        self,
        user_id: str,
        platform_id: str,
        username: str = "",
        display_name: str = "",
    ) -> UserModel:
        """Create or update a user."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.platform_id = platform_id
                user.username = username or user.username
                user.display_name = display_name or user.display_name
                user.updated_at = datetime.utcnow()
            else:
                user = UserModel(
                    user_id=user_id,
                    platform_id=platform_id,
                    username=username,
                    display_name=display_name,
                )
                session.add(user)
            
            await session.commit()
            await session.refresh(user)
            return user
    
    # Shared preferences methods
    
    async def get_preference(
        self,
        key: str,
        namespace: str = "global",
        default: str | None = None,
    ) -> str | None:
        """Get a preference value."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(SharedPreferencesModel).where(
                SharedPreferencesModel.namespace == namespace,
                SharedPreferencesModel.key == key,
            )
            result = await session.execute(stmt)
            pref = result.scalar_one_or_none()
            return pref.value if pref else default
    
    async def set_preference(
        self,
        key: str,
        value: str,
        namespace: str = "global",
    ) -> None:
        """Set a preference value."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(SharedPreferencesModel).where(
                SharedPreferencesModel.namespace == namespace,
                SharedPreferencesModel.key == key,
            )
            result = await session.execute(stmt)
            pref = result.scalar_one_or_none()
            
            if pref:
                pref.value = value
                pref.updated_at = datetime.utcnow()
            else:
                pref = SharedPreferencesModel(
                    namespace=namespace,
                    key=key,
                    value=value,
                )
                session.add(pref)
            
            await session.commit()
    
    # Plugin data methods
    
    async def get_plugin_data(
        self,
        plugin_name: str,
        key: str,
        default: str | None = None,
    ) -> str | None:
        """Get plugin data."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(PluginDataModel).where(
                PluginDataModel.plugin_name == plugin_name,
                PluginDataModel.key == key,
            )
            result = await session.execute(stmt)
            data = result.scalar_one_or_none()
            return data.value if data else default
    
    async def set_plugin_data(
        self,
        plugin_name: str,
        key: str,
        value: str,
    ) -> None:
        """Set plugin data."""
        async with self.session() as session:
            from sqlalchemy import select
            
            stmt = select(PluginDataModel).where(
                PluginDataModel.plugin_name == plugin_name,
                PluginDataModel.key == key,
            )
            result = await session.execute(stmt)
            data = result.scalar_one_or_none()
            
            if data:
                data.value = value
                data.updated_at = datetime.utcnow()
            else:
                data = PluginDataModel(
                    plugin_name=plugin_name,
                    key=key,
                    value=value,
                )
                session.add(data)
            
            await session.commit()
