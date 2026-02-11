"""
内置中间件 - 框架预置的消息处理中间件
Built-in middlewares - framework's preset message processing middlewares.

每个中间件对应消息处理流程中的一个环节。
Each middleware corresponds to a step in the message processing flow.
"""

from __future__ import annotations

import logging
import time

from AetherPackBot.kernel.middleware import (
    Middleware,
    NextFunction,
    ProcessingContext,
)

logger = logging.getLogger(__name__)


class WakeDetectionMiddleware(Middleware):
    """
    唤醒检测中间件 - 检查消息是否需要被处理
    Wake detection middleware - checks if a message needs processing.

    支持 @提及、唤醒词、私聊自动唤醒。
    Supports @mention, wake words, and auto-wake in private chat.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        event = ctx.event
        if event is None:
            return

        config = ctx.store.get("config", {})
        wake_prefixes: list[str] = config.get("wake_prefix", [])
        is_private = getattr(event, "is_private", False)
        is_mentioned = getattr(event, "is_mentioned", False)
        text = getattr(event, "plain_text", "")

        # 私聊或被 @ 直接唤醒
        if is_private or is_mentioned:
            ctx.store["is_awake"] = True
            await next_fn()
            return

        # 检查唤醒词前缀
        for prefix in wake_prefixes:
            if text.startswith(prefix):
                ctx.store["is_awake"] = True
                # 去掉唤醒词前缀
                ctx.store["stripped_text"] = text[len(prefix) :].strip()
                await next_fn()
                return

        # 未唤醒，不继续处理
        ctx.store["is_awake"] = False
        logger.debug("消息未被唤醒，跳过处理")

    @property
    def name(self) -> str:
        return "WakeDetection"


class AccessControlMiddleware(Middleware):
    """
    访问控制中间件 - 白名单/黑名单/权限检查
    Access control middleware - whitelist/blacklist/permission checks.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        event = ctx.event
        if event is None:
            return

        config = ctx.store.get("config", {})
        whitelist: list[str] = config.get("whitelist", [])
        blacklist: list[str] = config.get("blacklist", [])
        session_id = getattr(event, "session_id", "")

        # 黑名单优先
        if blacklist and session_id in blacklist:
            logger.debug("会话 %s 在黑名单中", session_id)
            ctx.terminate()
            return

        # 白名单为空表示不限制
        if whitelist and session_id not in whitelist:
            logger.debug("会话 %s 不在白名单中", session_id)
            ctx.terminate()
            return

        await next_fn()

    @property
    def name(self) -> str:
        return "AccessControl"


class RateLimiterMiddleware(Middleware):
    """
    频率限制中间件 - 防止消息处理过于频繁
    Rate limiter middleware - prevents processing messages too frequently.
    """

    def __init__(self) -> None:
        # session_id -> (最后请求时间, 请求计数)
        self._request_log: dict[str, tuple[float, int]] = {}

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        config = ctx.store.get("config", {})
        limit_per_min: int = config.get("rate_limit_per_minute", 30)

        if limit_per_min <= 0:
            await next_fn()
            return

        event = ctx.event
        session_id = getattr(event, "session_id", "unknown")
        now = time.time()

        last_time, count = self._request_log.get(session_id, (0.0, 0))

        # 重置计数（超过 60 秒）
        if now - last_time > 60:
            self._request_log[session_id] = (now, 1)
            await next_fn()
            return

        if count >= limit_per_min:
            logger.warning("会话 %s 超出频率限制", session_id)
            ctx.store["rate_limited"] = True
            ctx.terminate()
            return

        self._request_log[session_id] = (last_time, count + 1)
        await next_fn()

    @property
    def name(self) -> str:
        return "RateLimiter"


class ContentGuardMiddleware(Middleware):
    """
    内容安全中间件 - 检查消息内容是否合规
    Content guard middleware - checks if message content is compliant.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        config = ctx.store.get("config", {})
        enabled = config.get("content_safety_enabled", False)

        if not enabled:
            await next_fn()
            return

        event = ctx.event
        text = getattr(event, "plain_text", "")
        blocked_words: list[str] = config.get("blocked_words", [])

        for word in blocked_words:
            if word in text:
                logger.warning("检测到违禁词: %s", word)
                ctx.terminate()
                return

        await next_fn()

    @property
    def name(self) -> str:
        return "ContentGuard"


class SessionMiddleware(Middleware):
    """
    会话管理中间件 - 管理对话上下文和会话状态
    Session middleware - manages conversation context and session state.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        event = ctx.event
        if event is None:
            await next_fn()
            return

        # 将会话信息挂载到上下文
        session_id = getattr(event, "session_id", "")
        ctx.store["session_id"] = session_id
        ctx.store["conversation_id"] = getattr(event, "conversation_id", session_id)

        await next_fn()

    @property
    def name(self) -> str:
        return "Session"


class PackDispatchMiddleware(Middleware):
    """
    扩展包分发中间件 - 将消息分发给匹配的扩展包处理器
    Pack dispatch middleware - dispatches messages to matching pack handlers.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        from AetherPackBot.pack.loader import PackLoader

        container = ctx.store.get("container")
        if container is None:
            await next_fn()
            return

        try:
            pack_loader: PackLoader = await container.resolve(PackLoader)
        except KeyError:
            await next_fn()
            return

        # 让扩展包处理消息
        handled = await pack_loader.dispatch(ctx)

        if handled:
            # 如果扩展包处理了，检查是否需要继续走 LLM
            if not ctx.store.get("call_intellect", True):
                # 扩展包处理了且不需要 LLM
                await next_fn()
                return

        # 继续下一个中间件（可能是 LLM 处理）
        await next_fn()

    @property
    def name(self) -> str:
        return "PackDispatch"


class IntellectMiddleware(Middleware):
    """
    智能层中间件 - 调用 LLM 处理消息
    Intellect middleware - calls LLM to process messages.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        # 检查是否需要调用 LLM
        if not ctx.store.get("call_intellect", True):
            await next_fn()
            return

        if ctx.response is not None:
            # 已经有响应了，不需要 LLM
            await next_fn()
            return

        from AetherPackBot.intellect.registry import IntellectRegistry

        container = ctx.store.get("container")
        if container is None:
            await next_fn()
            return

        try:
            registry: IntellectRegistry = await container.resolve(IntellectRegistry)
        except KeyError:
            logger.warning("IntellectRegistry 不可用")
            await next_fn()
            return

        # 获取当前活跃的聊天提供者
        provider = await registry.get_active_chat_provider()
        if provider is None:
            await next_fn()
            return

        event = ctx.event
        text = ctx.store.get("stripped_text") or getattr(event, "plain_text", "")
        conversation_id = ctx.store.get("conversation_id", "")

        try:
            response = await provider.chat(text, conversation_id=conversation_id)
            ctx.response = response
        except Exception:
            logger.exception("智能层处理失败")

        await next_fn()

    @property
    def name(self) -> str:
        return "Intellect"


class ResponseDecoratorMiddleware(Middleware):
    """
    响应装饰中间件 - 对响应结果进行装饰（前缀、t2i等）
    Response decorator middleware - decorates response results (prefix, t2i, etc.).
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        # 先让后续中间件处理
        await next_fn()

        if ctx.response is None:
            return

        config = ctx.store.get("config", {})
        prefix = config.get("reply_prefix", "")

        # 添加回复前缀
        if prefix and isinstance(ctx.response, str):
            ctx.response = f"{prefix}{ctx.response}"

    @property
    def name(self) -> str:
        return "ResponseDecorator"


class DeliveryMiddleware(Middleware):
    """
    消息投递中间件 - 将处理结果发送回消息平台
    Delivery middleware - sends processing results back to the message platform.
    """

    async def handle(self, ctx: ProcessingContext, next_fn: NextFunction) -> None:
        # 确保前面的中间件都执行完
        await next_fn()

        if ctx.response is None or ctx.event is None:
            return

        # 通过事件的发送方法回复
        send_fn = getattr(ctx.event, "reply", None)
        if send_fn is not None and callable(send_fn):
            try:
                await send_fn(ctx.response)
                logger.debug("消息已投递，耗时 %.1fms", ctx.elapsed_ms)
            except Exception:
                logger.exception("消息投递失败")

    @property
    def name(self) -> str:
        return "Delivery"
