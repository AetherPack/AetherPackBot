"""
内置工具 - 提供 Agent 可调用的默认工具
Builtin tools - provides default tools callable by agents.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from AetherPackBot.agent.runner import ToolRegistry

logger = logging.getLogger(__name__)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """
    注册内置工具到注册表
    Register builtin tools into the registry.
    """
    from AetherPackBot.agent.runner import ToolSpec

    # 网络搜索（占位）/ Web search (placeholder)
    async def web_search(query: str) -> str:
        return f"[web_search] placeholder result for: {query}"

    registry.register(
        ToolSpec(
            name="web_search",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    }
                },
                "required": ["query"],
            },
            callback=web_search,
        )
    )

    # 代码执行（占位）/ Code execution (placeholder)
    async def code_exec(code: str, language: str = "python") -> str:
        return f"[code_exec] placeholder for {language}: {code[:100]}"

    registry.register(
        ToolSpec(
            name="code_exec",
            description="Execute code snippet",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code snippet to execute",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language",
                        "default": "python",
                    },
                },
                "required": ["code"],
            },
            callback=code_exec,
        )
    )

    # 文件读取 / File read
    async def read_file(path: str) -> str:
        sandboxed = os.path.normpath(os.path.join("data", "temp", path))
        if not sandboxed.startswith(os.path.normpath("data")):
            return "Error: path traversal not allowed"
        if not os.path.isfile(sandboxed):
            return f"Error: file not found: {sandboxed}"
        with open(sandboxed, encoding="utf-8", errors="replace") as f:
            content = f.read(10000)
        return content

    registry.register(
        ToolSpec(
            name="read_file",
            description="Read a file from sandbox area",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to sandbox",
                    }
                },
                "required": ["path"],
            },
            callback=read_file,
        )
    )
