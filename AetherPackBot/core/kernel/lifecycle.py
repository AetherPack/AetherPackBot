"""
Lifecycle Manager - Component lifecycle state management.

Manages the lifecycle states of application components:
- Created -> Initializing -> Running -> Stopping -> Stopped
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol, runtime_checkable


class LifecycleState(Enum):
    """Represents the current state of a component in its lifecycle."""
    
    CREATED = auto()       # Instance created, not yet initialized
    INITIALIZING = auto()  # Currently initializing
    RUNNING = auto()       # Actively running
    STOPPING = auto()      # Currently stopping
    STOPPED = auto()       # Completely stopped
    FAILED = auto()        # Failed during lifecycle transition


@runtime_checkable
class LifecycleAware(Protocol):
    """Protocol for components that participate in lifecycle management."""
    
    @property
    def state(self) -> LifecycleState:
        """Get the current lifecycle state."""
        ...
    
    async def start(self) -> None:
        """Start the component."""
        ...
    
    async def stop(self) -> None:
        """Stop the component."""
        ...


@dataclass
class LifecycleEvent:
    """Represents a lifecycle state transition event."""
    
    component: Any
    previous_state: LifecycleState
    new_state: LifecycleState
    error: Exception | None = None


@dataclass
class ManagedComponent:
    """Wrapper for a component managed by the lifecycle manager."""
    
    component: Any
    priority: int = 0
    state: LifecycleState = LifecycleState.CREATED
    error: Exception | None = None
    dependencies: list[type] = field(default_factory=list)


class LifecycleManager:
    """
    Manages the lifecycle of application components.
    
    Components are started in dependency order and stopped in reverse order.
    Supports async start/stop operations with timeout handling.
    """
    
    def __init__(self) -> None:
        self._components: list[ManagedComponent] = []
        self._listeners: list[callable] = []
        self._lock = asyncio.Lock()
        self._state = LifecycleState.CREATED
    
    @property
    def state(self) -> LifecycleState:
        """Get the current state of the lifecycle manager."""
        return self._state
    
    def register(
        self,
        component: Any,
        priority: int = 0,
        dependencies: list[type] | None = None,
    ) -> None:
        """
        Register a component for lifecycle management.
        
        Args:
            component: The component to manage
            priority: Higher priority components start first (default: 0)
            dependencies: List of component types this component depends on
        """
        managed = ManagedComponent(
            component=component,
            priority=priority,
            dependencies=dependencies or [],
        )
        self._components.append(managed)
        # Sort by priority (higher first)
        self._components.sort(key=lambda c: -c.priority)
    
    def register_listener(self, callback: callable) -> None:
        """Register a callback to be notified of lifecycle events."""
        self._listeners.append(callback)
    
    async def start_all(self, timeout: float = 60.0) -> None:
        """
        Start all registered components in dependency order.
        
        Args:
            timeout: Maximum time to wait for all components to start
        """
        async with self._lock:
            self._state = LifecycleState.INITIALIZING
            
            try:
                for managed in self._components:
                    await self._start_component(managed, timeout=timeout / len(self._components))
                
                self._state = LifecycleState.RUNNING
            except Exception as e:
                self._state = LifecycleState.FAILED
                raise LifecycleError(f"Failed to start components: {e}") from e
    
    async def stop_all(self, timeout: float = 30.0) -> None:
        """
        Stop all registered components in reverse order.
        
        Args:
            timeout: Maximum time to wait for all components to stop
        """
        async with self._lock:
            self._state = LifecycleState.STOPPING
            
            # Stop in reverse order
            for managed in reversed(self._components):
                try:
                    await self._stop_component(managed, timeout=timeout / len(self._components))
                except Exception:
                    # Log but continue stopping other components
                    pass
            
            self._state = LifecycleState.STOPPED
    
    async def _start_component(
        self,
        managed: ManagedComponent,
        timeout: float,
    ) -> None:
        """Start a single component."""
        component = managed.component
        previous_state = managed.state
        managed.state = LifecycleState.INITIALIZING
        
        try:
            if hasattr(component, "start"):
                if asyncio.iscoroutinefunction(component.start):
                    await asyncio.wait_for(component.start(), timeout=timeout)
                else:
                    component.start()
            
            managed.state = LifecycleState.RUNNING
            await self._notify_listeners(LifecycleEvent(
                component=component,
                previous_state=previous_state,
                new_state=managed.state,
            ))
            
        except asyncio.TimeoutError as e:
            managed.state = LifecycleState.FAILED
            managed.error = e
            raise LifecycleError(
                f"Component {type(component).__name__} start timed out"
            ) from e
        except Exception as e:
            managed.state = LifecycleState.FAILED
            managed.error = e
            await self._notify_listeners(LifecycleEvent(
                component=component,
                previous_state=previous_state,
                new_state=managed.state,
                error=e,
            ))
            raise
    
    async def _stop_component(
        self,
        managed: ManagedComponent,
        timeout: float,
    ) -> None:
        """Stop a single component."""
        component = managed.component
        previous_state = managed.state
        managed.state = LifecycleState.STOPPING
        
        try:
            if hasattr(component, "stop"):
                if asyncio.iscoroutinefunction(component.stop):
                    await asyncio.wait_for(component.stop(), timeout=timeout)
                else:
                    component.stop()
            
            managed.state = LifecycleState.STOPPED
            await self._notify_listeners(LifecycleEvent(
                component=component,
                previous_state=previous_state,
                new_state=managed.state,
            ))
            
        except Exception as e:
            managed.error = e
            await self._notify_listeners(LifecycleEvent(
                component=component,
                previous_state=previous_state,
                new_state=LifecycleState.FAILED,
                error=e,
            ))
            raise
    
    async def _notify_listeners(self, event: LifecycleEvent) -> None:
        """Notify all registered listeners of a lifecycle event."""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception:
                # Don't let listener errors affect lifecycle
                pass
    
    def get_component(self, component_type: type) -> Any | None:
        """Get a managed component by its type."""
        for managed in self._components:
            if isinstance(managed.component, component_type):
                return managed.component
        return None
    
    def get_all_running(self) -> list[Any]:
        """Get all components that are currently running."""
        return [
            managed.component
            for managed in self._components
            if managed.state == LifecycleState.RUNNING
        ]


class LifecycleError(Exception):
    """Raised when a lifecycle operation fails."""
    pass
