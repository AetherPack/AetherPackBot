"""
网关基类 - 所有消息平台适配器的抽象基类
Gateway base - abstract base class for all message platform adapters.

每个具体平台（如 Telegram、QQ）需要实现这个接口。
Each specific platform (e.g. Telegram, QQ) needs to implement this interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from AetherPackBot.message.event import MessageEvent

logger = logging.getLogger(__name__)


class GatewayStatus(Enum):
    """网关状态枚举 / Gateway status enum."""

    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    STOPPED = auto()


@dataclass
class GatewayMetadata:
    """
    网关元数据 - 描述一个网关实例的基本信息
    Gateway metadata - describes basic info about a gateway instance.
    """

    # 网关类型名（如 telegram, onebot）
    adapter_type: str = ""
    # 网关实例名（用户自定义）
    instance_name: str = ""
    # 描述
    description: str = ""
    # 是否支持 Webhook 模式
    supports_webhook: bool = False
    # 附加信息
    extra: dict[str, Any] = field(default_factory=dict)


class Gateway(ABC):
    """
    网关抽象基类 - 所有平台适配器的父类
    Gateway abstract base - parent of all platform adapters.

    设计要求：
    1. 网关负责接收消息并转换为 MessageEvent
    2. 网关通过 on_message 回调将事件提交给系统
    3. 网关负责发送消息到平台
    4. 网关管理自身的连接生命周期
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._status = GatewayStatus.INITIALIZING
        self._on_message: Callable[[MessageEvent], Awaitable[None]] | None = None
        self._metadata = GatewayMetadata()

    @property
    def status(self) -> GatewayStatus:
        """获取当前状态 / Get current status."""
        return self._status

    @property
    def metadata(self) -> GatewayMetadata:
        """获取网关元数据 / Get gateway metadata."""
        return self._metadata

    def set_message_handler(
        self, handler: Callable[[MessageEvent], Awaitable[None]]
    ) -> None:
        """
        设置消息接收回调
        Set the message receive callback.
        """
        self._on_message = handler

    async def submit_event(self, event: MessageEvent) -> None:
        """
        提交消息事件到系统
        Submit a message event to the system.
        """
        if self._on_message is not None:
            await self._on_message(event)
        else:
            logger.warning(
                "网关 %s 未设置消息处理器", self._metadata.instance_name
            )

    @abstractmethod
    async def launch(self) -> None:
        """
        启动网关
        Launch the gateway.

        应该建立与平台的连接并开始监听消息。
        Should establish connection to the platform and start listening.
        """
        ...

    @abstractmethod
    async def halt(self) -> None:
        """
        停止网关
        Halt the gateway.

        应该安全断开连接。
        Should safely disconnect.
        """
        ...

    @abstractmethod
    async def send_message(
        self,
        target_id: str,
        payload: Any,
        **kwargs: Any,
    ) -> None:
        """
        发送消息到指定目标
        Send a message to a specified target.
        """
        ...

    async def handle_webhook(self, request: Any) -> Any:
        """
        处理 Webhook 请求（可选）
        Handle webhook request (optional).
        """
        raise NotImplementedError("This gateway does not support webhook mode")
