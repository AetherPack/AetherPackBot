"""
路径工具 - 管理框架的文件路径
Path utility - manages framework file paths.
"""

from __future__ import annotations

import os


def get_data_path() -> str:
    """获取数据目录路径 / Get data directory path."""
    path = os.environ.get("AETHER_DATA_PATH", "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_config_path() -> str:
    """获取配置目录路径 / Get config directory path."""
    path = os.path.join(get_data_path(), "config")
    os.makedirs(path, exist_ok=True)
    return path


def get_packs_path() -> str:
    """获取扩展包目录路径 / Get packs directory path."""
    path = os.path.join(get_data_path(), "packs")
    os.makedirs(path, exist_ok=True)
    return path


def get_temp_path() -> str:
    """获取临时文件目录路径 / Get temp directory path."""
    path = os.path.join(get_data_path(), "temp")
    os.makedirs(path, exist_ok=True)
    return path


def get_logs_path() -> str:
    """获取日志目录路径 / Get logs directory path."""
    path = os.path.join(get_data_path(), "logs")
    os.makedirs(path, exist_ok=True)
    return path
