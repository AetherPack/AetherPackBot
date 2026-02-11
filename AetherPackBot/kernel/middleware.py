"""
中间件链 - Express 风格的消息处理中间件系统
Middleware Chain - Express-style message processing middleware system.

取代传统的管道/阶段模式，使用中间件链进行消息处理。
每个中间件可以决定是否将消息传递给下一个中间件。
Replaces the traditional pipeline/stage pattern with a middleware chain.
Each middleware can decide whether to pass the message to the next one.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """
    处理上下文 - 在中间件之间传递的共享上下文
    Processing context - shared context passed between middlewares.

    每条消息创建一个独立的上下文实例。
    A unique context instance is created for each message.
    """

    # 原始消息事件
    event: Any = None
    # 处理结果
    response: Any = None
    # 是否已经终止处理链
    terminated: bool = False
    # 上下文数据存储（中间件之间共享数据）
    store: dict[str, Any] = field(default_factory=dict)
    # 计时
    start_time: float = field(default_factory=time.time)
    # 错误信息
    errors: list[Exception] = field(default_factory=list)

    def terminate(self) -> None:
        """终止处理链 / Terminate the middleware chain."""
        self.terminated = True

    @property
    def elapsed_ms(self) -> float:
        """获取已经过的毫秒数 / Get elapsed milliseconds."""
        return (time.time() - self.start_time) * 1000


# 下一个中间件的调用类型
NextFunction = Callable[[], Awaitable[None]]


class Middleware(ABC):
    """
    中间件基类 - 所有消息处理中间件的抽象基类
    Middleware base - abstract base class for all message processing middlewares.

    中间件模式与管道/阶段模式的区别：
    - 管道模式是线性的，阶段之间耦合紧密
    - 中间件模式是嵌套的，每个中间件可以在调用 next 前/后执行逻辑
    - 中间件可以在任何时候短路处理链
    """

    @abstractmethod
    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        """
        处理消息事件
        Handle a message event.

        调用 next_fn() 将控制权传递给下一个中间件。
        不调用则短路处理链。
        Call next_fn() to pass control to the next middleware.
        Not calling it short-circuits the chain.
        """
        ...

    @property
    def name(self) -> str:
        """中间件名称 / Middleware name."""
        return self.__class__.__name__


class FunctionMiddleware(Middleware):
    """
    函数式中间件 - 用普通函数创建中间件
    Function middleware - create middleware from a plain function.
    """

    def __init__(
        self,
        handler: Callable[[ProcessingContext, NextFunction], Awaitable[None]],
        middleware_name: str = "FunctionMiddleware",
    ):
        self._handler = handler
        self._name = middleware_name

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        await self._handler(ctx, next_fn)

    @property
    def name(self) -> str:
        return self._name


class MiddlewareChain:
    """
    中间件链 - 管理和执行中间件序列
    Middleware chain - manages and executes a sequence of middlewares.

    支持：
    - 按优先级排序的中间件
    - 条件中间件（满足条件才执行）
    - 错误处理中间件
    - 计时和监控
    """

    def __init__(self) -> None:
        # (优先级, 中间件, 条件函数)
        self._middlewares: list[
            tuple[int, Middleware, Callable[[ProcessingContext], bool] | None]
        ] = []
        # 错误处理器
        self._error_handlers: list[
            Callable[[ProcessingContext, Exception], Awaitable[None]]
        ] = []
        # 是否已排序
        self._sorted = True

    def use(
        self,
        middleware: Middleware,
        priority: int = 50,
        condition: Callable[[ProcessingContext], bool] | None = None,
    ) -> MiddlewareChain:
        """
        添加中间件到链中
        Add a middleware to the chain.

        priority: 0 最先执行, 100 最后执行
        priority: 0 executes first, 100 executes last.
        """
        self._middlewares.append((priority, middleware, condition))
        self._sorted = False
        logger.debug("已添加中间件: %s (优先级=%d)", middleware.name, priority)
        return self

    def use_function(
        self,
        handler: Callable[[ProcessingContext, NextFunction], Awaitable[None]],
        name: str = "FunctionMiddleware",
        priority: int = 50,
        condition: Callable[[ProcessingContext], bool] | None = None,
    ) -> MiddlewareChain:
        """
        使用函数创建并添加中间件
        Create and add a middleware from a function.
        """
        mw = FunctionMiddleware(handler, name)
        return self.use(mw, priority, condition)

    def on_error(
        self,
        handler: Callable[[ProcessingContext, Exception], Awaitable[None]],
    ) -> MiddlewareChain:
        """
        注册错误处理器
        Register an error handler.
        """
        self._error_handlers.append(handler)
        return self

    def _ensure_sorted(self) -> None:
        """确保中间件按优先级排序 / Ensure middlewares are sorted by priority."""
        if not self._sorted:
            self._middlewares.sort(key=lambda item: item[0])
            self._sorted = True

    async def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """
        执行整个中间件链
        Execute the entire middleware chain.
        """
        self._ensure_sorted()

        # 收集本次执行需要运行的中间件
        active_middlewares: list[Middleware] = []
        for _priority, middleware, condition in self._middlewares:
            if condition is not None and not condition(ctx):
                continue
            active_middlewares.append(middleware)

        # 构建递归调用链
        index = 0

        async def next_fn() -> None:
            nonlocal index
            if ctx.terminated or index >= len(active_middlewares):
                return

            current = active_middlewares[index]
            index += 1

            try:
                await current.handle(ctx, next_fn)
            except Exception as exc:
                ctx.errors.append(exc)
                logger.exception("中间件 %s 抛出了错误", current.name)
                # 调用错误处理器
                for error_handler in self._error_handlers:
                    try:
                        await error_handler(ctx, exc)
                    except Exception:
                        logger.exception("错误处理器抛出了错误")

        await next_fn()
        return ctx

    def remove(self, middleware_name: str) -> bool:
        """
        按名称移除中间件
        Remove a middleware by name.
        """
        for i, (_, mw, _) in enumerate(self._middlewares):
            if mw.name == middleware_name:
                self._middlewares.pop(i)
                logger.debug("已移除中间件: %s", middleware_name)
                return True
        return False

    @property
    def count(self) -> int:
        """中间件数量 / Number of middlewares."""
        return len(self._middlewares)
