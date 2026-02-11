"""
Anthropic Claude 对话提供者
Anthropic Claude chat provider.
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


class AnthropicChatProvider(ChatProvider):
    """Anthropic Claude 对话提供者 / Anthropic Claude chat provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._api_key = config.get("api_key", "")
        self._model = config.get("model", "claude-sonnet-4-20250514")
        self._base_url = config.get("base_url", "")
        self._client: Any = None
        self._info = ProviderInfo(
            capability=ProviderCapability.CHAT,
            display_name="Anthropic Claude",
            model_name=self._model,
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic

            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    async def chat(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        client = self._ensure_client()

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        response = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        )

        return response.content[0].text if response.content else ""

    async def chat_stream(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._ensure_client()

        messages = []
        if contexts:
            messages.extend(contexts)
        messages.append({"role": "user", "content": prompt})

        async with client.messages.stream(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
