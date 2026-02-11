"""
网关注册表 - 管理所有网关适配器的注册和实例化
Gateway registry - manages registration and instantiation of all gateway adapters.

使用注册表模式替代装饰器注册，所有适配器显式注册。
Uses registry pattern instead of decorator registration; all adapters register explicitly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from AetherPackBot.gateway.base import Gateway, GatewayStatus
from AetherPackBot.kernel.container import ServiceContainer
from AetherPackBot.kernel.middleware import MiddlewareChain, ProcessingContext
from AetherPackBot.kernel.signal_hub import SignalHub, SignalKind
from AetherPackBot.message.event import MessageEvent

logger = logging.getLogger(__name__)


class GatewayRegistry:
    """
    网关注册表 - 集中管理网关类型和实例
    Gateway registry - centrally manages gateway types and instances.
    """

    def __init__(self, container: ServiceContainer, signal_hub: SignalHub) -> None:
        self._container = container
        self._signal_hub = signal_hub
        # 注册的网关类型: adapter_type -> Gateway类
        self._adapter_types: dict[str, type[Gateway]] = {}
        # 活跃的网关实例
        self._instances: dict[str, Gateway] = {}
        # 网关的后台任务
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def register_adapter_type(
        self,
        adapter_type: str,
        gateway_cls: type[Gateway],
    ) -> None:
        """
        注册一种网关适配器类型
        Register a gateway adapter type.
        """
        self._adapter_types[adapter_type] = gateway_cls
        logger.info("已注册网关适配器类型: %s", adapter_type)

    async def initialize_from_config(self, config_mgr: Any) -> None:
        """
        从配置加载并初始化所有网关
        Load and initialize all gateways from configuration.
        """
        # 注册所有内置适配器
        self._register_builtin_adapters()

        platforms = config_mgr.get("platforms", [])
        for platform_conf in platforms:
            adapter_type = platform_conf.get("type", "")
            instance_name = platform_conf.get("name", adapter_type)
            enabled = platform_conf.get("enabled", True)

            if not enabled:
                continue

            if adapter_type not in self._adapter_types:
                logger.warning("未知的适配器类型: %s", adapter_type)
                continue

            try:
                await self._create_and_launch(
                    adapter_type, instance_name, platform_conf
                )
            except Exception:
                logger.exception(
                    "启动网关失败: %s (%s)", instance_name, adapter_type
                )

    def _register_builtin_adapters(self) -> None:
        """
        注册所有内置网关适配器
        Register all built-in gateway adapters.
        """
        try:
            from AetherPackBot.gateway.adapters.onebot_adapter import OneBotGateway

            self.register_adapter_type("onebot", OneBotGateway)
        except ImportError:
            logger.debug("OneBot 适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.telegram_adapter import (
                TelegramGateway,
            )

            self.register_adapter_type("telegram", TelegramGateway)
        except ImportError:
            logger.debug("Telegram 适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.discord_adapter import DiscordGateway

            self.register_adapter_type("discord", DiscordGateway)
        except ImportError:
            logger.debug("Discord 适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.qq_official_adapter import (
                QQOfficialGateway,
            )

            self.register_adapter_type("qq_official", QQOfficialGateway)
        except ImportError:
            logger.debug("QQ 官方适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.lark_adapter import LarkGateway

            self.register_adapter_type("lark", LarkGateway)
        except ImportError:
            logger.debug("飞书适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.dingtalk_adapter import (
                DingTalkGateway,
            )

            self.register_adapter_type("dingtalk", DingTalkGateway)
        except ImportError:
            logger.debug("钉钉适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.wecom_adapter import WeComGateway

            self.register_adapter_type("wecom", WeComGateway)
        except ImportError:
            logger.debug("企业微信适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.slack_adapter import SlackGateway

            self.register_adapter_type("slack", SlackGateway)
        except ImportError:
            logger.debug("Slack 适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.webchat_adapter import WebChatGateway

            self.register_adapter_type("webchat", WebChatGateway)
        except ImportError:
            logger.debug("WebChat 适配器不可用")

        try:
            from AetherPackBot.gateway.adapters.satori_adapter import SatoriGateway

            self.register_adapter_type("satori", SatoriGateway)
        except ImportError:
            logger.debug("Satori 适配器不可用")

    async def _create_and_launch(
        self,
        adapter_type: str,
        instance_name: str,
        config: dict[str, Any],
    ) -> None:
        """
        创建并启动一个网关实例
        Create and launch a gateway instance.
        """
        gateway_cls = self._adapter_types[adapter_type]
        gateway = gateway_cls(config)
        gateway._metadata.adapter_type = adapter_type
        gateway._metadata.instance_name = instance_name

        # 设置消息回调
        gateway.set_message_handler(self._on_message_received)

        self._instances[instance_name] = gateway

        # 在后台启动
        task = asyncio.create_task(self._run_gateway(gateway))
        self._tasks[instance_name] = task

        logger.info("网关已启动: %s (%s)", instance_name, adapter_type)

    async def _run_gateway(self, gateway: Gateway) -> None:
        """
        运行网关并处理异常
        Run gateway and handle exceptions.
        """
        try:
            gateway._status = GatewayStatus.RUNNING
            await gateway.launch()
        except asyncio.CancelledError:
            pass
        except Exception:
            gateway._status = GatewayStatus.ERROR
            logger.exception(
                "网关 %s 遇到错误",
                gateway.metadata.instance_name,
            )

    async def _on_message_received(self, event: MessageEvent) -> None:
        """
        处理收到的消息 - 通过中间件链处理
        Handle a received message - process through middleware chain.
        """
        # 发射信号
        await self._signal_hub.emit_new(
            SignalKind.GATEWAY_MESSAGE_IN, payload=event, source="gateway"
        )

        # 构建处理上下文
        ctx = ProcessingContext(event=event)
        ctx.store["container"] = self._container

        # 注入配置
        try:
            config_mgr = await self._container.resolve_by_name("config")
            ctx.store["config"] = config_mgr.as_dict()
        except KeyError:
            ctx.store["config"] = {}

        # 通过中间件链处理
        middleware_chain: MiddlewareChain = await self._container.resolve(
            MiddlewareChain
        )
        await middleware_chain.execute(ctx)

    async def shutdown_all(self) -> None:
        """
        关闭所有网关
        Shutdown all gateways.
        """
        for name, gateway in self._instances.items():
            try:
                await gateway.halt()
                gateway._status = GatewayStatus.STOPPED
            except Exception:
                logger.exception("关闭网关出错: %s", name)

        # 取消所有后台任务
        for task in self._tasks.values():
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._instances.clear()
        self._tasks.clear()

    def get_instance(self, name: str) -> Gateway | None:
        """获取网关实例 / Get a gateway instance."""
        return self._instances.get(name)

    def all_instances(self) -> dict[str, Gateway]:
        """获取所有网关实例 / Get all gateway instances."""
        return dict(self._instances)

    @property
    def adapter_types(self) -> list[str]:
        """获取所有已注册的适配器类型 / Get all registered adapter types."""
        return list(self._adapter_types.keys())
