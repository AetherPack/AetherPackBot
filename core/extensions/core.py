"""
Core Extension - Basic bot functionality.

Provides essential commands and handlers for the bot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.api.plugins import Plugin, PluginMetadata, PluginStatus

if TYPE_CHECKING:
    from core.api.events import Event, MessageEvent
    from core.kernel.container import ServiceContainer


class CoreExtension(Plugin):
    """
    Core extension providing essential bot functionality.
    
    Features:
    - Help command
    - Status command
    - Ping command
    - Wake word handling
    """
    
    def __init__(self) -> None:
        self._status = PluginStatus.LOADED
        self._container: ServiceContainer | None = None
        self._wake_words: list[str] = []
    
    @property
    def name(self) -> str:
        return "core"
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="core",
            version="1.0.0",
            description="Core bot functionality",
            author="AetherPackBot",
            dependencies=[],
            entry_point="",
        )
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @property
    def is_builtin(self) -> bool:
        return True
    
    async def initialize(self, container: "ServiceContainer") -> None:
        """Initialize the extension."""
        self._container = container
        self._status = PluginStatus.LOADED
        
        # Load wake words from config
        try:
            from core.storage.config import ConfigurationManager
            config = await container.resolve(ConfigurationManager)
            self._wake_words = config.get("wake_words", ["bot", "hey bot"])
        except Exception:
            self._wake_words = ["bot", "hey bot"]
    
    async def activate(self) -> None:
        """Activate the extension."""
        self._status = PluginStatus.RUNNING
    
    async def deactivate(self) -> None:
        """Deactivate the extension."""
        self._status = PluginStatus.LOADED
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._status = PluginStatus.UNLOADED
    
    # Command handlers
    
    async def handle_help(self, event: "MessageEvent") -> str | None:
        """Handle /help command."""
        message = event.get_text()
        
        if not message or not message.lower().startswith(("/help", "help")):
            return None
        
        help_text = """📚 *AetherPackBot Help*

*Available Commands:*
• /help - Show this help message
• /status - Show bot status
• /ping - Check bot responsiveness
• /version - Show bot version

*Usage:*
Just send a message to chat with the bot!
You can also use @bot to mention the bot.

*Admin Commands:*
• /reload - Reload plugins
• /config - View/modify configuration

For more info, visit the dashboard at http://localhost:6185"""
        
        return help_text
    
    async def handle_status(self, event: "MessageEvent") -> str | None:
        """Handle /status command."""
        message = event.get_text()
        
        if not message or not message.lower().startswith(("/status", "status")):
            return None
        
        if not self._container:
            return "Status unavailable"
        
        try:
            from core.platform.manager import PlatformManager
            from core.provider.manager import ProviderManager
            from core.plugin.manager import PluginManager
            
            status_lines = ["📊 *Bot Status*\n"]
            
            # Platforms
            platform_manager = await self._container.resolve(PlatformManager)
            platform_status = platform_manager.get_status()
            
            status_lines.append("*Platforms:*")
            for name, running in platform_status.items():
                icon = "✅" if running else "❌"
                status_lines.append(f"  {icon} {name}")
            
            # Providers
            provider_manager = await self._container.resolve(ProviderManager)
            providers = provider_manager.list_provider_ids()
            
            status_lines.append(f"\n*Providers:* {len(providers)} active")
            
            # Plugins
            plugin_manager = await self._container.resolve(PluginManager)
            plugins = plugin_manager.get_all_plugins()
            running_plugins = sum(1 for p in plugins if p.status == PluginStatus.RUNNING)
            
            status_lines.append(f"*Plugins:* {running_plugins}/{len(plugins)} running")
            
            return "\n".join(status_lines)
        
        except Exception as e:
            return f"Error getting status: {e}"
    
    async def handle_ping(self, event: "MessageEvent") -> str | None:
        """Handle /ping command."""
        message = event.get_text()
        
        if not message or not message.lower().startswith(("/ping", "ping")):
            return None
        
        import time
        return f"🏓 Pong! Response time: {int(time.time() * 1000) % 1000}ms"
    
    async def handle_version(self, event: "MessageEvent") -> str | None:
        """Handle /version command."""
        message = event.get_text()
        
        if not message or not message.lower().startswith(("/version", "version")):
            return None
        
        return "🤖 *AetherPackBot v1.0.0*\nAsync LLM Chatbot Framework"
    
    def check_wake_word(self, text: str) -> bool:
        """Check if text contains a wake word."""
        text_lower = text.lower().strip()
        
        for wake_word in self._wake_words:
            if text_lower.startswith(wake_word.lower()):
                return True
            if f"@{wake_word.lower()}" in text_lower:
                return True
        
        return False
    
    def get_command_handlers(self) -> list[tuple[str, callable]]:
        """Get all command handlers."""
        return [
            ("help", self.handle_help),
            ("status", self.handle_status),
            ("ping", self.handle_ping),
            ("version", self.handle_version),
        ]
