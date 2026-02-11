"""
Agent 运行器 - 管理 function-call 循环和工具调度
Agent runner - manages function-call loops and tool dispatch.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# 工具函数类型别名
ToolCallback = Callable[..., Awaitable[Any]]


@dataclass
class ToolSpec:
    """
    工具规格描述
    Tool specification descriptor.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    callback: ToolCallback
    active: bool = True


@dataclass
class ToolResult:
    """
    工具调用结果
    Tool call result.
    """

    name: str
    call_id: str
    output: str
    success: bool = True


class ToolRegistry:
    """
    工具注册表 - 管理所有可用的函数工具
    Tool registry - manages all available function tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """注册工具 / Register a tool."""
        self._tools[spec.name] = spec
        logger.debug("已注册工具: %s", spec.name)

    def unregister(self, name: str) -> None:
        """注销工具 / Unregister a tool."""
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolSpec | None:
        """获取工具 / Get a tool."""
        return self._tools.get(name)

    def to_openai_schema(self) -> list[dict[str, Any]]:
        """
        导出为 OpenAI function calling 格式
        Export as OpenAI function calling schema.
        """
        schemas: list[dict[str, Any]] = []
        for spec in self._tools.values():
            if not spec.active:
                continue
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.parameters,
                    },
                }
            )
        return schemas

    @property
    def active_tools(self) -> list[ToolSpec]:
        """获取活跃工具列表 / Get active tools list."""
        return [t for t in self._tools.values() if t.active]


@dataclass
class AgentContext:
    """
    Agent 上下文 - 追踪一轮 Agent 循环的状态
    Agent context - tracks state during one agent loop.
    """

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    max_iterations: int = 15
    current_iteration: int = 0
    halted: bool = False


class AgentRunner:
    """
    Agent 运行器 - 执行工具调用循环

    与传统 ReAct 不同，采用「分阶段执行」策略：
    1. 将用户消息连同工具描述发送给 LLM
    2. 解析 LLM 返回的 tool_calls
    3. 并发执行多个工具调用
    4. 将结果注入上下文，再次调用 LLM
    5. 循环直到 LLM 不再请求工具调用

    Agent runner - executes tool-calling loops.
    Uses a "phased execution" strategy rather than traditional ReAct:
    1. Send user message + tool descriptions to LLM
    2. Parse tool_calls from LLM response
    3. Execute multiple tool calls concurrently
    4. Inject results back into context, call LLM again
    5. Loop until LLM stops requesting tool calls
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry

    async def execute_tool(self, name: str, call_id: str, arguments: str) -> ToolResult:
        """
        执行单个工具调用
        Execute a single tool call.
        """
        spec = self._registry.get(name)
        if spec is None:
            return ToolResult(
                name=name,
                call_id=call_id,
                output=f"Error: tool '{name}' not found",
                success=False,
            )

        try:
            args = json.loads(arguments) if arguments else {}
            result = await spec.callback(**args)
            return ToolResult(
                name=name,
                call_id=call_id,
                output=str(result),
                success=True,
            )
        except Exception as exc:
            logger.exception("工具 '%s' 执行失败", name)
            return ToolResult(
                name=name,
                call_id=call_id,
                output=f"Error: {exc}",
                success=False,
            )

    async def run_loop(
        self,
        ctx: AgentContext,
        chat_fn: Callable[
            [list[dict[str, Any]], list[dict[str, Any]]], Awaitable[dict[str, Any]]
        ],
    ) -> str:
        """
        运行 Agent 循环

        参数:
            ctx: Agent 上下文
            chat_fn: 异步函数，接收 (messages, tools) 返回 LLM 完整响应
        返回:
            最终的文本回复

        Run the agent loop.

        Args:
            ctx: Agent context
            chat_fn: Async function, takes (messages, tools) returns LLM response
        Returns:
            Final text reply
        """
        tools = self._registry.to_openai_schema()

        while ctx.current_iteration < ctx.max_iterations and not ctx.halted:
            ctx.current_iteration += 1
            logger.debug(
                "Agent 迭代 %d/%d (会话=%s)",
                ctx.current_iteration,
                ctx.max_iterations,
                ctx.session_id,
            )

            # 调用 LLM / Call LLM
            response = await chat_fn(ctx.messages, tools)

            # 获取 assistant 消息内容 / Get assistant message content
            choices = response.get("choices", [])
            if not choices:
                return "No response from model"

            message = choices[0].get("message", {})
            ctx.messages.append(message)

            # 检查是否有工具调用 / Check for tool calls
            tool_calls = message.get("tool_calls")
            if not tool_calls:
                # 无工具调用，直接返回文本 / No tool calls, return text directly
                return message.get("content", "")

            # 并行执行工具调用 / Execute tool calls in parallel
            import asyncio

            tasks = [
                self.execute_tool(
                    tc["function"]["name"],
                    tc["id"],
                    tc["function"].get("arguments", ""),
                )
                for tc in tool_calls
            ]
            results = await asyncio.gather(*tasks)

            # 注入工具结果 / Inject tool results
            for result in results:
                ctx.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.call_id,
                        "content": result.output,
                    }
                )

        return ctx.messages[-1].get("content", "") if ctx.messages else ""
