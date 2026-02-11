"""
消息类型定义 - 高级消息结构
Message type definitions - high-level message structures.

定义消息载荷（多组件消息）和消息段（单组件片段）。
Defines message payload (multi-component) and message segment (single component).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from AetherPackBot.message.components import (
    BaseComponent,
    ImageComponent,
    TextComponent,
)


@dataclass
class MessageSegment:
    """
    消息段 - 单个消息组件的封装
    Message segment - wrapper for a single message component.

    提供便捷的工厂方法创建各种类型的消息段。
    Provides convenient factory methods to create various segment types.
    """

    component: BaseComponent

    @classmethod
    def text(cls, text: str) -> MessageSegment:
        """创建文本段 / Create a text segment."""
        return cls(component=TextComponent(text=text))

    @classmethod
    def image(
        cls, url: str = "", base64: str = "", file_path: str = ""
    ) -> MessageSegment:
        """创建图片段 / Create an image segment."""
        return cls(
            component=ImageComponent(url=url, base64=base64, file_path=file_path)
        )

    def to_plain_text(self) -> str:
        """转为纯文本 / Convert to plain text."""
        return self.component.to_plain_text()


@dataclass
class MessagePayload:
    """
    消息载荷 - 包含多个消息组件的完整消息
    Message payload - a complete message containing multiple components.

    用于构建要发送的消息。
    Used to build messages to be sent.
    """

    segments: list[MessageSegment] = field(default_factory=list)

    def add_text(self, text: str) -> MessagePayload:
        """添加文本 / Add text."""
        self.segments.append(MessageSegment.text(text))
        return self

    def add_image(
        self, url: str = "", base64: str = "", file_path: str = ""
    ) -> MessagePayload:
        """添加图片 / Add image."""
        self.segments.append(MessageSegment.image(url, base64, file_path))
        return self

    def to_plain_text(self) -> str:
        """转为纯文本 / Convert to plain text."""
        return "".join(seg.to_plain_text() for seg in self.segments)

    @property
    def components(self) -> list[BaseComponent]:
        """获取所有组件 / Get all components."""
        return [seg.component for seg in self.segments]

    def is_empty(self) -> bool:
        """是否为空消息 / Whether the message is empty."""
        return len(self.segments) == 0
