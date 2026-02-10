"""
Agent Protocols - AI Agent and tool interfaces.

Defines the core abstractions for the agent system, including
agents, tools, and orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Protocol, runtime_checkable, AsyncIterator


class ToolResultStatus(Enum):
    """Status of a tool execution result."""
    
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    
    name: str
    type: str  # JSON Schema type
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None


@dataclass
class Tool:
    """
    Definition of a callable tool for agents.
    
    Tools are functions that agents can invoke to perform actions
    or retrieve information.
    """
    
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "string"
    returns_description: str = ""
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    is_async: bool = True
    timeout: float = 60.0
    
    def to_openai_function(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""
    
    tool_name: str
    status: ToolResultStatus = ToolResultStatus.SUCCESS
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if the tool executed successfully."""
        return self.status == ToolResultStatus.SUCCESS
    
    def to_message_content(self) -> str:
        """Convert result to a string for use in messages."""
        if self.is_success:
            if isinstance(self.result, str):
                return self.result
            return str(self.result)
        return f"Error: {self.error}"


@dataclass
class ToolCall:
    """A tool call requested by an agent."""
    
    id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_openai_format(cls, tool_call: dict[str, Any]) -> ToolCall:
        """Create from OpenAI tool call format."""
        import json
        return cls(
            id=tool_call.get("id", ""),
            tool_name=tool_call["function"]["name"],
            arguments=json.loads(tool_call["function"].get("arguments", "{}")),
        )


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    
    name: str
    instructions: str = ""
    model: str | None = None
    provider_id: str | None = None
    tools: list[Tool] = field(default_factory=list)
    max_steps: int = 30
    timeout: float = 300.0
    temperature: float = 0.7
    
    # Context management
    context_window_tokens: int = 128000
    truncation_strategy: str = "oldest_first"  # "oldest_first", "summary", "none"


@dataclass
class AgentContext:
    """Runtime context for an agent execution."""
    
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    step_count: int = 0
    total_tokens: int = 0
    
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the context."""
        message = {"role": role, "content": content, **kwargs}
        self.messages.append(message)


@runtime_checkable
class Agent(Protocol):
    """Protocol for agents."""
    
    @property
    def name(self) -> str:
        """Get the agent name."""
        ...
    
    @property
    def config(self) -> AgentConfig:
        """Get the agent configuration."""
        ...
    
    async def run(
        self,
        prompt: str,
        context: AgentContext | None = None,
    ) -> str:
        """
        Run the agent with a prompt.
        
        Returns the agent's response.
        """
        ...
    
    async def run_stream(
        self,
        prompt: str,
        context: AgentContext | None = None,
    ) -> AsyncIterator[str]:
        """Run the agent with streaming output."""
        ...


class BaseAgent(ABC):
    """
    Abstract base class for agents.
    
    Provides core agent functionality including tool execution loop.
    """
    
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._tools: dict[str, Tool] = {}
        
        # Register tools from config
        for tool in config.tools:
            self._tools[tool.name] = tool
    
    @property
    def name(self) -> str:
        return self._config.name
    
    @property
    def config(self) -> AgentConfig:
        return self._config
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the agent."""
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
    
    def get_tools_as_openai_functions(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        return [
            tool.to_openai_function()
            for tool in self._tools.values()
            if tool.enabled
        ]
    
    async def execute_tool(
        self,
        tool_call: ToolCall,
    ) -> ToolResult:
        """Execute a tool call."""
        import asyncio
        import time
        
        tool = self.get_tool(tool_call.tool_name)
        if tool is None:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.ERROR,
                error=f"Tool '{tool_call.tool_name}' not found",
            )
        
        start_time = time.time()
        
        try:
            if tool.is_async:
                result = await asyncio.wait_for(
                    tool.handler(**tool_call.arguments),
                    timeout=tool.timeout,
                )
            else:
                result = tool.handler(**tool_call.arguments)
            
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.SUCCESS,
                result=result,
                execution_time=time.time() - start_time,
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.TIMEOUT,
                error=f"Tool execution timed out after {tool.timeout}s",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.ERROR,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    @abstractmethod
    async def run(
        self,
        prompt: str,
        context: AgentContext | None = None,
    ) -> str:
        """Run the agent."""
        pass
    
    @abstractmethod
    async def run_stream(
        self,
        prompt: str,
        context: AgentContext | None = None,
    ) -> AsyncIterator[str]:
        """Run the agent with streaming."""
        pass


@dataclass
class HandoffTool(Tool):
    """
    Special tool for handing off to another agent.
    
    When invoked, this tool transfers control to the target agent.
    """
    
    target_agent: Agent | str = ""
    target_provider_id: str | None = None
    
    def __init__(
        self,
        name: str,
        description: str,
        target_agent: Agent | str,
        target_provider_id: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            handler=self._handoff_handler,
            parameters=[
                ToolParameter(
                    name="task",
                    type="string",
                    description="The task to hand off to the target agent",
                    required=True,
                )
            ],
        )
        self.target_agent = target_agent
        self.target_provider_id = target_provider_id
    
    async def _handoff_handler(self, task: str) -> str:
        """Handle the handoff. Actual implementation provided by orchestrator."""
        # This is a placeholder; actual handoff is handled by AgentOrchestrator
        return f"Handing off to {self.target_agent}: {task}"
