"""
Message Processor - Processing pipeline for incoming messages.

Implements a multi-stage pipeline (onion model) for processing messages:
1. Wake check
2. Permission check
3. Rate limiting
4. Content safety
5. Plugin handlers
6. Agent/LLM processing
7. Response decoration
8. Response delivery
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TYPE_CHECKING

from aetherpackbot.core.api.events import Event, EventType, MessageEvent
from aetherpackbot.core.api.messages import MessageChain
from aetherpackbot.core.kernel.logging import get_logger

if TYPE_CHECKING:
    from aetherpackbot.core.kernel.container import ServiceContainer

logger = get_logger("processor")


@dataclass
class PipelineContext:
    """Context passed through the processing pipeline."""
    
    event: MessageEvent
    is_wake: bool = False
    should_continue: bool = True
    matched_handlers: list[Any] = field(default_factory=list)
    response: MessageChain | None = None
    error: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the stage name."""
        pass
    
    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process the context and return the updated context."""
        pass


class WakeCheckStage(PipelineStage):
    """
    Stage 1: Check if the bot should wake up.
    
    Checks for:
    - Direct mentions (@bot)
    - Wake prefixes (/, !)
    - Wake words
    - Private messages
    """
    
    def __init__(
        self,
        wake_prefixes: list[str],
        wake_words: list[str],
    ) -> None:
        self._wake_prefixes = wake_prefixes
        self._wake_words = wake_words
    
    @property
    def name(self) -> str:
        return "wake_check"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        event = context.event
        message = event.message
        
        if not message:
            context.should_continue = False
            return context
        
        text = message.text.strip()
        
        # 参考 AstrBot WakingCheckStage: 按优先级检测唤醒条件
        
        # 1. 检查 @bot (参考 AstrBot: isinstance(message, At) and qq == self_id)
        if message.is_mentioned:
            context.is_wake = True
            # 标记为 at/wake 命令
            context.metadata["is_at_or_wake_command"] = True
            logger.debug(f"Wake check: Triggered by mention. User: {message.sender_id}")
        
        # 2. 检查唤醒前缀 (参考 AstrBot: 匹配后裁剪前缀)
        if not context.is_wake:
            for prefix in self._wake_prefixes:
                if text.startswith(prefix):
                    context.is_wake = True
                    # 参考 AstrBot: event.message_str = event.message_str[len(wake_prefix):]
                    text = text[len(prefix):].strip()
                    context.metadata["is_at_or_wake_command"] = True
                    context.metadata["stripped_prefix"] = prefix
                    logger.debug(f"Wake check: Triggered by prefix '{prefix}'. Clean text: {text}")
                    break
        
        # 3. 检查唤醒词/关键词 (参考 AstrBot: 关键词匹配)
        if not context.is_wake:
            for word in self._wake_words:
                if word and word.lower() in text.lower():
                    context.is_wake = True
                    context.metadata["matched_wake_word"] = word
                    logger.debug(f"Wake check: Triggered by wake word '{word}'.")
                    break
        
        # 4. 私聊消息始终唤醒 (参考 AstrBot: is_private_chat → is_wake=True)
        if not context.is_wake and not message.session.is_group:
            context.is_wake = True
            logger.debug("Wake check: Triggered by private message.")
        
        # 将裁剪后的文本存入 metadata，供后续 Agent 使用
        context.metadata["clean_text"] = text
        
        event.is_wake = context.is_wake
        
        if not context.is_wake:
             logger.debug(f"未唤醒: text={text!r}, is_group={message.session.is_group}, mentioned={message.is_mentioned}")
        
        return context


class PermissionCheckStage(PipelineStage):
    """
    Stage 2: Check user permissions and whitelist.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
    
    @property
    def name(self) -> str:
        return "permission_check"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        # TODO: Implement whitelist/blacklist checking
        # For now, allow all
        return context


class RateLimitStage(PipelineStage):
    """
    Stage 3: Rate limiting.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        rate_per_minute: int = 30,
    ) -> None:
        self._enabled = enabled
        self._rate_per_minute = rate_per_minute
        self._user_requests: dict[str, list[float]] = {}
    
    @property
    def name(self) -> str:
        return "rate_limit"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        if not self._enabled:
            return context
        
        import time
        
        event = context.event
        if not event.message:
            return context
        
        user_id = event.message.sender_id
        current_time = time.time()
        
        # Clean old entries
        if user_id in self._user_requests:
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id]
                if current_time - t < 60
            ]
        else:
            self._user_requests[user_id] = []
        
        # Check limit
        if len(self._user_requests[user_id]) >= self._rate_per_minute:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            context.should_continue = False
            return context
        
        self._user_requests[user_id].append(current_time)
        return context


class PluginHandlerStage(PipelineStage):
    """
    Stage 4: Execute matching plugin handlers.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
    
    @property
    def name(self) -> str:
        return "plugin_handler"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        from aetherpackbot.core.plugin.manager import PluginManager
        
        try:
            plugin_manager = await self._container.resolve(PluginManager)
        except Exception:
            return context
        
        # Get matching handlers
        handlers = await plugin_manager.get_matching_handlers(context.event)
        context.matched_handlers = handlers
        
        # Execute handlers in priority order
        for handler in handlers:
            if not context.should_continue:
                break
            
            try:
                await handler(context.event)
                
                # Check if event was handled
                if context.event.is_handled:
                    context.response = context.event.result
                    break
                    
            except Exception as e:
                logger.exception(f"Error in plugin handler: {e}")
        
        return context


class AgentProcessingStage(PipelineStage):
    """
    Stage 5: Process with LLM/Agent if needed.
    参考 AstrBot ProcessStage: 无插件命中 + 被唤醒 → 调 LLM
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
    
    @property
    def name(self) -> str:
        return "agent_processing"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        # Skip if already handled or not woken
        if context.event.is_handled or not context.is_wake:
            return context
        
        # Skip if no message
        if not context.event.message:
            return context
        
        # 使用裁剪前缀后的干净文本
        clean_text = context.metadata.get("clean_text", context.event.message.text).strip()
        if not clean_text:
            logger.debug("唤醒但消息文本为空，跳过 LLM 调用")
            return context
        
        from aetherpackbot.core.agent.orchestrator import AgentOrchestrator
        
        try:
            orchestrator = await self._container.resolve(AgentOrchestrator)
            response = await orchestrator.process_message(context.event, clean_text=clean_text)
            
            if response:
                context.response = response
                context.event.is_handled = True
                
        except Exception as e:
            logger.exception(f"Error in agent processing: {e}")
            context.error = e
        
        return context


class ResponseDecorationStage(PipelineStage):
    """
    Stage 6: Decorate the response before sending.
    """
    
    def __init__(
        self,
        add_prefix: bool = False,
        prefix_template: str = "",
        at_sender: bool = False,
    ) -> None:
        self._add_prefix = add_prefix
        self._prefix_template = prefix_template
        self._at_sender = at_sender
    
    @property
    def name(self) -> str:
        return "response_decoration"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        if not context.response:
            return context
        
        chain = context.response
        
        # Add @ mention if configured
        if self._at_sender and context.event.message:
            from aetherpackbot.core.api.messages import MentionComponent
            mention = MentionComponent(
                user_id=context.event.message.sender_id,
                user_name=context.event.message.sender_name,
            )
            chain._components.insert(0, mention)
        
        # Add prefix if configured
        if self._add_prefix and self._prefix_template:
            from aetherpackbot.core.api.messages import TextComponent
            prefix = TextComponent(self._prefix_template)
            chain._components.insert(0, prefix)
        
        return context


class ResponseDeliveryStage(PipelineStage):
    """
    Stage 7: Deliver the response to the platform.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
    
    @property
    def name(self) -> str:
        return "response_delivery"
    
    async def process(self, context: PipelineContext) -> PipelineContext:
        if not context.response or not context.event.message:
            return context
        
        from aetherpackbot.core.platform.manager import PlatformManager
        
        try:
            platform_manager = await self._container.resolve(PlatformManager)
            
            # Get the platform adapter
            platform_id = context.event.message.platform_meta.platform_id
            adapter = platform_manager.get_adapter(platform_id)
            
            if adapter:
                await adapter.send_message(
                    session=context.event.message.session,
                    chain=context.response,
                    reply_to=context.event.message.message_id,
                )
            else:
                logger.warning(f"No adapter found for platform {platform_id}")
                
        except Exception as e:
            logger.exception(f"Error delivering response: {e}")
            context.error = e
        
        return context


class MessageProcessor:
    """
    Main message processor that orchestrates the pipeline.
    
    Manages the processing of incoming messages through a series
    of stages, from wake detection to response delivery.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._stages: list[PipelineStage] = []
        self._running = False
    
    async def start(self) -> None:
        """Initialize and start the processor."""
        from aetherpackbot.core.storage.config import ConfigurationManager
        
        config_manager = await self._container.resolve(ConfigurationManager)
        
        # Build pipeline stages
        agent_config = config_manager.agent
        moderation_config = config_manager.get_section("moderation")
        reply_config = config_manager.get_section("reply")
        
        self._stages = [
            WakeCheckStage(
                wake_prefixes=agent_config.wake_prefixes,
                wake_words=agent_config.wake_words,
            ),
            PermissionCheckStage(self._container),
            RateLimitStage(
                enabled=moderation_config.get("rate_limit_enabled", True),
                rate_per_minute=moderation_config.get("rate_limit_per_minute", 30),
            ),
            PluginHandlerStage(self._container),
            AgentProcessingStage(self._container),
            ResponseDecorationStage(
                add_prefix=reply_config.get("add_prefix", False),
                prefix_template=reply_config.get("prefix_template", ""),
                at_sender=reply_config.get("at_sender", False),
            ),
            ResponseDeliveryStage(self._container),
        ]
        
        self._running = True
        logger.info("Message processor started with %d stages", len(self._stages))
    
    async def stop(self) -> None:
        """Stop the processor."""
        self._running = False
        logger.info("Message processor stopped")
    
    async def process(self, event: MessageEvent) -> PipelineContext:
        """
        Process a message event through the pipeline.
        
        Returns the final pipeline context.
        """
        context = PipelineContext(event=event)
        
        for stage in self._stages:
            if not context.should_continue:
                break
            
            try:
                context = await stage.process(context)
            except Exception as e:
                logger.exception(f"Error in stage {stage.name}: {e}")
                context.error = e
                context.should_continue = False
        
        return context
    
    def get_stages(self) -> list[PipelineStage]:
        """Get the list of pipeline stages."""
        return self._stages.copy()
