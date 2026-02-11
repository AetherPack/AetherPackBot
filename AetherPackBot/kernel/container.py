"""
依赖注入容器 - 管理所有服务的生命周期和依赖关系
Dependency Injection Container - manages lifecycle and dependencies of all services.

采用 IoC 模式，所有服务通过容器注册和获取，避免硬编码依赖。
Uses IoC pattern; all services are registered and resolved via the container.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from enum import Enum, auto
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Lifecycle(Enum):
    """服务生命周期类型 / Service lifecycle type."""

    # 单例：全局唯一实例
    SINGLETON = auto()
    # 瞬态：每次获取创建新实例
    TRANSIENT = auto()
    # 作用域：在同一作用域内共享
    SCOPED = auto()


class ServiceDescriptor:
    """
    服务描述符 - 记录如何创建和管理一个服务
    Service descriptor - records how to create and manage a service.
    """

    __slots__ = ("factory", "lifecycle", "instance", "alias")

    def __init__(
        self,
        factory: Callable[..., Any],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        alias: str | None = None,
    ):
        self.factory = factory
        self.lifecycle = lifecycle
        self.instance: Any = None
        self.alias = alias


class ServiceContainer:
    """
    服务容器 - 框架的核心 IoC 容器
    Service container - the core IoC container of the framework.

    支持：
    - 按类型注册和获取服务
    - 按名称注册和获取服务
    - 单例/瞬态/作用域生命周期
    - 异步初始化
    - 自动依赖解析
    """

    def __init__(self) -> None:
        # 按类型索引的服务描述符
        self._type_registry: dict[type, ServiceDescriptor] = {}
        # 按名称索引的服务描述符
        self._name_registry: dict[str, ServiceDescriptor] = {}
        # 作用域实例缓存
        self._scope_cache: dict[str, dict[type, Any]] = {}
        # 已初始化标记
        self._initialized = False
        # 锁，确保并发安全
        self._lock = asyncio.Lock()

    def register(
        self,
        service_type: type,
        factory: Callable[..., Any] | None = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        name: str | None = None,
    ) -> None:
        """
        注册一个服务到容器
        Register a service into the container.
        """
        if factory is None:
            factory = service_type

        descriptor = ServiceDescriptor(factory=factory, lifecycle=lifecycle, alias=name)
        self._type_registry[service_type] = descriptor

        if name:
            self._name_registry[name] = descriptor

        logger.debug(
            "已注册服务: 类型=%s, 名称=%s, 生命周期=%s",
            service_type.__name__,
            name,
            lifecycle.name,
        )

    def register_instance(
        self,
        service_type: type,
        instance: Any,
        name: str | None = None,
    ) -> None:
        """
        直接注册一个已有实例（单例）
        Register an existing instance directly (singleton).
        """
        descriptor = ServiceDescriptor(
            factory=lambda: instance, lifecycle=Lifecycle.SINGLETON, alias=name
        )
        descriptor.instance = instance
        self._type_registry[service_type] = descriptor

        if name:
            self._name_registry[name] = descriptor

    async def resolve(self, service_type: type[T]) -> T:
        """
        按类型解析服务
        Resolve a service by type.
        """
        descriptor = self._type_registry.get(service_type)
        if descriptor is None:
            raise KeyError(f"Service not found in container: {service_type.__name__}")
        return await self._create_instance(descriptor)

    async def resolve_by_name(self, name: str) -> Any:
        """
        按名称解析服务
        Resolve a service by name.
        """
        descriptor = self._name_registry.get(name)
        if descriptor is None:
            raise KeyError(f"Service not found by name: {name}")
        return await self._create_instance(descriptor)

    def resolve_sync(self, service_type: type[T]) -> T:
        """
        同步版本的解析（仅适用于已经初始化的单例）
        Synchronous resolve (only for already initialized singletons).
        """
        descriptor = self._type_registry.get(service_type)
        if descriptor is None:
            raise KeyError(f"Service not found in container: {service_type.__name__}")
        if descriptor.instance is not None:
            return descriptor.instance
        raise RuntimeError(
            f"Cannot resolve {service_type.__name__} synchronously - not yet initialized"
        )

    async def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        根据描述符创建或获取服务实例
        Create or retrieve a service instance based on the descriptor.
        """
        # 单例：复用已有实例
        if (
            descriptor.lifecycle == Lifecycle.SINGLETON
            and descriptor.instance is not None
        ):
            return descriptor.instance

        async with self._lock:
            # 双重检查（防止并发重复创建）
            if (
                descriptor.lifecycle == Lifecycle.SINGLETON
                and descriptor.instance is not None
            ):
                return descriptor.instance

            instance = descriptor.factory()

            # 如果工厂返回协程，则等待
            if inspect.isawaitable(instance):
                instance = await instance

            if descriptor.lifecycle == Lifecycle.SINGLETON:
                descriptor.instance = instance

            return instance

    def has(self, service_type: type) -> bool:
        """检查是否注册了指定类型的服务 / Check if a service type is registered."""
        return service_type in self._type_registry

    def has_name(self, name: str) -> bool:
        """检查是否注册了指定名称的服务 / Check if a named service is registered."""
        return name in self._name_registry

    def all_registered_types(self) -> list[type]:
        """获取所有注册的服务类型 / Get all registered service types."""
        return list(self._type_registry.keys())

    async def dispose(self) -> None:
        """
        销毁容器中所有服务
        Dispose all services in the container.
        """
        for descriptor in self._type_registry.values():
            if descriptor.instance is not None:
                # 如果实例有 dispose/close/shutdown 方法则调用
                for method_name in ("dispose", "close", "shutdown"):
                    method = getattr(descriptor.instance, method_name, None)
                    if callable(method):
                        result = method()
                        if inspect.isawaitable(result):
                            await result
                        break
                descriptor.instance = None

        self._type_registry.clear()
        self._name_registry.clear()
        self._scope_cache.clear()
        logger.info("服务容器已销毁")
