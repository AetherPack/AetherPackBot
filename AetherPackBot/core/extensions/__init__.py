"""
Extensions Package - Built-in extensions and plugins.
"""

from .core import CoreExtension
from .python_executor import PythonExecutorExtension
from .web_search import WebSearchExtension

__all__ = [
    "CoreExtension",
    "PythonExecutorExtension",
    "WebSearchExtension",
]
