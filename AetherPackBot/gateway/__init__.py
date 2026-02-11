"""
网关模块 - 消息平台适配层
Gateway module - message platform adapter layer.

负责与各种消息平台（Telegram、QQ、Discord 等）通信。
Responsible for communicating with various messaging platforms.
"""

from AetherPackBot.gateway.base import Gateway, GatewayStatus
from AetherPackBot.gateway.registry import GatewayRegistry
from AetherPackBot.gateway.session import SessionTracker

__all__ = ["Gateway", "GatewayStatus", "GatewayRegistry", "SessionTracker"]
