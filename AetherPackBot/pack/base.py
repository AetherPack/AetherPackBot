"""
扩展包基类 - 所有扩展包的父类
Pack base - parent of all extension packs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from AetherPackBot.kernel.container import ServiceContainer
    from AetherPackBot.pack.manifest import PackManifest

logger = logging.getLogger(__name__)


class Pack:
    """
    扩展包基类 - 所有用户/内置扩展包继承此类
    Pack base - all user/builtin extension packs inherit from this.

    生命周期：
    1. __init__(container, manifest) - 构造
    2. on_load() - 加载时调用
    3. on_unload() - 卸载时调用

    处理器通过装饰器（hooks.py）注册到全局注册表。
    Handlers are registered to the global registry via decorators (hooks.py).
    """

    def __init__(self, container: ServiceContainer, manifest: PackManifest) -> None:
        self._container = container
        self._manifest = manifest
        self._enabled = True

    @property
    def manifest(self) -> PackManifest:
        """获取包清单 / Get pack manifest."""
        return self._manifest

    @property
    def name(self) -> str:
        """包名 / Pack name."""
        return self._manifest.name

    @property
    def enabled(self) -> bool:
        """是否启用 / Whether enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    async def on_load(self) -> None:
        """
        加载时调用 - 可在此处进行初始化
        Called on load - perform initialization here.
        """
        pass

    async def on_unload(self) -> None:
        """
        卸载时调用 - 可在此处进行清理
        Called on unload - perform cleanup here.
        """
        pass

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取包配置
        Get pack configuration.
        """
        try:
            config_mgr = await self._container.resolve_by_name("config")
            pack_config = config_mgr.get(f"packs.{self.name}", {})
            return pack_config.get(key, default)
        except KeyError:
            return default

    async def set_config(self, key: str, value: Any) -> None:
        """
        设置包配置
        Set pack configuration.
        """
        try:
            config_mgr = await self._container.resolve_by_name("config")
            pack_config = config_mgr.get(f"packs.{self.name}", {})
            pack_config[key] = value
            config_mgr.set(f"packs.{self.name}", pack_config)
            await config_mgr.save()
        except KeyError:
            logger.warning("配置管理器不可用")
