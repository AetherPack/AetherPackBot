"""
Provider Protocols - LLM and service provider interfaces.

Defines abstract interfaces for various AI service providers including
LLM, TTS, STT, and embedding providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, AsyncIterator, Protocol, runtime_checkable


class ProviderType(Enum):
    """Types of service providers."""
    
    LLM = "llm"          # Large Language Model
    TTS = "tts"          # Text-to-Speech
    STT = "stt"          # Speech-to-Text
    EMBEDDING = "embedding"  # Text Embedding
    RERANK = "rerank"    # Reranking


@dataclass
class ProviderConfig:
    """Configuration for a provider instance."""
    
    provider_id: str
    provider_type: ProviderType
    provider_name: str
    api_key: str = ""
    api_base_url: str | None = None
    model: str = ""
    enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)
    
    @property
    def display_name(self) -> str:
        """Get a display name for the provider."""
        return f"{self.provider_name} ({self.model})" if self.model else self.provider_name


@dataclass
class LLMMessage:
    """A message in an LLM conversation."""
    
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """Request to an LLM provider."""
    
    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict | None = None
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    
    content: str = ""
    model: str = ""
    finish_reason: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    raw_response: Any = None
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if the response contains tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        if self.usage:
            return self.usage.get("total_tokens", 0)
        return 0


@dataclass
class StreamingChunk:
    """A chunk from a streaming LLM response."""
    
    content: str = ""
    is_final: bool = False
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    @property
    def provider_id(self) -> str:
        """Get the unique provider ID."""
        ...
    
    @property
    def model(self) -> str:
        """Get the model name."""
        ...
    
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Send a chat request and get a response."""
        ...
    
    async def chat_stream(self, request: LLMRequest) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request."""
        ...


@dataclass
class TTSRequest:
    """Request to a TTS provider."""
    
    text: str
    voice: str | None = None
    speed: float = 1.0
    format: str = "mp3"


@dataclass
class TTSResponse:
    """Response from a TTS provider."""
    
    audio_data: bytes
    format: str = "mp3"
    duration: float | None = None


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for Text-to-Speech providers."""
    
    @property
    def provider_id(self) -> str:
        """Get the unique provider ID."""
        ...
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Convert text to speech."""
        ...
    
    def get_available_voices(self) -> list[str]:
        """Get list of available voices."""
        ...


@dataclass
class STTRequest:
    """Request to an STT provider."""
    
    audio_data: bytes
    format: str = "wav"
    language: str | None = None


@dataclass
class STTResponse:
    """Response from an STT provider."""
    
    text: str
    language: str | None = None
    confidence: float | None = None


@runtime_checkable
class STTProvider(Protocol):
    """Protocol for Speech-to-Text providers."""
    
    @property
    def provider_id(self) -> str:
        """Get the unique provider ID."""
        ...
    
    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Transcribe audio to text."""
        ...


@dataclass
class EmbeddingRequest:
    """Request for text embeddings."""
    
    texts: list[str]
    model: str | None = None


@dataclass
class EmbeddingResponse:
    """Response containing embeddings."""
    
    embeddings: list[list[float]]
    model: str = ""
    dimensions: int = 0
    usage: dict[str, int] | None = None


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""
    
    @property
    def provider_id(self) -> str:
        """Get the unique provider ID."""
        ...
    
    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions."""
        ...
    
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        ...
