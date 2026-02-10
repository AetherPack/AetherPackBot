"""
Tool Loop Runner - Executes the tool-calling loop for agents.

Implements the iterative tool execution loop where the LLM can
call tools and receive results until producing a final response.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from AetherPackBot.core.api.agents import (
    Tool,
    ToolCall,
    ToolResult,
    ToolResultStatus,
    AgentConfig,
    AgentContext,
)
from AetherPackBot.core.api.providers import (
    LLMRequest,
    LLMResponse,
    LLMMessage,
    StreamingChunk,
)
from AetherPackBot.core.provider.base import BaseLLMProvider
from AetherPackBot.core.logging import get_logger

logger = get_logger("agents")


@dataclass
class RunnerState:
    """State of a tool loop execution."""
    
    step: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    final_response: str = ""
    is_complete: bool = False
    error: str | None = None


class ToolLoopRunner:
    """
    Executes the tool-calling loop for an agent.
    
    The runner manages the iterative process:
    1. Send messages to LLM
    2. Check if LLM requests tool calls
    3. Execute requested tools
    4. Add tool results to context
    5. Repeat until LLM produces final response or max steps reached
    """
    
    def __init__(
        self,
        provider: BaseLLMProvider,
        tools: list[Tool],
        config: AgentConfig,
    ) -> None:
        self._provider = provider
        self._tools: dict[str, Tool] = {t.name: t for t in tools}
        self._config = config
        self._state = RunnerState()
    
    def reset(self) -> None:
        """Reset the runner state."""
        self._state = RunnerState()
    
    @property
    def state(self) -> RunnerState:
        """Get the current runner state."""
        return self._state
    
    async def run(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str = "",
    ) -> str:
        """
        Run the complete tool loop until completion.
        
        Args:
            messages: Initial conversation messages
            system_prompt: Optional system prompt
        
        Returns:
            The final response text
        """
        self.reset()
        self._state.messages = messages.copy()
        
        # Add system prompt if provided
        if system_prompt:
            self._state.messages.insert(0, {
                "role": "system",
                "content": system_prompt,
            })
        
        while not self._state.is_complete:
            if self._state.step >= self._config.max_steps:
                logger.warning("Max steps reached, forcing completion")
                self._state.is_complete = True
                break
            
            try:
                await self._execute_step()
            except Exception as e:
                logger.exception(f"Error in tool loop step: {e}")
                self._state.error = str(e)
                self._state.is_complete = True
                break
        
        return self._state.final_response
    
    async def run_stream(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str = "",
    ) -> AsyncIterator[str]:
        """
        Run the tool loop with streaming output.
        
        Yields text chunks as they are generated.
        """
        self.reset()
        self._state.messages = messages.copy()
        
        if system_prompt:
            self._state.messages.insert(0, {
                "role": "system",
                "content": system_prompt,
            })
        
        while not self._state.is_complete:
            if self._state.step >= self._config.max_steps:
                self._state.is_complete = True
                break
            
            try:
                async for chunk in self._execute_step_stream():
                    yield chunk
            except Exception as e:
                logger.exception(f"Error in tool loop step: {e}")
                self._state.error = str(e)
                self._state.is_complete = True
                break
    
    async def _execute_step(self) -> None:
        """Execute a single step of the tool loop."""
        self._state.step += 1
        
        # Build request
        request = self._build_request()
        
        # Call LLM
        response = await self._provider.chat(request)
        self._state.total_tokens += response.total_tokens
        
        # Handle response
        if response.has_tool_calls:
            await self._handle_tool_calls(response)
        else:
            self._state.final_response = response.content
            self._state.is_complete = True
            
            # Add assistant message
            self._state.messages.append({
                "role": "assistant",
                "content": response.content,
            })
    
    async def _execute_step_stream(self) -> AsyncIterator[str]:
        """Execute a single step with streaming."""
        self._state.step += 1
        
        # Build request
        request = self._build_request()
        request.stream = True
        
        # Stream response
        content_buffer = ""
        tool_calls_buffer: list[dict[str, Any]] = []
        
        async for chunk in self._provider.chat_stream(request):
            if chunk.content:
                content_buffer += chunk.content
                yield chunk.content
            
            if chunk.tool_calls:
                tool_calls_buffer.extend(chunk.tool_calls)
        
        # If we got tool calls, execute them
        if tool_calls_buffer:
            response = LLMResponse(
                content=content_buffer,
                tool_calls=tool_calls_buffer,
            )
            await self._handle_tool_calls(response)
        else:
            self._state.final_response = content_buffer
            self._state.is_complete = True
            
            self._state.messages.append({
                "role": "assistant",
                "content": content_buffer,
            })
    
    def _build_request(self) -> LLMRequest:
        """Build an LLM request from current state."""
        messages = [
            LLMMessage(
                role=m["role"],
                content=m.get("content", ""),
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
            )
            for m in self._state.messages
        ]
        
        # Get tools in OpenAI format
        tools = [
            t.to_openai_function()
            for t in self._tools.values()
            if t.enabled
        ]
        
        return LLMRequest(
            messages=messages,
            model=self._config.model,
            temperature=self._config.temperature,
            tools=tools if tools else None,
        )
    
    async def _handle_tool_calls(self, response: LLMResponse) -> None:
        """Handle tool calls from LLM response."""
        if not response.tool_calls:
            return
        
        # Add assistant message with tool calls
        self._state.messages.append({
            "role": "assistant",
            "content": response.content,
            "tool_calls": response.tool_calls,
        })
        
        # Execute each tool call
        for tool_call_data in response.tool_calls:
            tool_call = ToolCall.from_openai_format(tool_call_data)
            result = await self._execute_tool(tool_call)
            
            # Add tool result message
            self._state.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.to_message_content(),
            })
    
    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = self._tools.get(tool_call.tool_name)
        
        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.ERROR,
                error=f"Unknown tool: {tool_call.tool_name}",
            )
        
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Executing tool: {tool_call.tool_name}")
            
            if tool.is_async:
                result = await asyncio.wait_for(
                    tool.handler(**tool_call.arguments),
                    timeout=tool.timeout,
                )
            else:
                result = tool.handler(**tool_call.arguments)
            
            execution_time = time.time() - start_time
            logger.info(f"Tool {tool_call.tool_name} completed in {execution_time:.2f}s")
            
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.SUCCESS,
                result=result,
                execution_time=execution_time,
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.TIMEOUT,
                error=f"Tool execution timed out after {tool.timeout}s",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.exception(f"Tool {tool_call.tool_name} failed: {e}")
            return ToolResult(
                tool_name=tool_call.tool_name,
                status=ToolResultStatus.ERROR,
                error=str(e),
                execution_time=time.time() - start_time,
            )
