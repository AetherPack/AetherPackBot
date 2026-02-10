"""`AetherPackBot.core` 下的内核兼容导出模块。"""

from AetherPackBot.core.app_kernel import ApplicationKernel
from AetherPackBot.core.container import ServiceContainer
from AetherPackBot.core.lifecycle import LifecycleManager, LifecycleState

__all__ = [
    "ApplicationKernel",
    "ServiceContainer",
    "LifecycleManager",
    "LifecycleState",
]
