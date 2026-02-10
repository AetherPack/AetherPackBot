"""
Platform Protocols - Platform adapter interfaces.

Defines abstract interfaces for messaging platform adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol, runtime_checkable

from aetherpackbot.core.api.messages import MessageChain, MessageSession


class PlatformStatus(Enum):
    """Status of a platform adapter."""
    
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ERROR = auto()


@dataclass
class PlatformConfig:
    """Configuration for a platform adapter."""
    
    platform_id: str
    platform_type: str
    enabled: bool = True
    display_name: str = ""
    credentials: dict[str, str] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get the platform display name."""
        return self.display_name or self.platform_id


@dataclass
class PlatformCapabilities:
    """Capabilities of a platform adapter."""
    
    supports_text: bool = True
    supports_images: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    supports_files: bool = False
    supports_reactions: bool = False
    supports_threads: bool = False
    supports_mentions: bool = False
    supports_rich_text: bool = False
    supports_buttons: bool = False
    max_message_length: int = 2000
    max_image_size: int = 10 * 1024 * 1024  # 10 MB


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for platform adapters."""
    
    @property
    def platform_id(self) -> str:
        """Get the unique platform ID."""
        ...
    
    @property
    def platform_type(self) -> str:
        """Get the platform type (e.g., 'telegram', 'discord')."""
        ...
    
    @property
    def status(self) -> PlatformStatus:
        """Get the current connection status."""
        ...
    
    @property
    def capabilities(self) -> PlatformCapabilities:
        """Get the platform capabilities."""
        ...
    
    async def start(self) -> None:
        """Start the platform adapter."""
        ...
    
    async def stop(self) -> None:
        """Stop the platform adapter."""
        ...
    
    async def send_message(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """
        Send a message to a session.
        
        Returns the message ID if successful.
        """
        ...


class BasePlatformAdapter(ABC):
    """
    Abstract base class for platform adapters.
    
    Provides common functionality for all platform adapters.
    """
    
    def __init__(self, config: PlatformConfig) -> None:
        self._config = config
        self._status = PlatformStatus.DISCONNECTED
        self._capabilities = PlatformCapabilities()
    
    @property
    def platform_id(self) -> str:
        return self._config.platform_id
    
    @property
    def platform_type(self) -> str:
        return self._config.platform_type
    
    @property
    def status(self) -> PlatformStatus:
        return self._status
    
    @property
    def capabilities(self) -> PlatformCapabilities:
        return self._capabilities
    
    @property
    def config(self) -> PlatformConfig:
        return self._config
    
    @abstractmethod
    async def start(self) -> None:
        """Start the platform adapter."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the platform adapter."""
        pass
    
    @abstractmethod
    async def send_message(
        self,
        session: MessageSession,
        chain: MessageChain,
        reply_to: str | None = None,
    ) -> str | None:
        """Send a message."""
        pass
    
    def _set_status(self, status: PlatformStatus) -> None:
        """Update the adapter status."""
        self._status = status


@dataclass
class PlatformInfo:
    """Information about a registered platform type."""
    
    type_name: str
    display_name: str
    adapter_class: type[BasePlatformAdapter]
    config_schema: dict[str, Any] = field(default_factory=dict)
    description: str = ""
