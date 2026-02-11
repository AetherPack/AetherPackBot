"""
消息模型模块 - 定义消息的所有组件和事件类型
Message model module - defines all message components and event types.

与原框架不同，采用 Pydantic v2 + 组合模式。
Unlike the original framework, uses Pydantic v2 + Composition pattern.
"""

from AetherPackBot.message.components import (
    AtComponent,
    AudioComponent,
    BaseComponent,
    ComponentKind,
    FaceComponent,
    FileComponent,
    ForwardComponent,
    ImageComponent,
    JsonComponent,
    NodeComponent,
    ReplyComponent,
    ShareComponent,
    TextComponent,
    VideoComponent,
)
from AetherPackBot.message.event import (
    EventKind,
    MessageEvent,
    MessageOrigin,
    SessionInfo,
)
from AetherPackBot.message.types import MessagePayload, MessageSegment

__all__ = [
    "ComponentKind",
    "BaseComponent",
    "TextComponent",
    "ImageComponent",
    "AudioComponent",
    "VideoComponent",
    "FileComponent",
    "AtComponent",
    "ReplyComponent",
    "FaceComponent",
    "ForwardComponent",
    "NodeComponent",
    "ShareComponent",
    "JsonComponent",
    "MessageEvent",
    "EventKind",
    "MessageOrigin",
    "SessionInfo",
    "MessagePayload",
    "MessageSegment",
]
