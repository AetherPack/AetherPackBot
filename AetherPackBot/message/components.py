"""
消息组件 - 定义消息中可以包含的各种元素
Message components - defines various elements that can be contained in a message.

所有组件继承自 BaseComponent，使用 Pydantic v2 进行序列化。
All components inherit from BaseComponent, using Pydantic v2 for serialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentKind(str, Enum):
    """消息组件类型枚举 / Message component kind enum."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    AT = "at"
    REPLY = "reply"
    FACE = "face"
    FORWARD = "forward"
    NODE = "node"
    SHARE = "share"
    JSON = "json"
    POKE = "poke"
    MUSIC = "music"


class BaseComponent(BaseModel):
    """
    消息组件基类
    Base message component.

    所有消息组件的父类，提供统一的序列化/反序列化能力。
    Parent of all message components, provides unified serialization.
    """

    kind: ComponentKind

    def to_plain_text(self) -> str:
        """转为纯文本表示 / Convert to plain text representation."""
        return ""

    def to_dict(self) -> dict[str, Any]:
        """转为字典 / Convert to dictionary."""
        return self.model_dump()


class TextComponent(BaseComponent):
    """纯文本组件 / Plain text component."""

    kind: ComponentKind = ComponentKind.TEXT
    text: str = ""

    def to_plain_text(self) -> str:
        return self.text


class ImageComponent(BaseComponent):
    """图片组件 / Image component."""

    kind: ComponentKind = ComponentKind.IMAGE
    # 图片 URL 或本地路径
    url: str = ""
    # Base64 数据（可选）
    base64: str = ""
    # 文件路径（可选）
    file_path: str = ""

    def to_plain_text(self) -> str:
        return "[Image]"


class AudioComponent(BaseComponent):
    """语音/音频组件 / Audio component."""

    kind: ComponentKind = ComponentKind.AUDIO
    url: str = ""
    file_path: str = ""
    # 时长（秒）
    duration: float = 0.0

    def to_plain_text(self) -> str:
        return "[Audio]"


class VideoComponent(BaseComponent):
    """视频组件 / Video component."""

    kind: ComponentKind = ComponentKind.VIDEO
    url: str = ""
    file_path: str = ""
    thumbnail_url: str = ""

    def to_plain_text(self) -> str:
        return "[Video]"


class FileComponent(BaseComponent):
    """文件组件 / File component."""

    kind: ComponentKind = ComponentKind.FILE
    url: str = ""
    file_path: str = ""
    filename: str = ""
    size: int = 0

    def to_plain_text(self) -> str:
        return f"[File: {self.filename}]"


class AtComponent(BaseComponent):
    """@提及组件 / At-mention component."""

    kind: ComponentKind = ComponentKind.AT
    # 被 @ 的用户 ID
    target_id: str = ""
    # 显示名称
    display_name: str = ""

    def to_plain_text(self) -> str:
        return f"@{self.display_name or self.target_id}"


class ReplyComponent(BaseComponent):
    """回复引用组件 / Reply/quote component."""

    kind: ComponentKind = ComponentKind.REPLY
    # 被引用的消息 ID
    message_id: str = ""
    # 被引用的消息内容（可选摘要）
    summary: str = ""

    def to_plain_text(self) -> str:
        return f"[Reply: {self.summary}]"


class FaceComponent(BaseComponent):
    """表情组件 / Emoji/face component."""

    kind: ComponentKind = ComponentKind.FACE
    face_id: str = ""
    face_name: str = ""

    def to_plain_text(self) -> str:
        return f"[{self.face_name or self.face_id}]"


class ForwardComponent(BaseComponent):
    """合并转发组件 / Forward/merge component."""

    kind: ComponentKind = ComponentKind.FORWARD
    nodes: list[NodeComponent] = Field(default_factory=list)

    def to_plain_text(self) -> str:
        return f"[Forward: {len(self.nodes)} messages]"


class NodeComponent(BaseComponent):
    """转发中的单条消息节点 / A single message node in forward."""

    kind: ComponentKind = ComponentKind.NODE
    sender_id: str = ""
    sender_name: str = ""
    content: list[BaseComponent] = Field(default_factory=list)
    timestamp: int = 0

    def to_plain_text(self) -> str:
        texts = [c.to_plain_text() for c in self.content]
        return f"{self.sender_name}: {''.join(texts)}"


class ShareComponent(BaseComponent):
    """分享链接组件 / Share link component."""

    kind: ComponentKind = ComponentKind.SHARE
    url: str = ""
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""

    def to_plain_text(self) -> str:
        return f"[Share: {self.title}]"


class JsonComponent(BaseComponent):
    """JSON 卡片消息组件 / JSON card message component."""

    kind: ComponentKind = ComponentKind.JSON
    data: dict[str, Any] = Field(default_factory=dict)
    raw: str = ""

    def to_plain_text(self) -> str:
        return "[JSON Message]"


# 允许 ForwardComponent 引用 NodeComponent
ForwardComponent.model_rebuild()
