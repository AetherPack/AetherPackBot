"""
Telegram 网关适配器 - 对接 Telegram Bot API
Telegram gateway adapter - interfaces with the Telegram Bot API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus
from AetherPackBot.message.components import ImageComponent, TextComponent
from AetherPackBot.message.event import (
    EventKind,
    MessageEvent,
    MessageOrigin,
    SessionInfo,
)

logger = logging.getLogger(__name__)


class TelegramGateway(Gateway):
    """
    Telegram 网关 - 通过 python-telegram-bot 库连接
    Telegram gateway - connects via python-telegram-bot library.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._token = config.get("token", "")
        self._proxy = config.get("proxy", "")
        self._application: Any = None
        self._metadata = GatewayMetadata(
            adapter_type="telegram",
            instance_name=config.get("name", "telegram"),
            description="Telegram Bot gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        """
        启动 Telegram Bot 轮询
        Start Telegram Bot polling.
        """
        from telegram.ext import ApplicationBuilder, MessageHandler, filters

        builder = ApplicationBuilder().token(self._token)
        if self._proxy:
            builder = builder.proxy(self._proxy).get_updates_proxy(self._proxy)

        self._application = builder.build()

        # 注册消息处理器
        self._application.add_handler(MessageHandler(filters.ALL, self._handle_update))

        self._status = GatewayStatus.RUNNING
        logger.info("Telegram 机器人开始轮询")

        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling()

        # 保持运行 / Keep running using event
        self._stop_event = asyncio.Event()
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass

    async def halt(self) -> None:
        """停止 Bot / Stop the bot."""
        self._status = GatewayStatus.STOPPED
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if self._application is not None:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()

    async def send_message(
        self,
        target_id: str,
        payload: Any,
        **kwargs: Any,
    ) -> None:
        """
        发送消息到 Telegram
        Send a message to Telegram.
        """
        if self._application is None:
            return

        bot = self._application.bot
        text = str(payload) if not isinstance(payload, str) else payload
        await bot.send_message(chat_id=target_id, text=text)

    async def _handle_update(self, update: Any, context: Any) -> None:
        """
        处理 Telegram Update
        Handle a Telegram Update.
        """
        message = update.message or update.edited_message
        if message is None:
            return

        text = message.text or message.caption or ""
        chat = message.chat
        sender = message.from_user

        is_private = chat.type == "private"
        session_id = str(chat.id)

        components = [TextComponent(text=text)]

        # 检查是否有图片
        if message.photo:
            photo = message.photo[-1]  # 取最大分辨率
            file = await photo.get_file()
            components.append(ImageComponent(url=file.file_path or ""))

        session = SessionInfo(
            platform="telegram",
            session_id=session_id,
            sender_id=str(sender.id) if sender else "",
            sender_nickname=(sender.full_name if sender else ""),
            is_private=is_private,
            is_group=not is_private,
        )

        origin = MessageOrigin(
            platform="telegram",
            message_type="private" if is_private else "group",
            session_id=session_id,
        )

        event = MessageEvent(
            event_id=str(message.message_id),
            kind=EventKind.MESSAGE_RECEIVED,
            components=components,
            session=session,
            origin=origin,
            raw_message=update,
            message_id=str(message.message_id),
        )

        # 注入回复
        async def reply_fn(content: Any) -> None:
            await self.send_message(session_id, content)

        event._reply_fn = reply_fn

        await self.submit_event(event)
