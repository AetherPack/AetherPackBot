"""
配置模块 - 管理框架配置
Config module - manages framework configuration.
"""

from AetherPackBot.config.defaults import build_default_config
from AetherPackBot.config.manager import ConfigManager

__all__ = ["ConfigManager", "build_default_config"]
