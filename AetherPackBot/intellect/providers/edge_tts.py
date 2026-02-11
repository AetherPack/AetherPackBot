"""
Edge TTS 文本转语音提供者
Edge TTS text-to-speech provider.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from AetherPackBot.intellect.base import (
    ProviderCapability,
    ProviderInfo,
    TextToSpeechProvider,
)

logger = logging.getLogger(__name__)


class EdgeTTSProvider(TextToSpeechProvider):
    """Edge TTS 提供者 / Edge TTS provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self._info = ProviderInfo(
            capability=ProviderCapability.TEXT_TO_SPEECH,
            display_name="Microsoft Edge TTS",
        )

    async def synthesize(self, text: str, **kwargs: Any) -> bytes:
        """合成语音 / Synthesize speech."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self._voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    async def synthesize_stream(self, text: str, **kwargs: Any) -> AsyncIterator[bytes]:
        """流式合成 / Streaming synthesis."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self._voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
