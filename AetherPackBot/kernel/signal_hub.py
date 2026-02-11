"""
信号中枢 - 基于发布/订阅模式的类型化事件系统
Signal Hub - typed event system based on publish/subscribe pattern.

与传统队列式事件总线不同，信号中枢使用类型化信号进行通信，
支持同步和异步处理器，支持优先级和过滤。
Unlike traditional queue-based event bus, the signal hub uses typed signals
for communication with sync/async handlers, priority, and filtering support.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SignalPriority(Enum):
    """信号处理器优先级 / Signal handler priority."""

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


class SignalKind(str, Enum):
    """
    预定义的信号类型 / Predefined signal kinds.

    覆盖了机器人生命周期中的所有关键事件。
    Covers all critical events in the bot lifecycle.
    """

    # 系统信号
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_CONFIG_CHANGED = "system.config_changed"

    # 网关信号（消息平台相关）
    GATEWAY_CONNECTED = "gateway.connected"
    GATEWAY_DISCONNECTED = "gateway.disconnected"
    GATEWAY_MESSAGE_IN = "gateway.message_in"
    GATEWAY_MESSAGE_OUT = "gateway.message_out"

    # 智能层信号（LLM 相关）
    INTELLECT_REQUEST = "intellect.request"
    INTELLECT_RESPONSE = "intellect.response"
    INTELLECT_TOOL_CALL = "intellect.tool_call"
    INTELLECT_TOOL_RESULT = "intellect.tool_result"

    # 扩展包信号
    PACK_LOADED = "pack.loaded"
    PACK_UNLOADED = "pack.unloaded"
    PACK_ERROR = "pack.error"

    # 用户自定义信号（通过字符串匹配）
    CUSTOM = "custom"


@dataclass
class Signal:
    """
    信号对象 - 在系统中传递的消息载体
    Signal object - the message carrier in the system.
    """

    kind: SignalKind | str
    payload: Any = None
    source: str = ""
    # 是否已消费（消费后不再传播）
    consumed: bool = False
    # 附加元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def consume(self) -> None:
        """标记信号为已消费，阻止后续处理器处理 / Mark signal as consumed."""
        self.consumed = True


@dataclass
class SlotBinding:
    """
    槽绑定 - 将处理器绑定到信号上
    Slot binding - binds a handler to a signal.
    """

    signal_kind: SignalKind | str
    handler: Callable[..., Any]
    priority: SignalPriority = SignalPriority.NORMAL
    # 可选过滤函数，返回 True 才执行
    filter_fn: Callable[[Signal], bool] | None = None
    # 唯一标识
    slot_id: str = ""
    # 是否只触发一次
    once: bool = False


class SignalHub:
    """
    信号中枢 - 管理所有信号的订阅和分发
    Signal hub - manages all signal subscriptions and dispatching.

    核心设计理念：
    1. 类型安全 - 信号和处理器都有明确类型
    2. 优先级排序 - 处理器按优先级执行
    3. 可消费 - 处理器可以阻止信号继续传播
    4. 异步优先 - 原生支持异步处理器
    """

    def __init__(self) -> None:
        # 信号类型 -> 槽绑定列表
        self._slots: dict[str, list[SlotBinding]] = {}
        # 全局拦截器（对所有信号生效）
        self._interceptors: list[Callable[[Signal], Awaitable[Signal | None]]] = []
        self._running = False
        self._counter = 0

    def connect(
        self,
        signal_kind: SignalKind | str,
        handler: Callable[..., Any],
        priority: SignalPriority = SignalPriority.NORMAL,
        filter_fn: Callable[[Signal], bool] | None = None,
        once: bool = False,
    ) -> str:
        """
        连接处理器到信号
        Connect a handler to a signal kind.

        返回 slot_id，可用于 disconnect。
        Returns slot_id for later disconnection.
        """
        kind_key = (
            signal_kind.value if isinstance(signal_kind, SignalKind) else signal_kind
        )
        self._counter += 1
        slot_id = f"slot_{self._counter}"

        binding = SlotBinding(
            signal_kind=signal_kind,
            handler=handler,
            priority=priority,
            filter_fn=filter_fn,
            slot_id=slot_id,
            once=once,
        )

        if kind_key not in self._slots:
            self._slots[kind_key] = []

        self._slots[kind_key].append(binding)
        # 按优先级排序
        self._slots[kind_key].sort(key=lambda b: b.priority.value)

        logger.debug("已连接槽 %s 到信号 %s", slot_id, kind_key)
        return slot_id

    def disconnect(self, slot_id: str) -> bool:
        """
        断开指定 slot 的连接
        Disconnect a specific slot.
        """
        for kind_key, bindings in self._slots.items():
            for binding in bindings:
                if binding.slot_id == slot_id:
                    bindings.remove(binding)
                    logger.debug("已断开槽 %s", slot_id)
                    return True
        return False

    def add_interceptor(
        self, interceptor: Callable[[Signal], Awaitable[Signal | None]]
    ) -> None:
        """
        添加全局信号拦截器
        Add a global signal interceptor.

        拦截器可以修改或吞噬信号（返回 None 则吞噬）。
        Interceptor can modify or swallow a signal (return None to swallow).
        """
        self._interceptors.append(interceptor)

    async def emit(self, signal: Signal) -> Signal:
        """
        发射信号，触发所有匹配的处理器
        Emit a signal, triggering all matching handlers.
        """
        # 先通过全局拦截器
        for interceptor in self._interceptors:
            result = await interceptor(signal)
            if result is None:
                logger.debug("信号 %s 被拦截器吞噬", signal.kind)
                return signal
            signal = result

        kind_key = (
            signal.kind.value if isinstance(signal.kind, SignalKind) else signal.kind
        )
        bindings = self._slots.get(kind_key, [])
        to_remove: list[SlotBinding] = []

        for binding in bindings:
            if signal.consumed:
                break

            # 过滤器检查
            if binding.filter_fn is not None and not binding.filter_fn(signal):
                continue

            try:
                result = binding.handler(signal)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await result
            except Exception:
                logger.exception(
                    "信号处理器 %s 处理 %s 时出错",
                    binding.slot_id,
                    kind_key,
                )

            if binding.once:
                to_remove.append(binding)

        # 清理一次性槽
        for binding in to_remove:
            if kind_key in self._slots:
                self._slots[kind_key].remove(binding)

        return signal

    async def emit_new(
        self,
        kind: SignalKind | str,
        payload: Any = None,
        source: str = "",
        **metadata: Any,
    ) -> Signal:
        """
        便捷方法：创建并发射一个新信号
        Convenience: create and emit a new signal.
        """
        signal = Signal(kind=kind, payload=payload, source=source, metadata=metadata)
        return await self.emit(signal)

    def slot_count(self, signal_kind: SignalKind | str | None = None) -> int:
        """获取槽绑定数量 / Get the number of slot bindings."""
        if signal_kind is None:
            return sum(len(bindings) for bindings in self._slots.values())
        kind_key = (
            signal_kind.value if isinstance(signal_kind, SignalKind) else signal_kind
        )
        return len(self._slots.get(kind_key, []))

    def clear(self) -> None:
        """清除所有槽绑定 / Clear all slot bindings."""
        self._slots.clear()
        self._interceptors.clear()
