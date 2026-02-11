"""
智能层注册表 - 管理所有 AI 提供者的注册和选择
Intellect registry - manages registration and selection of all AI providers.
"""

from __future__ import annotations

import logging
from typing import Any

from AetherPackBot.intellect.base import (
    ChatProvider,
    EmbeddingProvider,
    ProviderCapability,
    RerankProvider,
    SpeechToTextProvider,
    TextToSpeechProvider,
)

logger = logging.getLogger(__name__)


class IntellectRegistry:
    """
    智能层注册表 - 集中管理所有 AI 提供者
    Intellect registry - centrally manages all AI providers.

    支持：
    - 注册和实例化各类提供者
    - 设置活跃（默认）提供者
    - 按能力类型查找提供者
    """

    def __init__(self) -> None:
        # 注册的提供者类型: (capability, type_name) -> class
        self._provider_types: dict[tuple[ProviderCapability, str], type] = {}
        # 活跃的提供者实例: provider_id -> instance
        self._instances: dict[str, Any] = {}
        # 活跃的各能力默认提供者 ID
        self._active: dict[ProviderCapability, str] = {}

    def register_type(
        self,
        capability: ProviderCapability,
        type_name: str,
        provider_cls: type,
    ) -> None:
        """
        注册一种提供者类型
        Register a provider type.
        """
        key = (capability, type_name)
        self._provider_types[key] = provider_cls
        logger.info("已注册智能层类型: %s/%s", capability.value, type_name)

    async def create_instance(
        self,
        capability: ProviderCapability,
        type_name: str,
        provider_id: str,
        config: dict[str, Any],
        set_as_active: bool = False,
    ) -> Any:
        """
        创建一个提供者实例
        Create a provider instance.
        """
        key = (capability, type_name)
        provider_cls = self._provider_types.get(key)
        if provider_cls is None:
            raise KeyError(f"Unknown provider type: {capability.value}/{type_name}")

        instance = provider_cls(config)
        instance._info.provider_id = provider_id
        self._instances[provider_id] = instance

        if set_as_active:
            self._active[capability] = provider_id

        logger.info(
            "已创建智能层实例: %s (%s/%s)",
            provider_id,
            capability.value,
            type_name,
        )
        return instance

    def set_active(self, capability: ProviderCapability, provider_id: str) -> None:
        """设置某能力的活跃提供者 / Set active provider for a capability."""
        if provider_id not in self._instances:
            raise KeyError(f"Provider instance not found: {provider_id}")
        self._active[capability] = provider_id

    async def get_active_chat_provider(self) -> ChatProvider | None:
        """获取活跃的对话提供者 / Get the active chat provider."""
        pid = self._active.get(ProviderCapability.CHAT)
        if pid is None:
            return None
        return self._instances.get(pid)

    async def get_active_stt_provider(self) -> SpeechToTextProvider | None:
        """获取活跃的 STT 提供者 / Get the active STT provider."""
        pid = self._active.get(ProviderCapability.SPEECH_TO_TEXT)
        if pid is None:
            return None
        return self._instances.get(pid)

    async def get_active_tts_provider(self) -> TextToSpeechProvider | None:
        """获取活跃的 TTS 提供者 / Get the active TTS provider."""
        pid = self._active.get(ProviderCapability.TEXT_TO_SPEECH)
        if pid is None:
            return None
        return self._instances.get(pid)

    async def get_active_embedding_provider(self) -> EmbeddingProvider | None:
        """获取活跃的向量化提供者 / Get the active embedding provider."""
        pid = self._active.get(ProviderCapability.EMBEDDING)
        if pid is None:
            return None
        return self._instances.get(pid)

    async def get_active_rerank_provider(self) -> RerankProvider | None:
        """获取活跃的重排序提供者 / Get the active rerank provider."""
        pid = self._active.get(ProviderCapability.RERANK)
        if pid is None:
            return None
        return self._instances.get(pid)

    def get_instance(self, provider_id: str) -> Any | None:
        """按 ID 获取提供者实例 / Get provider instance by ID."""
        return self._instances.get(provider_id)

    def all_instances(self) -> dict[str, Any]:
        """获取所有实例 / Get all instances."""
        return dict(self._instances)

    async def initialize_from_config(self, config_mgr: Any) -> None:
        """
        从配置加载并初始化所有提供者
        Load and initialize all providers from configuration.
        """
        # 注册内置提供者类型
        self._register_builtin_types()

        # 从配置创建实例
        providers_conf = config_mgr.get("providers", [])
        for pconf in providers_conf:
            cap_str = pconf.get("capability", "chat")
            type_name = pconf.get("type", "")
            pid = pconf.get("id", type_name)
            enabled = pconf.get("enabled", True)
            is_default = pconf.get("default", False)

            if not enabled or not type_name:
                continue

            capability = ProviderCapability(cap_str)

            try:
                await self.create_instance(
                    capability, type_name, pid, pconf, set_as_active=is_default
                )
            except Exception:
                logger.exception("创建提供者失败: %s", pid)

    def _register_builtin_types(self) -> None:
        """注册内置提供者类型 / Register built-in provider types."""
        try:
            from AetherPackBot.intellect.providers.openai_chat import (
                OpenAIChatProvider,
            )

            self.register_type(ProviderCapability.CHAT, "openai", OpenAIChatProvider)
        except ImportError:
            pass

        try:
            from AetherPackBot.intellect.providers.anthropic_chat import (
                AnthropicChatProvider,
            )

            self.register_type(
                ProviderCapability.CHAT, "anthropic", AnthropicChatProvider
            )
        except ImportError:
            pass

        try:
            from AetherPackBot.intellect.providers.gemini_chat import (
                GeminiChatProvider,
            )

            self.register_type(ProviderCapability.CHAT, "gemini", GeminiChatProvider)
        except ImportError:
            pass

        try:
            from AetherPackBot.intellect.providers.openai_embedding import (
                OpenAIEmbeddingProvider,
            )

            self.register_type(
                ProviderCapability.EMBEDDING, "openai", OpenAIEmbeddingProvider
            )
        except ImportError:
            pass

        try:
            from AetherPackBot.intellect.providers.edge_tts import EdgeTTSProvider

            self.register_type(
                ProviderCapability.TEXT_TO_SPEECH, "edge_tts", EdgeTTSProvider
            )
        except ImportError:
            pass
