"""
Base Provider - Abstract base classes for providers.

Provides base implementations for LLM and other AI service providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from AetherPackBot.core.api.providers import (
    LLMProvider,
    ProviderConfig,
    LLMRequest,
    LLMResponse,
    StreamingChunk,
)
from AetherPackBot.core.kernel.logging import get_logger

logger = get_logger("providers")


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Provides common functionality for LLM service integration.
    """
    
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._model = config.model
        self._api_key = config.api_key
        self._api_base = config.api_base_url
    
    @property
    def provider_id(self) -> str:
        return self._config.provider_id
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def config(self) -> ProviderConfig:
        return self._config
    
    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request and get a response."""
        pass
    
    @abstractmethod
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request."""
        pass
    
    async def health_check(self) -> bool:
        """Check if the provider is healthy.
        
        Sends a minimal chat request. If the API responds without error,
        the provider is considered healthy – regardless of whether the
        response content is empty (some models/proxies return content=null
        with very small max_tokens).
        """
        try:
            from AetherPackBot.core.api.providers import LLMMessage
            
            request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hi")],
                max_tokens=10,
            )
            response = await self.chat(request)
            # API responded successfully → healthy
            # (don't check response.content; some models/proxies may return
            #  content=null with small max_tokens while still being functional)
            logger.debug(
                f"Health check OK for {self.provider_id}: "
                f"model={response.model}, content_len={len(response.content or '')}"
            )
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {self.provider_id}: {e}")
            return False


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider.
    
    Supports OpenAI's chat completions API and compatible endpoints.
    """
    
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import openai
        
        self._client = openai.AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._api_base,
        )
    
    @staticmethod
    def _build_openai_messages(llm_messages: list) -> list[dict[str, Any]]:
        """将 LLMMessage 列表转换为 OpenAI API 格式的消息列表。
        
        正确处理 tool_calls 和 tool_call_id 字段，
        保证 Agent 工具调用循环能正常工作。
        """
        messages = []
        for msg in llm_messages:
            m: dict[str, Any] = {"role": msg.role, "content": msg.content}
            # assistant 消息可能包含 tool_calls
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
                # OpenAI API: 当有 tool_calls 时 content 可以为 null
                if not msg.content:
                    m["content"] = None
            # tool 消息需要 tool_call_id
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            messages.append(m)
        return messages
    
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request to OpenAI."""
        messages = self._build_openai_messages(request.messages)
        
        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        
        response = await self._client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        tool_calls = None
        
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]
        
        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            raw_response=response,
        )
    
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request to OpenAI."""
        messages = self._build_openai_messages(request.messages)
        
        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        stream = await self._client.chat.completions.create(**kwargs)
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamingChunk(
                    content=chunk.choices[0].delta.content,
                    is_final=chunk.choices[0].finish_reason is not None,
                    finish_reason=chunk.choices[0].finish_reason,
                )


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude API provider.
    """
    
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import anthropic
        
        self._client = anthropic.AsyncAnthropic(
            api_key=self._api_key,
        )
    
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request to Anthropic."""
        # Extract system message
        system_message = ""
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        
        if system_message:
            kwargs["system"] = system_message
        
        if request.tools:
            # Convert OpenAI tool format to Anthropic format
            kwargs["tools"] = [
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"],
                }
                for tool in request.tools
            ]
        
        response = await self._client.messages.create(**kwargs)
        
        # Extract content
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": str(block.input),
                    },
                })
        
        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.stop_reason or "",
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            raw_response=response,
        )
    
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request to Anthropic."""
        system_message = ""
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        
        if system_message:
            kwargs["system"] = system_message
        
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield StreamingChunk(content=text)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API provider.
    """
    
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        from google import genai
        
        self._client = genai.Client(api_key=self._api_key)
    
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request to Gemini."""
        from google.genai import types
        
        # Build contents
        contents = []
        system_instruction = None
        
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.content)],
                ))
            elif msg.role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg.content)],
                ))
        
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_instruction,
        )
        
        response = await self._client.aio.models.generate_content(
            model=request.model or self._model,
            contents=contents,
            config=config,
        )
        
        content = response.text if response.text else ""
        
        return LLMResponse(
            content=content,
            model=request.model or self._model,
            finish_reason="stop",
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
            },
            raw_response=response,
        )
    
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request to Gemini."""
        from google.genai import types
        
        contents = []
        system_instruction = None
        
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg.content)],
                ))
            elif msg.role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg.content)],
                ))
        
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_instruction,
        )
        
        async for chunk in self._client.aio.models.generate_content_stream(
            model=request.model or self._model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield StreamingChunk(content=chunk.text)


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    OpenAI API compatible provider.

    Works with any service that exposes an OpenAI-compatible API such as
    DeepSeek, Moonshot/Kimi, SiliconFlow, Groq, Together AI, xAI (Grok),
    Zhipu (GLM), Mistral, etc.  Also used for local services like
    Ollama, LM Studio, vLLM, and LocalAI.
    """

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=self._api_key or "not-needed",
            base_url=self._api_base,
        )

    async def chat(self, request: LLMRequest) -> LLMResponse:
        messages = OpenAIProvider._build_openai_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice

        response = await self._client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""
        tool_calls = None

        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            raw_response=response,
        )

    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        messages = OpenAIProvider._build_openai_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamingChunk(
                    content=chunk.choices[0].delta.content,
                    is_final=chunk.choices[0].finish_reason is not None,
                    finish_reason=chunk.choices[0].finish_reason,
                )


# ── Pre-configured convenience aliases ──────────────────────────────


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.deepseek.com/v1",
                model=config.model or "deepseek-chat",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class MoonshotProvider(OpenAICompatibleProvider):
    """Moonshot / Kimi API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.moonshot.cn/v1",
                model=config.model or "moonshot-v1-8k",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class GroqProvider(OpenAICompatibleProvider):
    """Groq API (OpenAI-compatible, ultra-fast inference)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.groq.com/openai/v1",
                model=config.model or "llama-3.3-70b-versatile",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama local inference (OpenAI-compatible endpoint)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key or "ollama",
                api_base_url="http://localhost:11434/v1",
                model=config.model or "llama3.2",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class SiliconFlowProvider(OpenAICompatibleProvider):
    """SiliconFlow API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.siliconflow.cn/v1",
                model=config.model or "Qwen/Qwen2.5-72B-Instruct",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class ZhipuProvider(OpenAICompatibleProvider):
    """Zhipu AI / GLM API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://open.bigmodel.cn/api/paas/v4",
                model=config.model or "glm-4-flash",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class MistralProvider(OpenAICompatibleProvider):
    """Mistral AI API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.mistral.ai/v1",
                model=config.model or "mistral-large-latest",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class XAIProvider(OpenAICompatibleProvider):
    """xAI / Grok API (OpenAI-compatible)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key,
                api_base_url="https://api.x.ai/v1",
                model=config.model or "grok-3",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio local inference (OpenAI-compatible endpoint)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_base_url:
            config = ProviderConfig(
                provider_id=config.provider_id,
                provider_type=config.provider_type,
                provider_name=config.provider_name,
                api_key=config.api_key or "lm-studio",
                api_base_url="http://localhost:1234/v1",
                model=config.model or "local-model",
                enabled=config.enabled,
                extra=config.extra,
            )
        super().__init__(config)

