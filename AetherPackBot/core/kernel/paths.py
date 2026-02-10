"""
AetherPackBot 路径管理模块

集中管理所有数据目录和文件路径，对标 AstrBot 的路径结构。
所有数据统一存放在 data/ 目录下。

目录结构:
    data/
    ├── config/              ← 配置目录
    │   └── config.json      ← 主配置文件
    ├── dist/                ← Dashboard 前端文件
    ├── plugins/             ← 用户插件
    ├── plugin_data/         ← 插件数据存储
    ├── temp/                ← 临时文件
    ├── logs/                ← 日志目录
    │   └── aetherpackbot.log
    ├── knowledge_base/      ← 知识库
    ├── backups/             ← 备份
    └── aetherpackbot.db     ← SQLite 数据库
"""

from __future__ import annotations

import os
from pathlib import Path


def get_root() -> Path:
    """获取项目根目录，支持环境变量 AETHERPACKBOT_ROOT 覆盖。"""
    root = os.environ.get("AETHERPACKBOT_ROOT", "")
    return Path(root) if root else Path.cwd()


def get_data_path() -> Path:
    """数据根目录: data/"""
    return get_root() / "data"


# ── 配置 ──

def get_config_dir() -> Path:
    """配置目录: data/config/"""
    return get_data_path() / "config"


def get_config_file() -> Path:
    """主配置文件: data/config/config.json"""
    return get_config_dir() / "config.json"


# ── 数据库 ──

def get_db_path() -> Path:
    """数据库文件: data/aetherpackbot.db"""
    return get_data_path() / "AetherPackBot.db"


def get_db_url() -> str:
    """SQLAlchemy 异步数据库 URL"""
    return f"sqlite+aiosqlite:///{get_db_path()}"


# ── 日志 ──

def get_log_dir() -> Path:
    """日志目录: data/logs/"""
    return get_data_path() / "logs"


def get_log_file() -> Path:
    """主日志文件: data/logs/aetherpackbot.log"""
    return get_log_dir() / "AetherPackBot.log"


# ── 插件 ──

def get_plugin_dir() -> Path:
    """插件目录: data/plugins/"""
    return get_data_path() / "plugins"


def get_plugin_data_dir() -> Path:
    """插件数据目录: data/plugin_data/"""
    return get_data_path() / "plugin_data"


# ── 前端 ──

def get_dashboard_dir() -> Path:
    """Dashboard 前端目录: data/dist/"""
    return get_data_path() / "dist"


# ── 临时与其他 ──

def get_temp_dir() -> Path:
    """临时文件目录: data/temp/"""
    return get_data_path() / "temp"


def get_knowledge_base_dir() -> Path:
    """知识库目录: data/knowledge_base/"""
    return get_data_path() / "knowledge_base"


def get_backups_dir() -> Path:
    """备份目录: data/backups/"""
    return get_data_path() / "backups"


# ── 启动时需要创建的所有目录 ──

REQUIRED_DIRS: list[Path] = [
    get_data_path(),
    get_config_dir(),
    get_plugin_dir(),
    get_plugin_data_dir(),
    get_temp_dir(),
    get_log_dir(),
    get_knowledge_base_dir(),
    get_backups_dir(),
]


def ensure_directories() -> None:
    """创建所有必需的数据目录。"""
    for d in REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)
