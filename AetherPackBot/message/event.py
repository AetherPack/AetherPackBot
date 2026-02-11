"""
消息事件 - 定义收到消息后的事件结构
Message event - defines the event structure after receiving a message.

事件是不可变的输入描述，处理结果通过 ProcessingContext 传递。
Events are immutable input descriptions; results are passed via ProcessingContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from AetherPackBot.message.components import BaseComponent


class EventKind(str, Enum):
    """事件类型枚举 / Event kind enum."""

    # 收到普通消息
    MESSAGE_RECEIVED = "message.received"
    # 系统通知
    NOTICE_RECEIVED = "notice.received"
    # 加群/好友请求
    REQUEST_RECEIVED = "request.received"
    # 自定义事件
    CUSTOM = "custom"


@dataclass
class SessionInfo:
    """
    会话信息 - 描述消息来源的会话
    Session info - describes the session where the message comes from.
    """

    # 平台名称（如 telegram, onebot）
    platform: str = ""
    # 会话 ID（群号/频道 ID/用户 ID 等）
    session_id: str = ""
    # 发送者 ID
    sender_id: str = ""
    # 发送者昵称
    sender_nickname: str = ""
    # 是否为私聊
    is_private: bool = False
    # 是否为群聊
    is_group: bool = False
    # 是否被 @
    is_mentioned: bool = False
    # 附加平台特定数据
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageOrigin:
    """
    消息来源标识 - 唯一标识一条消息的来源
    Message origin identifier - uniquely identifies the source of a message.

    格式: platform:type:session_id
    Format: platform:type:session_id
    """

    platform: str = ""
    message_type: str = ""  # group/private/channel
    session_id: str = ""

    def __str__(self) -> str:
        return f"{self.platform}:{self.message_type}:{self.session_id}"

    @classmethod
    def from_string(cls, origin_str: str) -> MessageOrigin:
        """从字符串解析 / Parse from string."""
        parts = origin_str.split(":", 2)
        if len(parts) == 3:
            return cls(platform=parts[0], message_type=parts[1], session_id=parts[2])
        return cls(platform=origin_str)


@dataclass
class MessageEvent:
    """
    消息事件 - 表示一条收到的消息
    Message event - represents a received message.

    这是框架中消息流转的核心载体。
    This is the core carrier of message flow in the framework.
    """

    # 事件 ID（全局唯一）
    event_id: str = ""
    # 事件类型
    kind: EventKind = EventKind.MESSAGE_RECEIVED
    # 消息组件列表
    components: list[BaseComponent] = field(default_factory=list)
    # 会话信息
    session: SessionInfo = field(default_factory=SessionInfo)
    # 消息来源标识
    origin: MessageOrigin = field(default_factory=MessageOrigin)
    # 原始平台消息对象（保留供适配器使用）
    raw_message: Any = None
    # 时间戳（秒）
    timestamp: float = 0.0
    # 消息 ID（平台原始 ID）
    message_id: str = ""

    @property
    def plain_text(self) -> str:
        """获取纯文本内容 / Get plain text content."""
        return "".join(c.to_plain_text() for c in self.components)

    @property
    def is_private(self) -> bool:
        """是否私聊 / Is private chat."""
        return self.session.is_private

    @property
    def is_mentioned(self) -> bool:
        """是否被 @ / Is mentioned."""
        return self.session.is_mentioned

    # 回复函数（由网关适配器注入）
    _reply_fn: Any = None

    async def reply(self, content: Any) -> None:
        """
        回复消息
        Reply to this message.
        """
        if self._reply_fn is not None:
            await self._reply_fn(content)
