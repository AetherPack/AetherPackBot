"""
Satori 协议网关适配器
Satori protocol gateway adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayMetadata, GatewayStatus

logger = logging.getLogger(__name__)


class SatoriGateway(Gateway):
    """Satori 协议网关 / Satori protocol gateway."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._metadata = GatewayMetadata(
            adapter_type="satori",
            instance_name=config.get("name", "satori"),
            description="Satori protocol gateway adapter",
        )

    async def launch(self) -> None:
        self._status = GatewayStatus.RUNNING
        logger.info("Satori 网关已启动")

    async def halt(self) -> None:
        self._status = GatewayStatus.STOPPED

    async def send_message(self, target_id: str, payload: Any, **kwargs: Any) -> None:
        logger.info("正在通过 Satori 发送消息: %s", target_id)
