"""
AetherPackBot Kernel - Core application kernel and lifecycle management.

The kernel is the central orchestrator of the application, responsible for:
- Dependency injection and service container management
- Component lifecycle management (boot, run, shutdown)
- Configuration loading and validation
- Event dispatching and routing
"""

from aetherpackbot.core.kernel.app_kernel import ApplicationKernel
from aetherpackbot.core.kernel.container import ServiceContainer
from aetherpackbot.core.kernel.lifecycle import LifecycleManager, LifecycleState

__all__ = [
    "ApplicationKernel",
    "ServiceContainer",
    "LifecycleManager",
    "LifecycleState",
]
