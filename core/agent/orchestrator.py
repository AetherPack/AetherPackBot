"""
Agent Orchestrator - Coordinates agent execution and tool management.

The orchestrator is responsible for:
- Managing the main agent and sub-agents
- Collecting tools from plugins
- Processing messages through the agent system
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from core.api.agents import (
    Tool,
    ToolParameter,
    AgentConfig,
    AgentContext,
)
from core.api.events import MessageEvent
from core.api.messages import MessageChain, TextComponent
from core.agent.runner import ToolLoopRunner
from core.kernel.logging import get_logger

if TYPE_CHECKING:
    from core.kernel.container import ServiceContainer

logger = get_logger("agents")


class AgentOrchestrator:
    """
    Coordinates agent execution for message processing.
    
    Manages:
    - Main agent configuration
    - Tool collection from plugins
    - Conversation context
    - Agent execution
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._tools: dict[str, Tool] = {}
        self._main_config: AgentConfig | None = None
        self._system_prompt: str = ""
    
    async def start(self) -> None:
        """Initialize the orchestrator."""
        from core.storage.config import ConfigurationManager
        
        config_manager = await self._container.resolve(ConfigurationManager)
        
        # Build main agent config
        agent_settings = config_manager.agent
        
        self._main_config = AgentConfig(
            name="main",
            instructions="You are a helpful AI assistant.",
            max_steps=agent_settings.max_tool_steps,
            timeout=agent_settings.tool_timeout,
        )
        
        # Load persona if configured
        personas = config_manager.get("personas", [])
        default_persona = config_manager.get("default_persona", "")
        
        for persona in personas:
            if persona.get("name") == default_persona:
                self._system_prompt = persona.get("prompt", "")
                break
        
        # Collect tools from plugins
        await self._collect_tools()
        
        logger.info(f"Agent orchestrator initialized with {len(self._tools)} tools")
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._tools.clear()
    
    async def _collect_tools(self) -> None:
        """Collect tools from all sources."""
        from core.plugin.manager import PluginManager
        
        self._tools.clear()
        
        # Get tools from plugins
        try:
            plugin_manager = await self._container.resolve(PluginManager)
            llm_tools = plugin_manager.get_llm_tools()
            
            for tool_def in llm_tools:
                tool = self._convert_tool_def(tool_def)
                if tool:
                    self._tools[tool.name] = tool
        except Exception as e:
            logger.warning(f"Failed to collect plugin tools: {e}")
        
        # Add built-in tools
        self._register_builtin_tools()
    
    def _convert_tool_def(self, tool_def: dict[str, Any]) -> Tool | None:
        """Convert a plugin tool definition to a Tool object."""
        try:
            parameters = []
            param_schema = tool_def.get("parameters", {})
            
            if "properties" in param_schema:
                required = param_schema.get("required", [])
                for name, prop in param_schema["properties"].items():
                    parameters.append(ToolParameter(
                        name=name,
                        type=prop.get("type", "string"),
                        description=prop.get("description", ""),
                        required=name in required,
                    ))
            
            return Tool(
                name=tool_def["name"],
                description=tool_def.get("description", ""),
                handler=tool_def["handler"],
                parameters=parameters,
            )
        except Exception as e:
            logger.warning(f"Failed to convert tool definition: {e}")
            return None
    
    def _register_builtin_tools(self) -> None:
        """Register built-in system tools."""
        # Example: Clear conversation tool
        self._tools["clear_conversation"] = Tool(
            name="clear_conversation",
            description="Clear the current conversation context and start fresh",
            handler=self._handle_clear_conversation,
            parameters=[],
        )
    
    async def _handle_clear_conversation(self) -> str:
        """Handle clear conversation tool."""
        return "Conversation cleared. Starting fresh."
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]
    
    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    async def process_message(
        self,
        event: MessageEvent,
        clean_text: str | None = None,
    ) -> MessageChain | None:
        """
        Process a message through the agent system.
        
        Args:
            event: The message event to process
            clean_text: Optional pre-processed text (with wake prefix stripped)
        
        Returns:
            Response message chain, or None if no response
        """
        if not event.message:
            return None
        
        from core.provider.manager import ProviderManager
        from core.storage.database import DatabaseManager
        
        try:
            provider_manager = await self._container.resolve(ProviderManager)
            db_manager = await self._container.resolve(DatabaseManager)
        except Exception as e:
            logger.error(f"Failed to resolve dependencies: {e}")
            return MessageChain().text(f"内部错误: 无法获取必要服务 ({e})")
        
        # Get provider
        provider = provider_manager.get_default()
        if not provider:
            logger.error("Agent Orchestrator: No default LLM provider configured/found.")
            return MessageChain().text("未配置 LLM 提供商，请在管理面板中添加并设置默认提供商。")
        
        logger.info(f"Agent executing. LLM: {provider.provider_id} (model={provider.model})")
        
        # 使用裁剪后的文本，否则用原始文本
        user_text = clean_text or event.message.text
        
        # Get or create conversation
        message = event.message
        session = message.session
        
        conversation = await db_manager.get_conversation(
            session_id=session.session_id,
            user_id=message.sender_id,
        )
        
        if not conversation:
            conversation = await db_manager.create_conversation(
                session_id=session.session_id,
                user_id=message.sender_id,
                platform_id=message.platform_meta.platform_id,
            )
        
        # Build messages for context
        messages: list[dict[str, Any]] = []
        
        # Load existing context
        if conversation.context:
            try:
                messages = json.loads(conversation.context)
            except json.JSONDecodeError:
                messages = []
        
        # Add user message (使用裁剪后的干净文本)
        messages.append({
            "role": "user",
            "content": user_text,
        })
        
        # Create runner
        if not self._main_config:
            self._main_config = AgentConfig(name="main")
        
        runner = ToolLoopRunner(
            provider=provider,
            tools=list(self._tools.values()),
            config=self._main_config,
        )
        
        # Run agent
        try:
            response = await runner.run(
                messages=messages,
                system_prompt=self._system_prompt,
            )
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return MessageChain().text(f"An error occurred: {str(e)}")
        
        # Update conversation context
        context_messages = runner.state.messages.copy()
        if len(context_messages) > 0 and context_messages[0].get("role") == "system":
            context_messages = context_messages[1:]  # Remove system prompt
        
        await db_manager.update_conversation(
            conversation_id=conversation.id,
            context=json.dumps(context_messages),
            token_count=conversation.token_count + runner.state.total_tokens,
        )
        
        # Build response chain
        return MessageChain().text(response)
    
    async def process_with_stream(
        self,
        event: MessageEvent,
    ):
        """
        Process a message with streaming response.
        
        Yields text chunks as they are generated.
        """
        if not event.message:
            return
        
        from core.provider.manager import ProviderManager
        
        try:
            provider_manager = await self._container.resolve(ProviderManager)
        except Exception:
            yield "Failed to get provider"
            return
        
        provider = provider_manager.get_default()
        if not provider:
            yield "No provider configured"
            return
        
        messages = [{"role": "user", "content": event.message.text}]
        
        if not self._main_config:
            self._main_config = AgentConfig(name="main")
        
        runner = ToolLoopRunner(
            provider=provider,
            tools=list(self._tools.values()),
            config=self._main_config,
        )
        
        async for chunk in runner.run_stream(
            messages=messages,
            system_prompt=self._system_prompt,
        ):
            yield chunk
