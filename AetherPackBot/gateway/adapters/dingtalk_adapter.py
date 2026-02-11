"""
钉钉网关适配器
DingTalk gateway adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus

logger = logging.getLogger(__name__)


class DingTalkGateway(Gateway):
    """钉钉网关 / DingTalk gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._metadata = GatewayMetadata(
            adapter_type="dingtalk",
            instance_name=config.get("name", "dingtalk"),
            description="DingTalk gateway adapter",
            supports_webhook=True,
        )

    async def launch(self) -> None:
        self._status = GatewayStatus.RUNNING
        logger.info("钉钉网关已启动")

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        logger.info("正在发送消息到钉钉: %s", target_id)

    async def handle_webhook(self, request: Any) -> Any:
        return {"status": "ok"}
