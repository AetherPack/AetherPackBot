"""
Protocols - Core abstract interfaces and type definitions.

This module defines Protocol classes that establish abstract contracts
for the major components of the system, enabling loose coupling and
clean dependency injection.
"""

from aetherpackbot.protocols.messages import (
    MessageComponent,
    MessageChain,
    MessageSession,
    PlatformMetadata,
)
from aetherpackbot.protocols.events import (
    Event,
    EventType,
    EventHandler,
    EventFilter,
)
from aetherpackbot.protocols.providers import (
    LLMProvider,
    TTSProvider,
    STTProvider,
    EmbeddingProvider,
    ProviderConfig,
)
from aetherpackbot.protocols.platforms import (
    PlatformAdapter,
    PlatformConfig,
    PlatformStatus,
)
from aetherpackbot.protocols.plugins import (
    Plugin,
    PluginMetadata,
    PluginHandler,
)
from aetherpackbot.protocols.agents import (
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
