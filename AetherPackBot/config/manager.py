"""
配置管理器 - 读写和合并配置
Config manager - reads, writes, and merges configuration.

使用 JSON 文件存储，支持默认值合并和嵌套键访问。
Uses JSON file storage with default value merging and nested key access.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join("data", "config", "aether_config.json")


class ConfigManager:
    """
    配置管理器 - 框架的配置中心
    Config manager - the configuration center of the framework.

    支持：
    - 嵌套键访问（如 "web.port"）
    - 默认值自动合并
    - 持久化到 JSON 文件
    """

    def __init__(
        self,
        defaults: dict[str, Any] | None = None,
        config_path: str = CONFIG_FILE,
    ) -> None:
        self._defaults = defaults or {}
        self._config: dict[str, Any] = {}
        self._config_path = config_path

    async def load(self) -> None:
        """
        加载配置文件
        Load configuration file.
        """
        os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info("配置已从 %s 加载", self._config_path)
            except (json.JSONDecodeError, OSError):
                logger.warning("加载配置失败，使用默认值")
                self._config = {}
        else:
            self._config = {}
            logger.info("未找到配置文件，将创建默认配置")

        # 合并默认值
        self._merge_defaults(self._config, self._defaults)
        await self.save()

    async def save(self) -> None:
        """
        保存配置到文件
        Save configuration to file.
        """
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.exception("保存配置失败")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持嵌套键，如 "web.port"）
        Get config value (supports nested keys like "web.port").
        """
        keys = key.split(".")
        current = self._config
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                return default
            if current is None:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值（支持嵌套键）
        Set config value (supports nested keys).
        """
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        """获取完整配置字典 / Get the full config dictionary."""
        return dict(self._config)

    def _merge_defaults(self, config: dict[str, Any], defaults: dict[str, Any]) -> None:
        """
        递归合并默认值到配置中（不覆盖已有值）
        Recursively merge defaults into config (does not overwrite existing).
        """
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
            elif isinstance(default_value, dict) and isinstance(config[key], dict):
                self._merge_defaults(config[key], default_value)
