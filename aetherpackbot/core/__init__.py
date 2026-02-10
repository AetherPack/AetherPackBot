"""
AetherPackBot - Multi-platform LLM Chatbot Framework

A modern, extensible chatbot framework supporting multiple messaging platforms
and LLM providers with a plugin-based architecture.
"""

__version__ = "1.0.0"
__author__ = "AetherPackBot Team"

from aetherpackbot.core.kernel import ApplicationKernel

__all__ = [
    "ApplicationKernel",
    "__version__",
]
