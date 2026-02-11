"""
QQ 官方 Bot 网关适配器 - 对接 QQ 官方 Bot API
QQ Official Bot gateway adapter - interfaces with QQ Official Bot API.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus
from AetherPackBot.message.components import TextComponent
from AetherPackBot.message.event import (
    EventKind,
    MessageEvent,
    MessageOrigin,
    SessionInfo,
)

logger = logging.getLogger(__name__)


class QQOfficialGateway(Gateway):
    """
    QQ 官方 Bot 网关 - 通过 qq-botpy 库连接
    QQ Official Bot gateway - connects via qq-botpy library.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._app_id = config.get("app_id", "")
        self._client_secret = config.get("client_secret", "")
        self._is_sandbox = config.get("sandbox", False)
        self._client: Any = None
        self._metadata = GatewayMetadata(
            adapter_type="qq_official",
            instance_name=config.get("name", "qq_official"),
            description="QQ Official Bot gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        """启动 QQ 官方 Bot / Start QQ Official Bot."""
        import botpy

        class BotClient(botpy.Client):
            gateway_ref: QQOfficialGateway | None = None

            async def on_at_message_create(self, message: Any) -> None:
                if self.gateway_ref:
                    await self.gateway_ref._handle_message(message, is_at=True)

            async def on_direct_message_create(self, message: Any) -> None:
                if self.gateway_ref:
                    await self.gateway_ref._handle_message(message, is_private=True)

        intents = botpy.Intents(public_guild_messages=True, direct_message=True)
        self._client = BotClient(
            intents=intents,
            is_sandbox=self._is_sandbox,
        )
        self._client.gateway_ref = self
        self._status = GatewayStatus.RUNNING

        await self._client.start(appid=self._app_id, secret=self._client_secret)

    async def halt(self) -> None:
        """停止 Bot / Stop the bot."""
        self._status = GatewayStatus.STOPPED
        if self._client is not None:
            await self._client.close()

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        """发送消息 / Send a message."""
        if self._client is None:
            return

        text = str(payload) if not isinstance(payload, str) else payload
        channel_id = kwargs.get("channel_id", target_id)
        msg_id = kwargs.get("msg_id", "")

        await self._client.api.post_message(
            channel_id=channel_id, content=text, msg_id=msg_id
        )

    async def _handle_message(
        self,
        message: Any,
        is_at: bool = False,
        is_private: bool = False,
    ) -> None:
        """处理消息 / Handle a message."""
        content = getattr(message, "content", "")
        author = getattr(message, "author", None)
        channel_id = getattr(message, "channel_id", "")
        guild_id = getattr(message, "guild_id", "")

        session_id = channel_id or guild_id

        components = [TextComponent(text=content.strip())]

        session = SessionInfo(
            platform="qq_official",
            session_id=session_id,
            sender_id=getattr(author, "id", "") if author else "",
            sender_nickname=getattr(author, "username", "") if author else "",
            is_private=is_private,
            is_group=not is_private,
            is_mentioned=is_at,
        )

        origin = MessageOrigin(
            platform="qq_official",
            message_type="private" if is_private else "group",
            session_id=session_id,
        )

        event = MessageEvent(
            event_id=getattr(message, "id", ""),
            kind=EventKind.MESSAGE_RECEIVED,
            components=components,
            session=session,
            origin=origin,
            raw_message=message,
            message_id=getattr(message, "id", ""),
        )

        msg_id = getattr(message, "id", "")

        async def reply_fn(resp: Any) -> None:
            await self.send_message(
                session_id, resp, channel_id=channel_id, msg_id=msg_id
            )

        event._reply_fn = reply_fn
        await self.submit_event(event)
