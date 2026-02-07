"""
Event Protocols - Event types and handlers.

Defines the event system used for decoupled communication between components.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Protocol, TypeVar, Generic, runtime_checkable


class EventType(Enum):
    """Core event types in the system."""
    
    # Lifecycle events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_READY = "system.ready"
    
    # Message events
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENDING = "message.sending"
    MESSAGE_SENT = "message.sent"
    MESSAGE_FAILED = "message.failed"
    
    # LLM events
    LLM_REQUEST_START = "llm.request.start"
    LLM_REQUEST_COMPLETE = "llm.request.complete"
    LLM_REQUEST_ERROR = "llm.request.error"
    LLM_STREAMING_CHUNK = "llm.streaming.chunk"
    
    # Tool events
    TOOL_CALL_START = "tool.call.start"
    TOOL_CALL_COMPLETE = "tool.call.complete"
    TOOL_CALL_ERROR = "tool.call.error"
    
    # Platform events
    PLATFORM_CONNECTED = "platform.connected"
    PLATFORM_DISCONNECTED = "platform.disconnected"
    PLATFORM_ERROR = "platform.error"
    
    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"
    
    # Conversation events
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    CONVERSATION_CLEARED = "conversation.cleared"
    
    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """
    Base event class.
    
    Events are immutable data objects that carry information about
    something that has happened in the system.
    """
    
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Event flow control
    _cancelled: bool = field(default=False, repr=False)
    _propagation_stopped: bool = field(default=False, repr=False)
    
    def cancel(self) -> None:
        """Cancel the event, preventing further processing."""
        self._cancelled = True
    
    def stop_propagation(self) -> None:
        """Stop the event from propagating to more handlers."""
        self._propagation_stopped = True
    
    @property
    def is_cancelled(self) -> bool:
        """Check if the event was cancelled."""
        return self._cancelled
    
    @property
    def is_propagation_stopped(self) -> bool:
        """Check if propagation was stopped."""
        return self._propagation_stopped


@dataclass
class MessageEvent(Event):
    """Event carrying a message."""
    
    from core.api.messages import Message, MessageChain
    
    message: Message | None = None
    
    # Processing state
    is_wake: bool = False
    is_handled: bool = False
    
    # Response
    _result: MessageChain | None = field(default=None, repr=False)
    
    def __init__(self, message: Message, **kwargs) -> None:
        super().__init__(
            event_type=EventType.MESSAGE_RECEIVED,
            **kwargs,
        )
        self.message = message
        self.is_wake = False
        self.is_handled = False
        self._result = None
    
    @property
    def text(self) -> str:
        """Get the message text."""
        return self.message.text if self.message else ""
    
    @property
    def result(self) -> MessageChain | None:
        """Get the response result."""
        return self._result
    
    def set_result(self, chain: MessageChain) -> None:
        """Set the response result."""
        from core.api.messages import MessageChain
        self._result = chain
        self.is_handled = True
    
    def get_extra(self, key: str, default: Any = None) -> Any:
        """Get an extra data value."""
        return self.data.get(key, default)
    
    def set_extra(self, key: str, value: Any) -> None:
        """Set an extra data value."""
        self.data[key] = value


@dataclass
class LLMEvent(Event):
    """Event related to LLM processing."""
    
    provider_id: str = ""
    model: str = ""
    prompt: str = ""
    response: str = ""
    tokens_used: int = 0
    error: str | None = None
    
    def __init__(
        self,
        event_type: EventType,
        provider_id: str,
        model: str = "",
        **kwargs,
    ) -> None:
        super().__init__(event_type=event_type, **kwargs)
        self.provider_id = provider_id
        self.model = model


@dataclass 
class ToolEvent(Event):
    """Event related to tool execution."""
    
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    
    def __init__(
        self,
        event_type: EventType,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(event_type=event_type, **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for event handlers."""
    
    async def handle(self, event: Event) -> None:
        """Handle an event."""
        ...


@dataclass
class EventFilter:
    """
    Filter for matching events.
    
    Used to determine which events a handler should receive.
    """
    
    event_types: list[EventType] | None = None
    source_pattern: str | None = None
    predicate: Callable[[Event], bool] | None = None
    
    def matches(self, event: Event) -> bool:
        """Check if an event matches this filter."""
        # Check event type
        if self.event_types is not None and event.event_type not in self.event_types:
            return False
        
        # Check source pattern
        if self.source_pattern is not None:
            import re
            if not re.match(self.source_pattern, event.source):
                return False
        
        # Check custom predicate
        if self.predicate is not None and not self.predicate(event):
            return False
        
        return True


@dataclass
class HandlerRegistration:
    """Registration data for an event handler."""
    
    handler: Callable[[Event], Any]
    filter: EventFilter
    priority: int = 0
    name: str = ""
    enabled: bool = True
    
    def __lt__(self, other: HandlerRegistration) -> bool:
        # Higher priority handlers come first
        return self.priority > other.priority
