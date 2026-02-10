"""
Service Container - Dependency Injection Container

Provides a centralized service container for managing application dependencies
using the inversion of control pattern.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TypeVar, Generic

T = TypeVar("T")


class ServiceScope(Enum):
    """Defines the lifecycle scope of a registered service."""
    
    SINGLETON = auto()  # Single instance throughout application lifetime
    TRANSIENT = auto()  # New instance on every resolution
    SCOPED = auto()     # Single instance per scope context


@dataclass
class ServiceDescriptor:
    """Describes a registered service in the container."""
    
    service_type: type
    implementation: type | Callable[..., Any] | None = None
    instance: Any = None
    scope: ServiceScope = ServiceScope.SINGLETON
    factory: Callable[..., Any] | None = None
    dependencies: list[type] = field(default_factory=list)


class ServiceContainer:
    """
    Dependency injection container for managing service registration and resolution.
    
    Supports constructor injection with automatic dependency resolution.
    """
    
    def __init__(self) -> None:
        self._descriptors: dict[type, ServiceDescriptor] = {}
        self._resolved_singletons: dict[type, Any] = {}
        self._lock = asyncio.Lock()
        self._current_scope: dict[type, Any] = {}
    
    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        instance: T | None = None,
    ) -> ServiceContainer:
        """Register a singleton service (one instance per container)."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            instance=instance,
            scope=ServiceScope.SINGLETON,
        )
        self._descriptors[service_type] = descriptor
        if instance is not None:
            self._resolved_singletons[service_type] = instance
        return self
    
    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
    ) -> ServiceContainer:
        """Register a transient service (new instance per resolution)."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            scope=ServiceScope.TRANSIENT,
        )
        self._descriptors[service_type] = descriptor
        return self
    
    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[..., T],
        scope: ServiceScope = ServiceScope.SINGLETON,
    ) -> ServiceContainer:
        """Register a service with a custom factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            scope=scope,
        )
        self._descriptors[service_type] = descriptor
        return self
    
    def register_instance(self, service_type: type[T], instance: T) -> ServiceContainer:
        """Register a pre-created instance as a singleton."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            scope=ServiceScope.SINGLETON,
        )
        self._descriptors[service_type] = descriptor
        self._resolved_singletons[service_type] = instance
        return self
    
    async def resolve(self, service_type: type[T]) -> T:
        """Resolve a service by its type with automatic dependency injection."""
        async with self._lock:
            return await self._resolve_internal(service_type)
    
    async def _resolve_internal(self, service_type: type[T]) -> T:
        """Internal resolution logic."""
        if service_type not in self._descriptors:
            raise ServiceNotFoundError(f"Service {service_type.__name__} not registered")
        
        descriptor = self._descriptors[service_type]
        
        # Return cached singleton if available
        if descriptor.scope == ServiceScope.SINGLETON:
            if service_type in self._resolved_singletons:
                return self._resolved_singletons[service_type]
        
        # Return pre-created instance
        if descriptor.instance is not None:
            return descriptor.instance
        
        # Create using factory
        if descriptor.factory is not None:
            instance = await self._invoke_factory(descriptor.factory)
            if descriptor.scope == ServiceScope.SINGLETON:
                self._resolved_singletons[service_type] = instance
            return instance
        
        # Create using implementation constructor
        if descriptor.implementation is not None:
            instance = await self._create_instance(descriptor.implementation)
            if descriptor.scope == ServiceScope.SINGLETON:
                self._resolved_singletons[service_type] = instance
            return instance
        
        raise ServiceResolutionError(
            f"Cannot resolve service {service_type.__name__}: no implementation found"
        )
    
    async def _create_instance(self, implementation: type[T]) -> T:
        """Create an instance of the implementation with injected dependencies."""
        import inspect
        
        signature = inspect.signature(implementation.__init__)
        resolved_args: dict[str, Any] = {}
        
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation
                # Handle Optional types and other parameterized generics
                origin = getattr(param_type, "__origin__", None)
                if origin is not None:
                    # Skip generics like Optional, List, etc for now
                    if param.default != inspect.Parameter.empty:
                        resolved_args[name] = param.default
                    continue
                
                # Resolve the dependency if it's registered
                if param_type in self._descriptors:
                    resolved_args[name] = await self._resolve_internal(param_type)
                elif param.default != inspect.Parameter.empty:
                    resolved_args[name] = param.default
                else:
                    raise ServiceResolutionError(
                        f"Cannot resolve parameter '{name}' of type {param_type} "
                        f"for {implementation.__name__}"
                    )
            elif param.default != inspect.Parameter.empty:
                resolved_args[name] = param.default
        
        return implementation(**resolved_args)
    
    async def _invoke_factory(self, factory: Callable[..., T]) -> T:
        """Invoke a factory function with injected dependencies."""
        import inspect
        
        signature = inspect.signature(factory)
        resolved_args: dict[str, Any] = {}
        
        for name, param in signature.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation
                if param_type in self._descriptors:
                    resolved_args[name] = await self._resolve_internal(param_type)
                elif param.default != inspect.Parameter.empty:
                    resolved_args[name] = param.default
            elif param.default != inspect.Parameter.empty:
                resolved_args[name] = param.default
        
        result = factory(**resolved_args)
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    def is_registered(self, service_type: type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._descriptors
    
    def get_all_descriptors(self) -> dict[type, ServiceDescriptor]:
        """Get all registered service descriptors."""
        return self._descriptors.copy()
    
    async def dispose(self) -> None:
        """Dispose all singleton instances that support disposal."""
        for instance in self._resolved_singletons.values():
            # Skip self to avoid infinite recursion
            if instance is self:
                continue
            if hasattr(instance, "dispose"):
                if asyncio.iscoroutinefunction(instance.dispose):
                    await instance.dispose()
                else:
                    instance.dispose()
            elif hasattr(instance, "close"):
                if asyncio.iscoroutinefunction(instance.close):
                    await instance.close()
                else:
                    instance.close()
        
        self._resolved_singletons.clear()
        self._current_scope.clear()


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not registered."""
    pass


class ServiceResolutionError(Exception):
    """Raised when a service cannot be resolved due to dependency issues."""
    pass
