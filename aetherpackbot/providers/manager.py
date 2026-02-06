"""
Provider Manager - Manages LLM and service providers.

Handles provider registration, configuration, and lifecycle.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from aetherpackbot.protocols.providers import (
    LLMProvider,
    ProviderConfig,
    ProviderType,
)
from aetherpackbot.providers.base import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
)
from aetherpackbot.kernel.logging import get_logger

if TYPE_CHECKING:
    from aetherpackbot.kernel.container import ServiceContainer

logger = get_logger("providers")


# Provider type to implementation mapping
PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    # Add more providers here
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
        from aetherpackbot.storage.config import ConfigurationManager
        
        config_manager = await self._container.resolve(ConfigurationManager)
        providers_config = config_manager.get("providers", [])
        
        for provider_data in providers_config:
            if not provider_data.get("enabled", True):
                continue
            
            try:
                await self.register_from_config(provider_data)
            except Exception as e:
                logger.error(f"Failed to register provider: {e}")
        
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
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        config = ProviderConfig(
            provider_id=config_data.get("id", f"{provider_type}_{len(self._providers)}"),
            provider_type=ProviderType.LLM,
            provider_name=config_data.get("name", provider_type),
            api_key=config_data.get("api_key", ""),
            api_base_url=config_data.get("api_base_url"),
            model=config_data.get("model", ""),
            enabled=config_data.get("enabled", True),
            extra=config_data.get("extra", {}),
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
    
    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all providers."""
        results = {}
        for provider_id, provider in self._providers.items():
            results[provider_id] = await provider.health_check()
        return results
