"""
Messaging Layer - Message handling and processing pipeline.

Provides the message processing pipeline including event dispatching,
message transformation, and response generation.
"""

from AetherPackBot.core.messaging.events import EventDispatcher
from AetherPackBot.core.messaging.processor import MessageProcessor

__all__ = [
    "EventDispatcher",
    "MessageProcessor",
]
