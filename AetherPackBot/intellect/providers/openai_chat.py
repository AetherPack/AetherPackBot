"""
OpenAI 对话提供者 - 对接 OpenAI 及兼容 API
OpenAI chat provider - interfaces with OpenAI and compatible APIs.

支持所有 OpenAI 兼容端点（Ollama、vLLM、DeepSeek 等）。
Supports all OpenAI-compatible endpoints (Ollama, vLLM, DeepSeek, etc.).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from AetherPackBot.intellect.base import (
    ChatProvider,
    ProviderCapability,
    ProviderInfo,
)

logger = logging.getLogger(__name__)


class OpenAIChatProvider(ChatProvider):
    """
    OpenAI 对话提供者
    OpenAI chat provider.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._api_key = config.get("api_key", "")
        self._base_url = config.get("base_url", "https://api.openai.com/v1")
        self._model = config.get("model", "gpt-4o")
        self._client: Any = None
        self._info = ProviderInfo(
            capability=ProviderCapability.CHAT,
            display_name="OpenAI",
            model_name=self._model,
            endpoint=self._base_url,
        )

    def _ensure_client(self) -> Any:
        """确保客户端已初始化 / Ensure client is initialized."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def chat(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        发送对话请求
        Send a chat request.
        """
        client = self._ensure_client()

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }

        if tools:
            request_kwargs["tools"] = tools

        response = await client.chat.completions.create(**request_kwargs)
        choice = response.choices[0]

        return choice.message.content or ""

    async def chat_stream(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        流式对话
        Streaming chat.
        """
        client = self._ensure_client()

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
