"""
包清单 - 描述扩展包的元数据
Pack manifest - describes extension pack metadata.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PackManifest:
    """
    包清单 - 从 manifest.json 或 metadata.yaml 加载
    Pack manifest - loaded from manifest.json or metadata.yaml.
    """

    # 包名（唯一标识）
    name: str = ""
    # 显示名称
    display_name: str = ""
    # 描述
    description: str = ""
    # 版本
    version: str = "0.1.0"
    # 作者
    author: str = ""
    # 仓库地址
    repository: str = ""
    # 入口模块（相对于包目录）
    entry_module: str = "main"
    # 入口类名
    entry_class: str = ""
    # 依赖列表
    dependencies: list[str] = field(default_factory=list)
    # 配置 Schema
    config_schema: dict[str, Any] = field(default_factory=dict)
    # 包目录路径
    directory: str = ""
    # 是否内置
    is_builtin: bool = False
    # 是否已激活
    activated: bool = True

    @classmethod
    def from_file(cls, file_path: str) -> PackManifest:
        """
        从文件加载清单
        Load manifest from file.
        """
        if not os.path.exists(file_path):
            return cls()

        with open(file_path, encoding="utf-8") as f:
            if file_path.endswith(".json"):
                data = json.load(f)
            elif file_path.endswith((".yaml", ".yml")):
                try:
                    import yaml

                    data = yaml.safe_load(f)
                except ImportError:
                    data = {}
            else:
                data = {}

        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", data.get("name", "")),
            description=data.get("description", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", ""),
            repository=data.get("repository", data.get("repo", "")),
            entry_module=data.get("entry_module", data.get("entry", "main")),
            entry_class=data.get("entry_class", ""),
            dependencies=data.get("dependencies", []),
            config_schema=data.get("config_schema", {}),
            directory=os.path.dirname(file_path),
        )

    def to_dict(self) -> dict[str, Any]:
        """转为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "repository": self.repository,
            "entry_module": self.entry_module,
            "entry_class": self.entry_class,
            "activated": self.activated,
            "is_builtin": self.is_builtin,
        }
