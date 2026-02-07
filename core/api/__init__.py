"""
Protocols - Core abstract interfaces and type definitions.

This module defines Protocol classes that establish abstract contracts
for the major components of the system, enabling loose coupling and
clean dependency injection.
"""

from core.api.messages import (
    MessageComponent,
    MessageChain,
    MessageSession,
    PlatformMetadata,
)
from core.api.events import (
    Event,
    EventType,
    EventHandler,
    EventFilter,
)
from core.api.providers import (
    LLMProvider,
    TTSProvider,
    STTProvider,
    EmbeddingProvider,
    ProviderConfig,
)
from core.api.platforms import (
    PlatformAdapter,
    PlatformConfig,
    PlatformStatus,
)
from core.api.plugins import (
    Plugin,
    PluginMetadata,
    PluginHandler,
)
from core.api.agents import (
    Agent,
    Tool,
    ToolResult,
)

__all__ = [
    # Messages
    "MessageComponent",
    "MessageChain",
    "MessageSession",
    "PlatformMetadata",
    # Events
    "Event",
    "EventType",
    "EventHandler",
    "EventFilter",
    # Providers
    "LLMProvider",
    "TTSProvider",
    "STTProvider",
    "EmbeddingProvider",
    "ProviderConfig",
    # Platforms
    "PlatformAdapter",
    "PlatformConfig",
    "PlatformStatus",
    # Plugins
    "Plugin",
    "PluginMetadata",
    "PluginHandler",
    # Agents
    "Agent",
    "Tool",
    "ToolResult",
]
