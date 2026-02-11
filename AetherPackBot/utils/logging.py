"""
日志工具 - 配置日志系统
Logging utility - configures the logging system.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 日志颜色映射
COLORS = {
    "DEBUG": "\033[36m",  # 青色
    "INFO": "\033[32m",  # 绿色
    "WARNING": "\033[33m",  # 黄色
    "ERROR": "\033[31m",  # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m",  # 重置
}


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器 / Colored log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        level_name = record.levelname
        color = COLORS.get(level_name, COLORS["RESET"])
        reset = COLORS["RESET"]
        record.levelname = f"{color}{level_name}{reset}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """
    配置日志系统
    Configure the logging system.
    """
    root_logger = logging.getLogger("AetherPackBot")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台输出（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_fmt = ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # 文件输出（可选）
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)

    root_logger.info("日志系统已初始化 (级别=%s)", level)


class LogBroadcaster:
    """
    日志广播器 - 将日志发送给多个订阅者（如 WebSocket 客户端）
    Log broadcaster - sends logs to multiple subscribers (e.g., WebSocket clients).
    """

    def __init__(self) -> None:
        self._subscribers: list[logging.Handler] = []

    def subscribe(self, handler: logging.Handler) -> None:
        """添加订阅者 / Add subscriber."""
        root_logger = logging.getLogger("AetherPackBot")
        root_logger.addHandler(handler)
        self._subscribers.append(handler)

    def unsubscribe(self, handler: logging.Handler) -> None:
        """移除订阅者 / Remove subscriber."""
        root_logger = logging.getLogger("AetherPackBot")
        root_logger.removeHandler(handler)
        if handler in self._subscribers:
            self._subscribers.remove(handler)
