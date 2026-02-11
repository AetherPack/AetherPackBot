"""
Discord 网关适配器 - 对接 Discord Bot API
Discord gateway adapter - interfaces with the Discord Bot API.
"""

from __future__ import annotations

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


class DiscordGateway(Gateway):
    """
    Discord 网关 - 通过 py-cord 库连接
    Discord gateway - connects via py-cord library.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._token = config.get("token", "")
        self._bot: Any = None
        self._metadata = GatewayMetadata(
            adapter_type="discord",
            instance_name=config.get("name", "discord"),
            description="Discord Bot gateway adapter",
        )

    async def launch(self) -> None:
        """启动 Discord Bot / Start Discord Bot."""
        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        self._bot = discord.Bot(intents=intents)

        @self._bot.event
        async def on_ready() -> None:
            logger.info("Discord 机器人已登录: %s", self._bot.user)

        @self._bot.event
        async def on_message(message: Any) -> None:
            if message.author == self._bot.user:
                return
            await self._handle_discord_message(message)

        self._status = GatewayStatus.RUNNING
        await self._bot.start(self._token)

    async def halt(self) -> None:
        """停止 Bot / Stop the bot."""
        self._status = GatewayStatus.STOPPED
        if self._bot is not None:
            await self._bot.close()

    async def send_message(
        self,
        target_id: str,
        payload: Any,
        **kwargs: Any,
    ) -> None:
        """发送消息到 Discord / Send message to Discord."""
        if self._bot is None:
            return
        channel = self._bot.get_channel(int(target_id))
        if channel is not None:
            text = str(payload) if not isinstance(payload, str) else payload
            await channel.send(text)

    async def _handle_discord_message(self, message: Any) -> None:
        """处理 Discord 消息 / Handle a Discord message."""
        is_private = message.guild is None
        session_id = str(message.channel.id)

        components = [TextComponent(text=message.content)]

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                components.append(ImageComponent(url=attachment.url))

        session = SessionInfo(
            platform="discord",
            session_id=session_id,
            sender_id=str(message.author.id),
            sender_nickname=message.author.display_name,
            is_private=is_private,
            is_group=not is_private,
            is_mentioned=self._bot.user in message.mentions
            if self._bot.user
            else False,
        )

        origin = MessageOrigin(
            platform="discord",
            message_type="private" if is_private else "group",
            session_id=session_id,
        )

        event = MessageEvent(
            event_id=str(message.id),
            kind=EventKind.MESSAGE_RECEIVED,
            components=components,
            session=session,
            origin=origin,
            raw_message=message,
            message_id=str(message.id),
        )

        async def reply_fn(content: Any) -> None:
            text = str(content) if not isinstance(content, str) else content
            await message.channel.send(text)

        event._reply_fn = reply_fn
        await self.submit_event(event)
