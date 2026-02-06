"""
Platform Manager - Manages messaging platform adapters.

Handles platform adapter registration, lifecycle, and message routing.
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from aetherpackbot.protocols.platforms import (
    BasePlatformAdapter,
    PlatformConfig,
    PlatformStatus,
    PlatformInfo,
)
from aetherpackbot.protocols.events import EventType, MessageEvent
from aetherpackbot.protocols.messages import Message, MessageChain, MessageSession, PlatformMetadata
from aetherpackbot.kernel.logging import get_logger

if TYPE_CHECKING:
    from aetherpackbot.kernel.container import ServiceContainer
    from aetherpackbot.messaging.events import EventDispatcher

logger = get_logger("platforms")


# Platform type registry
PLATFORM_REGISTRY: dict[str, PlatformInfo] = {}


def register_platform_type(
    type_name: str,
    display_name: str,
    adapter_class: type[BasePlatformAdapter],
    config_schema: dict[str, Any] | None = None,
    description: str = "",
) -> None:
    """Register a platform adapter type."""
    PLATFORM_REGISTRY[type_name] = PlatformInfo(
        type_name=type_name,
        display_name=display_name,
        adapter_class=adapter_class,
        config_schema=config_schema or {},
        description=description,
    )


class PlatformManager:
    """
    Manages messaging platform adapters.
    
    Handles:
    - Platform adapter lifecycle
    - Message routing from platforms to event system
    - Sending messages back to platforms
    """
    
    def __init__(
        self,
        container: ServiceContainer,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._container = container
        self._event_dispatcher = event_dispatcher
        self._adapters: dict[str, BasePlatformAdapter] = {}
        self._adapter_tasks: dict[str, asyncio.Task] = {}
    
    async def start(self) -> None:
        """Start the platform manager and all adapters."""
        from aetherpackbot.storage.config import ConfigurationManager
        
        config_manager = await self._container.resolve(ConfigurationManager)
        platforms_config = config_manager.get("platforms", [])
        
        for platform_data in platforms_config:
            if not platform_data.get("enabled", True):
                continue
            
            try:
                await self.register_from_config(platform_data)
            except Exception as e:
                logger.error(f"Failed to register platform: {e}")
        
        # Start all adapters
        for adapter in self._adapters.values():
            await self._start_adapter(adapter)
        
        logger.info(f"Started {len(self._adapters)} platform adapters")
    
    async def stop(self) -> None:
        """Stop the platform manager and all adapters."""
        # Cancel all adapter tasks
        for task in self._adapter_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._adapter_tasks:
            await asyncio.gather(
                *self._adapter_tasks.values(),
                return_exceptions=True,
            )
        
        # Stop all adapters
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping adapter {adapter.platform_id}: {e}")
        
        self._adapters.clear()
        self._adapter_tasks.clear()
        logger.info("Platform manager stopped")
    
    async def register_from_config(
        self,
        config_data: dict[str, Any],
    ) -> BasePlatformAdapter:
        """
        Register a platform adapter from configuration.
        
        Args:
            config_data: Platform configuration dictionary
        
        Returns:
            The registered adapter instance
        """
        platform_type = config_data.get("type", "")
        
        if platform_type not in PLATFORM_REGISTRY:
            raise ValueError(f"Unknown platform type: {platform_type}")
        
        platform_info = PLATFORM_REGISTRY[platform_type]
        
        config = PlatformConfig(
            platform_id=config_data.get("id", f"{platform_type}_{len(self._adapters)}"),
            platform_type=platform_type,
            enabled=config_data.get("enabled", True),
            display_name=config_data.get("name", platform_info.display_name),
            credentials=config_data.get("credentials", {}),
            settings=config_data.get("settings", {}),
        )
        
        adapter = platform_info.adapter_class(config)
        self._adapters[config.platform_id] = adapter
        
        logger.info(f"Registered platform adapter: {config.platform_id}")
        return adapter
    
    async def _start_adapter(self, adapter: BasePlatformAdapter) -> None:
        """Start a single adapter."""
        try:
            await adapter.start()
            logger.info(f"Started adapter: {adapter.platform_id}")
        except Exception as e:
            logger.error(f"Failed to start adapter {adapter.platform_id}: {e}")
    
    def register(
        self,
        platform_id: str,
        adapter: BasePlatformAdapter,
    ) -> None:
        """Register a platform adapter."""
        self._adapters[platform_id] = adapter
    
    def unregister(self, platform_id: str) -> None:
        """Unregister a platform adapter."""
        if platform_id in self._adapters:
            del self._adapters[platform_id]
    
    def get_adapter(self, platform_id: str) -> BasePlatformAdapter | None:
        """Get an adapter by platform ID."""
        return self._adapters.get(platform_id)
    
    def get_all_adapters(self) -> dict[str, BasePlatformAdapter]:
        """Get all registered adapters."""
        return self._adapters.copy()
    
    def list_platform_ids(self) -> list[str]:
        """Get a list of all platform IDs."""
        return list(self._adapters.keys())
    
    async def dispatch_message(self, message: Message) -> None:
        """
        Dispatch an incoming message to the event system.
        
        Called by platform adapters when a message is received.
        """
        event = MessageEvent(message=message)
        await self._event_dispatcher.emit(event)
    
    async def send_message(
        self,
        platform_id: str,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """
        Send a message through a platform adapter.
        
        Returns the message ID if successful.
        """
        adapter = self.get_adapter(platform_id)
        if not adapter:
            logger.warning(f"No adapter found for platform: {platform_id}")
            return None
        
        if adapter.status != PlatformStatus.CONNECTED:
            logger.warning(f"Adapter {platform_id} is not connected")
            return None
        
        try:
            return await adapter.send_message(session, chain, reply_to)
        except Exception as e:
            logger.exception(f"Error sending message on {platform_id}: {e}")
            return None
    
    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all platform adapters."""
        return {
            platform_id: {
                "status": adapter.status.name,
                "type": adapter.platform_type,
                "capabilities": {
                    "supports_text": adapter.capabilities.supports_text,
                    "supports_images": adapter.capabilities.supports_images,
                    "supports_audio": adapter.capabilities.supports_audio,
                },
            }
            for platform_id, adapter in self._adapters.items()
        }


# Built-in platform adapter implementations

class TelegramAdapter(BasePlatformAdapter):
    """Telegram platform adapter using python-telegram-bot."""
    
    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._bot = None
        self._application = None
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        from telegram.ext import Application, MessageHandler, filters
        
        bot_token = self._config.credentials.get("bot_token", "")
        if not bot_token:
            raise ValueError("Telegram bot token not configured")
        
        self._application = Application.builder().token(bot_token).build()
        
        # Register message handler
        self._application.add_handler(
            MessageHandler(filters.ALL, self._handle_message)
        )
        
        await self._application.initialize()
        await self._application.start()
        
        self._set_status(PlatformStatus.CONNECTED)
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._application:
            await self._application.stop()
            await self._application.shutdown()
        self._set_status(PlatformStatus.DISCONNECTED)
    
    async def send_message(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """Send a message via Telegram."""
        if not self._application or not self._application.bot:
            return None
        
        chat_id = session.group_id if session.is_group else session.user_id
        text = chain.plain_text
        
        kwargs = {"chat_id": chat_id, "text": text}
        if reply_to:
            kwargs["reply_to_message_id"] = int(reply_to)
        
        message = await self._application.bot.send_message(**kwargs)
        return str(message.message_id)
    
    async def _handle_message(self, update, context) -> None:
        """Handle incoming Telegram message."""
        # This would be connected to the event dispatcher
        pass


class DiscordAdapter(BasePlatformAdapter):
    """Discord platform adapter using py-cord."""
    
    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._bot = None
    
    async def start(self) -> None:
        """Start the Discord bot."""
        import discord
        
        bot_token = self._config.credentials.get("bot_token", "")
        if not bot_token:
            raise ValueError("Discord bot token not configured")
        
        intents = discord.Intents.default()
        intents.message_content = True
        
        self._bot = discord.Bot(intents=intents)
        
        @self._bot.event
        async def on_message(message):
            await self._handle_message(message)
        
        # Start bot in background task
        asyncio.create_task(self._bot.start(bot_token))
        self._set_status(PlatformStatus.CONNECTED)
    
    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._bot:
            await self._bot.close()
        self._set_status(PlatformStatus.DISCONNECTED)
    
    async def send_message(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """Send a message via Discord."""
        if not self._bot:
            return None
        
        channel_id = int(session.group_id or session.user_id or "0")
        channel = self._bot.get_channel(channel_id)
        
        if channel:
            message = await channel.send(chain.plain_text)
            return str(message.id)
        return None
    
    async def _handle_message(self, message) -> None:
        """Handle incoming Discord message."""
        pass


# Register built-in platform types
register_platform_type(
    "telegram",
    "Telegram",
    TelegramAdapter,
    config_schema={
        "bot_token": {"type": "string", "required": True},
    },
    description="Telegram messaging platform",
)

register_platform_type(
    "discord",
    "Discord",
    DiscordAdapter,
    config_schema={
        "bot_token": {"type": "string", "required": True},
    },
    description="Discord messaging platform",
)
