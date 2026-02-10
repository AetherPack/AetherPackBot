"""
Configuration Manager - Application configuration management.

Provides configuration loading, validation, and persistence with
support for JSON configuration files and environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, TypeVar, Generic

from AetherPackBot.core.kernel.logging import get_logger

T = TypeVar("T")
logger = get_logger("config")

# Default configuration values
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "debug": False,
    
    # Web server settings
    "web": {
        "host": "0.0.0.0",
        "port": 8080,
        "enable_cors": True,
        "admin_username": "aetherpackbot",
        "admin_password": "aetherpackbot",
        "jwt_secret": "",
    },
    
    # Logging settings
    "logging": {
        "level": "INFO",
        "log_dir": "data/logs",
    },
    
    # Database settings
    "database": {
        "url": "sqlite+aiosqlite:///data/aetherpackbot.db",
    },
    
    # Platform settings
    "platforms": [],
    
    # Provider settings
    "providers": [],
    
    # Plugin settings
    "plugins": {
        "enabled": True,
        "directory": "data/plugins",
        "plugin_data_dir": "data/plugin_data",
        "auto_update": False,
    },
    
    # Agent settings
    "agent": {
        "default_provider": "",
        "max_tool_steps": 30,
        "tool_timeout": 60,
        "wake_prefixes": ["/", "!"],
        "wake_words": [],
    },
    
    # Content moderation
    "moderation": {
        "enabled": False,
        "rate_limit_enabled": True,
        "rate_limit_per_minute": 30,
    },
    
    # Reply behavior
    "reply": {
        "add_prefix": False,
        "prefix_template": "[AetherPackBot] ",
        "at_sender": False,
        "quote_original": False,
    },
    
    # Persona settings
    "personas": [],
    "default_persona": "",
    
    # Sub-agents
    "subagents": [],
}


@dataclass
class WebConfig:
    """Web server configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8080
    enable_cors: bool = True
    admin_username: str = "aetherpackbot"
    admin_password: str = "aetherpackbot"
    jwt_secret: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"
    log_dir: str = "data/logs"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    url: str = "sqlite+aiosqlite:///data/storage/aetherpackbot.db"


@dataclass
class PluginConfig:
    """Plugin system configuration."""
    
    enabled: bool = True
    directory: str = "data/plugins"
    auto_update: bool = False


@dataclass
class AgentMainConfig:
    """Agent configuration."""
    
    default_provider: str = ""
    max_tool_steps: int = 30
    tool_timeout: int = 60
    wake_prefixes: list[str] = field(default_factory=lambda: ["/", "!"])
    wake_words: list[str] = field(default_factory=list)


@dataclass
class ModerationConfig:
    """Content moderation configuration."""
    
    enabled: bool = False
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30


@dataclass
class ReplyConfig:
    """Reply behavior configuration."""
    
    add_prefix: bool = False
    prefix_template: str = "[AetherPackBot] "
    at_sender: bool = False
    quote_original: bool = False


class ConfigurationManager:
    """
    Manages application configuration.
    
    Loads configuration from file, provides access to config values,
    and handles configuration updates.
    """
    
    def __init__(self, config_path: str | None = None) -> None:
        if config_path:
            self._config_path = Path(config_path)
        else:
            from AetherPackBot.core.kernel.paths import get_config_file
            self._config_path = get_config_file()
        self._config: dict[str, Any] = {}
        self._loaded = False
    
    async def load(self) -> None:
        """Load configuration from file."""
        if self._loaded:
            return
        
        # Start with defaults
        self._config = self._deep_copy(DEFAULT_CONFIG)
        
        # Load from file if exists
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                self._deep_merge(self._config, file_config)
                logger.info(f"Configuration loaded from {self._config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}. Using defaults.")
        else:
            # Save default config
            await self.save()
            logger.info("Created default configuration file")
        
        # Override with environment variables
        self._load_env_overrides()
        
        self._loaded = True
    
    async def save(self) -> None:
        """Save current configuration to file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Configuration saved to {self._config_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-notation key.
        
        Example:
            config.get("web.port", 8080)
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by dot-notation key.
        
        Example:
            config.set("web.port", 9000)
        """
        keys = key.split(".")
        target = self._config
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire configuration section."""
        return self._config.get(section, {})
    
    def set_section(self, section: str, data: dict[str, Any]) -> None:
        """Set an entire configuration section."""
        self._config[section] = data
    
    def to_dict(self) -> dict[str, Any]:
        """Get the full configuration as a dictionary."""
        return self._deep_copy(self._config)
    
    @property
    def web(self) -> WebConfig:
        """Get web server configuration."""
        data = self.get_section("web")
        return WebConfig(**{k: v for k, v in data.items() if k in WebConfig.__dataclass_fields__})
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        data = self.get_section("logging")
        return LoggingConfig(**{k: v for k, v in data.items() if k in LoggingConfig.__dataclass_fields__})
    
    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        data = self.get_section("database")
        return DatabaseConfig(**{k: v for k, v in data.items() if k in DatabaseConfig.__dataclass_fields__})
    
    @property
    def plugins(self) -> PluginConfig:
        """Get plugin configuration."""
        data = self.get_section("plugins")
        return PluginConfig(**{k: v for k, v in data.items() if k in PluginConfig.__dataclass_fields__})
    
    @property
    def agent(self) -> AgentMainConfig:
        """Get agent configuration."""
        data = self.get_section("agent")
        return AgentMainConfig(**{k: v for k, v in data.items() if k in AgentMainConfig.__dataclass_fields__})
    
    def _load_env_overrides(self) -> None:
        """Override config values from environment variables."""
        env_mappings = {
            "AETHERPACKBOT_WEB_PORT": ("web.port", int),
            "AETHERPACKBOT_WEB_HOST": ("web.host", str),
            "AETHERPACKBOT_ADMIN_USERNAME": ("web.admin_username", str),
            "AETHERPACKBOT_ADMIN_PASSWORD": ("web.admin_password", str),
            "AETHERPACKBOT_DEBUG": ("debug", lambda x: x.lower() == "true"),
            "AETHERPACKBOT_LOG_LEVEL": ("logging.level", str),
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    self.set(config_key, converter(value))
                    logger.debug(f"Config override from env: {config_key}")
                except ValueError:
                    logger.warning(f"Invalid env value for {env_var}")
    
    def _deep_merge(self, base: dict, updates: dict) -> None:
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of a config object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj
