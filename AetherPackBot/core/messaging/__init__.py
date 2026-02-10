"""
Messaging Layer - Message handling and processing pipeline.

Provides the message processing pipeline including event dispatching,
message transformation, and response generation.
"""

from aetherpackbot.core.messaging.events import EventDispatcher
from aetherpackbot.core.messaging.processor import MessageProcessor

__all__ = [
    "EventDispatcher",
    "MessageProcessor",
]
