"""
Logging System - Centralized logging management.

参考 AstrBot 日志系统实现：
- 彩色控制台输出，格式: [HH:MM:SS] [Core/Plug] [INFO] [folder.file:line]: message
- 文件日志（无颜色），支持按大小轮转
- LogBroker 实时推送给 Dashboard

Filters:
- SourceTagFilter: 区分 [Core] / [Plug] 来源
- FileNameFilter: 修改文件名为 <folder>.<file> 格式
- LevelNameFilter: 级别缩写 DBUG/INFO/WARN/ERRO/CRIT
- VersionTagFilter: WARNING 及以上追加版本号标签
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

import colorlog


# ── 版本号 ──────────────────────────────────────────────────────────
try:
    from AetherPackBot.core import __version__ as VERSION
except ImportError:
    VERSION = "1.0.0"

# ── 日志缓存大小 ────────────────────────────────────────────────────
CACHED_SIZE = 500

# ── 颜色配置（参考 AstrBot） ────────────────────────────────────────
LOG_COLORS = {
    "DEBUG": "green",
    "INFO": "bold_green",
    "WARNING": "bold_yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
    "RESET": "reset",
    "asctime": "green",
}


# ── 工具函数 ────────────────────────────────────────────────────────

def _is_plugin_path(pathname: str) -> bool:
    """检查文件路径是否来自插件目录"""
    if not pathname:
        return False
    norm = os.path.normpath(pathname)
    return "data/plugins" in norm or "data\\plugins" in norm


def _get_short_level_name(level_name: str) -> str:
    """将日志级别名称转换为四个字母的缩写（参考 AstrBot）"""
    return {
        "DEBUG": "DBUG",
        "INFO": "INFO",
        "WARNING": "WARN",
        "ERROR": "ERRO",
        "CRITICAL": "CRIT",
    }.get(level_name, level_name[:4].upper())


# ── 日志过滤器（参考 AstrBot 四个 Filter）────────────────────────────

class SourceTagFilter(logging.Filter):
    """区分日志来源：[Core] 核心组件 / [Plug] 插件"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.source_tag = (  # type: ignore[attr-defined]
            "[Plug]" if _is_plugin_path(record.pathname) else "[Core]"
        )
        return True


class FileNameFilter(logging.Filter):
    """修改文件名为 <folder>.<file> 格式，去除 .py 后缀
    
    例如: /core/kernel/app_kernel.py → kernel.app_kernel
    """

    def filter(self, record: logging.LogRecord) -> bool:
        dirname = os.path.dirname(record.pathname)
        record.filename = (
            os.path.basename(dirname)
            + "."
            + os.path.basename(record.pathname).replace(".py", "")
        )
        return True


class LevelNameFilter(logging.Filter):
    """将日志级别名称转换为四个字母的缩写: DBUG/INFO/WARN/ERRO/CRIT"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.short_levelname = _get_short_level_name(record.levelname)  # type: ignore[attr-defined]
        return True


class VersionTagFilter(logging.Filter):
    """WARNING 及以上级别追加版本号标签 [vX.X.X]"""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            record.version_tag = f" [v{VERSION}]"  # type: ignore[attr-defined]
        else:
            record.version_tag = ""  # type: ignore[attr-defined]
        return True


# ── LogBroker（参考 AstrBot 发布-订阅模式）──────────────────────────

class LogBroker:
    """
    日志代理类，用于缓存和分发日志消息。
    
    维护一个环形缓冲区和订阅者队列列表，
    通过 SSE 将日志实时推送给 Dashboard 前端。
    """

    def __init__(self, max_buffer: int = CACHED_SIZE) -> None:
        self.log_cache: deque[dict[str, Any]] = deque(maxlen=max_buffer)
        self.subscribers: list[asyncio.Queue] = []

    def register(self) -> asyncio.Queue:
        """注册新的订阅者，返回一个带有日志缓存的队列"""
        q: asyncio.Queue = asyncio.Queue(maxsize=CACHED_SIZE + 10)
        self.subscribers.append(q)
        return q

    def unregister(self, q: asyncio.Queue) -> None:
        """取消订阅"""
        if q in self.subscribers:
            self.subscribers.remove(q)

    def publish(self, log_entry: dict[str, Any]) -> None:
        """发布日志到所有订阅者（非阻塞）"""
        self.log_cache.append(log_entry)
        for q in self.subscribers:
            try:
                q.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass

    def get_recent(self, count: int = 100) -> list[dict[str, Any]]:
        """获取最近的日志记录"""
        return list(self.log_cache)[-count:]


class LogQueueHandler(logging.Handler):
    """将日志消息发送到 LogBroker 的处理器"""

    def __init__(self, broker: LogBroker) -> None:
        super().__init__()
        self._broker = broker

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        self._broker.publish({
            "level": record.levelname,
            "time": time.time(),
            "logger": record.name,
            "message": log_entry,  # Raw message or formatted? The previous code used 'data' for formatted
            "data": log_entry,     # Keep 'data' for compatibility if needed, but 'message' is better
        })


# ── LogManager（参考 AstrBot LogManager 架构）───────────────────────

class LogManager:
    """
    日志管理器，提供统一的日志配置。
    
    日志格式（控制台，带颜色）:
        [14:30:05] [Core] [INFO] [kernel.app_kernel:130]: 启动成功
    
    日志格式（文件，无颜色）:
        [2026-02-07 14:30:05] [Core] [INFO] [kernel.app_kernel:130]: 启动成功
    """

    _FILE_HANDLER_FLAG = "_aetherpackbot_file_handler"
    _broker: LogBroker | None = None
    _initialized: bool = False
    _root_logger: logging.Logger | None = None

    @staticmethod
    def _attach_filters_to_handler(handler: logging.Handler) -> None:
        """为处理器添加标准过滤器"""
        handler.addFilter(SourceTagFilter())
        handler.addFilter(FileNameFilter())
        handler.addFilter(LevelNameFilter())
        handler.addFilter(VersionTagFilter())

    @classmethod
    def GetLogger(cls, log_name: str = "aetherpackbot") -> logging.Logger:
        """获取日志记录器（参考 AstrBot LogManager.GetLogger）"""
        logger = logging.getLogger(log_name)

        # 避免重复配置
        if logger.hasHandlers():
            return logger

        # 控制台处理器 + 彩色格式
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        console_formatter = colorlog.ColoredFormatter(
            fmt=(
                "%(log_color)s [%(asctime)s] %(source_tag)s "
                "[%(short_levelname)-4s]%(version_tag)s "
                "[%(filename)s:%(lineno)d]: %(message)s %(reset)s"
            ),
            datefmt="%H:%M:%S",
            log_colors=LOG_COLORS,
        )
        console_handler.setFormatter(console_formatter)

        # 添加过滤器到处理器
        cls._attach_filters_to_handler(console_handler)

        logger.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

        cls._root_logger = logger
        return logger

    @classmethod
    def set_queue_handler(cls, logger: logging.Logger, broker: LogBroker) -> None:
        """挂载 LogBroker 用于 Dashboard 实时推送"""
        cls._broker = broker
        handler = LogQueueHandler(broker)
        handler.setLevel(logging.DEBUG)

        # 添加过滤器到处理器
        cls._attach_filters_to_handler(handler)

        # 使用与控制台相同格式（不带颜色）
        formatter = logging.Formatter(
            "[%(asctime)s] %(source_tag)s [%(short_levelname)-4s]%(version_tag)s "
            "[%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    @classmethod
    def configure_file_logging(
        cls,
        logger: logging.Logger,
        log_dir: str | Path = "data/logs",
        max_mb: int = 10,
        backup_count: int = 3,
    ) -> None:
        """配置文件日志（RotatingFileHandler）"""
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "AetherPackBot.log"

        # 移除旧的文件处理器
        for handler in list(logger.handlers):
            if getattr(handler, cls._FILE_HANDLER_FLAG, False):
                logger.removeHandler(handler)
                handler.close()

        # 创建新的文件处理器
        max_bytes = max_mb * 1024 * 1024 if max_mb > 0 else 0
        if max_bytes > 0:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")

        file_handler.setLevel(logging.DEBUG)
        setattr(file_handler, cls._FILE_HANDLER_FLAG, True)
        
        # 添加过滤器到处理器
        cls._attach_filters_to_handler(file_handler)

        # 文件日志格式（无颜色，完整日期）
        file_formatter = logging.Formatter(
            "[%(asctime)s] %(source_tag)s [%(short_levelname)-4s]%(version_tag)s "
            "[%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    @classmethod
    def configure_from_settings(cls, logger: logging.Logger, settings: dict) -> None:
        """根据配置设置日志级别和文件日志"""
        level = settings.get("level", "INFO")
        try:
            logger.setLevel(level)
        except Exception:
            logger.setLevel(logging.INFO)

        log_dir = settings.get("log_dir", "data/logs")
        cls.configure_file_logging(logger, log_dir=log_dir)

    @classmethod
    def get_broker(cls) -> LogBroker | None:
        """获取 LogBroker 实例"""
        return cls._broker


# ── 全局便捷函数 ────────────────────────────────────────────────────

# 模块级 logger 实例（延迟初始化）
_root_logger: logging.Logger | None = None
_log_broker: LogBroker | None = None


def _ensure_initialized() -> logging.Logger:
    """确保日志系统已初始化"""
    global _root_logger
    if _root_logger is None:
        _root_logger = LogManager.GetLogger("aetherpackbot")
    return _root_logger


def get_logger(name: str) -> logging.Logger:
    """获取子 logger（如 get_logger("platforms") → aetherpackbot.platforms）
    
    子 logger 会继承父 logger 的 handler 和 filter。
    """
    _ensure_initialized()
    return logging.getLogger(f"AetherPackBot.{name}")


def get_log_manager() -> type[LogManager]:
    """获取 LogManager 类"""
    return LogManager


def get_log_broker() -> LogBroker:
    """获取或创建全局 LogBroker 实例"""
    global _log_broker
    if _log_broker is None:
        _log_broker = LogBroker()
    return _log_broker


def setup_logging(settings: dict | None = None) -> tuple[logging.Logger, LogBroker]:
    """一键初始化日志系统
    
    Returns:
        (logger, log_broker) 元组
    """
    logger = _ensure_initialized()
    broker = get_log_broker()
    LogManager.set_queue_handler(logger, broker)

    if settings:
        LogManager.configure_from_settings(logger, settings)
    else:
        LogManager.configure_file_logging(logger)

    return logger, broker
