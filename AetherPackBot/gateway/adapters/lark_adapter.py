"""
飞书/Lark 网关适配器
Lark (Feishu) gateway adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus

logger = logging.getLogger(__name__)


class LarkGateway(Gateway):
    """飞书网关 / Lark gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._app_id = config.get("app_id", "")
        self._app_secret = config.get("app_secret", "")
        self._metadata = GatewayMetadata(
            adapter_type="lark",
            instance_name=config.get("name", "lark"),
            description="Lark/Feishu gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        """启动飞书 Bot / Start Lark Bot."""

        self._status = GatewayStatus.RUNNING
        logger.info("飞书网关已启动 (Webhook 模式)")
        # 飞书采用 Webhook 模式，由 Web 服务路由调用 handle_webhook

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        """发送消息到飞书 / Send message to Lark."""
        logger.info("正在发送消息到飞书: %s", target_id)

    async def handle_webhook(self, request: Any) -> Any:
        """处理飞书 Webhook / Handle Lark webhook."""
        # 解析飞书回调数据并生成事件
        return {"status": "ok"}
