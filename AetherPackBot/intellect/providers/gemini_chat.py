"""
Google Gemini 对话提供者
Google Gemini chat provider.
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


class GeminiChatProvider(ChatProvider):
    """Google Gemini 对话提供者 / Google Gemini chat provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._api_key = config.get("api_key", "")
        self._model = config.get("model", "gemini-2.0-flash")
        self._client: Any = None
        self._info = ProviderInfo(
            capability=ProviderCapability.CHAT,
            display_name="Google Gemini",
            model_name=self._model,
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
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

        contents = []
        if contexts:
            for ctx in contexts:
                contents.append(
                    {
                        "role": ctx.get("role", "user"),
                        "parts": [{"text": ctx.get("content", "")}],
                    }
                )
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        response = await client.aio.models.generate_content(
            model=self._model,
            contents=contents,
        )

        return response.text or ""

    async def chat_stream(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._ensure_client()

        contents = [{"role": "user", "parts": [{"text": prompt}]}]

        async for chunk in await client.aio.models.generate_content_stream(
            model=self._model,
            contents=contents,
        ):
            if chunk.text:
                yield chunk.text
