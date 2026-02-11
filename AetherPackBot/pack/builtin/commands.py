"""
内置命令包 - 提供基础命令
Built-in commands pack - provides basic commands.
"""

from __future__ import annotations

from typing import Any

from AetherPackBot.kernel.middleware import ProcessingContext
from AetherPackBot.pack.base import Pack
from AetherPackBot.pack.hooks import command_hook


class BuiltinCommandsPack(Pack):
    """内置命令扩展包 / Built-in commands extension pack."""

    async def on_load(self) -> None:
        pass

    @command_hook("help", description="显示帮助信息 / Show help info")
    async def cmd_help(self, event: Any, ctx: ProcessingContext) -> str:
        """帮助命令 / Help command."""
        from AetherPackBot.pack.hooks import HookKind, get_all_hooks

        lines = ["AetherPackBot - 可用命令列表:", ""]
        for h in get_all_hooks():
            if h.kind == HookKind.COMMAND and h.enabled:
                desc = h.description or "无描述"
                lines.append(f"  /{h.pattern} - {desc}")

        return "\n".join(lines)

    @command_hook("ping", description="检测机器人是否在线 / Check if bot is online")
    async def cmd_ping(self, event: Any, ctx: ProcessingContext) -> str:
        """Ping 命令 / Ping command."""
        return "pong!"

    @command_hook("version", description="显示版本信息 / Show version info")
    async def cmd_version(self, event: Any, ctx: ProcessingContext) -> str:
        """版本命令 / Version command."""
        from AetherPackBot import __app_name__, __version__

        return f"{__app_name__} v{__version__}"

    @command_hook("status", description="显示运行状态 / Show running status")
    async def cmd_status(self, event: Any, ctx: ProcessingContext) -> str:
        """状态命令 / Status command."""
        from AetherPackBot.pack.loader import PackLoader

        try:
            loader: PackLoader = await self._container.resolve(PackLoader)
            packs = loader.list_packs()
            pack_info = f"已加载扩展包: {len(packs)}"
        except KeyError:
            pack_info = "扩展包信息不可用"

        return f"AetherPackBot 运行中\n{pack_info}"
