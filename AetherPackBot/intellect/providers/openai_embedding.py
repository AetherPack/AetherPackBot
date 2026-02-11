"""
OpenAI 向量化提供者
OpenAI embedding provider.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.intellect.base import (
    EmbeddingProvider,
    ProviderCapability,
    ProviderInfo,
)

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI 向量化提供者 / OpenAI embedding provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._api_key = config.get("api_key", "")
        self._base_url = config.get("base_url", "https://api.openai.com/v1")
        self._model = config.get("model", "text-embedding-3-small")
        self._client: Any = None
        self._info = ProviderInfo(
            capability=ProviderCapability.EMBEDDING,
            display_name="OpenAI Embedding",
            model_name=self._model,
        )

    def _ensure_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        client = self._ensure_client()
        response = await client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        client = self._ensure_client()
        response = await client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
