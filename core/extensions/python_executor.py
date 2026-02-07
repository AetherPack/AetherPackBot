"""
Python Executor Extension - Execute Python code safely.

Provides a sandboxed environment for running Python code.
"""

from __future__ import annotations

import ast
import asyncio
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import TYPE_CHECKING, Any

from core.api.plugins import Plugin, PluginMetadata, PluginStatus
from core.api.agents import Tool, ToolParameter, ToolResult

if TYPE_CHECKING:
    from core.kernel.container import ServiceContainer


FORBIDDEN_IMPORTS = {
    "os", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests",
    "ctypes", "multiprocessing", "threading",
    "_thread", "signal", "resource",
    "builtins", "__builtins__",
}

ALLOWED_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool",
    "bytes", "callable", "chr", "complex", "dict",
    "divmod", "enumerate", "filter", "float", "format",
    "frozenset", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max",
    "min", "next", "oct", "ord", "pow", "print",
    "range", "repr", "reversed", "round", "set",
    "slice", "sorted", "str", "sum", "tuple", "type",
    "zip",
}


class PythonExecutorExtension(Plugin):
    """
    Python code executor extension.
    
    Provides sandboxed Python code execution with safety restrictions.
    """
    
    def __init__(self) -> None:
        self._status = PluginStatus.LOADED
        self._container: ServiceContainer | None = None
        self._max_execution_time: float = 10.0
        self._max_output_length: int = 4096
    
    @property
    def name(self) -> str:
        return "python_executor"
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="python_executor",
            version="1.0.0",
            description="Execute Python code safely",
            author="AetherPackBot",
            dependencies=[],
            entry_point="",
        )
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @property
    def is_builtin(self) -> bool:
        return True
    
    async def initialize(self, container: "ServiceContainer") -> None:
        """Initialize the extension."""
        self._container = container
        self._status = PluginStatus.LOADED
        
        try:
            from core.storage.config import ConfigurationManager
            config = await container.resolve(ConfigurationManager)
            self._max_execution_time = config.get("python_executor.max_time", 10.0)
            self._max_output_length = config.get("python_executor.max_output", 4096)
        except Exception:
            pass
    
    async def activate(self) -> None:
        """Activate the extension."""
        self._status = PluginStatus.RUNNING
    
    async def deactivate(self) -> None:
        """Deactivate the extension."""
        self._status = PluginStatus.LOADED
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._status = PluginStatus.UNLOADED
    
    def get_tool(self) -> Tool:
        """Get the Python execution tool."""
        return Tool(
            name="run_python",
            description="Execute Python code and return the output. "
                        "Use this for calculations, data processing, or any Python task.",
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                    required=True,
                ),
            ],
            handler=self.execute,
            enabled=True,
        )
    
    async def execute(self, code: str) -> ToolResult:
        """
        Execute Python code safely.
        
        Args:
            code: Python code to execute.
            
        Returns:
            Tool result with execution output.
        """
        # Validate code safety
        try:
            self._validate_code(code)
        except ValueError as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
        
        # Execute in thread pool with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self._execute_code,
                    code,
                ),
                timeout=self._max_execution_time,
            )
            
            return ToolResult(
                success=not result.get("error"),
                output=result.get("output"),
                error=result.get("error"),
            )
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error=f"Execution timed out after {self._max_execution_time}s",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    def _validate_code(self, code: str) -> None:
        """
        Validate code for safety.
        
        Raises:
            ValueError: If code contains forbidden constructs.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}")
        
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        if module in FORBIDDEN_IMPORTS:
                            raise ValueError(f"Import of '{module}' is not allowed")
                else:
                    module = (node.module or "").split(".")[0]
                    if module in FORBIDDEN_IMPORTS:
                        raise ValueError(f"Import of '{module}' is not allowed")
            
            # Check function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in ("exec", "eval", "compile", "__import__", "open"):
                        raise ValueError(f"Call to '{name}' is not allowed")
                
                elif isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    if attr in ("system", "popen", "spawn"):
                        raise ValueError(f"Call to '{attr}' is not allowed")
            
            # Check attribute access
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    raise ValueError(f"Access to private attribute '{node.attr}' is not allowed")
    
    def _execute_code(self, code: str) -> dict[str, Any]:
        """
        Execute code in sandboxed environment.
        
        Returns:
            Dict with 'output' and/or 'error' keys.
        """
        # Create restricted builtins
        safe_builtins = {
            name: getattr(__builtins__ if isinstance(__builtins__, dict) else vars(__builtins__), name, None)
            for name in ALLOWED_BUILTINS
        }
        
        # Add safe imports
        import math
        import json
        import datetime
        import random
        import re
        import collections
        import itertools
        import functools
        import statistics
        
        safe_globals = {
            "__builtins__": safe_builtins,
            "math": math,
            "json": json,
            "datetime": datetime,
            "random": random,
            "re": re,
            "collections": collections,
            "itertools": itertools,
            "functools": functools,
            "statistics": statistics,
        }
        
        safe_locals: dict[str, Any] = {}
        
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(code, safe_globals, safe_locals)
            
            output = stdout.getvalue()
            error = stderr.getvalue()
            
            # Truncate if too long
            if len(output) > self._max_output_length:
                output = output[:self._max_output_length] + "\n... (output truncated)"
            
            if error:
                return {"output": output, "error": error}
            
            return {"output": output or "(no output)"}
        
        except Exception as e:
            tb = traceback.format_exc()
            return {"output": stdout.getvalue(), "error": f"{type(e).__name__}: {e}\n{tb}"}
