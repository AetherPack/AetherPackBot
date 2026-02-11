"""
Slack 网关适配器
Slack gateway adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus

logger = logging.getLogger(__name__)


class SlackGateway(Gateway):
    """Slack 网关 / Slack gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._metadata = GatewayMetadata(
            adapter_type="slack",
            instance_name=config.get("name", "slack"),
            description="Slack gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        self._status = GatewayStatus.RUNNING
        logger.info("Slack 网关已启动")

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        logger.info("正在发送消息到 Slack: %s", target_id)

    async def handle_webhook(self, request: Any) -> Any:
        return {"status": "ok"}
