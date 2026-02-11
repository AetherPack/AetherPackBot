from threading import RLock
from typing import Dict, List
import logging


class PluginError(Exception):
    """插件相关异常基类"""

    pass


class PluginValidationError(PluginError):
    """插件验证错误"""

    pass


class PluginNotFoundError(PluginError):
    """插件未找到错误"""

    pass


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self.plugins: Dict[str, Dict] = {}
        self._plugins_lock = RLock()

    def add_plugin(self, plugin_data: Dict) -> bool:
        """添加插件"""
        try:
            # 验证必要字段
            if "name" not in plugin_data or "author" not in plugin_data:
                raise PluginValidationError("缺少必要的插件信息: name 和 author")

            plugin_name = plugin_data["name"]
            with self._plugins_lock:
                self.plugins[plugin_name] = {
                    "name": plugin_name,
                    "author": plugin_data["author"],
                    "status": "active",
                }
            logging.info(f"成功注册插件: {plugin_name} by {plugin_data['author']}")
            return True

        except PluginError:
            raise
        except Exception as e:
            logging.error(f"注册插件失败: {e}")
            raise PluginError(f"内部错误: {str(e)}")

    def get_plugins(self) -> List[Dict]:
        """获取所有插件"""
        with self._plugins_lock:
            return [plugin.copy() for plugin in self.plugins.values()]

    def remove_plugin(self, name: str) -> bool:
        """移除插件"""
        with self._plugins_lock:
            if name in self.plugins:
                del self.plugins[name]
                logging.info(f"已移除插件: {name}")
                return True
            return False

    def get_plugin(self, name: str) -> Dict:
        """获取单个插件"""
        with self._plugins_lock:
            plugin = self.plugins.get(name)
        if plugin is None:
            raise PluginNotFoundError(f"插件 {name} 未找到")
        return plugin.copy()
