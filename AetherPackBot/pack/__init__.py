"""
扩展包系统 - Pack 是 AetherPackBot 的核心扩展机制
Pack system - Pack is the core extension mechanism of AetherPackBot.

与传统插件系统不同，Pack 使用清单文件描述元数据，
通过钩子系统注册处理器，支持热重载。
Unlike traditional plugin systems, Packs use manifest files for metadata,
register handlers through the hook system, and support hot reloading.
"""

from AetherPackBot.pack.base import Pack
from AetherPackBot.pack.hooks import (
    agent_hook,
    command_hook,
    hook,
    llm_tool_hook,
    regex_hook,
)
from AetherPackBot.pack.loader import PackLoader
from AetherPackBot.pack.manifest import PackManifest

__all__ = [
    "Pack",
    "PackLoader",
    "PackManifest",
    "hook",
    "command_hook",
    "regex_hook",
    "agent_hook",
    "llm_tool_hook",
]
