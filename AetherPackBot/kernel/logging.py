"""
Logging System - Centralized logging management.

Provides colored console logging and file logging with log rotation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import colorlog


@dataclass
class LogRecord:
    """Represents a log entry for broadcasting."""
    
    timestamp: datetime
    level: str
    logger_name: str
    message: str
    extra: dict | None = None


class LogBroker:
    """
    Log message broker for real-time log streaming.
    
    Maintains a circular buffer of recent logs and broadcasts to subscribers.
    """
    
    def __init__(self, max_buffer: int = 1000) -> None:
        self._buffer: deque[LogRecord] = deque(maxlen=max_buffer)
        self._subscribers: list[Callable[[LogRecord], None]] = []
        self._lock = asyncio.Lock()
    
    async def publish(self, record: LogRecord) -> None:
        """Publish a log record to all subscribers."""
        async with self._lock:
            self._buffer.append(record)
        
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(record)
                else:
                    subscriber(record)
            except Exception:
                pass
    
    def subscribe(self, callback: Callable[[LogRecord], None]) -> Callable[[], None]:
        """
        Subscribe to log messages.
        
        Returns a function to unsubscribe.
        """
        self._subscribers.append(callback)
        
        def unsubscribe():
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        
        return unsubscribe
    
    def get_recent(self, count: int = 100) -> list[LogRecord]:
        """Get the most recent log records."""
        return list(self._buffer)[-count:]


class BrokerHandler(logging.Handler):
    """Handler that forwards log records to a LogBroker."""
    
    def __init__(self, broker: LogBroker) -> None:
        super().__init__()
        self._broker = broker
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the broker."""
        log_record = LogRecord(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            logger_name=record.name,
            message=self.format(record),
        )
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._broker.publish(log_record))
            else:
                loop.run_until_complete(self._broker.publish(log_record))
        except RuntimeError:
            # No event loop - skip broker publishing
            pass


class LogManager:
    """
    Centralized logging configuration and management.
    
    Provides consistent formatting across all loggers with support for:
    - Colored console output
    - File logging with rotation
    - Real-time log streaming via broker
    """
    
    _instance: LogManager | None = None
    _initialized: bool = False
    
    def __new__(cls) -> LogManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if LogManager._initialized:
            return
        
        LogManager._initialized = True
        self._loggers: dict[str, logging.Logger] = {}
        self._broker = LogBroker()
        from AetherPackBot.kernel.paths import get_log_dir
        self._log_dir = get_log_dir()
        self._log_level = logging.INFO
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Configure the root logger with colored output."""
        # Ensure log directory exists
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Console handler with colors
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s%(reset)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "green",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(self._log_level)
        
        # File handler with rotation
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        log_file = self._log_dir / "AetherPackBot.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Broker handler
        broker_handler = BrokerHandler(self._broker)
        broker_handler.setFormatter(file_formatter)
        broker_handler.setLevel(logging.INFO)
        
        # Configure root logger
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(console_handler)
        root.addHandler(file_handler)
        root.addHandler(broker_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]
    
    def set_level(self, level: int | str) -> None:
        """Set the logging level for all handlers."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        
        self._log_level = level
        root = logging.getLogger()
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)
    
    @property
    def broker(self) -> LogBroker:
        """Get the log broker for real-time streaming."""
        return self._broker
    
    def configure_from_settings(self, settings: dict) -> None:
        """Configure logging from application settings."""
        if "level" in settings:
            self.set_level(settings["level"])
        
        if "log_dir" in settings:
            self._log_dir = Path(settings["log_dir"])
            self._log_dir.mkdir(parents=True, exist_ok=True)


# Global log manager instance
_log_manager: LogManager | None = None


def get_log_manager() -> LogManager:
    """Get the global log manager instance."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return get_log_manager().get_logger(name)
