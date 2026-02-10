"""
Event Dispatcher - Central event distribution system.

Provides async event dispatching with support for:
- Priority-based handler ordering
- Event filtering
- Event cancellation and propagation control
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Awaitable
from heapq import heappush, heappop

from AetherPackBot.core.api.events import (
    Event,
    EventType,
    EventFilter,
    HandlerRegistration,
)
from AetherPackBot.core.kernel.logging import get_logger

logger = get_logger("events")


HandlerType = Callable[[Event], Awaitable[None] | None]


class EventDispatcher:
    """
    Central event dispatcher for the application.
    
    Manages event handler registration and event dispatching.
    Handlers are invoked in priority order (higher priority first).
    """
    
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[HandlerRegistration]] = defaultdict(list)
        self._global_handlers: list[HandlerRegistration] = []
        self._lock = asyncio.Lock()
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._dispatch_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Start the event dispatcher."""
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("Event dispatcher started")
    
    async def stop(self) -> None:
        """Stop the event dispatcher."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info("Event dispatcher stopped")
    
    def register(
        self,
        handler: HandlerType,
        event_types: list[EventType] | EventType | None = None,
        filter: EventFilter | None = None,
        priority: int = 0,
        name: str = "",
    ) -> Callable[[], None]:
        """
        Register an event handler.
        
        Args:
            handler: The handler function
            event_types: Event types to handle (None = all events)
            filter: Optional filter for fine-grained event matching
            priority: Handler priority (higher = called first)
            name: Optional handler name for debugging
        
        Returns:
            A function to unregister this handler
        """
        if event_types is None:
            types_list = None
        elif isinstance(event_types, EventType):
            types_list = [event_types]
        else:
            types_list = event_types
        
        registration = HandlerRegistration(
            handler=handler,
            filter=filter or EventFilter(event_types=types_list),
            priority=priority,
            name=name or handler.__name__,
        )
        
        if types_list is None:
            # Global handler for all events
            self._global_handlers.append(registration)
            self._global_handlers.sort()
        else:
            # Register for specific event types
            for event_type in types_list:
                self._handlers[event_type].append(registration)
                self._handlers[event_type].sort()
        
        logger.debug(f"Registered handler: {registration.name}")
        
        def unregister():
            if types_list is None:
                if registration in self._global_handlers:
                    self._global_handlers.remove(registration)
            else:
                for event_type in types_list:
                    if registration in self._handlers[event_type]:
                        self._handlers[event_type].remove(registration)
        
        return unregister
    
    async def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all matching handlers.
        
        Handlers are called in priority order. The event can be cancelled
        or have propagation stopped by handlers.
        """
        # Collect matching handlers
        handlers: list[HandlerRegistration] = []
        
        # Add global handlers
        for reg in self._global_handlers:
            if reg.enabled and reg.filter.matches(event):
                handlers.append(reg)
        
        # Add type-specific handlers
        for reg in self._handlers.get(event.event_type, []):
            if reg.enabled and reg.filter.matches(event):
                handlers.append(reg)
        
        # Sort by priority (highest first)
        handlers.sort()
        
        # Invoke handlers
        for registration in handlers:
            if event.is_propagation_stopped:
                break
            
            try:
                result = registration.handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception(
                    f"Error in handler {registration.name}: {e}"
                )
    
    async def emit(self, event: Event) -> None:
        """
        Emit an event to the queue for async processing.
        
        Use this for events that don't need immediate handling.
        """
        await self._event_queue.put(event)
    
    def emit_sync(self, event: Event) -> None:
        """
        Emit an event synchronously (non-blocking queue put).
        
        Use from sync contexts that need to emit events.
        """
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
    
    async def dispatch_immediate(self, event: Event) -> None:
        """
        Dispatch an event immediately, bypassing the queue.
        
        Use for events that need immediate handling.
        """
        await self.dispatch(event)
    
    async def _dispatch_loop(self) -> None:
        """Main dispatch loop that processes queued events."""
        while self._running:
            try:
                # Wait for event with timeout to allow shutdown
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self.dispatch(event)
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in dispatch loop: {e}")
    
    def get_handler_count(self) -> int:
        """Get the total number of registered handlers."""
        count = len(self._global_handlers)
        for handlers in self._handlers.values():
            count += len(handlers)
        return count
    
    def get_handlers_for_type(
        self,
        event_type: EventType,
    ) -> list[HandlerRegistration]:
        """Get all handlers for a specific event type."""
        handlers = list(self._global_handlers)
        handlers.extend(self._handlers.get(event_type, []))
        handlers.sort()
        return handlers
