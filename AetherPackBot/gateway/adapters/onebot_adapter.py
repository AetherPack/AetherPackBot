"""
OneBot 协议网关适配器 - 对接 OneBot v11/v12 协议
OneBot protocol gateway adapter - interfaces with OneBot v11/v12 protocol.

支持 NapCat、LagrangeCore 等 OneBot 实现。
Supports NapCat, LagrangeCore and other OneBot implementations.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus
from AetherPackBot.message.components import (
    AtComponent,
    ImageComponent,
    TextComponent,
)
from AetherPackBot.message.event import (
    EventKind,
    MessageEvent,
    MessageOrigin,
    SessionInfo,
)

logger = logging.getLogger(__name__)


class OneBotGateway(Gateway):
    """
    OneBot 协议网关 - 通过 WebSocket 连接 OneBot 服务
    OneBot protocol gateway - connects to OneBot service via WebSocket.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._ws_host = config.get("host", "127.0.0.1")
        self._ws_port = config.get("port", 6700)
        self._access_token = config.get("access_token", "")
        self._connection: Any = None
        self._metadata = GatewayMetadata(
            adapter_type="onebot",
            instance_name=config.get("name", "onebot"),
            description="OneBot v11/v12 (QQ/QQNT) gateway adapter",
            supports_webhook=False,
        )

    async def launch(self) -> None:
        """
        启动 WebSocket 连接到 OneBot 服务
        Start WebSocket connection to OneBot service.
        """
        import websockets

        url = f"ws://{self._ws_host}:{self._ws_port}/ws"
        if self._access_token:
            url += f"?access_token={self._access_token}"

        logger.info("正在连接 OneBot: %s", url)
        self._status = GatewayStatus.RUNNING

        try:
            async with websockets.connect(url) as ws:
                self._connection = ws
                async for raw_msg in ws:
                    try:
                        data = json.loads(raw_msg)
                        await self._handle_raw_event(data)
                    except json.JSONDecodeError:
                        logger.warning("收到无效的 OneBot JSON 数据")
                    except Exception:
                        logger.exception("处理 OneBot 事件出错")
        except asyncio.CancelledError:
            raise
        except Exception:
            self._status = GatewayStatus.ERROR
            logger.exception("OneBot WebSocket 连接失败")

    async def halt(self) -> None:
        """关闭连接 / Close connection."""
        if self._connection is not None:
            await self._connection.close()
        self._status = GatewayStatus.STOPPED

    async def send_message(
        self,
        target_id: str,
        payload: Any,
        **kwargs: Any,
    ) -> None:
        """
        发送消息到 OneBot
        Send a message via OneBot.
        """
        if self._connection is None:
            logger.warning("OneBot 连接未建立")
            return

        message_type = kwargs.get("message_type", "private")
        action = "send_private_msg" if message_type == "private" else "send_group_msg"

        # 转换消息载荷为 OneBot CQ 消息格式
        ob_message = self._convert_to_ob_message(payload)

        request = {
            "action": action,
            "params": {
                ("user_id" if message_type == "private" else "group_id"): int(
                    target_id
                ),
                "message": ob_message,
            },
        }

        await self._connection.send(json.dumps(request))

    async def _handle_raw_event(self, data: dict[str, Any]) -> None:
        """
        解析 OneBot 原始事件并转换为 MessageEvent
        Parse raw OneBot event and convert to MessageEvent.
        """
        post_type = data.get("post_type", "")

        if post_type != "message":
            return

        msg_type = data.get("message_type", "")
        is_private = msg_type == "private"

        # 解析消息组件
        components = self._parse_ob_message(data.get("message", []))

        # 构建会话信息
        sender = data.get("sender", {})
        group_id = str(data.get("group_id", ""))
        user_id = str(data.get("user_id", ""))
        session_id = user_id if is_private else group_id

        session = SessionInfo(
            platform="onebot",
            session_id=session_id,
            sender_id=user_id,
            sender_nickname=sender.get("nickname", ""),
            is_private=is_private,
            is_group=not is_private,
            extra={"raw": data},
        )

        origin = MessageOrigin(
            platform="onebot",
            message_type="private" if is_private else "group",
            session_id=session_id,
        )

        event = MessageEvent(
            event_id=str(data.get("message_id", "")),
            kind=EventKind.MESSAGE_RECEIVED,
            components=components,
            session=session,
            origin=origin,
            raw_message=data,
            message_id=str(data.get("message_id", "")),
            timestamp=float(data.get("time", 0)),
        )

        # 注入回复函数
        async def reply_fn(content: Any) -> None:
            await self.send_message(session_id, content, message_type=msg_type)

        event._reply_fn = reply_fn

        await self.submit_event(event)

    def _parse_ob_message(self, message: Any) -> list[Any]:
        """
        解析 OneBot 消息段为组件列表
        Parse OneBot message segments to component list.
        """
        components = []

        if isinstance(message, str):
            components.append(TextComponent(text=message))
            return components

        if isinstance(message, list):
            for seg in message:
                seg_type = seg.get("type", "")
                seg_data = seg.get("data", {})

                if seg_type == "text":
                    components.append(TextComponent(text=seg_data.get("text", "")))
                elif seg_type == "image":
                    components.append(ImageComponent(url=seg_data.get("url", "")))
                elif seg_type == "at":
                    components.append(
                        AtComponent(target_id=str(seg_data.get("qq", "")))
                    )
                # 可扩展更多类型

        return components

    def _convert_to_ob_message(self, payload: Any) -> list[dict[str, Any]]:
        """
        将消息载荷转换为 OneBot CQ 消息格式
        Convert message payload to OneBot CQ message format.
        """
        if isinstance(payload, str):
            return [{"type": "text", "data": {"text": payload}}]

        if isinstance(payload, list):
            result = []
            for item in payload:
                if hasattr(item, "kind"):
                    if item.kind.value == "text":
                        result.append({"type": "text", "data": {"text": item.text}})
                    elif item.kind.value == "image":
                        result.append({"type": "image", "data": {"file": item.url}})
                else:
                    result.append({"type": "text", "data": {"text": str(item)}})
            return result

        return [{"type": "text", "data": {"text": str(payload)}}]
