"""
智能层模块 - LLM 提供者管理
Intellect module - LLM provider management.

取代传统的 Provider 模式，采用注册表 + 能力描述的方式管理。
Replaces traditional Provider pattern with registry + capability descriptor approach.
"""

from AetherPackBot.intellect.base import (
    ChatProvider,
    EmbeddingProvider,
    ProviderCapability,
    RerankProvider,
    SpeechToTextProvider,
    TextToSpeechProvider,
)
from AetherPackBot.intellect.registry import IntellectRegistry

__all__ = [
    "ChatProvider",
    "SpeechToTextProvider",
    "TextToSpeechProvider",
    "EmbeddingProvider",
    "RerankProvider",
    "ProviderCapability",
    "IntellectRegistry",
]
