"""
Provider Manager - Manages LLM and service providers.

Handles provider registration, configuration, and lifecycle.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from aetherpackbot.core.api.providers import (
    LLMProvider,
    ProviderConfig,
    ProviderType,
)
from aetherpackbot.core.provider.base import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
    DeepSeekProvider,
    MoonshotProvider,
    GroqProvider,
    OllamaProvider,
    SiliconFlowProvider,
    ZhipuProvider,
    MistralProvider,
    XAIProvider,
    LMStudioProvider,
)
from aetherpackbot.core.kernel.logging import get_logger

if TYPE_CHECKING:
    from aetherpackbot.core.kernel.container import ServiceContainer

logger = get_logger("providers")


# ── Provider type registry with display info ────────────────────────

_ProviderInfo = dict[str, Any]  # type alias

PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "moonshot": MoonshotProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
    "siliconflow": SiliconFlowProvider,
    "zhipu": ZhipuProvider,
    "mistral": MistralProvider,
    "xai": XAIProvider,
    "lm_studio": LMStudioProvider,
    "openai_compatible": OpenAICompatibleProvider,
}

# Display metadata for each provider type
PROVIDER_TYPE_INFO: dict[str, _ProviderInfo] = {
    "openai": {
        "name": "OpenAI",
        "description": "OpenAI GPT 系列模型",
        "requires_api_key": True,
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"],
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Anthropic Claude 系列模型",
        "requires_api_key": True,
        "default_model": "claude-sonnet-4-20250514",
        "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
    },
    "gemini": {
        "name": "Google Gemini",
        "description": "Google Gemini 系列模型",
        "requires_api_key": True,
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "description": "DeepSeek 深度求索",
        "requires_api_key": True,
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "moonshot": {
        "name": "Moonshot (Kimi)",
        "description": "月之暗面 Kimi",
        "requires_api_key": True,
        "default_model": "moonshot-v1-8k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
    "groq": {
        "name": "Groq",
        "description": "Groq 超快推理",
        "requires_api_key": True,
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    },
    "ollama": {
        "name": "Ollama",
        "description": "Ollama 本地推理",
        "requires_api_key": False,
        "default_model": "llama3.2",
        "models": ["llama3.2", "llama3.1", "qwen2.5", "deepseek-r1", "mistral", "gemma2", "phi3"],
        "default_api_base": "http://localhost:11434/v1",
    },
    "siliconflow": {
        "name": "SiliconFlow (硅基流动)",
        "description": "硅基流动 API 平台",
        "requires_api_key": True,
        "default_model": "Qwen/Qwen2.5-72B-Instruct",
        "models": ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-V3", "THUDM/glm-4-9b-chat"],
    },
    "zhipu": {
        "name": "智谱 AI (GLM)",
        "description": "智谱 AI GLM 系列模型",
        "requires_api_key": True,
        "default_model": "glm-4-flash",
        "models": ["glm-4-flash", "glm-4-plus", "glm-4-air", "glm-4-long", "glm-4"],
    },
    "mistral": {
        "name": "Mistral AI",
        "description": "Mistral AI 模型",
        "requires_api_key": True,
        "default_model": "mistral-large-latest",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mixtral-8x22b"],
    },
    "xai": {
        "name": "xAI (Grok)",
        "description": "xAI Grok 系列模型",
        "requires_api_key": True,
        "default_model": "grok-3",
        "models": ["grok-3", "grok-3-mini", "grok-2"],
    },
    "lm_studio": {
        "name": "LM Studio",
        "description": "LM Studio 本地推理",
        "requires_api_key": False,
        "default_model": "local-model",
        "models": [],
        "default_api_base": "http://localhost:1234/v1",
    },
    "openai_compatible": {
        "name": "OpenAI 兼容接口",
        "description": "任何兼容 OpenAI API 格式的服务",
        "requires_api_key": False,
        "default_model": "",
        "models": [],
    },
}


class ProviderManager:
    """
    Manages LLM and service providers.
    
    Handles provider lifecycle, registration, and access.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._providers: dict[str, BaseLLMProvider] = {}
        self._default_provider_id: str | None = None
    
    async def initialize(self) -> None:
        """Initialize providers from configuration."""
        from aetherpackbot.core.storage.config import ConfigurationManager
        
        config_manager = await self._container.resolve(ConfigurationManager)
        providers_config = config_manager.get("providers", [])
        
        config_changed = False
        for provider_data in providers_config:
            if not provider_data.get("enabled", True):
                continue
            
            try:
                # Auto-heal: Ensure ID exists in config
                if not provider_data.get("id"):
                    ptype = provider_data.get("type", "openai")
                    # Generate a simple ID
                    provider_data["id"] = f"{ptype}_{len(self._providers)}"
                    config_changed = True

                await self.register_from_config(provider_data)
            except Exception as e:
                logger.error(f"Failed to register provider: {e}")
        
        if config_changed:
            config_manager.set("providers", providers_config)
            await config_manager.save()
            logger.info("Auto-healed provider configuration (added missing IDs)")
        
        # Set default provider
        default_id = config_manager.get("agent.default_provider", "")
        if default_id and default_id in self._providers:
            self._default_provider_id = default_id
        elif self._providers:
            self._default_provider_id = next(iter(self._providers))
        
        logger.info(f"Initialized {len(self._providers)} providers")
    
    async def start(self) -> None:
        """Start the provider manager (lifecycle hook)."""
        pass
    
    async def stop(self) -> None:
        """Stop the provider manager (lifecycle hook)."""
        self._providers.clear()
    
    async def register_from_config(self, config_data: dict[str, Any]) -> BaseLLMProvider:
        """
        Register a provider from configuration data.
        
        Args:
            config_data: Provider configuration dictionary
        
        Returns:
            The registered provider instance
        """
        provider_type = config_data.get("type", "openai")
        
        if provider_type not in PROVIDER_REGISTRY:
            # Fallback for old configs or unknown types? Default to openai
            if "openai" in PROVIDER_REGISTRY:
                provider_type = "openai"
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")
        
        # Store the actual registry type in extra for accurate type lookup logic
        extra = config_data.get("extra", {}).copy()
        extra["registry_type"] = provider_type
        
        config = ProviderConfig(
            provider_id=config_data.get("id", f"{provider_type}_{len(self._providers)}"),
            provider_type=ProviderType.LLM,
            provider_name=config_data.get("name", provider_type),
            api_key=config_data.get("api_key", ""),
            api_base_url=config_data.get("api_base_url"),
            model=config_data.get("model", ""),
            enabled=config_data.get("enabled", True),
            extra=extra,
        )
        
        provider_class = PROVIDER_REGISTRY[provider_type]
        provider = provider_class(config)
        
        self._providers[config.provider_id] = provider
        logger.info(f"Registered provider: {config.provider_id} ({provider_type})")
        
        return provider
    
    def register(
        self,
        provider_id: str,
        provider: BaseLLMProvider,
    ) -> None:
        """Register a provider instance."""
        self._providers[provider_id] = provider
    
    def unregister(self, provider_id: str) -> None:
        """Unregister a provider."""
        if provider_id in self._providers:
            del self._providers[provider_id]
    
    def get(self, provider_id: str) -> BaseLLMProvider | None:
        """Get a provider by ID."""
        return self._providers.get(provider_id)
    
    def get_default(self) -> BaseLLMProvider | None:
        """Get the default provider."""
        if self._default_provider_id:
            return self._providers.get(self._default_provider_id)
        return None
    
    def set_default(self, provider_id: str) -> None:
        """Set the default provider."""
        if provider_id not in self._providers:
            raise ValueError(f"Provider not found: {provider_id}")
        self._default_provider_id = provider_id
    
    def get_all(self) -> dict[str, BaseLLMProvider]:
        """Get all registered providers."""
        return self._providers.copy()
    
    def list_provider_ids(self) -> list[str]:
        """Get a list of all provider IDs."""
        return list(self._providers.keys())

    def get_status_list(self) -> list[dict[str, Any]]:
        """Get a list of all providers with status info for the dashboard."""
        result = []
        for pid, provider in self._providers.items():
            # Use registry_type if available, otherwise fallback to provider_name
            ptype = provider.config.extra.get("registry_type", provider.config.provider_name)
            
            # If ptype is a user-custom name (old config), try to infer or default
            if ptype not in PROVIDER_TYPE_INFO and provider.config.provider_name in PROVIDER_TYPE_INFO:
                ptype = provider.config.provider_name
                
            type_info = PROVIDER_TYPE_INFO.get(ptype, {})
            result.append({
                "id": pid,
                "type": ptype,
                "model": provider.model,
                "display_name": provider.config.display_name,
                "is_default": pid == self._default_provider_id,
                "enabled": provider.config.enabled,
                "status": "running",
                "type_display": type_info.get("name", ptype),
                "api_base_url": provider.config.api_base_url or "",
            })
        return result

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all providers."""
        results = {}
        for provider_id, provider in self._providers.items():
            results[provider_id] = await provider.health_check()
        return results

    def get_provider_config(self, provider_id: str) -> dict[str, Any] | None:
        """Get the raw config data for a provider (for update merging)."""
        provider = self._providers.get(provider_id)
        if not provider:
            return None
        return {
            "id": provider.config.provider_id,
            "type": provider.config.extra.get("registry_type", provider.config.provider_name),
            "api_key": provider.config.api_key,
            "api_base_url": provider.config.api_base_url,
            "model": provider.config.model,
            "enabled": provider.config.enabled,
            "extra": provider.config.extra,
        }
