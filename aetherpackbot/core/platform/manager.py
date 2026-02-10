"""
Platform Manager - Manages messaging platform adapters.

Supports: Telegram, Discord, QQ (OneBot), Slack, DingTalk, Lark (Feishu).
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from aetherpackbot.core.api.platforms import (
    BasePlatformAdapter,
    PlatformConfig,
    PlatformStatus,
    PlatformCapabilities,
    PlatformInfo,
)
from aetherpackbot.core.api.events import EventType, MessageEvent
from aetherpackbot.core.api.messages import (
    Message,
    MessageChain,
    MessageSession,
    PlatformMetadata,
    TextComponent,
)
from aetherpackbot.core.kernel.logging import get_logger

if TYPE_CHECKING:
    from aetherpackbot.core.kernel.container import ServiceContainer
    from aetherpackbot.core.messaging.events import EventDispatcher

logger = get_logger("platforms")


# Graceful import: if aiocqhttp is missing, QQOneBotAdapter will be None
try:
    from aetherpackbot.core.platform.qq_onebot import QQOneBotAdapter
except ImportError:
    QQOneBotAdapter = None  # type: ignore
    logger.warning("aiocqhttp not installed – QQ OneBot adapter disabled. Run: pip install aiocqhttp")

# ─── Platform Type Registry ───────────────────────────────────────────
PLATFORM_REGISTRY: dict[str, PlatformInfo] = {}


def register_platform_type(
    type_name: str,
    display_name: str,
    adapter_class: type[BasePlatformAdapter],
    config_schema: dict[str, Any] | None = None,
    description: str = "",
) -> None:
    PLATFORM_REGISTRY[type_name] = PlatformInfo(
        type_name=type_name,
        display_name=display_name,
        adapter_class=adapter_class,
        config_schema=config_schema or {},
        description=description,
    )


# ─── Platform Manager ─────────────────────────────────────────────────

class PlatformManager:
    """Manages platform adapter lifecycle and message routing."""

    def __init__(
        self,
        container: "ServiceContainer",
        event_dispatcher: "EventDispatcher",
    ) -> None:
        self._container = container
        self._event_dispatcher = event_dispatcher
        self._adapters: dict[str, BasePlatformAdapter] = {}
        self._adapter_tasks: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        from aetherpackbot.core.storage.config import ConfigurationManager

        cm = await self._container.resolve(ConfigurationManager)
        platforms_config = cm.get("platforms", [])
        
        config_changed = False
        for pdata in platforms_config:
            if not pdata.get("enabled", True):
                continue
            try:
                # Auto-heal: Ensure ID exists in config
                if not pdata.get("id"):
                    ptype = pdata.get("type", "telegram")
                    pdata["id"] = f"{ptype}_{len(self._adapters)}"
                    config_changed = True
                    
                await self.register_from_config(pdata)
            except Exception as e:
                logger.error(f"Failed to register platform: {e}")
                
        if config_changed:
            cm.set("platforms", platforms_config)
            await cm.save()
            logger.info("Auto-healed platform configuration (added missing IDs)")

        for adapter in self._adapters.values():
            await self._start_adapter(adapter)

        logger.info(f"Started {len(self._adapters)} platform adapters")

    async def stop(self) -> None:
        for task in self._adapter_tasks.values():
            task.cancel()
        if self._adapter_tasks:
            await asyncio.gather(*self._adapter_tasks.values(), return_exceptions=True)
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping {adapter.platform_id}: {e}")
        self._adapters.clear()
        self._adapter_tasks.clear()
        logger.info("Platform manager stopped")

    async def register_from_config(self, config_data: dict[str, Any]) -> BasePlatformAdapter:
        platform_type = config_data.get("type", "")
        if platform_type not in PLATFORM_REGISTRY:
            raise ValueError(f"Unknown platform type: {platform_type}. Available: {list(PLATFORM_REGISTRY.keys())}")

        info = PLATFORM_REGISTRY[platform_type]

        # Flatten nested "config" key from frontend into top-level config_data
        nested_cfg = config_data.get("config", {})
        if isinstance(nested_cfg, dict):
            for k, v in nested_cfg.items():
                config_data.setdefault(k, v)

        # Build credentials and settings from config_schema fields
        # Frontend sends flat config fields; we need to map them into
        # credentials (secrets like tokens) and settings (non-secret options)
        credentials = config_data.get("credentials", {})
        settings = config_data.get("settings", {})

        # Auto-map flat config fields based on config_schema
        schema = info.config_schema
        token_schema_keys = []  # track token-like schema keys for fallback
        for key, schema_def in schema.items():
            is_credential = any(s in key.lower() for s in ("token", "secret", "key", "password", "app_id", "client_id"))
            if is_credential:
                token_schema_keys.append(key)
            if key in config_data and key not in ("type", "id", "name", "enabled"):
                # Fields containing token/secret/key/password go to credentials
                if is_credential:
                    credentials.setdefault(key, config_data[key])
                else:
                    settings.setdefault(key, config_data[key])

        # Fallback: if frontend sent generic 'token' but no schema key matched,
        # map it to the first token-like key in the schema
        if not credentials and config_data.get("token") and token_schema_keys:
            credentials[token_schema_keys[0]] = config_data["token"]

        # Handle ID generation if missing or empty
        pid = config_data.get("id")
        if not pid:
            pid = f"{platform_type}_{len(self._adapters)}"

        config = PlatformConfig(
            platform_id=pid,
            platform_type=platform_type,
            enabled=config_data.get("enabled", True),
            display_name=config_data.get("name", info.display_name),
            credentials=credentials,
            settings=settings,
        )
        adapter = info.adapter_class(config)
        adapter._platform_manager = self  # back-reference for message dispatching
        self._adapters[config.platform_id] = adapter
        logger.info(f"Registered platform: {config.platform_id}")
        return adapter

    async def _start_adapter(self, adapter: BasePlatformAdapter) -> None:
        try:
            await adapter.start()
            logger.info(f"Started adapter: {adapter.platform_id}")
        except Exception as e:
            logger.error(f"Failed to start {adapter.platform_id}: {e}")

    def register(self, platform_id: str, adapter: BasePlatformAdapter) -> None:
        self._adapters[platform_id] = adapter

    def unregister(self, platform_id: str) -> None:
        self._adapters.pop(platform_id, None)

    def get_adapter(self, platform_id: str) -> BasePlatformAdapter | None:
        return self._adapters.get(platform_id)

    def get_all_adapters(self) -> dict[str, BasePlatformAdapter]:
        return self._adapters.copy()

    async def dispatch_message(self, message: Message) -> None:
        event = MessageEvent(message=message)
        await self._event_dispatcher.emit(event)

    async def send_message(
        self,
        platform_id: str,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        adapter = self.get_adapter(platform_id)
        if not adapter:
            logger.warning(f"No adapter for platform: {platform_id}")
            return None
        if adapter.status != PlatformStatus.CONNECTED:
            logger.warning(f"Adapter {platform_id} not connected")
            return None
        try:
            return await adapter.send_message(session, chain, reply_to)
        except Exception as e:
            logger.exception(f"Error sending on {platform_id}: {e}")
            return None

    def get_status_list(self) -> list[dict[str, Any]]:
        """Get a list of all platform adapters with their status, used by the dashboard."""
        result = []
        for pid, adapter in self._adapters.items():
            # Map PlatformStatus to frontend-friendly strings
            status_map = {
                PlatformStatus.CONNECTED: "running",
                PlatformStatus.CONNECTING: "connecting",
                PlatformStatus.RECONNECTING: "reconnecting",
                PlatformStatus.ERROR: "error",
                PlatformStatus.DISCONNECTED: "stopped",
            }
            result.append({
                "id": pid,
                "type": adapter.platform_type,
                "name": adapter.config.display_name or adapter.platform_type,
                "status": status_map.get(adapter.status, "stopped"),
                "enabled": adapter.config.enabled,
                "settings": adapter.config.settings,
                "credentials": adapter.config.credentials,
                "capabilities": {
                    "text": adapter.capabilities.supports_text,
                    "images": adapter.capabilities.supports_images,
                    "audio": adapter.capabilities.supports_audio,
                    "video": adapter.capabilities.supports_video,
                    "files": adapter.capabilities.supports_files,
                },
            })
        return result

    # Keep old dict-based API for backwards compat
    def get_status(self) -> dict[str, dict[str, Any]]:
        return {
            pid: {
                "status": a.status.name,
                "type": a.platform_type,
                "capabilities": {
                    "supports_text": a.capabilities.supports_text,
                    "supports_images": a.capabilities.supports_images,
                    "supports_audio": a.capabilities.supports_audio,
                },
            }
            for pid, a in self._adapters.items()
        }


# ═══════════════════════════════════════════════════════════════════════
# Built-in Platform Adapter Implementations
# ═══════════════════════════════════════════════════════════════════════


class TelegramAdapter(BasePlatformAdapter):
    """Telegram via python-telegram-bot."""

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._application = None
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_audio=True,
            supports_files=True,
            supports_reactions=True,
            supports_mentions=True,
            max_message_length=4096,
        )

    async def start(self) -> None:
        from telegram.ext import Application, MessageHandler, filters

        token = self._config.credentials.get("bot_token", "")
        if not token:
            raise ValueError("Telegram bot_token not configured")

        self._application = Application.builder().token(token).build()
        self._application.add_handler(MessageHandler(filters.ALL, self._handle_message))

        await self._application.initialize()
        await self._application.start()
        # Start polling in background
        asyncio.create_task(self._application.updater.start_polling())
        self._set_status(PlatformStatus.CONNECTED)

    async def stop(self) -> None:
        if self._application:
            if self._application.updater and self._application.updater.running:
                await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
        self._set_status(PlatformStatus.DISCONNECTED)

    async def send_message(self, session: MessageSession, chain: MessageChain, reply_to: str | None = None) -> str | None:
        if not self._application or not self._application.bot:
            return None
        chat_id = session.group_id if session.is_group else session.user_id
        text = chain.plain_text
        kwargs: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_to:
            kwargs["reply_to_message_id"] = int(reply_to)
        msg = await self._application.bot.send_message(**kwargs)
        return str(msg.message_id)

    async def _handle_message(self, update, context) -> None:
        """Convert Telegram update to internal Message and dispatch."""
        if not update.message or not update.message.text:
            return

        user_id = str(update.message.from_user.id) if update.message.from_user else ""
        user_name = update.message.from_user.first_name if update.message.from_user else ""
        is_group = update.message.chat.type != "private"
        group_id = str(update.message.chat.id) if is_group else ""

        session = MessageSession(
            session_id=f"telegram:{group_id or user_id}",
            platform_id=self.platform_id,
            is_group=is_group,
            group_id=group_id if is_group else None,
            user_id=user_id,
        )

        msg = Message(
            message_id=str(update.message.message_id),
            chain=MessageChain().text(update.message.text),
            session=session,
            platform_meta=PlatformMetadata(
                platform_name="Telegram",
                platform_id=self.platform_id,
                adapter_type="telegram",
            ),
            sender_id=user_id,
            sender_name=user_name,
            raw_data=update,
        )
        logger.debug(f"[Telegram] {user_name}: {update.message.text}")

        # Dispatch message into processing pipeline
        if hasattr(self, '_platform_manager') and self._platform_manager:
            try:
                await self._platform_manager.dispatch_message(msg)
            except Exception as e:
                logger.error(f"[Telegram] Failed to dispatch message: {e}")


class DiscordAdapter(BasePlatformAdapter):
    """Discord via py-cord."""

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._bot = None
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_audio=False,
            supports_files=True,
            supports_reactions=True,
            supports_threads=True,
            supports_mentions=True,
            max_message_length=2000,
        )

    async def start(self) -> None:
        import discord

        token = self._config.credentials.get("bot_token", "")
        if not token:
            raise ValueError("Discord bot_token not configured")

        intents = discord.Intents.default()
        intents.message_content = True
        self._bot = discord.Bot(intents=intents)

        @self._bot.event
        async def on_ready():
            logger.info(f"[Discord] Logged in as {self._bot.user}")

        @self._bot.event
        async def on_message(message):
            if message.author == self._bot.user:
                return
            await self._handle_message(message)

        asyncio.create_task(self._bot.start(token))
        self._set_status(PlatformStatus.CONNECTED)

    async def stop(self) -> None:
        if self._bot:
            await self._bot.close()
        self._set_status(PlatformStatus.DISCONNECTED)

    async def send_message(self, session: MessageSession, chain: MessageChain, reply_to: str | None = None) -> str | None:
        if not self._bot:
            return None
        ch_id = int(session.group_id or session.user_id or "0")
        channel = self._bot.get_channel(ch_id)
        if channel:
            msg = await channel.send(chain.plain_text)
            return str(msg.id)
        return None

    async def _handle_message(self, message) -> None:
        user_id = str(message.author.id)
        user_name = str(message.author)
        is_group = message.guild is not None
        group_id = str(message.channel.id) if is_group else ""

        session = MessageSession(
            session_id=f"discord:{message.channel.id}",
            platform_id=self.platform_id,
            is_group=is_group,
            group_id=group_id if is_group else None,
            user_id=user_id,
        )

        msg = Message(
            message_id=str(message.id),
            chain=MessageChain().text(message.content),
            session=session,
            platform_meta=PlatformMetadata(
                platform_name="Discord",
                platform_id=self.platform_id,
                adapter_type="discord",
            ),
            sender_id=user_id,
            sender_name=user_name,
            raw_data=message,
        )
        logger.debug(f"[Discord] {user_name}: {message.content}")

        if hasattr(self, '_platform_manager') and self._platform_manager:
            try:
                await self._platform_manager.dispatch_message(msg)
            except Exception as e:
                logger.error(f"[Discord] Failed to dispatch message: {e}")


class SlackAdapter(BasePlatformAdapter):
    """Slack via slack-sdk with Socket Mode support."""

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._client = None
        self._app = None
        self._socket_client = None
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_files=True,
            supports_reactions=True,
            supports_threads=True,
            supports_rich_text=True,
            max_message_length=4000,
        )

    async def start(self) -> None:
        from slack_sdk.web.async_client import AsyncWebClient

        bot_token = self._config.credentials.get("bot_token", "")
        if not bot_token:
            raise ValueError("Slack bot_token not configured")

        self._client = AsyncWebClient(token=bot_token)
        # Verify connection
        try:
            auth = await self._client.auth_test()
            logger.info(f"[Slack] Connected as {auth.get('user', 'unknown')}")
        except Exception as e:
            raise ValueError(f"Slack auth failed: {e}")

        self._set_status(PlatformStatus.CONNECTED)

    async def stop(self) -> None:
        self._client = None
        self._set_status(PlatformStatus.DISCONNECTED)

    async def send_message(self, session: MessageSession, chain: MessageChain, reply_to: str | None = None) -> str | None:
        if not self._client:
            return None
        channel = session.group_id or session.user_id
        if not channel:
            return None
        kwargs: dict[str, Any] = {"channel": channel, "text": chain.plain_text}
        if reply_to:
            kwargs["thread_ts"] = reply_to
        resp = await self._client.chat_postMessage(**kwargs)
        return resp.get("ts")

    async def _handle_message(self, event: dict) -> None:
        user_id = event.get("user", "")
        channel = event.get("channel", "")
        text = event.get("text", "")

        session = MessageSession(
            session_id=f"slack:{channel}",
            platform_id=self.platform_id,
            is_group=True,  # Slack channels are group-like
            group_id=channel,
            user_id=user_id,
        )

        msg = Message(
            message_id=event.get("ts", ""),
            chain=MessageChain().text(text),
            session=session,
            platform_meta=PlatformMetadata(
                platform_name="Slack",
                platform_id=self.platform_id,
                adapter_type="slack",
            ),
            sender_id=user_id,
            sender_name=user_id,
            raw_data=event,
        )
        logger.debug(f"[Slack] {user_id}: {text}")

        if hasattr(self, '_platform_manager') and self._platform_manager:
            try:
                await self._platform_manager.dispatch_message(msg)
            except Exception as e:
                logger.error(f"[Slack] Failed to dispatch message: {e}")


class DingTalkAdapter(BasePlatformAdapter):
    """DingTalk (钉钉) via dingtalk-stream."""

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._client = None
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_files=True,
            supports_mentions=True,
            max_message_length=20000,
        )

    async def start(self) -> None:
        import dingtalk_stream

        client_id = self._config.credentials.get("client_id", "")
        client_secret = self._config.credentials.get("client_secret", "")
        if not client_id or not client_secret:
            raise ValueError("DingTalk client_id and client_secret required")

        credential = dingtalk_stream.Credential(client_id, client_secret)
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        class MsgHandler(dingtalk_stream.ChatbotHandler):
            async def process(handler_self, callback):
                await self._handle_message(callback)
                return dingtalk_stream.AckMessage.STATUS_OK, "ok"

        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            MsgHandler(),
        )
        asyncio.create_task(asyncio.to_thread(self._client.start_forever))
        self._set_status(PlatformStatus.CONNECTED)
        logger.info("[DingTalk] Stream client started")

    async def stop(self) -> None:
        self._set_status(PlatformStatus.DISCONNECTED)

    async def send_message(self, session: MessageSession, chain: MessageChain, reply_to: str | None = None) -> str | None:
        logger.debug(f"[DingTalk] send: {chain.plain_text}")
        return None

    async def _handle_message(self, callback) -> None:
        text = callback.data.get("text", {}).get("content", "")
        sender = callback.data.get("senderNick", "unknown")
        sender_id = callback.data.get("senderId", "")
        conversation_id = callback.data.get("conversationId", "")
        is_group = callback.data.get("conversationType", "1") == "2"

        session = MessageSession(
            session_id=f"dingtalk:{conversation_id}",
            platform_id=self.platform_id,
            is_group=is_group,
            group_id=conversation_id if is_group else None,
            user_id=sender_id,
        )

        msg = Message(
            message_id=callback.data.get("msgId", ""),
            chain=MessageChain().text(text),
            session=session,
            platform_meta=PlatformMetadata(
                platform_name="DingTalk",
                platform_id=self.platform_id,
                adapter_type="dingtalk",
            ),
            sender_id=sender_id,
            sender_name=sender,
            raw_data=callback.data,
        )
        logger.debug(f"[DingTalk] {sender}: {text}")

        if hasattr(self, '_platform_manager') and self._platform_manager:
            try:
                await self._platform_manager.dispatch_message(msg)
            except Exception as e:
                logger.error(f"[DingTalk] Failed to dispatch message: {e}")


class LarkAdapter(BasePlatformAdapter):
    """Lark/Feishu (飞书) via lark-oapi."""

    def __init__(self, config: PlatformConfig) -> None:
        super().__init__(config)
        self._client = None
        self._capabilities = PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_files=True,
            supports_rich_text=True,
            supports_reactions=True,
            max_message_length=30000,
        )

    async def start(self) -> None:
        import lark_oapi as lark

        app_id = self._config.credentials.get("app_id", "")
        app_secret = self._config.credentials.get("app_secret", "")
        if not app_id or not app_secret:
            raise ValueError("Lark app_id and app_secret required")

        self._client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()
        self._set_status(PlatformStatus.CONNECTED)
        logger.info("[Lark] Client initialized")

    async def stop(self) -> None:
        self._client = None
        self._set_status(PlatformStatus.DISCONNECTED)

    async def send_message(self, session: MessageSession, chain: MessageChain, reply_to: str | None = None) -> str | None:
        if not self._client:
            return None
        logger.debug(f"[Lark] send: {chain.plain_text}")
        return None

    async def _handle_message(self, event) -> None:
        # Extract message data from Lark event
        event_data = event if isinstance(event, dict) else {}
        msg_data = event_data.get("message", {})
        sender_data = event_data.get("sender", {})
        text = ""
        if msg_data.get("message_type") == "text":
            import json as _json
            try:
                text = _json.loads(msg_data.get("content", "{}")).get("text", "")
            except Exception:
                text = msg_data.get("content", "")

        sender_id = sender_data.get("sender_id", {}).get("open_id", "")
        chat_id = msg_data.get("chat_id", "")
        is_group = msg_data.get("chat_type") == "group"

        session = MessageSession(
            session_id=f"lark:{chat_id or sender_id}",
            platform_id=self.platform_id,
            is_group=is_group,
            group_id=chat_id if is_group else None,
            user_id=sender_id,
        )

        msg = Message(
            message_id=msg_data.get("message_id", ""),
            chain=MessageChain().text(text),
            session=session,
            platform_meta=PlatformMetadata(
                platform_name="Lark",
                platform_id=self.platform_id,
                adapter_type="lark",
            ),
            sender_id=sender_id,
            sender_name=sender_data.get("sender_id", {}).get("name", sender_id),
            raw_data=event,
        )
        logger.debug(f"[Lark] received message from {sender_id}")

        if hasattr(self, '_platform_manager') and self._platform_manager:
            try:
                await self._platform_manager.dispatch_message(msg)
            except Exception as e:
                logger.error(f"[Lark] Failed to dispatch message: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Register all built-in platform types
# ═══════════════════════════════════════════════════════════════════════

register_platform_type(
    "telegram", "Telegram", TelegramAdapter,
    config_schema={"bot_token": {"type": "string", "required": True, "label": "Bot Token"}},
    description="Telegram Bot 平台",
)

register_platform_type(
    "discord", "Discord", DiscordAdapter,
    config_schema={"bot_token": {"type": "string", "required": True, "label": "Bot Token"}},
    description="Discord Bot 平台",
)

if QQOneBotAdapter is not None:
    register_platform_type(
        "qq_onebot", "QQ (OneBot)", QQOneBotAdapter,
        config_schema={
            "host": {"type": "string", "default": "0.0.0.0", "label": "反向 Websocket 主机"},
            "port": {"type": "number", "default": 8081, "label": "反向 Websocket 端口"},
            "token": {"type": "string", "default": "", "label": "反向 Websocket Token", "required": False},
        },
        description="QQ 通过 OneBot (NAPCat/LLOneBot/Lagrange) 协议接入",
    )

register_platform_type(
    "slack", "Slack", SlackAdapter,
    config_schema={"bot_token": {"type": "string", "required": True, "label": "Bot Token"}},
    description="Slack Bot 平台",
)

register_platform_type(
    "dingtalk", "DingTalk (钉钉)", DingTalkAdapter,
    config_schema={
        "client_id": {"type": "string", "required": True, "label": "Client ID"},
        "client_secret": {"type": "string", "required": True, "label": "Client Secret"},
    },
    description="钉钉机器人平台",
)

register_platform_type(
    "lark", "Lark (飞书)", LarkAdapter,
    config_schema={
        "app_id": {"type": "string", "required": True, "label": "App ID"},
        "app_secret": {"type": "string", "required": True, "label": "App Secret"},
    },
    description="飞书/Lark 机器人平台",
)

# (qq_onebot already registered above, no duplicate needed)

