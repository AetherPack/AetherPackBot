"""
智能层基类 - 所有 LLM/AI 提供者的抽象基类
Intellect base - abstract base classes for all LLM/AI providers.

按能力分为五大类：对话、语音转文本、文本转语音、向量化、重排序。
Categorized by capability: chat, STT, TTS, embedding, rerank.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderCapability(str, Enum):
    """提供者能力枚举 / Provider capability enum."""

    CHAT = "chat"
    SPEECH_TO_TEXT = "stt"
    TEXT_TO_SPEECH = "tts"
    EMBEDDING = "embedding"
    RERANK = "rerank"


@dataclass
class ProviderInfo:
    """
    提供者信息描述
    Provider information descriptor.
    """

    # 提供者唯一标识
    provider_id: str = ""
    # 显示名称
    display_name: str = ""
    # 描述
    description: str = ""
    # 能力类型
    capability: ProviderCapability = ProviderCapability.CHAT
    # 当前使用的模型名
    model_name: str = ""
    # API 端点
    endpoint: str = ""
    # 附加元数据
    extra: dict[str, Any] = field(default_factory=dict)


class ChatProvider(ABC):
    """
    对话提供者基类 - 所有 LLM 聊天模型的抽象
    Chat provider base - abstraction for all LLM chat models.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._info = ProviderInfo(capability=ProviderCapability.CHAT)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @abstractmethod
    async def chat(
        self,
        prompt: str,
        conversation_id: str = "",
        contexts: list[dict[str, str]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        发送对话请求并获取响应
        Send a chat request and get a response.
        """
        ...

    @abstractmethod
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
        ...
        yield ""  # 保证这是一个 AsyncIterator

    async def close(self) -> None:
        """释放资源 / Release resources."""
        pass


class SpeechToTextProvider(ABC):
    """
    语音转文本提供者
    Speech-to-text provider.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._info = ProviderInfo(capability=ProviderCapability.SPEECH_TO_TEXT)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @abstractmethod
    async def transcribe(self, audio_url: str, **kwargs: Any) -> str:
        """
        将语音转为文本
        Convert speech to text.
        """
        ...


class TextToSpeechProvider(ABC):
    """
    文本转语音提供者
    Text-to-speech provider.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._info = ProviderInfo(capability=ProviderCapability.TEXT_TO_SPEECH)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @abstractmethod
    async def synthesize(self, text: str, **kwargs: Any) -> bytes:
        """
        将文本合成语音
        Synthesize text to speech.
        """
        ...

    async def synthesize_stream(self, text: str, **kwargs: Any) -> AsyncIterator[bytes]:
        """
        流式语音合成（可选）
        Streaming speech synthesis (optional).
        """
        data = await self.synthesize(text, **kwargs)
        yield data


class EmbeddingProvider(ABC):
    """
    向量化提供者
    Embedding provider.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._info = ProviderInfo(capability=ProviderCapability.EMBEDDING)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @abstractmethod
    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        """
        获取单条文本的向量
        Get embedding vector for a single text.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """
        批量获取向量
        Get embedding vectors for a batch of texts.
        """
        ...


class RerankProvider(ABC):
    """
    重排序提供者
    Rerank provider.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._info = ProviderInfo(capability=ProviderCapability.RERANK)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int = 5,
        **kwargs: Any,
    ) -> list[tuple[int, float]]:
        """
        对文档进行重排序
        Rerank documents.

        返回 (文档索引, 分数) 列表。
        Returns list of (document index, score).
        """
        ...
