"""
启动引导器 - 框架的生命周期管理
Bootstrap - framework lifecycle management.

负责按正确顺序初始化所有子系统，并管理关闭流程。
Responsible for initializing all subsystems in the correct order
and managing the shutdown process.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Any

from AetherPackBot.kernel.container import ServiceContainer
from AetherPackBot.kernel.middleware import MiddlewareChain
from AetherPackBot.kernel.signal_hub import SignalHub, SignalKind

logger = logging.getLogger(__name__)


class Bootstrap:
    """
    引导器 - 编排整个框架的启动和关闭
    Bootstrap - orchestrates the startup and shutdown of the entire framework.

    启动顺序：
    1. 初始化日志系统
    2. 加载配置
    3. 初始化存储层
    4. 注册核心服务到容器
    5. 构建中间件链
    6. 加载扩展包
    7. 启动网关（消息平台）
    8. 启动 Web 服务
    9. 发射 SYSTEM_READY 信号
    """

    def __init__(self) -> None:
        self.container = ServiceContainer()
        self.signal_hub = SignalHub()
        self.middleware_chain = MiddlewareChain()
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> None:
        """
        启动框架
        Start the framework.
        """
        logger.info("AetherPackBot 正在启动...")

        # 注册核心组件到容器
        self.container.register_instance(ServiceContainer, self.container)
        self.container.register_instance(SignalHub, self.signal_hub)
        self.container.register_instance(MiddlewareChain, self.middleware_chain)
        self.container.register_instance(Bootstrap, self)

        # 初始化配置
        await self._init_config()

        # 初始化存储层
        await self._init_store()

        # 构建中间件链
        await self._build_middleware_chain()

        # 加载扩展包
        await self._load_packs()

        # 启动网关
        await self._start_gateways()

        # 启动 Web 服务
        await self._start_web_service()

        # 发射系统就绪信号
        await self.signal_hub.emit_new(SignalKind.SYSTEM_READY, source="bootstrap")

        logger.info("AetherPackBot 启动成功")

    async def _init_config(self) -> None:
        """初始化配置系统 / Initialize the configuration system."""
        from AetherPackBot.config.defaults import build_default_config
        from AetherPackBot.config.manager import ConfigManager

        config_mgr = ConfigManager(defaults=build_default_config())
        await config_mgr.load()
        self.container.register_instance(ConfigManager, config_mgr, name="config")
        logger.info("配置已加载")

    async def _init_store(self) -> None:
        """初始化存储层 / Initialize the storage layer."""
        from AetherPackBot.store.engine import StorageEngine

        config_mgr = await self.container.resolve_by_name("config")
        db_path = config_mgr.get("store.db_path", "data/aether.db")

        engine = StorageEngine(db_path)
        await engine.initialize()
        self.container.register_instance(StorageEngine, engine, name="store")
        logger.info("存储引擎已初始化: %s", db_path)

    async def _build_middleware_chain(self) -> None:
        """
        构建中间件链
        Build the middleware chain.

        中间件按优先级排序（数字越小越先执行）：
        0-9: 唤醒检测
        10-19: 安全检查
        20-29: 会话管理
        30-39: 预处理
        40-59: 核心处理（扩展包 + LLM）
        60-79: 结果装饰
        80-99: 响应发送
        """
        from AetherPackBot.kernel.builtin_middlewares import (
            AccessControlMiddleware,
            ContentGuardMiddleware,
            DeliveryMiddleware,
            IntellectMiddleware,
            PackDispatchMiddleware,
            RateLimiterMiddleware,
            ResponseDecoratorMiddleware,
            SessionMiddleware,
            WakeDetectionMiddleware,
        )

        self.middleware_chain.use(WakeDetectionMiddleware(), priority=5)
        self.middleware_chain.use(AccessControlMiddleware(), priority=10)
        self.middleware_chain.use(RateLimiterMiddleware(), priority=12)
        self.middleware_chain.use(ContentGuardMiddleware(), priority=15)
        self.middleware_chain.use(SessionMiddleware(), priority=20)
        self.middleware_chain.use(PackDispatchMiddleware(), priority=40)
        self.middleware_chain.use(IntellectMiddleware(), priority=50)
        self.middleware_chain.use(ResponseDecoratorMiddleware(), priority=70)
        self.middleware_chain.use(DeliveryMiddleware(), priority=90)

        logger.info(
            "中间件链已构建，共 %d 个中间件", self.middleware_chain.count
        )

    async def _load_packs(self) -> None:
        """加载扩展包 / Load extension packs."""
        from AetherPackBot.pack.loader import PackLoader

        loader = PackLoader(self.container)
        await loader.discover_and_load()
        self.container.register_instance(PackLoader, loader, name="pack_loader")
        logger.info("扩展包已加载")

    async def _start_gateways(self) -> None:
        """启动消息网关 / Start message gateways."""
        from AetherPackBot.gateway.registry import GatewayRegistry

        registry = GatewayRegistry(self.container, self.signal_hub)
        config_mgr = await self.container.resolve_by_name("config")
        await registry.initialize_from_config(config_mgr)
        self.container.register_instance(
            GatewayRegistry, registry, name="gateway_registry"
        )
        logger.info("网关已启动")

    async def _start_web_service(self) -> None:
        """启动 Web 服务 / Start the web service."""
        from AetherPackBot.web.app import WebApplication

        config_mgr = await self.container.resolve_by_name("config")
        host = config_mgr.get("web.host", "0.0.0.0")
        port = config_mgr.get("web.port", 6185)

        web_app = WebApplication(self.container, host=host, port=port)
        self.container.register_instance(WebApplication, web_app, name="web_app")

        # 后台启动 Web 服务
        task = asyncio.create_task(web_app.run())
        self._tasks.append(task)
        logger.info("Web 服务正在启动: %s:%d", host, port)

    async def run_forever(self) -> None:
        """
        持续运行直到收到关闭信号
        Run until a shutdown signal is received.
        """
        loop = asyncio.get_running_loop()

        # 注册系统信号（仅 Unix）
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._shutdown_event.set)
        else:
            # Windows 下使用键盘中断
            pass

        try:
            await self._shutdown_event.wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """
        优雅关闭
        Graceful shutdown.
        """
        logger.info("AetherPackBot 正在关闭...")

        # 发射关闭信号
        await self.signal_hub.emit_new(SignalKind.SYSTEM_SHUTDOWN, source="bootstrap")

        # 取消所有任务
        for task in self._tasks:
            task.cancel()

        # 等待任务结束
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # 销毁容器
        await self.container.dispose()

        # 清理信号中枢
        self.signal_hub.clear()

        logger.info("AetherPackBot 已完全关闭")
