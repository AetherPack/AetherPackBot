"""
Plugin Protocols - Plugin system interfaces.

Defines abstract interfaces for the plugin (extension) system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from aetherpackbot.protocols.events import Event, EventFilter, EventType


class PluginStatus(Enum):
    """Status of a plugin."""
    
    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ENABLED = auto()
    DISABLED = auto()
    ERROR = auto()


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""
    
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = ""
    min_version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_builtin: bool = False
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginMetadata:
        """Create metadata from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            license=data.get("license", ""),
            min_version=data.get("min_version", "1.0.0"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            is_builtin=data.get("is_builtin", False),
        )


@dataclass
class PluginHandler:
    """
    Registration for a plugin event handler.
    
    Associates a handler function with event filters and priority.
    """
    
    handler: Callable[..., Any]
    event_type: EventType
    filters: list[EventFilter] = field(default_factory=list)
    priority: int = 0
    name: str = ""
    description: str = ""
    enabled: bool = True


@dataclass
class CommandDefinition:
    """Definition of a command that can be invoked."""
    
    name: str
    handler: Callable[..., Any]
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""
    permission_level: int = 0
    hidden: bool = False


@runtime_checkable
class Plugin(Protocol):
    """Protocol for plugins."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        ...
    
    async def on_load(self) -> None:
        """Called when the plugin is loaded."""
        ...
    
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        ...


class BasePlugin(ABC):
    """
    Abstract base class for plugins.
    
    Provides common functionality and lifecycle hooks for plugins.
    """
    
    def __init__(self) -> None:
        self._metadata: PluginMetadata | None = None
        self._handlers: list[PluginHandler] = []
        self._commands: dict[str, CommandDefinition] = {}
        self._status = PluginStatus.UNLOADED
        self._context: Any = None
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @property
    def status(self) -> PluginStatus:
        """Get plugin status."""
        return self._status
    
    @property
    def handlers(self) -> list[PluginHandler]:
        """Get registered handlers."""
        return self._handlers.copy()
    
    @property
    def commands(self) -> dict[str, CommandDefinition]:
        """Get registered commands."""
        return self._commands.copy()
    
    def set_context(self, context: Any) -> None:
        """Set the plugin context (injected by plugin manager)."""
        self._context = context
    
    async def on_load(self) -> None:
        """Called when the plugin is loaded. Override to add custom logic."""
        pass
    
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override to add cleanup logic."""
        pass
    
    async def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        pass
    
    async def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        pass


# Decorators for plugin handler registration

def command(
    name: str,
    aliases: list[str] | None = None,
    description: str = "",
    usage: str = "",
    permission_level: int = 0,
    hidden: bool = False,
) -> Callable:
    """
    Decorator to register a command handler.
    
    Example:
        @command("help", aliases=["h"], description="Show help")
        async def help_command(self, event):
            ...
    """
    def decorator(func: Callable) -> Callable:
        func._command_def = CommandDefinition(
            name=name,
            handler=func,
            aliases=aliases or [],
            description=description,
            usage=usage,
            permission_level=permission_level,
            hidden=hidden,
        )
        return func
    return decorator


def on_message(
    priority: int = 0,
    filters: list | None = None,
) -> Callable:
    """
    Decorator to register a message handler.
    
    Example:
        @on_message(priority=10)
        async def handle_message(self, event):
            ...
    """
    def decorator(func: Callable) -> Callable:
        from aetherpackbot.protocols.events import EventType
        func._handler_def = PluginHandler(
            handler=func,
            event_type=EventType.MESSAGE_RECEIVED,
            filters=filters or [],
            priority=priority,
            name=func.__name__,
        )
        return func
    return decorator


def on_event(
    event_type: EventType,
    priority: int = 0,
    filters: list | None = None,
) -> Callable:
    """
    Decorator to register an event handler.
    
    Example:
        @on_event(EventType.SYSTEM_STARTUP)
        async def on_startup(self, event):
            ...
    """
    def decorator(func: Callable) -> Callable:
        func._handler_def = PluginHandler(
            handler=func,
            event_type=event_type,
            filters=filters or [],
            priority=priority,
            name=func.__name__,
        )
        return func
    return decorator


def llm_tool(
    name: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator to register an LLM tool.
    
    Example:
        @llm_tool("search_web", description="Search the web")
        async def search_web(self, query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        func._tool_def = {
            "name": name,
            "description": description,
            "parameters": parameters or {},
            "handler": func,
        }
        return func
    return decorator
