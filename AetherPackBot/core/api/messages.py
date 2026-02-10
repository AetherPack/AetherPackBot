"""
Message Protocols - Abstract interfaces for message handling.

Defines the core message types and structures used throughout the system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol, runtime_checkable


class ComponentType(Enum):
    """Types of message components."""
    
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    MENTION = "mention"
    MENTION_ALL = "mention_all"
    REPLY = "reply"
    FORWARD = "forward"
    EMOJI = "emoji"
    LOCATION = "location"
    LINK = "link"
    QUOTE = "quote"


@dataclass
class MessageComponent:
    """
    Base class for message components.
    
    Each component represents a discrete unit of content in a message,
    such as text, images, mentions, etc.
    """
    
    type: ComponentType
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def as_dict(self) -> dict[str, Any]:
        """Convert component to dictionary representation."""
        return {
            "type": self.type.value,
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class TextComponent(MessageComponent):
    """Plain text content."""
    
    text: str = ""
    
    def __init__(self, text: str) -> None:
        super().__init__(type=ComponentType.TEXT)
        self.text = text
        self.data = text


@dataclass
class ImageComponent(MessageComponent):
    """Image content."""
    
    url: str | None = None
    file_path: str | None = None
    base64_data: str | None = None
    width: int | None = None
    height: int | None = None
    
    def __init__(
        self,
        url: str | None = None,
        file_path: str | None = None,
        base64_data: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        super().__init__(type=ComponentType.IMAGE)
        self.url = url
        self.file_path = file_path
        self.base64_data = base64_data
        self.width = width
        self.height = height


@dataclass
class AudioComponent(MessageComponent):
    """Audio content."""
    
    url: str | None = None
    file_path: str | None = None
    duration: float | None = None
    format: str = "mp3"
    
    def __init__(
        self,
        url: str | None = None,
        file_path: str | None = None,
        duration: float | None = None,
        format: str = "mp3",
    ) -> None:
        super().__init__(type=ComponentType.AUDIO)
        self.url = url
        self.file_path = file_path
        self.duration = duration
        self.format = format


@dataclass
class MentionComponent(MessageComponent):
    """User mention."""
    
    user_id: str = ""
    user_name: str | None = None
    
    def __init__(self, user_id: str, user_name: str | None = None) -> None:
        super().__init__(type=ComponentType.MENTION)
        self.user_id = user_id
        self.user_name = user_name


@dataclass
class ReplyComponent(MessageComponent):
    """Reply to another message."""
    
    message_id: str = ""
    sender_id: str | None = None
    content_preview: str | None = None
    
    def __init__(
        self,
        message_id: str,
        sender_id: str | None = None,
        content_preview: str | None = None,
    ) -> None:
        super().__init__(type=ComponentType.REPLY)
        self.message_id = message_id
        self.sender_id = sender_id
        self.content_preview = content_preview


@dataclass
class FileComponent(MessageComponent):
    """File attachment."""
    
    url: str | None = None
    file_path: str | None = None
    file_name: str = ""
    file_size: int | None = None
    mime_type: str | None = None
    
    def __init__(
        self,
        file_name: str,
        url: str | None = None,
        file_path: str | None = None,
        file_size: int | None = None,
        mime_type: str | None = None,
    ) -> None:
        super().__init__(type=ComponentType.FILE)
        self.file_name = file_name
        self.url = url
        self.file_path = file_path
        self.file_size = file_size
        self.mime_type = mime_type


class MessageChain:
    """
    A chain of message components representing a complete message.
    
    Provides fluent API for building messages and utilities for
    extracting content.
    """
    
    def __init__(self, components: list[MessageComponent] | None = None) -> None:
        self._components: list[MessageComponent] = components or []
    
    def append(self, component: MessageComponent) -> MessageChain:
        """Append a component to the chain."""
        self._components.append(component)
        return self
    
    def text(self, content: str) -> MessageChain:
        """Add text content."""
        self._components.append(TextComponent(content))
        return self
    
    def image(self, url: str | None = None, file_path: str | None = None) -> MessageChain:
        """Add an image."""
        self._components.append(ImageComponent(url=url, file_path=file_path))
        return self
    
    def audio(self, url: str | None = None, file_path: str | None = None) -> MessageChain:
        """Add audio content."""
        self._components.append(AudioComponent(url=url, file_path=file_path))
        return self
    
    def mention(self, user_id: str, user_name: str | None = None) -> MessageChain:
        """Add a user mention."""
        self._components.append(MentionComponent(user_id, user_name))
        return self
    
    def reply_to(self, message_id: str) -> MessageChain:
        """Add a reply reference."""
        self._components.append(ReplyComponent(message_id))
        return self
    
    def file(self, file_name: str, url: str | None = None) -> MessageChain:
        """Add a file attachment."""
        self._components.append(FileComponent(file_name, url=url))
        return self
    
    @property
    def components(self) -> list[MessageComponent]:
        """Get all components in the chain."""
        return self._components.copy()
    
    @property
    def plain_text(self) -> str:
        """Extract all text content as a single string."""
        texts = []
        for component in self._components:
            if isinstance(component, TextComponent):
                texts.append(component.text)
            elif component.type == ComponentType.TEXT and component.data:
                texts.append(str(component.data))
        return "".join(texts)
    
    def get_components_by_type(self, component_type: ComponentType) -> list[MessageComponent]:
        """Get all components of a specific type."""
        return [c for c in self._components if c.type == component_type]
    
    def has_component(self, component_type: ComponentType) -> bool:
        """Check if the chain contains a component of the specified type."""
        return any(c.type == component_type for c in self._components)
    
    def __len__(self) -> int:
        return len(self._components)
    
    def __iter__(self):
        return iter(self._components)
    
    def __str__(self) -> str:
        return self.plain_text


@dataclass
class MessageSession:
    """
    Represents a conversation session.
    
    A session tracks the context of a conversation, including
    the message source, platform, and conversation type.
    """
    
    session_id: str
    platform_id: str
    is_group: bool = False
    group_id: str | None = None
    user_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    
    @property
    def unified_origin(self) -> str:
        """Get a unified identifier for this session."""
        session_type = "group" if self.is_group else "private"
        target_id = self.group_id if self.is_group else self.user_id
        return f"{self.platform_id}:{session_type}:{target_id}"


@dataclass
class PlatformMetadata:
    """
    Metadata about the originating platform.
    
    Contains platform-specific information about the message source.
    """
    
    platform_name: str
    platform_id: str
    adapter_type: str
    platform_version: str | None = None
    capabilities: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """
    Complete message structure.
    
    Represents a full message with all its metadata, content,
    and session information.
    """
    
    message_id: str
    chain: MessageChain
    session: MessageSession
    platform_meta: PlatformMetadata
    sender_id: str
    sender_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    is_from_self: bool = False
    is_mentioned: bool = False
    raw_data: Any = None
    extra: dict[str, Any] = field(default_factory=dict)
    
    @property
    def text(self) -> str:
        """Get the plain text content of the message."""
        return self.chain.plain_text
    
    @property
    def unified_origin(self) -> str:
        """Get the unified message origin identifier."""
        return self.session.unified_origin


@runtime_checkable
class MessageSender(Protocol):
    """Protocol for sending messages."""
    
    async def send(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """
        Send a message to a session.
        
        Returns the message ID if successful, None otherwise.
        """
        ...
