"""
Plugin Manager - Manages plugin lifecycle and execution.

Handles plugin discovery, loading, registration, and execution.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

from AetherPackBot.core.api.plugins import (
    BasePlugin,
    PluginMetadata,
    PluginHandler,
    PluginStatus,
    CommandDefinition,
)
from AetherPackBot.core.api.events import Event, EventType, MessageEvent
from AetherPackBot.core.logging import get_logger

if TYPE_CHECKING:
    from AetherPackBot.core.container import ServiceContainer

logger = get_logger("plugins")


class ManagedPlugin:
    """Wrapper for a managed plugin instance."""
    
    def __init__(
        self,
        plugin: BasePlugin,
        module_path: str,
        is_builtin: bool = False,
    ) -> None:
        self.plugin = plugin
        self.module_path = module_path
        self.is_builtin = is_builtin
        self.status = PluginStatus.UNLOADED
        self.error: Exception | None = None
        
        # Collected handlers and commands
        self.handlers: list[PluginHandler] = []
        self.commands: dict[str, CommandDefinition] = {}
        self.llm_tools: list[dict[str, Any]] = []
    
    @property
    def name(self) -> str:
        return self.plugin.metadata.name
    
    @property
    def metadata(self) -> PluginMetadata:
        return self.plugin.metadata


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    
    Scans plugin directories, loads plugins, and manages their lifecycle.
    Also collects and routes handlers to the appropriate events.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._plugins: dict[str, ManagedPlugin] = {}
        self._handlers_by_event: dict[EventType, list[tuple[int, Callable]]] = {}
        self._commands: dict[str, tuple[ManagedPlugin, CommandDefinition]] = {}
        
        # Plugin directories
        self._builtin_dir = Path(__file__).parent.parent / "extensions"
        self._user_dir = Path("data/plugins")
    
    async def scan_and_load(self) -> None:
        """Scan and load all plugins."""
        # Ensure directories exist
        self._builtin_dir.mkdir(parents=True, exist_ok=True)
        self._user_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan builtin plugins
        await self._scan_directory(self._builtin_dir, is_builtin=True)
        
        # Scan user plugins
        await self._scan_directory(self._user_dir, is_builtin=False)
        
        logger.info(f"Loaded {len(self._plugins)} plugins")
    
    async def start(self) -> None:
        """Start the plugin manager (lifecycle hook)."""
        # Enable all loaded plugins
        for managed in self._plugins.values():
            if managed.status == PluginStatus.LOADED:
                await self._enable_plugin(managed)
    
    async def stop(self) -> None:
        """Stop the plugin manager (lifecycle hook)."""
        # Disable all plugins
        for managed in list(self._plugins.values()):
            if managed.status == PluginStatus.ENABLED:
                await self._disable_plugin(managed)
    
    async def _scan_directory(
        self,
        directory: Path,
        is_builtin: bool,
    ) -> None:
        """Scan a directory for plugins."""
        if not directory.exists():
            return
        
        for item in directory.iterdir():
            if item.is_dir() and (item / "main.py").exists():
                # Plugin is a directory with main.py
                await self._load_plugin(item / "main.py", is_builtin)
            elif item.is_file() and item.suffix == ".py" and item.stem != "__init__":
                # Plugin is a single file
                await self._load_plugin(item, is_builtin)
    
    async def _load_plugin(
        self,
        plugin_path: Path,
        is_builtin: bool,
    ) -> ManagedPlugin | None:
        """Load a single plugin from a file."""
        try:
            module_name = f"AetherPackBot.core.plugin.loaded.{plugin_path.stem}"
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load module spec for {plugin_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, BasePlugin) and
                    attr is not BasePlugin
                ):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.warning(f"No plugin class found in {plugin_path}")
                return None
            
            # Create plugin instance
            plugin = plugin_class()
            
            # Create managed wrapper
            managed = ManagedPlugin(
                plugin=plugin,
                module_path=str(plugin_path),
                is_builtin=is_builtin,
            )
            
            # Collect handlers and commands
            self._collect_handlers(managed)
            
            # Call on_load
            await plugin.on_load()
            
            managed.status = PluginStatus.LOADED
            self._plugins[managed.name] = managed
            
            logger.info(f"Loaded plugin: {managed.name}")
            return managed
            
        except Exception as e:
            logger.exception(f"Failed to load plugin from {plugin_path}: {e}")
            return None
    
    def _collect_handlers(self, managed: ManagedPlugin) -> None:
        """Collect handlers from a plugin."""
        plugin = managed.plugin
        
        for attr_name in dir(plugin):
            attr = getattr(plugin, attr_name)
            
            if not callable(attr):
                continue
            
            # Check for handler definition
            if hasattr(attr, "_handler_def"):
                handler_def: PluginHandler = attr._handler_def
                handler_def.handler = attr  # Bind to instance
                managed.handlers.append(handler_def)
            
            # Check for command definition
            if hasattr(attr, "_command_def"):
                command_def: CommandDefinition = attr._command_def
                command_def.handler = attr  # Bind to instance
                managed.commands[command_def.name] = command_def
                
                # Also register aliases
                for alias in command_def.aliases:
                    managed.commands[alias] = command_def
            
            # Check for LLM tool definition
            if hasattr(attr, "_tool_def"):
                tool_def = attr._tool_def
                tool_def["handler"] = attr  # Bind to instance
                managed.llm_tools.append(tool_def)
    
    async def _enable_plugin(self, managed: ManagedPlugin) -> None:
        """Enable a plugin."""
        try:
            await managed.plugin.on_enable()
            
            # Register handlers
            for handler in managed.handlers:
                if handler.event_type not in self._handlers_by_event:
                    self._handlers_by_event[handler.event_type] = []
                
                self._handlers_by_event[handler.event_type].append(
                    (handler.priority, handler.handler)
                )
                # Sort by priority (higher first)
                self._handlers_by_event[handler.event_type].sort(
                    key=lambda x: -x[0]
                )
            
            # Register commands
            for name, command in managed.commands.items():
                self._commands[name] = (managed, command)
            
            managed.status = PluginStatus.ENABLED
            logger.info(f"Enabled plugin: {managed.name}")
            
        except Exception as e:
            managed.error = e
            managed.status = PluginStatus.ERROR
            logger.exception(f"Failed to enable plugin {managed.name}: {e}")
    
    async def _disable_plugin(self, managed: ManagedPlugin) -> None:
        """Disable a plugin."""
        try:
            await managed.plugin.on_disable()
            
            # Unregister handlers
            for handler in managed.handlers:
                if handler.event_type in self._handlers_by_event:
                    self._handlers_by_event[handler.event_type] = [
                        (p, h) for p, h in self._handlers_by_event[handler.event_type]
                        if h != handler.handler
                    ]
            
            # Unregister commands
            for name in managed.commands:
                if name in self._commands:
                    del self._commands[name]
            
            managed.status = PluginStatus.DISABLED
            logger.info(f"Disabled plugin: {managed.name}")
            
        except Exception as e:
            logger.exception(f"Failed to disable plugin {managed.name}: {e}")
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        if plugin_name not in self._plugins:
            return False
        
        managed = self._plugins[plugin_name]
        
        # Disable
        if managed.status == PluginStatus.ENABLED:
            await self._disable_plugin(managed)
        
        # Unload
        await managed.plugin.on_unload()
        del self._plugins[plugin_name]
        
        # Reload the module
        module_path = Path(managed.module_path)
        new_managed = await self._load_plugin(module_path, managed.is_builtin)
        
        if new_managed:
            await self._enable_plugin(new_managed)
            return True
        
        return False
    
    def get_plugin(self, name: str) -> ManagedPlugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> list[ManagedPlugin]:
        """Get all plugins."""
        return list(self._plugins.values())
    
    def get_command(self, name: str) -> tuple[ManagedPlugin, CommandDefinition] | None:
        """Get a command by name."""
        return self._commands.get(name)
    
    def get_llm_tools(self) -> list[dict[str, Any]]:
        """Get all registered LLM tools."""
        tools = []
        for managed in self._plugins.values():
            if managed.status == PluginStatus.ENABLED:
                tools.extend(managed.llm_tools)
        return tools
    
    async def get_matching_handlers(
        self,
        event: MessageEvent,
    ) -> list[Callable]:
        """Get handlers that match the event."""
        handlers = []
        
        # Get message text for command matching
        text = event.text.strip() if event.message else ""
        
        # Check for command
        for prefix in ["/", "!"]:  # TODO: Get from config
            if text.startswith(prefix):
                command_name = text[len(prefix):].split()[0]
                command_info = self.get_command(command_name)
                if command_info:
                    managed, command = command_info
                    handlers.append(command.handler)
                break
        
        # Get general message handlers
        event_type = EventType.MESSAGE_RECEIVED
        if event_type in self._handlers_by_event:
            for priority, handler in self._handlers_by_event[event_type]:
                handlers.append(handler)
        
        return handlers
