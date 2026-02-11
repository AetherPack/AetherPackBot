"""
钩子系统 - 扩展包通过钩子注册处理器
Hook system - packs register handlers through hooks.

使用函数装饰器而非类装饰器，更简洁灵活。
Uses function decorators instead of class decorators, more concise and flexible.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HookKind(str, Enum):
    """钩子类型 / Hook kind."""

    COMMAND = "command"
    REGEX = "regex"
    MESSAGE = "message"
    AGENT = "agent"
    LLM_TOOL = "llm_tool"
    EVENT = "event"


@dataclass
class HookDescriptor:
    """
    钩子描述符 - 描述一个注册的处理器
    Hook descriptor - describes a registered handler.
    """

    kind: HookKind
    handler: Callable[..., Any]
    # 命令名/正则模式/事件类型
    pattern: str = ""
    # 描述
    description: str = ""
    # 优先级（越小越先执行）
    priority: int = 50
    # 所属包名
    pack_name: str = ""
    # 权限要求
    permission: str = ""  # "admin" / "member" / ""
    # 是否启用
    enabled: bool = True
    # LLM 工具的参数描述
    tool_params: dict[str, Any] = field(default_factory=dict)


# 全局钩子注册表
_hook_registry: list[HookDescriptor] = []


def get_all_hooks() -> list[HookDescriptor]:
    """获取所有已注册的钩子 / Get all registered hooks."""
    return list(_hook_registry)


def clear_hooks() -> None:
    """清空所有钩子（用于测试） / Clear all hooks (for testing)."""
    _hook_registry.clear()


def hook(
    kind: HookKind = HookKind.MESSAGE,
    pattern: str = "",
    description: str = "",
    priority: int = 50,
    permission: str = "",
) -> Callable:
    """
    通用钩子装饰器
    Generic hook decorator.
    """

    def decorator(func: Callable) -> Callable:
        descriptor = HookDescriptor(
            kind=kind,
            handler=func,
            pattern=pattern,
            description=description or func.__doc__ or "",
            priority=priority,
            permission=permission,
        )
        _hook_registry.append(descriptor)
        # 将描述符附加到函数上以便后续使用
        if not hasattr(func, "_hook_descriptors"):
            func._hook_descriptors = []
        func._hook_descriptors.append(descriptor)
        return func

    return decorator


def command_hook(
    command: str,
    description: str = "",
    priority: int = 50,
    permission: str = "",
) -> Callable:
    """
    命令钩子装饰器 - 匹配特定命令
    Command hook decorator - matches a specific command.
    """
    return hook(
        kind=HookKind.COMMAND,
        pattern=command,
        description=description,
        priority=priority,
        permission=permission,
    )


def regex_hook(
    pattern: str,
    description: str = "",
    priority: int = 50,
) -> Callable:
    """
    正则钩子装饰器 - 匹配正则表达式
    Regex hook decorator - matches a regex pattern.
    """
    return hook(
        kind=HookKind.REGEX,
        pattern=pattern,
        description=description,
        priority=priority,
    )


def agent_hook(
    description: str = "",
    priority: int = 50,
) -> Callable:
    """
    Agent 钩子装饰器 - 注册为 Agent 处理器
    Agent hook decorator - registers as an Agent handler.
    """
    return hook(
        kind=HookKind.AGENT,
        description=description,
        priority=priority,
    )


def llm_tool_hook(
    name: str,
    description: str = "",
    params: dict[str, Any] | None = None,
) -> Callable:
    """
    LLM 工具钩子 - 注册为 LLM Function Tool
    LLM tool hook - registers as an LLM Function Tool.
    """

    def decorator(func: Callable) -> Callable:
        descriptor = HookDescriptor(
            kind=HookKind.LLM_TOOL,
            handler=func,
            pattern=name,
            description=description or func.__doc__ or "",
            tool_params=params or {},
        )
        _hook_registry.append(descriptor)
        if not hasattr(func, "_hook_descriptors"):
            func._hook_descriptors = []
        func._hook_descriptors.append(descriptor)
        return func

    return decorator


def match_command(text: str, command: str) -> tuple[bool, str]:
    """
    检查文本是否匹配命令
    Check if text matches a command.

    返回 (是否匹配, 剩余参数文本)
    Returns (matched, remaining argument text).
    """
    text = text.strip()
    if text.startswith("/"):
        text = text[1:]

    parts = text.split(maxsplit=1)
    if not parts:
        return False, ""

    if parts[0].lower() == command.lower():
        return True, parts[1] if len(parts) > 1 else ""

    return False, ""


def match_regex(text: str, pattern: str) -> re.Match | None:
    """
    正则匹配
    Regex match.
    """
    try:
        return re.search(pattern, text)
    except re.error:
        return None
