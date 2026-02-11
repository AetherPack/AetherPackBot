"""
内置网页聊天网关适配器
WebChat (built-in web chat) gateway adapter.
"""

from __future__ import annotations

import json
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


class WebChatGateway(Gateway):
    """内置网页聊天网关 / Built-in web chat gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._clients: dict[str, Any] = {}
        self._metadata = GatewayMetadata(
            adapter_type="webchat",
            instance_name=config.get("name", "webchat"),
            description="Built-in web chat gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        """WebChat 通过 Web 服务的 WebSocket 运行 / Runs via web service WebSocket."""
        self._status = GatewayStatus.RUNNING
        logger.info("WebChat 网关已启动 (通过 Web 服务运行)")

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED
        for ws in self._clients.values():
            try:
                await ws.close()
            except Exception:
                pass
        self._clients.clear()

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        ws = self._clients.get(target_id)
        if ws is not None:
            text = str(payload) if not isinstance(payload, str) else payload
            await ws.send(json.dumps({"type": "message", "content": text}))

    async def on_ws_message(self, ws: Any, session_id: str, data: str) -> None:
        """
        处理 WebSocket 消息
        Handle a WebSocket message.
        """
        self._clients[session_id] = ws

        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            return

        text = msg.get("content", "")
        components = [TextComponent(text=text)]

        session = SessionInfo(
            platform="webchat",
            session_id=session_id,
            sender_id=session_id,
            is_private=True,
        )

        origin = MessageOrigin(
            platform="webchat", message_type="private", session_id=session_id
        )

        event = MessageEvent(
            kind=EventKind.MESSAGE_RECEIVED,
            components=components,
            session=session,
            origin=origin,
        )

        async def reply_fn(content: Any) -> None:
            await self.send_message(session_id, content)

        event._reply_fn = reply_fn
        await self.submit_event(event)
