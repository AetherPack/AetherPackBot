"""
企业微信网关适配器
WeCom (Enterprise WeChat) gateway adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus

logger = logging.getLogger(__name__)


class WeComGateway(Gateway):
    """企业微信网关 / WeCom gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._metadata = GatewayMetadata(
            adapter_type="wecom",
            instance_name=config.get("name", "wecom"),
            description="WeCom (Enterprise WeChat) gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        self._status = GatewayStatus.RUNNING
        logger.info("企业微信网关已启动")

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        logger.info("正在发送消息到企业微信: %s", target_id)

    async def handle_webhook(self, request: Any) -> Any:
        return {"status": "ok"}
