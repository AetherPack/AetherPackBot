"""
包加载器 - 发现、加载和管理扩展包
Pack loader - discovers, loads, and manages extension packs.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from typing import TYPE_CHECKING, Any

from AetherPackBot.kernel.middleware import ProcessingContext
from AetherPackBot.pack.base import Pack
from AetherPackBot.pack.hooks import (
    HookDescriptor,
    HookKind,
    get_all_hooks,
    match_command,
    match_regex,
)
from AetherPackBot.pack.manifest import PackManifest

if TYPE_CHECKING:
    from AetherPackBot.kernel.container import ServiceContainer

logger = logging.getLogger(__name__)


class PackLoader:
    """
    包加载器 - 扫描、加载和管理扩展包
    Pack loader - scans, loads, and manages extension packs.
    """

    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        # 已加载的包实例: pack_name -> Pack
        self._packs: dict[str, Pack] = {}
        # 包的钩子: pack_name -> [HookDescriptor]
        self._pack_hooks: dict[str, list[HookDescriptor]] = {}
        # 搜索路径
        self._search_paths: list[str] = [
            os.path.join("data", "packs"),
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "pack",
                "builtin",
            ),
        ]

    async def discover_and_load(self) -> None:
        """
        发现并加载所有扩展包
        Discover and load all extension packs.
        """
        for search_path in self._search_paths:
            if not os.path.isdir(search_path):
                os.makedirs(search_path, exist_ok=True)
                continue

            for entry in os.listdir(search_path):
                pack_dir = os.path.join(search_path, entry)
                if not os.path.isdir(pack_dir):
                    continue

                try:
                    await self._load_pack(pack_dir)
                except Exception:
                    logger.exception("加载扩展包失败: %s", pack_dir)

        logger.info("已加载 %d 个扩展包", len(self._packs))

    async def _load_pack(self, pack_dir: str) -> None:
        """
        加载单个扩展包
        Load a single extension pack.
        """
        # 查找清单文件
        manifest_path = None
        for filename in ("manifest.json", "metadata.yaml", "metadata.yml"):
            candidate = os.path.join(pack_dir, filename)
            if os.path.exists(candidate):
                manifest_path = candidate
                break

        if manifest_path is None:
            # 没有清单，尝试使用目录名作为包名
            manifest = PackManifest(
                name=os.path.basename(pack_dir),
                directory=pack_dir,
            )
        else:
            manifest = PackManifest.from_file(manifest_path)
            manifest.directory = pack_dir

        if not manifest.name:
            manifest.name = os.path.basename(pack_dir)

        if not manifest.activated:
            logger.info("扩展包 %s 已停用，跳过加载", manifest.name)
            return

        # 动态加载模块
        module_name = manifest.entry_module
        module_path = os.path.join(pack_dir, f"{module_name}.py")

        if not os.path.exists(module_path):
            # 尝试 __init__.py
            module_path = os.path.join(pack_dir, module_name, "__init__.py")

        if not os.path.exists(module_path):
            logger.warning("扩展包 %s 未找到入口模块", manifest.name)
            return

        # 将包目录加入 sys.path
        if pack_dir not in sys.path:
            sys.path.insert(0, pack_dir)

        # 加载模块
        spec = importlib.util.spec_from_file_location(
            f"aether_pack_{manifest.name}", module_path
        )
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 查找 Pack 子类
        pack_cls = None
        if manifest.entry_class:
            pack_cls = getattr(module, manifest.entry_class, None)
        else:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Pack)
                    and attr is not Pack
                ):
                    pack_cls = attr
                    break

        if pack_cls is None:
            logger.warning("扩展包 %s 中未找到 Pack 子类", manifest.name)
            return

        # 实例化
        pack_instance = pack_cls(self._container, manifest)
        await pack_instance.on_load()

        self._packs[manifest.name] = pack_instance

        # 收集该包注册的钩子
        hooks = []
        for h in get_all_hooks():
            if not h.pack_name:
                # 未绑定包名的钩子，检查是否属于刚加载的模块
                handler_module = getattr(h.handler, "__module__", "")
                if handler_module == module.__name__ or handler_module.startswith(
                    f"aether_pack_{manifest.name}"
                ):
                    h.pack_name = manifest.name
                    hooks.append(h)

        self._pack_hooks[manifest.name] = hooks
        logger.info(
            "已加载扩展包: %s v%s (%d 个钩子)",
            manifest.name,
            manifest.version,
            len(hooks),
        )

    async def dispatch(self, ctx: ProcessingContext) -> bool:
        """
        将消息分发给匹配的扩展包处理器
        Dispatch message to matching pack handlers.

        返回是否有任何处理器处理了消息。
        Returns whether any handler processed the message.
        """
        event = ctx.event
        if event is None:
            return False

        text = ctx.store.get("stripped_text") or getattr(event, "plain_text", "")
        handled = False

        # 收集所有活跃的钩子并排序
        all_hooks: list[HookDescriptor] = []
        for pack_name, hooks in self._pack_hooks.items():
            pack = self._packs.get(pack_name)
            if pack is None or not pack.enabled:
                continue
            all_hooks.extend(h for h in hooks if h.enabled)

        all_hooks.sort(key=lambda h: h.priority)

        for h in all_hooks:
            try:
                if h.kind == HookKind.COMMAND:
                    matched, args = match_command(text, h.pattern)
                    if matched:
                        ctx.store["command_args"] = args
                        result = h.handler(event, ctx)
                        if hasattr(result, "__await__"):
                            result = await result
                        if result is not None:
                            ctx.response = result
                        handled = True
                        ctx.store["call_intellect"] = False
                        break

                elif h.kind == HookKind.REGEX:
                    match = match_regex(text, h.pattern)
                    if match:
                        ctx.store["regex_match"] = match
                        result = h.handler(event, ctx)
                        if hasattr(result, "__await__"):
                            result = await result
                        if result is not None:
                            ctx.response = result
                        handled = True
                        break

                elif h.kind == HookKind.MESSAGE:
                    result = h.handler(event, ctx)
                    if hasattr(result, "__await__"):
                        result = await result
                    if result is not None:
                        ctx.response = result
                        handled = True

            except Exception:
                logger.exception(
                    "扩展包 %s 的钩子 %s 执行出错",
                    h.pack_name,
                    h.pattern or h.kind.value,
                )

        return handled

    async def unload_pack(self, pack_name: str) -> bool:
        """
        卸载扩展包
        Unload an extension pack.
        """
        pack = self._packs.get(pack_name)
        if pack is None:
            return False

        await pack.on_unload()
        del self._packs[pack_name]
        self._pack_hooks.pop(pack_name, None)
        logger.info("已卸载扩展包: %s", pack_name)
        return True

    async def reload_pack(self, pack_name: str) -> bool:
        """
        重载扩展包
        Reload an extension pack.
        """
        pack = self._packs.get(pack_name)
        if pack is None:
            return False

        pack_dir = pack.manifest.directory
        await self.unload_pack(pack_name)
        await self._load_pack(pack_dir)
        return True

    def list_packs(self) -> list[dict[str, Any]]:
        """
        获取所有包的信息列表
        Get info list of all packs.
        """
        result = []
        for name, pack in self._packs.items():
            info = pack.manifest.to_dict()
            info["enabled"] = pack.enabled
            info["hook_count"] = len(self._pack_hooks.get(name, []))
            result.append(info)
        return result
